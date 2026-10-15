//! Chat-model players: OpenAI and Anthropic subscriptions, Gemini API keys, and
//! OpenAI-compatible servers (SGLang, vLLM, Ollama, paid providers). All get Cygnet's letter
//! prompt (`prompt::letter_user`), the options lettered in the seeded order.
//!
//! OpenAI-compatible servers return letter probabilities: with reasoning on, request 1 lets
//! the model reason (its answer constrained to the option letters); request 2 sends the
//! conversation back with the reasoning and a prefilled `Answer:` (`continue_final_message`),
//! one output token and `top_logprobs`, and the option letters' probabilities are read and
//! normalised. Reasoning off is request 2 alone. A server that returns no logprobs falls back
//! to the constrained letter (choice only). Subscription models return no probabilities and
//! answer with one constrained letter.

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Instant;

use anyhow::{Context, Result, anyhow};
use serde_json::{Value, json};

use super::prompt::{LETTERS, letter_probabilities, letter_system, letter_user, parse_letter};
use super::{Decision, DecisionRequest};
use crate::auth::Credentials;
use crate::db::Exchange;
use crate::http::{self, CallError};

const CODEX_URL: &str = "https://chatgpt.com/backend-api/codex/responses";
const ANTHROPIC_URL: &str = "https://api.anthropic.com/v1/messages";
const GEMINI_URL: &str = "https://generativelanguage.googleapis.com/v1beta";
/// Anthropic serves subscription tokens only when this is the first system block.
const CLAUDE_CODE_IDENTITY: &str = "You are Claude Code, Anthropic's official CLI for Claude.";
/// Log-probabilities asked for the answer token unless the player config sets fewer
/// (OpenAI's maximum; Fireworks allows 5).
const TOP_LOGPROBS: u32 = 20;
/// Prefilled before the answer letter.
const ANSWER_PREFIX: &str = "Answer:";

/// How an OpenAI-compatible server's letter probabilities are read.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Readout {
    /// A request continuing a prefilled `Answer:` (after the reasoning, when on), one
    /// output token (`continue_final_message`; SGLang, vLLM).
    #[default]
    Prefill,
    /// The log-probabilities of the answer letter in the ordinary (reasoning, when on)
    /// response, constrained to the letters: for servers that do not continue a prefill
    /// (Fireworks, Novita and Together through OpenRouter).
    Answer,
}

impl Readout {
    pub fn parse(name: Option<&str>) -> Result<Self> {
        match name {
            None | Some("prefill") => Ok(Readout::Prefill),
            Some("answer") => Ok(Readout::Answer),
            Some(other) => Err(anyhow!(
                "letter_readout must be `prefill` or `answer`, not `{other}`"
            )),
        }
    }
}

/// Per-player settings from its config.
pub struct Options {
    /// Reasoning effort; `None` = reasoning off (subscriptions: the provider default).
    pub reasoning: Option<String>,
    /// Fields merged into every request body; a null value removes the field.
    pub request: Option<Value>,
    pub max_tokens: Option<u32>,
    pub top_logprobs: Option<u32>,
    pub readout: Readout,
    /// Rate-limit pacing shared with the other players of the group.
    pub pacer: Option<Arc<super::Pacer>>,
}

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
    options: Options,
    /// Set when the server answered a logprobs request without logprobs; later decisions
    /// skip that request and use the constrained letter.
    no_logprobs: AtomicBool,
}

#[derive(Debug, Default, PartialEq)]
struct Completion {
    /// The answer, without reasoning.
    text: String,
    /// Reasoning returned separately (`reasoning_content`) or in `<think>` tags.
    reasoning: Option<String>,
    /// Top log-probabilities at the answer letter: the first answer token that is a single
    /// letter, else the first answer token; `None` when not returned.
    top: Option<Vec<(String, f64)>>,
    input_tokens: u64,
    output_tokens: u64,
    /// Reasoning tokens, when the provider reports them.
    reasoning_tokens: Option<u64>,
    /// Dollars, when the provider reports them (OpenRouter's `usage.cost`).
    cost: Option<f64>,
}

/// JSON schema of a one-letter answer among `count` options.
fn letter_schema(count: usize) -> Value {
    json!({
        "type": "object",
        "properties": {"choice": {"type": "string", "enum": letters(count)}},
        "required": ["choice"],
        "additionalProperties": false,
    })
}

fn letters(count: usize) -> Vec<String> {
    LETTERS[..count]
        .iter()
        .map(|l| (*l as char).to_string())
        .collect()
}

fn tokens(value: &Value, pointer: &str) -> u64 {
    value.pointer(pointer).and_then(Value::as_u64).unwrap_or(0)
}

/// `body` with the configured extra fields merged in at the top level; a null value
/// removes that field.
fn merged(mut body: Value, extra: Option<&Value>) -> Value {
    if let (Some(Value::Object(extra)), Value::Object(fields)) = (extra, &mut body) {
        for (key, value) in extra {
            if value.is_null() {
                fields.remove(key);
            } else {
                fields.insert(key.clone(), value.clone());
            }
        }
    }
    body
}

fn optional(value: &Value, pointer: &str) -> Option<u64> {
    value.pointer(pointer).and_then(Value::as_u64)
}

impl LlmClient {
    fn new(http: reqwest::Client, model: String, kind: Kind, options: Options) -> Self {
        LlmClient {
            http,
            model,
            kind,
            session_id: uuid::Uuid::new_v4().to_string(),
            options,
            no_logprobs: AtomicBool::new(false),
        }
    }

    pub fn openai_subscription(
        http: reqwest::Client,
        model: String,
        creds: Arc<Credentials>,
        options: Options,
    ) -> Self {
        Self::new(http, model, Kind::OpenAiSubscription(creds), options)
    }

    pub fn anthropic_subscription(
        http: reqwest::Client,
        model: String,
        creds: Arc<Credentials>,
        options: Options,
    ) -> Self {
        Self::new(http, model, Kind::AnthropicSubscription(creds), options)
    }

    pub fn gemini(http: reqwest::Client, model: String, key: String, options: Options) -> Self {
        Self::new(http, model, Kind::Gemini(key), options)
    }

    pub fn openai_compatible(
        http: reqwest::Client,
        model: String,
        base_url: String,
        api_key: Option<String>,
        options: Options,
    ) -> Self {
        Self::new(
            http,
            model,
            Kind::OpenAiCompatible { base_url, api_key },
            options,
        )
    }

    /// One question over `shown` (indices into the plays, at most 26, in the shown order).
    /// Returns the chosen play, or `None` for an invalid answer.
    pub async fn choose(
        &self,
        req: &DecisionRequest<'_>,
        shown: &[usize],
        decision: &mut Decision,
    ) -> Result<Option<usize>> {
        let count = shown.len();
        let user = letter_user(req, shown);
        let picked = match self.kind {
            Kind::OpenAiCompatible { .. } => {
                self.choose_compatible(req, &user, count, decision).await?
            }
            _ => {
                let body = self.constrained_body(&user, count);
                let completion = self.call(&body, req, decision).await?;
                self.constrained_letter(&completion, count, decision)
                    .map(|position| (position, None))
            }
        };
        Ok(picked.map(|(position, probabilities)| {
            decision.probabilities = match probabilities {
                Some(probabilities) => shown.iter().copied().zip(probabilities).collect(),
                None => vec![(shown[position], 1.0)],
            };
            decision.probability_source = Some(if decision.probabilities.len() > 1 {
                "logprobs"
            } else {
                "choice_only"
            });
            shown[position]
        }))
    }

    /// `(shown position, letter probabilities when read)`, or `None` when invalid.
    async fn choose_compatible(
        &self,
        req: &DecisionRequest<'_>,
        user: &str,
        count: usize,
        decision: &mut Decision,
    ) -> Result<Option<(usize, Option<Vec<f64>>)>> {
        let messages = json!([
            {"role": "system", "content": letter_system()},
            {"role": "user", "content": user},
        ]);
        let top_logprobs = self.options.top_logprobs.unwrap_or(TOP_LOGPROBS);
        let schema = json!({
            "type": "json_schema",
            "json_schema": {"name": "play", "schema": letter_schema(count), "strict": true},
        });
        if self.options.readout == Readout::Answer {
            // One request; its answer letter carries the probabilities.
            let mut body = json!({
                "model": self.model,
                "messages": messages,
                "temperature": 1.0,
                "max_tokens": match self.options.reasoning {
                    Some(_) => self.options.max_tokens.unwrap_or(32768),
                    None => 16,
                },
                "response_format": schema,
                "logprobs": true,
                "top_logprobs": top_logprobs,
            });
            if let Some(effort) = &self.options.reasoning {
                body["reasoning_effort"] = json!(effort);
            }
            let completion = self.call(&body, req, decision).await?;
            let letter = self.constrained_letter(&completion, count, decision);
            let probabilities = completion
                .top
                .as_ref()
                .and_then(|top| letter_probabilities(top, count));
            return Ok(match probabilities {
                Some(probabilities) => Some((argmax(&probabilities), Some(probabilities))),
                None => {
                    if letter.is_some() {
                        mark(decision, "no letter logprobs returned; choice only");
                    }
                    letter.map(|position| (position, None))
                }
            });
        }
        // Reasoning on: the model reasons and answers with a constrained letter.
        let mut constrained = None;
        let prefill = match &self.options.reasoning {
            Some(effort) => {
                let body = json!({
                    "model": self.model,
                    "messages": messages,
                    "temperature": 1.0,
                    "max_tokens": self.options.max_tokens.unwrap_or(32768),
                    "reasoning_effort": effort,
                    "response_format": schema,
                });
                let completion = self.call(&body, req, decision).await?;
                constrained = self.constrained_letter(&completion, count, decision);
                format!(
                    "<think>{}</think>{ANSWER_PREFIX}",
                    completion.reasoning.unwrap_or_default()
                )
            }
            None => ANSWER_PREFIX.to_owned(),
        };
        // The letter probabilities after "Answer:".
        if !self.no_logprobs.load(Ordering::Relaxed) {
            let mut conversation = messages.as_array().cloned().unwrap_or_default();
            conversation.push(json!({"role": "assistant", "content": prefill}));
            let body = json!({
                "model": self.model,
                "messages": conversation,
                "continue_final_message": true,
                // vLLM refuses continue_final_message next to its default true.
                "add_generation_prompt": false,
                "temperature": 1.0,
                "max_tokens": 1,
                "logprobs": true,
                "top_logprobs": top_logprobs,
            });
            let completion = self.call(&body, req, decision).await?;
            match &completion.top {
                Some(top) => match letter_probabilities(top, count) {
                    Some(probabilities) => {
                        return Ok(Some((argmax(&probabilities), Some(probabilities))));
                    }
                    None => mark(decision, "no option letter among the top logprobs"),
                },
                None => {
                    mark(decision, "no logprobs returned; constrained letter used");
                    self.no_logprobs.store(true, Ordering::Relaxed);
                }
            }
        }
        // No probabilities: the constrained letter, asked now when reasoning is off.
        if self.options.reasoning.is_none() {
            let body = self.constrained_body(user, count);
            let completion = self.call(&body, req, decision).await?;
            constrained = self.constrained_letter(&completion, count, decision);
        }
        Ok(constrained.map(|position| (position, None)))
    }

    /// The parsed letter of a constrained answer; an unparseable one is noted on its
    /// exchange.
    fn constrained_letter(
        &self,
        completion: &Completion,
        count: usize,
        decision: &mut Decision,
    ) -> Option<usize> {
        let position = parse_letter(&completion.text, count);
        if position.is_none() {
            mark(
                decision,
                &format!(
                    "reply is not one of the letters A-{}",
                    LETTERS[count - 1] as char
                ),
            );
        }
        position
    }

    /// A request for one letter, constrained to the option letters by the provider.
    fn constrained_body(&self, user: &str, count: usize) -> Value {
        let system = letter_system();
        let effort = self.options.reasoning.as_deref();
        match &self.kind {
            Kind::OpenAiSubscription(_) => {
                let mut body = json!({
                    "model": self.model,
                    "instructions": system,
                    "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": user}]}],
                    "stream": true,
                    "store": false,
                    "text": {"format": {"type": "json_schema", "name": "backgammon_play", "schema": letter_schema(count), "strict": true}},
                });
                if let Some(effort) = effort {
                    body["reasoning"] = json!({"effort": effort});
                }
                body
            }
            Kind::AnthropicSubscription(_) => {
                let mut output =
                    json!({"format": {"type": "json_schema", "schema": letter_schema(count)}});
                if let Some(effort) = effort {
                    output["effort"] = json!(effort);
                }
                json!({
                    "model": self.model,
                    // Room for adaptive thinking at high effort (1,024 ran out in the smoke test).
                    "max_tokens": self.options.max_tokens.unwrap_or(32000),
                    "system": [
                        {"type": "text", "text": CLAUDE_CODE_IDENTITY},
                        {"type": "text", "text": system},
                    ],
                    "messages": [{"role": "user", "content": user}],
                    "output_config": output,
                })
            }
            Kind::Gemini(_) => {
                let mut config = json!({
                    "responseMimeType": "text/x.enum",
                    "responseSchema": {"type": "STRING", "enum": letters(count)},
                    "temperature": 1.0,
                });
                if let Some(effort) = effort {
                    config["thinkingConfig"] = json!({"thinkingLevel": effort});
                }
                json!({
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": config,
                })
            }
            Kind::OpenAiCompatible { .. } => json!({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 1.0,
                "max_tokens": self.options.max_tokens.unwrap_or(32768),
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "play", "schema": letter_schema(count), "strict": true},
                },
            }),
        }
    }

    /// Sends `body` (with the configured extra fields) and records the exchange and tokens.
    async fn call(
        &self,
        body: &Value,
        req: &DecisionRequest<'_>,
        decision: &mut Decision,
    ) -> Result<Completion> {
        let body = merged(body.clone(), self.options.request.as_ref());
        if let Some(pacer) = &self.options.pacer {
            // Not thinking time: logged with the retries, off the clock.
            req.retry.add(pacer.wait().await);
        }
        let started = Instant::now();
        let retry_before = req.retry.get();
        let result = self.send(&body, req).await;
        let latency_ms = started
            .elapsed()
            .saturating_sub(req.retry.get() - retry_before)
            .as_millis() as u64;
        let (raw, completion) = match result {
            Ok(done) => done,
            Err(error) => {
                return Err(error
                    .into_anyhow()
                    .context(format!("{} request failed", self.model)));
            }
        };
        decision.input_tokens += completion.input_tokens;
        decision.output_tokens += completion.output_tokens;
        if let Some(reasoning) = completion.reasoning_tokens {
            *decision.reasoning_tokens.get_or_insert(0) += reasoning;
        }
        if let Some(cost) = completion.cost {
            *decision.reported_cost.get_or_insert(0.0) += cost;
        }
        decision.exchanges.push(Exchange {
            request: body.to_string(),
            response: Some(raw),
            error: None,
            latency_ms,
        });
        Ok(completion)
    }

    /// The response as stored (raw body; the answer text for Codex's event stream) and
    /// its parse.
    async fn send(
        &self,
        body: &Value,
        req: &DecisionRequest<'_>,
    ) -> Result<(String, Completion), CallError> {
        let retry = req.retry;
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
                    match http::send(request, retry).await {
                        Err(CallError::Auth(_)) if !refreshed => {
                            token = creds.refresh_after_rejection(&token.access).await?;
                            refreshed = true;
                        }
                        other => {
                            let completion = parse_codex_sse(&other?)?;
                            return Ok((completion.text.clone(), completion));
                        }
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
                    match http::send(request, retry).await {
                        Err(CallError::Auth(_)) if !refreshed => {
                            token = creds.refresh_after_rejection(&token.access).await?;
                            refreshed = true;
                        }
                        other => {
                            let raw = other?;
                            let completion = parse_anthropic(&raw)?;
                            return Ok((raw, completion));
                        }
                    }
                }
            }
            Kind::Gemini(key) => {
                let url = format!("{GEMINI_URL}/models/{}:generateContent", self.model);
                let raw = http::send(
                    || {
                        self.http
                            .post(&url)
                            .header("x-goog-api-key", key)
                            .json(body)
                    },
                    retry,
                )
                .await?;
                let completion = parse_gemini(&raw)?;
                Ok((raw, completion))
            }
            Kind::OpenAiCompatible { base_url, api_key } => {
                let url = format!("{base_url}/chat/completions");
                let raw = http::send(
                    || {
                        let builder = self.http.post(&url).json(body);
                        match api_key {
                            Some(key) => builder.bearer_auth(key),
                            None => builder,
                        }
                    },
                    retry,
                )
                .await?;
                let completion = parse_chat_completion(&raw)?;
                Ok((raw, completion))
            }
        }
    }
}

/// Notes `reason` on the decision's latest exchange.
fn mark(decision: &mut Decision, reason: &str) {
    if let Some(exchange) = decision.exchanges.last_mut() {
        exchange.error = Some(reason.to_owned());
    }
}

/// Position of the most probable letter (the first on ties).
fn argmax(probabilities: &[f64]) -> usize {
    let mut best = 0;
    for (position, p) in probabilities.iter().enumerate() {
        if *p > probabilities[best] {
            best = position;
        }
    }
    best
}

/// A token that is one letter, give or take spaces, quotes and punctuation (`C`, ` C`, `"C`).
fn letter_token(token: &str) -> bool {
    let core = token.trim_matches(|c: char| c.is_whitespace() || "([{'\".,:)]}".contains(c));
    core.len() == 1 && core.as_bytes()[0].is_ascii_alphabetic()
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
        reasoning_tokens: optional(&usage, "/output_tokens_details/reasoning_tokens"),
        ..Completion::default()
    })
}

fn parse_anthropic(body: &str) -> Result<Completion> {
    let value: Value = serde_json::from_str(body).context("Anthropic response is not JSON")?;
    let content = value
        .get("content")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let text: String = content
        .iter()
        .filter(|block| block.get("type").and_then(Value::as_str) == Some("text"))
        .filter_map(|block| block.get("text").and_then(Value::as_str))
        .collect();
    Ok(Completion {
        text,
        input_tokens: tokens(&value, "/usage/input_tokens")
            + tokens(&value, "/usage/cache_read_input_tokens")
            + tokens(&value, "/usage/cache_creation_input_tokens"),
        output_tokens: tokens(&value, "/usage/output_tokens"),
        reasoning_tokens: optional(&value, "/usage/output_tokens_details/thinking_tokens"),
        ..Completion::default()
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
    Ok(Completion {
        text,
        input_tokens: tokens(&value, "/usageMetadata/promptTokenCount"),
        output_tokens: tokens(&value, "/usageMetadata/candidatesTokenCount")
            + tokens(&value, "/usageMetadata/thoughtsTokenCount"),
        reasoning_tokens: Some(tokens(&value, "/usageMetadata/thoughtsTokenCount")),
        ..Completion::default()
    })
}

fn parse_chat_completion(body: &str) -> Result<Completion> {
    let value: Value = serde_json::from_str(body).context("chat completion is not JSON")?;
    let message = value.pointer("/choices/0/message").ok_or_else(|| {
        anyhow!(
            "chat completion had no message: {}",
            crate::auth::snippet(body)
        )
    })?;
    let mut text = message
        .get("content")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned();
    let mut reasoning = ["reasoning_content", "reasoning"]
        .iter()
        .find_map(|key| message.get(*key).and_then(Value::as_str))
        .filter(|r| !r.is_empty())
        .map(str::to_owned);
    if reasoning.is_none()
        && let Some(end) = text.find("</think>")
    {
        let thought = text[..end]
            .trim_start()
            .trim_start_matches("<think>")
            .to_owned();
        text = text[end + "</think>".len()..].to_owned();
        reasoning = Some(thought);
    }
    // The answer letter's alternatives: the first single-letter answer token (inside a
    // constrained `{"choice":"C"}` it is the fourth), else the first token.
    let entries = value
        .pointer("/choices/0/logprobs/content")
        .and_then(Value::as_array)
        .cloned()
        .unwrap_or_default();
    let at = entries
        .iter()
        .find(|e| {
            e.get("token")
                .and_then(Value::as_str)
                .is_some_and(letter_token)
        })
        .or(entries.first());
    let top = at
        .and_then(|e| e.get("top_logprobs"))
        .and_then(Value::as_array)
        .map(|entries| {
            entries
                .iter()
                .filter_map(|e| {
                    Some((
                        e.get("token")?.as_str()?.to_owned(),
                        e.get("logprob")?.as_f64()?,
                    ))
                })
                .collect::<Vec<_>>()
        })
        .filter(|top| !top.is_empty());
    Ok(Completion {
        text,
        reasoning,
        top,
        input_tokens: tokens(&value, "/usage/prompt_tokens"),
        output_tokens: tokens(&value, "/usage/completion_tokens"),
        reasoning_tokens: optional(&value, "/usage/completion_tokens_details/reasoning_tokens")
            .or_else(|| optional(&value, "/usage/reasoning_tokens")),
        cost: value.pointer("/usage/cost").and_then(Value::as_f64),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_reasoning_answer_and_top_logprobs() {
        let body = r#"{"choices":[{"message":{"content":" C","reasoning_content":"hmm"},
            "logprobs":{"content":[{"token":" C","logprob":-0.1,
            "top_logprobs":[{"token":" C","logprob":-0.1},{"token":" A","logprob":-2.5}]}]}}],
            "usage":{"prompt_tokens":3903,"completion_tokens":1}}"#;
        let c = parse_chat_completion(body).unwrap();
        assert_eq!(c.text, " C");
        assert_eq!(c.reasoning.as_deref(), Some("hmm"));
        assert_eq!(c.top.as_ref().unwrap().len(), 2);
        assert_eq!((c.input_tokens, c.output_tokens), (3903, 1));

        let inline =
            r#"{"choices":[{"message":{"content":"<think>plan</think>{\"choice\":\"B\"}"}}]}"#;
        let c = parse_chat_completion(inline).unwrap();
        assert_eq!(c.reasoning.as_deref(), Some("plan"));
        assert_eq!(parse_letter(&c.text, 3), Some(1));
        assert!(c.top.is_none());
    }

    #[test]
    fn extra_fields_are_merged() {
        let body = merged(
            json!({"model": "m", "temperature": 1.0}),
            Some(&json!({"chat_template_kwargs": {"thinking": true}, "temperature": 0.6})),
        );
        assert_eq!(body["chat_template_kwargs"]["thinking"], true);
        assert_eq!(body["temperature"], 0.6);
        assert_eq!(
            letter_schema(3)["properties"]["choice"]["enum"],
            json!(["A", "B", "C"])
        );
        // A null removes the field (endpoints without a JSON schema).
        let body = merged(
            json!({"response_format": {"type": "json_schema"}, "reasoning_effort": "low"}),
            Some(&json!({"response_format": null})),
        );
        assert!(body.get("response_format").is_none());
        assert_eq!(body["reasoning_effort"], "low");
    }

    /// Answer readout: the letter inside a constrained `{"choice":"M"}` carries the
    /// alternatives; usage gives reasoning tokens and the provider's cost.
    #[test]
    fn reads_the_answer_letter_inside_json() {
        let body = r#"{"choices":[{"message":{"content":"{\"choice\":\"B\"}","reasoning":"think"},
            "logprobs":{"content":[
              {"token":"{\"","logprob":0.0,"top_logprobs":[{"token":"{\"","logprob":0.0}]},
              {"token":"choice","logprob":0.0,"top_logprobs":[{"token":"choice","logprob":0.0}]},
              {"token":"\":\"","logprob":0.0,"top_logprobs":[{"token":"\":\"","logprob":0.0}]},
              {"token":"B","logprob":-0.2,"top_logprobs":[{"token":"B","logprob":-0.2},{"token":"A","logprob":-1.8},{"token":" B","logprob":-4.0}]},
              {"token":"\"}","logprob":0.0,"top_logprobs":[{"token":"\"}","logprob":0.0}]}]}}],
            "usage":{"prompt_tokens":3600,"completion_tokens":900,"cost":0.0042,
                     "completion_tokens_details":{"reasoning_tokens":880}}}"#;
        let c = parse_chat_completion(body).unwrap();
        assert_eq!(parse_letter(&c.text, 3), Some(1));
        let probs = letter_probabilities(c.top.as_ref().unwrap(), 3).unwrap();
        assert!(probs[1] > 0.8 && probs[0] > 0.1 && probs[2] == 0.0);
        assert_eq!(argmax(&probs), 1);
        assert_eq!(c.reasoning_tokens, Some(880));
        assert_eq!(c.cost, Some(0.0042));
        assert!(letter_token(" B") && letter_token("\"C") && !letter_token("choice"));
        assert_eq!(Readout::parse(Some("answer")).unwrap(), Readout::Answer);
        assert!(Readout::parse(Some("x")).is_err());
    }
}
