//! Decision models: TypeSafe's System One format (Jev and the services that copy it) and
//! OpenAI's Decisions API. The legal plays become the options of one `choice` question, in
//! the seeded option order, and the service returns its probability for each.

use std::time::{Duration, Instant};

use anyhow::{Result, bail};
use serde_json::{Map, Value, json};

use super::prompt::{instructions, option_text, state};
use super::{Decision, DecisionRequest};
use crate::db::Exchange;
use crate::http::{self, RetryTime};

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
        key_vars: &["LIQUID_API_KEY", "LIQUIDAI_API_KEY"],
        key_required: true,
        default_model: Some("d1:free"),
        openai_format: false,
        max_choices: 255,
    },
    Service {
        provider: "subq",
        label: "SubQ",
        base_url: "https://api.subq.ai",
        url_var: "SUBQ_BASE_URL",
        path: "/v1/systemone",
        key_vars: &["SUBQ_API_KEY"],
        key_required: true,
        default_model: Some("subq-snap-preview"),
        openai_format: false,
        max_choices: 255,
    },
    Service {
        provider: "celeris",
        label: "Celeris",
        base_url: "https://inference.celeris.ai/celeris-1-decision",
        url_var: "CELERIS_BASE_URL",
        path: "/v1/systemone",
        key_vars: &["CELERIS_API_KEY"],
        key_required: true,
        default_model: Some("celeris-1-decision"),
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
    /// `model` field. `base_url` (a player config's) overrides the service's URL and its
    /// environment variable. Fails when a required API key is missing.
    pub fn new(
        http: reqwest::Client,
        service: &'static Service,
        model: Option<String>,
        base_url: Option<&str>,
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
        let base = match base_url {
            Some(url) => url.to_owned(),
            None => std::env::var(service.url_var).unwrap_or_else(|_| service.base_url.into()),
        };
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

    pub fn max_choices(&self) -> usize {
        self.service.max_choices
    }

    /// Sends a two-option request until the service answers, so a cold start (e.g.
    /// Fastino's HTTP 425 "warming up") happens before a match instead of on a clock.
    /// Returns how long it took; fails after `WARM_UP_LIMIT`.
    pub async fn warm_up(&self) -> Result<Duration> {
        let started = Instant::now();
        let body = self.body(
            "Warm-up request before a backgammon match.",
            "Answer yes.",
            &[
                ("yes".to_owned(), "yes".to_owned()),
                ("no".to_owned(), "no".to_owned()),
            ],
        );
        loop {
            match self.send(&body, &RetryTime::default()).await {
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

    async fn send(&self, body: &Value, retry: &RetryTime) -> Result<String> {
        http::send(
            || {
                let request = self.http.post(&self.url).json(body);
                match &self.key {
                    Some(key) => request.bearer_auth(key),
                    None => request,
                }
            },
            retry,
        )
        .await
        .map_err(|e| {
            e.into_anyhow()
                .context(format!("{} request failed", self.service.label))
        })
    }

    /// `plays`: `(notation, description)`; the notation identifies the option in the answer
    /// and the description is the option text the model reads.
    fn body(&self, state: &str, instructions: &str, plays: &[(String, String)]) -> Value {
        let mut body = Map::new();
        if let Some(model) = &self.model {
            body.insert("model".into(), model.as_str().into());
        }
        if self.service.openai_format {
            let choices: Vec<Value> = plays
                .iter()
                .map(|(play, text)| json!({"value": play, "description": text}))
                .collect();
            body.insert("input".into(), state.into());
            body.insert(
                "questions".into(),
                json!([{"type": "choice", "name": QUESTION, "instructions": instructions, "choices": choices}]),
            );
        } else {
            // Keys keep the shown order (serde_json's `preserve_order`).
            let mut criteria = Map::new();
            for (play, text) in plays {
                criteria.insert(play.clone(), text.as_str().into());
            }
            body.insert("state".into(), state.into());
            body.insert(
                "questions".into(),
                json!({QUESTION: {"type": "choice", "instructions": instructions, "criteria": criteria}}),
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

    /// The service's probability per option, by notation, in either response format.
    fn probabilities(&self, answer: &Value) -> Vec<(String, f64)> {
        let Some(probabilities) = answer.get("probabilities") else {
            return Vec::new();
        };
        if let Some(list) = probabilities.as_array() {
            list.iter()
                .filter_map(|p| {
                    Some((
                        p.get("value")?.as_str()?.to_owned(),
                        p.get("probability")?.as_f64()?,
                    ))
                })
                .collect()
        } else if let Some(map) = probabilities.as_object() {
            map.iter()
                .filter_map(|(play, p)| Some((play.clone(), p.as_f64()?)))
                .collect()
        } else {
            Vec::new()
        }
    }

    /// One question over `shown` (indices into the plays, in the shown order). Returns the
    /// chosen play, or `None` for an invalid answer (a refusal, a reply that is not JSON or
    /// names no candidate).
    pub async fn choose(
        &self,
        req: &DecisionRequest<'_>,
        shown: &[usize],
        decision: &mut Decision,
    ) -> Result<Option<usize>> {
        let plays: Vec<(String, String)> = shown
            .iter()
            .map(|&i| (req.notations[i].clone(), option_text(req, i)))
            .collect();
        let body = self.body(&state(req), instructions(req), &plays);
        let started = Instant::now();
        let retry_before = req.retry.get();
        let text = self.send(&body, req.retry).await?;
        let latency_ms = started
            .elapsed()
            .saturating_sub(req.retry.get() - retry_before)
            .as_millis() as u64;
        let value: Option<Value> = serde_json::from_str(&text).ok();
        let usage = |key: &str| {
            value
                .as_ref()
                .and_then(|v| v.pointer(&format!("/usage/{key}")))
                .and_then(Value::as_u64)
                .unwrap_or(0)
        };
        decision.input_tokens += usage("input_tokens");
        decision.output_tokens += usage("output_tokens");
        let answer = value.as_ref().and_then(|v| self.answer(v));
        let refused = answer.and_then(|a| a.get("type")).and_then(Value::as_str) == Some("refusal");
        let choice = answer
            .filter(|_| !refused)
            .and_then(|a| a.get("choice"))
            .and_then(Value::as_str)
            .and_then(|choice| shown.iter().copied().find(|&i| req.notations[i] == choice));
        let error = match (&value, refused, choice) {
            (None, _, _) => Some("response is not JSON".to_owned()),
            (_, true, _) => Some("refusal".to_owned()),
            (_, _, None) => Some(format!("no {QUESTION} choice among the candidates")),
            _ => None,
        };
        if choice.is_some() {
            let probabilities = answer.map(|a| self.probabilities(a)).unwrap_or_default();
            decision.probabilities = shown
                .iter()
                .filter_map(|&i| {
                    probabilities
                        .iter()
                        .find(|(play, _)| *play == req.notations[i])
                        .map(|&(_, p)| (i, p))
                })
                .collect();
            decision.probability_source =
                (!decision.probabilities.is_empty()).then_some("decision");
        }
        decision.exchanges.push(Exchange {
            request: body.to_string(),
            response: Some(text),
            error,
            latency_ms,
        });
        Ok(choice)
    }
}
