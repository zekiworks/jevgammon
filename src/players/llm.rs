//! Chat-model players: OpenAI, Anthropic, Google Antigravity and xAI subscriptions, Gemini API
//! keys, and OpenAI-compatible servers (SGLang, vLLM, Ollama, paid providers). All get
//! Cygnet's letter prompt (`prompt::letter_user`), the options lettered in the seeded order.
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
/// xAI's Responses API, which takes OMP's `xai-oauth` subscription token.
const XAI_URL: &str = "https://api.x.ai/v1/responses";
const GEMINI_URL: &str = "https://generativelanguage.googleapis.com/v1beta";
/// Cloud Code Assist endpoints serving Antigravity, in OMP's order (the production
/// `cloudcode-pa` host answers Antigravity requests with Gemini CLI's quota: 429).
const ANTIGRAVITY_URLS: [&str; 2] = [
    "https://daily-cloudcode-pa.googleapis.com",
    "https://daily-cloudcode-pa.sandbox.googleapis.com",
];
/// The Antigravity app's user agent, as OMP sends it (its default version).
const ANTIGRAVITY_USER_AGENT: &str =
    "antigravity/hub/2.19.1 (aidev_client; os_type=darwin; arch=arm64; cl=963137146)";
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
    /// Prefill text before the letter when reasoning is off (default `Answer:`).
    pub answer_prefix: Option<String>,
    /// Rate-limit pacing shared with the other players of the group.
    pub pacer: Option<Arc<super::Pacer>>,
    /// Hard spending cap (OpenAI-compatible servers): every attempt reserves its worst case.
    pub budget: Option<Arc<crate::budget::Ledger>>,
}

enum Kind {
    OpenAiSubscription(Arc<Credentials>),
    AnthropicSubscription(Arc<Credentials>),
    Gemini(String),
    /// Gemini through the Antigravity subscription: the Gemini request inside a Cloud
    /// Code Assist envelope.
    Antigravity(Arc<Credentials>),
    /// Grok through the xAI subscription (OMP's login) on xAI's Responses API.
    Xai(Arc<Credentials>),
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
    /// Top log-probabilities at the answer letter (see `letter_entry`); `None` when not
    /// returned or when the answer letter's token is not found.
    top: Option<Vec<(String, f64)>>,
    /// The token whose alternatives are `top`.
    answer_token: Option<String>,
    /// Top log-probabilities of the only logprobs entry, when there is exactly one.
    single_entry_top: Option<Vec<(String, f64)>>,
    input_tokens: u64,
    /// Prompt tokens served from the provider's cache (part of `input_tokens`).
    cached_tokens: u64,
    output_tokens: u64,
    /// Reasoning tokens, when the provider reports them.
    reasoning_tokens: Option<u64>,
    /// Dollars, when the provider reports them (OpenRouter's `usage.cost`).
    cost: Option<f64>,
}

impl Completion {
    /// The alternatives at the prefill readout's one generated token (`max_tokens` 1): that
    /// only logprobs entry's, wherever the server filed the token (a reasoning parser may
    /// put it under reasoning), else `top`.
    fn prefill_top(&self) -> Option<&Vec<(String, f64)>> {
        self.single_entry_top.as_ref().or(self.top.as_ref())
    }
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

    pub fn antigravity(
        http: reqwest::Client,
        model: String,
        creds: Arc<Credentials>,
        options: Options,
    ) -> Self {
        Self::new(http, model, Kind::Antigravity(creds), options)
    }

    pub fn xai(
        http: reqwest::Client,
        model: String,
        creds: Arc<Credentials>,
        options: Options,
    ) -> Self {
        Self::new(http, model, Kind::Xai(creds), options)
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
            let (picked, note) = answer_decision(&completion, count);
            if let Some(note) = note {
                mark(decision, &note);
            }
            return Ok(picked);
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
            None => self
                .options
                .answer_prefix
                .clone()
                .unwrap_or_else(|| ANSWER_PREFIX.to_owned()),
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
            match completion.prefill_top() {
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
            mark(decision, &not_a_letter(count));
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
            Kind::Xai(_) => {
                let mut body = json!({
                    "model": self.model,
                    "instructions": system,
                    "input": [{"role": "user", "content": user}],
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
            Kind::Gemini(_) | Kind::Antigravity(_) => {
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
            Kind::Xai(creds) => {
                let mut token = creds.token().await?;
                let mut refreshed = false;
                loop {
                    let request = || {
                        self.http
                            .post(XAI_URL)
                            .bearer_auth(&token.access)
                            .json(body)
                    };
                    match http::send(request, retry).await {
                        Err(CallError::Auth(_)) if !refreshed => {
                            token = creds.refresh_after_rejection(&token.access).await?;
                            refreshed = true;
                        }
                        other => {
                            let raw = other?;
                            let completion = parse_xai(&raw)?;
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
            Kind::Antigravity(creds) => {
                let mut token = creds.token().await?;
                let mut refreshed = false;
                let mut endpoint = 0;
                let session = antigravity_session(&self.session_id);
                loop {
                    let project = token
                        .project
                        .clone()
                        .ok_or_else(|| anyhow!("the Antigravity login has no project id"))?;
                    let envelope = antigravity_envelope(&self.model, &project, body, &session);
                    let url = format!("{}/v1internal:generateContent", ANTIGRAVITY_URLS[endpoint]);
                    let request = || {
                        self.http
                            .post(&url)
                            .bearer_auth(&token.access)
                            .header("User-Agent", ANTIGRAVITY_USER_AGENT)
                            .json(&envelope)
                    };
                    match http::send(request, retry).await {
                        Err(CallError::Auth(_)) if !refreshed => {
                            token = creds.refresh_after_rejection(&token.access).await?;
                            refreshed = true;
                        }
                        // The next endpoint, as OMP falls back from daily to sandbox.
                        Err(CallError::Fatal(_)) if endpoint + 1 < ANTIGRAVITY_URLS.len() => {
                            endpoint += 1;
                        }
                        other => {
                            let raw = other?;
                            let completion = parse_antigravity(&raw)?;
                            return Ok((raw, completion));
                        }
                    }
                }
            }
            Kind::OpenAiCompatible { base_url, api_key } => {
                let url = format!("{base_url}/chat/completions");
                let make = || {
                    let builder = self.http.post(&url).json(body);
                    match api_key {
                        Some(key) => builder.bearer_auth(key),
                        None => builder,
                    }
                };
                let Some(ledger) = &self.options.budget else {
                    let raw = http::send(make, retry).await?;
                    let completion = parse_chat_completion(&raw)?;
                    return Ok((raw, completion));
                };
                let max_output = body
                    .get("max_tokens")
                    .and_then(Value::as_u64)
                    .unwrap_or(32768);
                let worst = ledger.worst_case(body.to_string().len(), max_output);
                let (raw, hold) = http::send_metered(make, retry, ledger, worst).await?;
                match parse_chat_completion(&raw) {
                    Ok(completion) => {
                        hold.settle(
                            crate::budget::Usage {
                                input_tokens: completion.input_tokens,
                                cached_tokens: completion.cached_tokens,
                                output_tokens: completion.output_tokens,
                                reasoning_tokens: completion.reasoning_tokens.unwrap_or(0),
                            },
                            completion.cost,
                        );
                        Ok((raw, completion))
                    }
                    // Unreadable answer: its cost is unknown, so `hold` keeps its worst case.
                    Err(error) => Err(error.into()),
                }
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

/// Why a reply without one of the first `count` letters is invalid.
fn not_a_letter(count: usize) -> String {
    format!(
        "reply is not one of the letters A-{}",
        LETTERS[count - 1] as char
    )
}

/// The answer readout's decision from its one completion — `(shown position, letter
/// probabilities when read)`, `None` when invalid — and the reason to note on its exchange.
/// The play is the most probable letter, but it counts only when the reply has a letter and
/// the probabilities were read at that letter's token.
fn answer_decision(
    completion: &Completion,
    count: usize,
) -> (Option<(usize, Option<Vec<f64>>)>, Option<String>) {
    let Some(letter) = parse_letter(&completion.text, count) else {
        return (None, Some(not_a_letter(count)));
    };
    let probabilities = completion
        .top
        .as_ref()
        .and_then(|top| letter_probabilities(top, count));
    let Some(probabilities) = probabilities else {
        let note = "no letter logprobs returned; choice only";
        return (Some((letter, None)), Some(note.to_owned()));
    };
    let token = completion.answer_token.as_deref();
    if token.and_then(token_letter) != Some(LETTERS[letter]) {
        let note = format!(
            "letter logprobs read at token {:?}, not at the reply's letter {}",
            token.unwrap_or_default(),
            LETTERS[letter] as char
        );
        return (None, Some(note));
    }
    (Some((argmax(&probabilities), Some(probabilities))), None)
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

/// The letter of a token that is one uppercase letter, give or take spaces, quotes and
/// punctuation (`C`, ` C`, `"C`).
fn token_letter(token: &str) -> Option<u8> {
    let core = token.trim_matches(|c: char| c.is_whitespace() || "([{'\".,:)]}".contains(c));
    match core.as_bytes() {
        [byte] if byte.is_ascii_uppercase() => Some(*byte),
        _ => None,
    }
}

/// The entry of `entries` (one per token, as in `choices[0].logprobs.content`) at the
/// answer letter: the last one-uppercase-letter token, provided the tokens after it spell
/// the end of the answer `text`, leaving out trailing special tokens such as vLLM's
/// `<|im_end|>`, which are not in the text. Read from the end because some providers list
/// the reasoning's tokens first and others leave tokens out. `None` when `text` is blank or
/// no such entry exists.
fn letter_entry<'a>(entries: &'a [Value], text: &str) -> Option<&'a Value> {
    let text = text.trim();
    if text.is_empty() {
        return None;
    }
    let token = |e: &'a Value| e.get("token").and_then(Value::as_str).unwrap_or_default();
    let at = entries
        .iter()
        .rposition(|e| token_letter(token(e)).is_some())?;
    let mut end = entries.len();
    while end > at + 1 && is_special_token(token(&entries[end - 1])) {
        end -= 1;
    }
    let after: String = entries[at + 1..end].iter().map(token).collect();
    text.ends_with(after.trim()).then_some(&entries[at])
}

/// A tokenizer control token (`<|im_end|>`, `<eos>`, `</s>`, `<｜end▁of▁sentence｜>`): one
/// angle-bracketed word without spaces.
fn is_special_token(token: &str) -> bool {
    token.len() > 2
        && token.starts_with('<')
        && token.ends_with('>')
        && !token[1..token.len() - 1].contains(|c: char| c.is_whitespace() || c == '<' || c == '>')
}

/// The `(token, logprob)` alternatives of a logprobs entry; `None` when it has none.
fn top_logprobs(entry: &Value) -> Option<Vec<(String, f64)>> {
    let top: Vec<_> = entry
        .get("top_logprobs")?
        .as_array()?
        .iter()
        .filter_map(|e| {
            Some((
                e.get("token")?.as_str()?.to_owned(),
                e.get("logprob")?.as_f64()?,
            ))
        })
        .collect();
    (!top.is_empty()).then_some(top)
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

/// xAI's Responses API answer: the `output_text` of its message items (reasoning items carry
/// none), usage as OpenAI's.
fn parse_xai(body: &str) -> Result<Completion> {
    let value: Value = serde_json::from_str(body).context("xAI response is not JSON")?;
    if value.get("status").and_then(Value::as_str) != Some("completed") {
        return Err(anyhow!(
            "xAI response not completed: {}",
            crate::auth::snippet(body)
        ));
    }
    let text: String = value
        .get("output")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter(|item| item.get("type").and_then(Value::as_str) == Some("message"))
        .filter_map(|item| item.get("content").and_then(Value::as_array))
        .flatten()
        .filter(|part| part.get("type").and_then(Value::as_str) == Some("output_text"))
        .filter_map(|part| part.get("text").and_then(Value::as_str))
        .collect();
    Ok(Completion {
        text,
        input_tokens: tokens(&value, "/usage/input_tokens"),
        output_tokens: tokens(&value, "/usage/output_tokens"),
        reasoning_tokens: optional(&value, "/usage/output_tokens_details/reasoning_tokens"),
        ..Completion::default()
    })
}

fn parse_gemini(body: &str) -> Result<Completion> {
    let value: Value = serde_json::from_str(body).context("Gemini response is not JSON")?;
    Ok(gemini_completion(&value))
}

/// Antigravity wraps the Gemini response: `{"response": {...}, "traceId": ...}`.
fn parse_antigravity(body: &str) -> Result<Completion> {
    let value: Value = serde_json::from_str(body).context("Antigravity response is not JSON")?;
    let response = value.get("response").ok_or_else(|| {
        anyhow!(
            "Antigravity answer has no response: {}",
            crate::auth::snippet(body)
        )
    })?;
    Ok(gemini_completion(response))
}

fn gemini_completion(value: &Value) -> Completion {
    let text: String = value
        .pointer("/candidates/0/content/parts")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter(|part| part.get("thought").and_then(Value::as_bool) != Some(true))
        .filter_map(|part| part.get("text").and_then(Value::as_str))
        .collect();
    Completion {
        text,
        input_tokens: tokens(value, "/usageMetadata/promptTokenCount"),
        output_tokens: tokens(value, "/usageMetadata/candidatesTokenCount")
            + tokens(value, "/usageMetadata/thoughtsTokenCount"),
        reasoning_tokens: Some(tokens(value, "/usageMetadata/thoughtsTokenCount")),
        ..Completion::default()
    }
}

/// Antigravity's model id for a spec's model at a reasoning level: Antigravity lists each
/// Gemini model per level (`gemini-3.8-flash-low`, `gemini-4-argon-high`), so the level is
/// appended unless the spec already names it. The request's `thinkingLevel` still sets
/// the level (the id picks the quota bucket and the default budget).
pub fn antigravity_model(model: &str, reasoning: Option<&str>) -> String {
    match reasoning {
        Some(level) if !model.ends_with(&format!("-{level}")) => format!("{model}-{level}"),
        _ => model.to_owned(),
    }
}

/// Antigravity's session id form: `-` and a random number below 9e18.
fn antigravity_session(session_id: &str) -> String {
    let bits = uuid::Uuid::parse_str(session_id)
        .map(|id| id.as_u128() as u64)
        .unwrap_or_default();
    format!("-{}", (bits & i64::MAX as u64) % 9_000_000_000_000_000_000)
}

/// The Cloud Code Assist envelope around a Gemini `request`, as the Antigravity app sends
/// it (`project`, a fresh agent `requestId`, the model, `requestType: agent`).
fn antigravity_envelope(model: &str, project: &str, request: &Value, session: &str) -> Value {
    let mut request = request.clone();
    request["sessionId"] = json!(session);
    json!({
        "project": project,
        "requestId": format!(
            "agent/{}/{}/{}/2",
            uuid::Uuid::new_v4(),
            chrono::Utc::now().timestamp_millis(),
            uuid::Uuid::new_v4()
        ),
        "request": request,
        "model": model,
        "userAgent": "antigravity",
        "requestType": "agent",
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
    let entries = value
        .pointer("/choices/0/logprobs/content")
        .and_then(Value::as_array)
        .map(Vec::as_slice)
        .unwrap_or_default();
    let at = letter_entry(entries, &text);
    let top = at.and_then(top_logprobs);
    let answer_token = top
        .as_ref()
        .and(at)
        .and_then(|e| e.get("token"))
        .and_then(Value::as_str)
        .map(str::to_owned);
    let single_entry_top = match entries {
        [entry] => top_logprobs(entry),
        _ => None,
    };
    Ok(Completion {
        text,
        reasoning,
        top,
        answer_token,
        single_entry_top,
        input_tokens: tokens(&value, "/usage/prompt_tokens"),
        cached_tokens: tokens(&value, "/usage/prompt_tokens_details/cached_tokens"),
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
        assert_eq!(c.answer_token.as_deref(), Some("B"));
        assert_eq!(answer_decision(&c, 3).0.unwrap().0, 1);
        assert!(token_letter(" b").is_none());
        assert_eq!(token_letter("\"C"), Some(b'C'));
        assert!(token_letter("choice").is_none());
        assert_eq!(Readout::parse(Some("answer")).unwrap(), Readout::Answer);
        assert!(Readout::parse(Some("x")).is_err());
    }

    /// Providers that list the reasoning's tokens before the answer's: the letter is read
    /// at the answer's letter, not at a letter in the reasoning.
    #[test]
    fn reads_the_letter_in_the_answer_not_the_reasoning() {
        let reasoning = r#"
              {"token":"We","logprob":0.0,"top_logprobs":[{"token":"We","logprob":0.0}]},
              {"token":" need","logprob":0.0,"top_logprobs":[{"token":" need","logprob":0.0}]},
              {"token":" option","logprob":0.0,"top_logprobs":[{"token":" option","logprob":0.0}]},
              {"token":" A","logprob":-0.1,"top_logprobs":[{"token":" A","logprob":-0.1},{"token":" C","logprob":-2.4}]},
              {"token":" or","logprob":0.0,"top_logprobs":[{"token":" or","logprob":0.0}]},
              {"token":" B","logprob":0.0,"top_logprobs":[{"token":" B","logprob":0.0}]}"#;
        let answer = r#",
              {"token":"{\"","logprob":0.0,"top_logprobs":[{"token":"{\"","logprob":0.0}]},
              {"token":"choice","logprob":0.0,"top_logprobs":[{"token":"choice","logprob":0.0}]},
              {"token":"\":\"","logprob":0.0,"top_logprobs":[{"token":"\":\"","logprob":0.0}]},
              {"token":"B","logprob":-0.3,"top_logprobs":[{"token":"B","logprob":-0.3},{"token":"A","logprob":-1.5}]},
              {"token":"\"}","logprob":0.0,"top_logprobs":[{"token":"\"}","logprob":0.0}]}"#;
        let body = format!(
            r#"{{"choices":[{{"message":{{"content":"{{\"choice\":\"B\"}}",
            "reasoning_content":"We need option A or B"}},"finish_reason":"stop",
            "logprobs":{{"content":[{reasoning}{answer}]}}}}]}}"#
        );
        let c = parse_chat_completion(&body).unwrap();
        assert_eq!(c.answer_token.as_deref(), Some("B"));
        assert_eq!(c.top.as_ref().unwrap()[0], ("B".to_owned(), -0.3));
        let (picked, note) = answer_decision(&c, 3);
        let (position, probabilities) = picked.unwrap();
        assert_eq!(position, 1);
        assert!(probabilities.unwrap()[1] > 0.7);
        assert!(note.is_none());

        // Reasoning cut short by max_tokens: no answer, so no letter read and no play.
        let body = format!(
            r#"{{"choices":[{{"message":{{"content":"",
            "reasoning_content":"We need option A or B"}},"finish_reason":"length",
            "logprobs":{{"content":[{reasoning}]}}}}]}}"#
        );
        let c = parse_chat_completion(&body).unwrap();
        assert!(c.top.is_none() && c.answer_token.is_none());
        let (picked, note) = answer_decision(&c, 3);
        assert!(picked.is_none());
        assert_eq!(note.as_deref(), Some("reply is not one of the letters A-C"));
    }

    /// Providers that list the answer's tokens only (Cerebras, OpenRouter).
    #[test]
    fn reads_the_letter_when_logprobs_cover_the_answer_only() {
        let body = r#"{"choices":[{"message":{"content":"\n\nD"},
            "logprobs":{"content":[
              {"token":"\n\n","logprob":0.0,"top_logprobs":[{"token":"\n\n","logprob":0.0}]},
              {"token":"D","logprob":-0.2,"top_logprobs":[{"token":"D","logprob":-0.2},{"token":"B","logprob":-1.9}]}]}}]}"#;
        let c = parse_chat_completion(body).unwrap();
        assert_eq!(c.answer_token.as_deref(), Some("D"));
        let (picked, note) = answer_decision(&c, 4);
        assert_eq!(picked.unwrap().0, 3);
        assert!(note.is_none());
    }

    /// A chat completion whose logprobs list `tokens`; the token `A` has `B` as an
    /// alternative.
    fn chat_with_tokens(content: &str, reasoning: Option<&str>, tokens: &[&str]) -> String {
        let entries: Vec<Value> = tokens
            .iter()
            .map(|token| {
                let top = match *token {
                    "A" => {
                        json!([{"token": "A", "logprob": -0.4}, {"token": "B", "logprob": -1.1}])
                    }
                    _ => json!([{"token": token, "logprob": 0.0}]),
                };
                json!({"token": token, "logprob": 0.0, "top_logprobs": top})
            })
            .collect();
        json!({"choices": [{
            "message": {"content": content, "reasoning_content": reasoning},
            "logprobs": {"content": entries},
        }]})
        .to_string()
    }

    /// Fireworks (GLM-5.3) leaves tokens out of the logprobs; Alibaba (Qwen3.8 Flash) splits
    /// the key into lowercase letters. Both read the answer's `A`.
    #[test]
    fn reads_the_last_uppercase_letter_followed_by_the_answers_end() {
        let glm = chat_with_tokens(
            "{\n\"choice\": \"A\"\n}",
            None,
            &["\":", " \"", "A", "\"\n", "}"],
        );
        let qwen = chat_with_tokens(
            "{\"choice\": \"A\"}",
            None,
            &["{\"", "c", "ho", "ice", "\":", " \"", "A", "\"}"],
        );
        for body in [glm, qwen] {
            let c = parse_chat_completion(&body).unwrap();
            assert_eq!(c.answer_token.as_deref(), Some("A"));
            let (picked, note) = answer_decision(&c, 3);
            assert_eq!(picked.unwrap().0, 0);
            assert!(note.is_none());
        }
        // The tokens after the letter must end the answer.
        let c = parse_chat_completion(&chat_with_tokens(
            "{\"choice\": \"A\"}",
            None,
            &["{\"choice\": \"", "A", "\"}", " extra"],
        ))
        .unwrap();
        assert!(c.top.is_none() && c.answer_token.is_none());
    }

    /// vLLM lists the end-of-sequence token after the answer (Qwen3.8-27B (off): `A`, then
    /// `<|im_end|>`), though it is not in the text; the letter is still read.
    #[test]
    fn reads_the_letter_before_a_trailing_end_of_sequence_token() {
        for tokens in [
            &["A", "<|im_end|>"][..],
            &["{\"choice\":\"", "A", "\"}", "<｜end▁of▁sentence｜>"][..],
            &["A", "<end_of_turn>", "<eos>"][..],
        ] {
            let text: String = tokens
                .iter()
                .filter(|t| !is_special_token(t))
                .copied()
                .collect();
            let c = parse_chat_completion(&chat_with_tokens(&text, None, tokens)).unwrap();
            assert_eq!(c.answer_token.as_deref(), Some("A"));
            let (picked, note) = answer_decision(&c, 3);
            assert_eq!(picked.unwrap().0, 0);
            assert!(note.is_none());
        }
        assert!(!is_special_token("<"));
        assert!(!is_special_token("< b >"));
    }

    /// Prefill readout: the one generated token is read even when a reasoning parser filed
    /// it under reasoning and left the content empty.
    #[test]
    fn prefill_reads_the_only_token_when_content_is_empty() {
        let c = parse_chat_completion(&chat_with_tokens("", Some("A"), &["A"])).unwrap();
        assert!(c.top.is_none());
        let probabilities = letter_probabilities(c.prefill_top().unwrap(), 3).unwrap();
        assert_eq!(argmax(&probabilities), 0);

        let c = parse_chat_completion(&chat_with_tokens(" A", None, &[" A"])).unwrap();
        assert_eq!(c.prefill_top(), c.top.as_ref());

        // More than one entry: no single generated token to read.
        let c = parse_chat_completion(&chat_with_tokens("", Some("A B"), &["A", " B"])).unwrap();
        assert!(c.prefill_top().is_none());
    }

    /// The answer readout is invalid when the reply has no letter, or when the
    /// probabilities were read at a token other than the reply's letter; without
    /// probabilities the reply's letter is played.
    #[test]
    fn answer_readout_requires_the_replys_letter_at_the_readout() {
        let top = Some(vec![("A".to_owned(), -0.1), ("B".to_owned(), -2.0)]);
        let mismatch = Completion {
            text: r#"{"choice":"B"}"#.to_owned(),
            top: top.clone(),
            answer_token: Some("A".to_owned()),
            ..Completion::default()
        };
        let (picked, note) = answer_decision(&mismatch, 3);
        assert!(picked.is_none());
        assert_eq!(
            note.as_deref(),
            Some(r#"letter logprobs read at token "A", not at the reply's letter B"#)
        );

        let no_letter_token = Completion {
            answer_token: Some("{\"".to_owned()),
            ..mismatch
        };
        assert!(answer_decision(&no_letter_token, 3).0.is_none());

        let unparseable = Completion {
            text: "B or A".to_owned(),
            top: top.clone(),
            answer_token: Some("B".to_owned()),
            ..Completion::default()
        };
        assert!(answer_decision(&unparseable, 3).0.is_none());

        // Sampled B, but A is the more probable: the readout matches, so A is played.
        let matched = Completion {
            text: "B".to_owned(),
            ..unparseable
        };
        let (picked, note) = answer_decision(&matched, 3);
        assert_eq!(picked.unwrap().0, 0);
        assert!(note.is_none());

        let choice_only = Completion {
            text: "C".to_owned(),
            ..Completion::default()
        };
        let (picked, note) = answer_decision(&choice_only, 3);
        assert_eq!(picked, Some((2, None)));
        assert_eq!(
            note.as_deref(),
            Some("no letter logprobs returned; choice only")
        );
    }

    /// Antigravity: the Gemini request (enum-constrained letter, thinking level) inside the
    /// Cloud Code Assist envelope; the answer and usage read from the wrapped response.
    #[test]
    fn builds_antigravity_requests_and_reads_the_wrapped_answer() {
        assert_eq!(
            antigravity_model("gemini-3.8-flash", Some("low")),
            "gemini-3.8-flash-low"
        );
        assert_eq!(
            antigravity_model("gemini-4-argon-high", Some("high")),
            "gemini-4-argon-high"
        );
        assert_eq!(
            antigravity_model("gemini-3.8-flash-high", None),
            "gemini-3.8-flash-high"
        );

        let http = reqwest::Client::new();
        let creds = Arc::new(Credentials::new(
            crate::auth::Subscription::Antigravity,
            std::path::PathBuf::new(),
            http.clone(),
        ));
        let client = LlmClient::antigravity(
            http,
            antigravity_model("gemini-3.8-flash", Some("high")),
            creds,
            Options {
                reasoning: Some("high".into()),
                request: None,
                max_tokens: None,
                top_logprobs: None,
                readout: Readout::Prefill,
                answer_prefix: None,
                pacer: None,
                budget: None,
            },
        );
        let body = client.constrained_body("the position", 3);
        assert_eq!(body["contents"][0]["parts"][0]["text"], "the position");
        assert_eq!(
            body["systemInstruction"]["parts"][0]["text"],
            letter_system()
        );
        let config = &body["generationConfig"];
        assert_eq!(config["responseMimeType"], "text/x.enum");
        assert_eq!(config["responseSchema"]["enum"], json!(["A", "B", "C"]));
        assert_eq!(config["thinkingConfig"]["thinkingLevel"], "high");

        let session = antigravity_session(&client.session_id);
        assert!(session.starts_with('-') && session[1..].parse::<u64>().is_ok());
        let envelope = antigravity_envelope(&client.model, "proj", &body, &session);
        assert_eq!(envelope["project"], "proj");
        assert_eq!(envelope["model"], "gemini-3.8-flash-high");
        assert_eq!(envelope["userAgent"], "antigravity");
        assert_eq!(envelope["requestType"], "agent");
        assert!(
            envelope["requestId"]
                .as_str()
                .unwrap()
                .starts_with("agent/")
        );
        assert_eq!(envelope["request"]["sessionId"], session.as_str());
        assert_eq!(envelope["request"]["generationConfig"], *config);

        let raw = r#"{"response": {"candidates": [{"content": {"role": "model", "parts": [
            {"thoughtSignature": "sig", "text": "\"B\""}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 3900, "candidatesTokenCount": 3,
            "totalTokenCount": 4400, "thoughtsTokenCount": 497},
            "modelVersion": "gemini-3.8-flash"}, "traceId": "t"}"#;
        let c = parse_antigravity(raw).unwrap();
        assert_eq!(parse_letter(&c.text, 3), Some(1));
        assert_eq!((c.input_tokens, c.output_tokens), (3900, 500));
        assert_eq!(c.reasoning_tokens, Some(497));
        assert!(parse_antigravity(r#"{"error": {"code": 429}}"#).is_err());
    }

    #[test]
    fn reads_the_xai_answer_after_its_reasoning() {
        let raw = r#"{"status": "completed", "model": "grok-4.7", "output": [
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": "A or C? C."}]},
            {"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": "{\"choice\":\"B\"}", "annotations": []}]}],
            "usage": {"input_tokens": 1327, "output_tokens": 196,
                "output_tokens_details": {"reasoning_tokens": 190}}}"#;
        let c = parse_xai(raw).unwrap();
        assert_eq!(parse_letter(&c.text, 3), Some(1));
        assert_eq!((c.input_tokens, c.output_tokens), (1327, 196));
        assert_eq!(c.reasoning_tokens, Some(190));
        assert!(parse_xai(r#"{"status": "incomplete", "output": []}"#).is_err());
    }
}
