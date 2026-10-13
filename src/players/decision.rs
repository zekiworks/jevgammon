//! Decision models: TypeSafe's System One format (Jev and the services that copy it) and
//! OpenAI's Decisions API. The legal plays become the options of one `choice` question, so
//! the answer is always one of them.

use std::time::{Duration, Instant};

use anyhow::{Context, Result, anyhow, bail};
use serde_json::{Map, Value, json};

use super::prompt::{JEV_INSTRUCTIONS, descriptions, jev_state};
use super::{Decision, DecisionRequest};
use crate::db::Exchange;
use crate::http;

const QUESTION: &str = "play";
/// Longest wait for a service to answer its warm-up request.
const WARM_UP_LIMIT: Duration = Duration::from_secs(900);

/// A decision service and how to call it.
pub struct Service {
    /// Provider prefix in model specs.
    pub provider: &'static str,
    /// Named in messages.
    label: &'static str,
    base_url: &'static str,
    /// Environment variable overriding `base_url`.
    url_var: &'static str,
    path: &'static str,
    /// Environment variables holding the API key, checked in order; empty = no key.
    key_vars: &'static [&'static str],
    /// Without it, requests carry no key when none is set.
    key_required: bool,
    /// Model when the spec names none; `None` for a server without a `model` field.
    default_model: Option<&'static str>,
    /// OpenAI's Decisions API: `input`, a list of named questions, `choices` as
    /// `{value, description}`, and answers listed by name.
    openai_format: bool,
    /// Largest number of options the service accepts in one question.
    max_choices: usize,
}

pub const SERVICES: &[Service] = &[
    Service {
        provider: "jev",
        label: "TypeSafe",
        base_url: "https://api.typesafe.ai",
        url_var: "TYPESAFE_BASE_URL",
        path: "/v1/systemone",
        key_vars: &["TYPESAFE_API_KEY", "JEV_API_KEY"],
        key_required: true,
        default_model: Some("jev-latest"),
        openai_format: false,
        max_choices: 255,
    },
    Service {
        provider: "fastino",
        label: "Fastino",
        base_url: "https://api.fastino.ai",
        url_var: "FASTINO_BASE_URL",
        path: "/v1/systemone",
        key_vars: &["FASTINO_API_KEY"],
        key_required: true,
        default_model: Some("fastino/GLiDE"),
        openai_format: false,
        max_choices: 255,
    },
    Service {
        provider: "openai-decisions",
        label: "OpenAI Decisions",
        base_url: "https://api.openai.com",
        url_var: "OPENAI_DECISIONS_BASE_URL",
        path: "/v1/decisions",
        key_vars: &["OPENAI_API_KEY"],
        key_required: true,
        default_model: Some("gpt-6-luna"),
        openai_format: true,
        max_choices: 255,
    },
    Service {
        provider: "perplexity",
        label: "Perplexity",
        base_url: "https://api.perplexity.ai",
        url_var: "PERPLEXITY_BASE_URL",
        path: "/v1/decisions",
        key_vars: &["PERPLEXITY_API_KEY"],
        key_required: true,
        default_model: Some("pplx-decider-v1-27b"),
        openai_format: false,
        max_choices: 255,
    },
    // pplx-decider-v1.1-27b served locally by ~/code/pplx-decider/server.py; one request at
    // a time (others get 529, which is retried). It rejects inputs over 8192 tokens (state
    // about 2,900, each described option about 110), and on our shared GPUs 40 options ran
    // out of memory while 30 worked, so longer play lists are split.
    Service {
        provider: "pplx-local",
        label: "Decider v1.1 (local)",
        base_url: "http://127.0.0.1:18097",
        url_var: "PPLX_LOCAL_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("pplx-decider-v1.1-27b"),
        openai_format: false,
        max_choices: 25,
    },
    Service {
        provider: "liquid",
        label: "Liquid AI",
        base_url: "https://api.liquid.ai/decisions",
        url_var: "LIQUID_BASE_URL",
        path: "/v1/systemone",
        key_vars: &["LIQUID_API_KEY"],
        key_required: true,
        default_model: Some("d1:free"),
        openai_format: false,
        max_choices: 255,
    },
    Service {
        provider: "clef",
        label: "Clef",
        base_url: "http://127.0.0.1:18091",
        url_var: "CLEF_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("clef"),
        openai_format: false,
        // The option list may take 16,384 tokens; a described option is about 117.
        max_choices: 110,
    },
    Service {
        provider: "open-jev",
        label: "Open-Jev",
        base_url: "http://127.0.0.1:8791",
        url_var: "OPEN_JEV_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: None,
        openai_format: false,
        max_choices: 255,
    },
    Service {
        provider: "cygnet",
        label: "Cygnet",
        base_url: "http://127.0.0.1:18093",
        url_var: "CYGNET_BASE_URL",
        path: "/v1/systemone",
        key_vars: &["CYGNET_API_KEY"],
        key_required: false,
        default_model: Some("cygnet"),
        openai_format: false,
        // One option letter each.
        max_choices: 26,
    },
    // A second Cygnet decision server (same recipe: option-letter readout) in front of the
    // gemma-4-31B-it vLLM server.
    Service {
        provider: "gemma",
        label: "Gemma (Cygnet recipe)",
        base_url: "http://127.0.0.1:18094",
        url_var: "GEMMA_BASE_URL",
        path: "/v1/systemone",
        key_vars: &["GEMMA_API_KEY"],
        key_required: false,
        default_model: Some("gemma-4-31B-it"),
        openai_format: false,
        max_choices: 26,
    },
];

pub fn service(provider: &str) -> Option<&'static Service> {
    SERVICES
        .iter()
        .find(|s| s.provider.eq_ignore_ascii_case(provider))
}

pub struct DecisionClient {
    http: reqwest::Client,
    service: &'static Service,
    key: Option<String>,
    /// `None` when the service takes no `model` field.
    model: Option<String>,
    url: String,
}

impl DecisionClient {
    /// `model` overrides the service's default; it is ignored by services without a
    /// `model` field. Fails when a required API key is missing.
    pub fn new(
        http: reqwest::Client,
        service: &'static Service,
        model: Option<String>,
    ) -> Result<Self> {
        let key = service
            .key_vars
            .iter()
            .find_map(|var| std::env::var(var).ok().filter(|k| !k.is_empty()));
        if service.key_required && key.is_none() {
            bail!(
                "{} needs an API key: set {}",
                service.label,
                service.key_vars.join(" or ")
            );
        }
        let base = std::env::var(service.url_var).unwrap_or_else(|_| service.base_url.into());
        Ok(DecisionClient {
            http,
            service,
            key,
            model: service
                .default_model
                .map(|default| model.unwrap_or_else(|| default.to_owned())),
            url: format!("{}{}", base.trim_end_matches('/'), service.path),
        })
    }

    pub async fn decide(&self, req: &DecisionRequest<'_>) -> Result<Decision> {
        let mut decision = Decision {
            index: 0,
            fallback: false,
            exchanges: Vec::new(),
            input_tokens: 0,
            output_tokens: 0,
        };
        let state = jev_state(req);
        let texts = descriptions(req);
        let max = self.service.max_choices;
        // Above the option limit: pick a winner per (balanced) chunk, then choose among
        // the winners, until one play is left.
        let mut candidates: Vec<usize> = (0..req.notations.len()).collect();
        while candidates.len() > 1 {
            let chunks = candidates.len().div_ceil(max);
            let size = candidates.len().div_ceil(chunks);
            let mut winners = Vec::with_capacity(chunks);
            for chunk in candidates.chunks(size) {
                winners.push(
                    self.choose(&state, req, &texts, chunk, &mut decision)
                        .await?,
                );
            }
            candidates = winners;
        }
        decision.index = candidates[0];
        Ok(decision)
    }

    /// Sends a two-option request until the service answers, so a cold start (e.g.
    /// Fastino's HTTP 425 "warming up") happens before a match instead of on a clock.
    /// Returns how long it took; fails after `WARM_UP_LIMIT`.
    pub async fn warm_up(&self) -> Result<Duration> {
        let started = Instant::now();
        let body = self.body(
            &json!("Warm-up request before a backgammon match."),
            &[("yes", "yes"), ("no", "no")],
        );
        loop {
            match self.send(&body).await {
                Ok(_) => return Ok(started.elapsed()),
                Err(error) if started.elapsed() < WARM_UP_LIMIT => {
                    eprintln!("{} warming up: {error:#}", self.service.label);
                    tokio::time::sleep(Duration::from_secs(10)).await;
                }
                Err(error) => {
                    return Err(error.context(format!(
                        "{} did not answer within {} s of warm-up",
                        self.service.label,
                        WARM_UP_LIMIT.as_secs()
                    )));
                }
            }
        }
    }

    async fn send(&self, body: &Value) -> Result<String> {
        http::send(|| {
            let request = self.http.post(&self.url).json(body);
            match &self.key {
                Some(key) => request.bearer_auth(key),
                None => request,
            }
        })
        .await
        .map_err(|e| {
            e.into_anyhow()
                .context(format!("{} request failed", self.service.label))
        })
    }

    /// `plays`: `(notation, description)`; the notation identifies the option in the answer
    /// and the description is the option text the model reads.
    fn body(&self, state: &Value, plays: &[(&str, &str)]) -> Value {
        let mut body = Map::new();
        if let Some(model) = &self.model {
            body.insert("model".into(), model.as_str().into());
        }
        if self.service.openai_format {
            let choices: Vec<Value> = plays
                .iter()
                .map(|(play, text)| json!({"value": play, "description": text}))
                .collect();
            body.insert(
                "input".into(),
                match state {
                    Value::String(text) => text.clone(),
                    other => serde_json::to_string_pretty(other).expect("state serializes"),
                }
                .into(),
            );
            body.insert(
                "questions".into(),
                json!([{"type": "choice", "name": QUESTION, "instructions": JEV_INSTRUCTIONS, "choices": choices}]),
            );
        } else {
            let mut criteria = Map::new();
            for &(play, text) in plays {
                criteria.insert(play.to_owned(), text.into());
            }
            body.insert("state".into(), state.clone());
            body.insert(
                "questions".into(),
                json!({QUESTION: {"type": "choice", "instructions": JEV_INSTRUCTIONS, "criteria": criteria}}),
            );
        }
        Value::Object(body)
    }

    /// The answer object for the play question, in either response format.
    fn answer<'v>(&self, value: &'v Value) -> Option<&'v Value> {
        if self.service.openai_format {
            value
                .get("answers")?
                .as_array()?
                .iter()
                .find(|a| a.get("name").and_then(Value::as_str) == Some(QUESTION))
        } else {
            value.pointer(&format!("/answers/{QUESTION}"))
        }
    }

    async fn choose(
        &self,
        state: &Value,
        req: &DecisionRequest<'_>,
        texts: &[String],
        candidates: &[usize],
        decision: &mut Decision,
    ) -> Result<usize> {
        if let [only] = candidates {
            return Ok(*only);
        }
        let label = self.service.label;
        let plays: Vec<(&str, &str)> = candidates
            .iter()
            .map(|&i| (req.notations[i].as_str(), texts[i].as_str()))
            .collect();
        let body = self.body(state, &plays);
        let started = Instant::now();
        let result = self.send(&body).await;
        let latency_ms = started.elapsed().as_millis() as u64;
        let text = result?;
        let value: Value =
            serde_json::from_str(&text).with_context(|| format!("{label} response is not JSON"))?;
        decision.input_tokens += value
            .pointer("/usage/input_tokens")
            .and_then(Value::as_u64)
            .unwrap_or(0);
        decision.output_tokens += value
            .pointer("/usage/output_tokens")
            .and_then(Value::as_u64)
            .unwrap_or(0);
        let answer = self.answer(&value);
        let refused = answer.and_then(|a| a.get("type")).and_then(Value::as_str) == Some("refusal");
        decision.exchanges.push(Exchange {
            request: body.to_string(),
            response: Some(text.clone()),
            error: refused.then(|| "refusal".to_owned()),
            latency_ms,
        });
        if refused {
            // No choice to use: the first candidate stands in, and the turn is marked.
            decision.fallback = true;
            return Ok(candidates[0]);
        }
        let choice = answer
            .and_then(|a| a.get("choice"))
            .and_then(Value::as_str)
            .ok_or_else(|| anyhow!("{label} response lacks the {QUESTION} choice: {text}"))?;
        candidates
            .iter()
            .copied()
            .find(|&index| req.notations[index] == choice)
            .ok_or_else(|| anyhow!("{label} chose `{choice}`, which is not a candidate"))
    }
}
