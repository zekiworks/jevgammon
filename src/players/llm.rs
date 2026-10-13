//! Chat-model players: OpenAI and Anthropic subscriptions, Gemini API keys, and
//! OpenAI-compatible local servers (Ollama, llama.cpp, LM Studio, vLLM).

use std::sync::Arc;
use std::time::Instant;

use anyhow::{Context, Result, anyhow};
use serde_json::{Value, json};

use super::prompt::{llm_system, llm_user, parse_choice};
use super::{Decision, DecisionRequest};
use crate::auth::Credentials;
use crate::db::Exchange;
use crate::http::{self, CallError};

const CODEX_URL: &str = "https://chatgpt.com/backend-api/codex/responses";
const ANTHROPIC_URL: &str = "https://api.anthropic.com/v1/messages";
const GEMINI_URL: &str = "https://generativelanguage.googleapis.com/v1beta";
/// Anthropic serves subscription tokens only when this is the first system block.
const CLAUDE_CODE_IDENTITY: &str = "You are Claude Code, Anthropic's official CLI for Claude.";
/// Model replies per decision before falling back to the first legal play.
const MAX_REPLIES: usize = 3;

enum Kind {
    OpenAiSubscription(Arc<Credentials>),
    AnthropicSubscription(Arc<Credentials>),
    Gemini(String),
    OpenAiCompatible {
        base_url: String,
        api_key: Option<String>,
    },
}

pub struct LlmClient {
    http: reqwest::Client,
    model: String,
    kind: Kind,
    session_id: String,
}

struct Completion {
    text: String,
    input_tokens: u64,
    output_tokens: u64,
}

fn schema() -> Value {
    json!({
        "type": "object",
        "properties": {"choice": {"type": "integer", "description": "Number of the chosen play"}},
        "required": ["choice"],
        "additionalProperties": false,
    })
}

fn tokens(value: &Value, pointer: &str) -> u64 {
    value.pointer(pointer).and_then(Value::as_u64).unwrap_or(0)
}

impl LlmClient {
    fn new(http: reqwest::Client, model: String, kind: Kind) -> Self {
        LlmClient {
            http,
            model,
            kind,
            session_id: uuid::Uuid::new_v4().to_string(),
        }
    }

    pub fn openai_subscription(
        http: reqwest::Client,
        model: String,
        creds: Arc<Credentials>,
    ) -> Self {
        Self::new(http, model, Kind::OpenAiSubscription(creds))
    }

    pub fn anthropic_subscription(
        http: reqwest::Client,
        model: String,
        creds: Arc<Credentials>,
    ) -> Self {
        Self::new(http, model, Kind::AnthropicSubscription(creds))
    }

    pub fn gemini(http: reqwest::Client, model: String, key: String) -> Self {
        Self::new(http, model, Kind::Gemini(key))
    }

    pub fn openai_compatible(
        http: reqwest::Client,
        model: String,
        base_url: String,
        api_key: Option<String>,
    ) -> Self {
        Self::new(http, model, Kind::OpenAiCompatible { base_url, api_key })
    }

    pub async fn decide(&self, req: &DecisionRequest<'_>) -> Result<Decision> {
        let count = req.notations.len();
        let system = llm_system(req);
        let prompt = llm_user(req);
        let mut user = prompt.clone();
        let mut decision = Decision {
            index: 0,
            fallback: false,
            exchanges: Vec::new(),
            input_tokens: 0,
            output_tokens: 0,
        };
        for _ in 0..MAX_REPLIES {
            let body = self.body(&system, &user);
            let started = Instant::now();
            let result = self.send(&body).await;
            let latency_ms = started.elapsed().as_millis() as u64;
            let completion = match result {
                Ok(completion) => completion,
                Err(error) => {
                    return Err(error
                        .into_anyhow()
                        .context(format!("{} request failed", self.model)));
                }
            };
            decision.input_tokens += completion.input_tokens;
            decision.output_tokens += completion.output_tokens;
            let parsed = parse_choice(&completion.text, count);
            decision.exchanges.push(Exchange {
                request: body.to_string(),
                response: Some(completion.text.clone()),
                error: parsed.as_ref().err().cloned(),
                latency_ms,
            });
            match parsed {
                Ok(index) => {
                    decision.index = index;
                    return Ok(decision);
                }
                Err(reason) => {
                    user = format!(
                        "{prompt}\n\nYour previous reply was rejected ({reason}). \
                         Reply with JSON only: {{\"choice\": N}} with N from 1 to {count}."
                    );
                }
            }
        }
        decision.fallback = true;
        Ok(decision)
    }

    fn body(&self, system: &str, user: &str) -> Value {
        match &self.kind {
            Kind::OpenAiSubscription(_) => json!({
                "model": self.model,
                "instructions": system,
                "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": user}]}],
                "stream": true,
                "store": false,
                "text": {"format": {"type": "json_schema", "name": "backgammon_play", "schema": schema(), "strict": true}},
            }),
            Kind::AnthropicSubscription(_) => json!({
                "model": self.model,
                "max_tokens": 1024,
                "system": [
                    {"type": "text", "text": CLAUDE_CODE_IDENTITY},
                    {"type": "text", "text": system},
                ],
                "messages": [{"role": "user", "content": user}],
                "tools": [{"name": "choose_play", "description": "Submit the chosen play.", "input_schema": schema()}],
                "tool_choice": {"type": "tool", "name": "choose_play"},
            }),
            Kind::Gemini(_) => json!({
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": {
                        "type": "OBJECT",
                        "properties": {"choice": {"type": "INTEGER"}},
                        "required": ["choice"],
                    },
                },
            }),
            Kind::OpenAiCompatible { .. } => json!({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "backgammon_play", "strict": true, "schema": schema()},
                },
            }),
        }
    }

    async fn send(&self, body: &Value) -> Result<Completion, CallError> {
        match &self.kind {
            Kind::OpenAiSubscription(creds) => {
                let mut token = creds.token().await?;
                let mut refreshed = false;
                loop {
                    let request = || {
                        let mut builder = self
                            .http
                            .post(CODEX_URL)
                            .bearer_auth(&token.access)
                            .header("OAI-Product-Sku", "codex")
                            .header("originator", "codex_cli_rs")
                            .header("session_id", &self.session_id)
                            .header("accept", "text/event-stream")
                            .json(body);
                        if let Some(account) = &token.account_id {
                            builder = builder.header("ChatGPT-Account-Id", account);
                        }
                        builder
                    };
                    match http::send(request).await {
                        Err(CallError::Auth(_)) if !refreshed => {
                            token = creds.refresh_after_rejection(&token.access).await?;
                            refreshed = true;
                        }
                        other => return Ok(parse_codex_sse(&other?)?),
                    }
                }
            }
            Kind::AnthropicSubscription(creds) => {
                let mut token = creds.token().await?;
                let mut refreshed = false;
                loop {
                    let request = || {
                        self.http
                            .post(ANTHROPIC_URL)
                            .bearer_auth(&token.access)
                            .header("anthropic-version", "2023-06-01")
                            .header("anthropic-beta", "claude-code-20250219,oauth-2025-04-20")
                            .json(body)
                    };
                    match http::send(request).await {
                        Err(CallError::Auth(_)) if !refreshed => {
                            token = creds.refresh_after_rejection(&token.access).await?;
                            refreshed = true;
                        }
                        other => return Ok(parse_anthropic(&other?)?),
                    }
                }
            }
            Kind::Gemini(key) => {
                let url = format!("{GEMINI_URL}/models/{}:generateContent", self.model);
                let text = http::send(|| {
                    self.http
                        .post(&url)
                        .header("x-goog-api-key", key)
                        .json(body)
                })
                .await?;
                Ok(parse_gemini(&text)?)
            }
            Kind::OpenAiCompatible { base_url, api_key } => {
                let url = format!("{base_url}/chat/completions");
                let text = http::send(|| {
                    let builder = self.http.post(&url).json(body);
                    match api_key {
                        Some(key) => builder.bearer_auth(key),
                        None => builder,
                    }
                })
                .await?;
                Ok(parse_chat_completion(&text)?)
            }
        }
    }
}

fn parse_codex_sse(stream: &str) -> Result<Completion> {
    let mut text = String::new();
    let mut done_text = None;
    let mut usage = Value::Null;
    for line in stream.lines() {
        let Some(data) = line.strip_prefix("data:") else {
            continue;
        };
        let Ok(event) = serde_json::from_str::<Value>(data.trim()) else {
            continue;
        };
        match event.get("type").and_then(Value::as_str) {
            Some("response.output_text.delta") => {
                text.push_str(
                    event
                        .get("delta")
                        .and_then(Value::as_str)
                        .unwrap_or_default(),
                );
            }
            Some("response.output_text.done") => {
                done_text = event.get("text").and_then(Value::as_str).map(str::to_owned);
            }
            Some("response.completed") => {
                usage = event
                    .pointer("/response/usage")
                    .cloned()
                    .unwrap_or_default()
            }
            Some("response.failed" | "response.incomplete" | "error") => {
                return Err(anyhow!("OpenAI response failed: {event}"));
            }
            _ => {}
        }
    }
    if usage.is_null() {
        return Err(anyhow!("OpenAI stream ended before response.completed"));
    }
    Ok(Completion {
        text: done_text.unwrap_or(text),
        input_tokens: tokens(&usage, "/input_tokens"),
        output_tokens: tokens(&usage, "/output_tokens"),
    })
}

fn parse_anthropic(body: &str) -> Result<Completion> {
    let value: Value = serde_json::from_str(body).context("Anthropic response is not JSON")?;
    let content = value
        .get("content")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let text = content
        .iter()
        .find(|block| block.get("type").and_then(Value::as_str) == Some("tool_use"))
        .and_then(|block| block.get("input"))
        .map(Value::to_string)
        .or_else(|| {
            let joined: String = content
                .iter()
                .filter_map(|block| block.get("text").and_then(Value::as_str))
                .collect();
            (!joined.is_empty()).then_some(joined)
        })
        .ok_or_else(|| anyhow!("Anthropic response had no tool call or text: {body}"))?;
    Ok(Completion {
        text,
        input_tokens: tokens(&value, "/usage/input_tokens")
            + tokens(&value, "/usage/cache_read_input_tokens")
            + tokens(&value, "/usage/cache_creation_input_tokens"),
        output_tokens: tokens(&value, "/usage/output_tokens"),
    })
}

fn parse_gemini(body: &str) -> Result<Completion> {
    let value: Value = serde_json::from_str(body).context("Gemini response is not JSON")?;
    let parts = value
        .pointer("/candidates/0/content/parts")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let text: String = parts
        .iter()
        .filter(|part| part.get("thought").and_then(Value::as_bool) != Some(true))
        .filter_map(|part| part.get("text").and_then(Value::as_str))
        .collect();
    if text.is_empty() {
        return Err(anyhow!(
            "Gemini response had no text: {}",
            crate::auth::snippet(body)
        ));
    }
    Ok(Completion {
        text,
        input_tokens: tokens(&value, "/usageMetadata/promptTokenCount"),
        output_tokens: tokens(&value, "/usageMetadata/candidatesTokenCount")
            + tokens(&value, "/usageMetadata/thoughtsTokenCount"),
    })
}

fn parse_chat_completion(body: &str) -> Result<Completion> {
    let value: Value = serde_json::from_str(body).context("chat completion is not JSON")?;
    let text = value
        .pointer("/choices/0/message/content")
        .and_then(Value::as_str)
        .ok_or_else(|| {
            anyhow!(
                "chat completion had no message content: {}",
                crate::auth::snippet(body)
            )
        })?;
    Ok(Completion {
        text: text.to_owned(),
        input_tokens: tokens(&value, "/usage/prompt_tokens"),
        output_tokens: tokens(&value, "/usage/completion_tokens"),
    })
}
