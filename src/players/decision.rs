//! Decision models: TypeSafe's System One format (Jev and the services that copy it) and
//! OpenAI's Decisions API. The legal plays become the options of one `choice` question, in
//! the seeded option order, and the service returns its probability for each.

use std::sync::Arc;
use std::time::{Duration, Instant};

use anyhow::{Result, bail};
use serde_json::{Map, Value, json};

use super::prompt::{instructions, option_text, state};
use super::{Decision, DecisionRequest};
use crate::budget::{Ledger, Usage};
use crate::db::Exchange;
use crate::http::{self, RetryTime};

const QUESTION: &str = "play";
/// Longest wait for a service to answer its warm-up request.
const WARM_UP_LIMIT: Duration = Duration::from_secs(900);
/// Budget worst case: input tokens a provider may add to a request's own bytes for its
/// system prompt and chat template (unpublished for the hosted services; Drex Max v1's own
/// loader adds about 80, measured with its tokenizer on an empty two-option question).
const TEMPLATE_MARGIN: usize = 4096;
/// Models whose probability maps must pass `map_fault` (Zeki #4977, #4985): Gemini Decision 1's late entry only, so
/// no other setup's stored rows change. A map that fails keeps its raw response and the returned choice is played,
/// but the decision stores no probabilities (probability_source NULL, as for an invalid answer).
const MAP_CHECKED_MODELS: &[&str] = &["google/gemini-decision-1"];
/// Named in every map-check error, so answers before the switch (no check) stay distinguishable.
const MAP_CHECK: &str = "map-check v2";
/// Largest |sum - 1| a checked map may have. No frozen sum tolerance existed (the runner never checked a sum); 1e-6
/// was chosen 11 Nov for Gemini Decision 1 only (Main), covering a provider's float32 rounding.
const SUM_TOLERANCE: f64 = 1e-6;

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
    // Perplexity's Decider checkpoints served locally: pplx-decider-v1.1-27b by
    // ~/code/pplx-decider/server.py, v1.2 and Flash v1.2 by pplx_decider_server.py (a
    // player config's `base_url` picks the server, its spec the model). One request at a time
    // (v1.1 answers others 529, which is retried). v1.1 rejects inputs over 8192 tokens (state
    // about 2,900, each described option about 110), and on our shared GPUs 40 options ran
    // out of memory while 30 worked, so longer play lists are split.
    Service {
        provider: "pplx-local",
        label: "Perplexity Decider (local)",
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
    // OpenRouter's System One route for the decision models it lists; a request names the
    // model with its vendor prefix (a bare name is read as typesafe/<name>).
    Service {
        provider: "openrouter-decisions",
        label: "OpenRouter (System One)",
        base_url: "https://openrouter.ai/api",
        url_var: "OPENROUTER_DECISIONS_BASE_URL",
        path: "/v1/systemone",
        key_vars: &["OPENROUTER_API_KEY"],
        key_required: true,
        default_model: Some("inception/mercury-decide"),
        openai_format: false,
        max_choices: 255,
    },
    // Winnow-12B through its author's winnow-inference server (tools/v3/servers/winnow.sh):
    // at most 64 options per question, and state plus options must fit its 8,192-token
    // decision context (state about 2,900 tokens, a described option about 117).
    Service {
        provider: "winnow",
        label: "Winnow",
        base_url: "http://127.0.0.1:8091",
        url_var: "WINNOW_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("winnow-12b"),
        openai_format: false,
        max_choices: 40,
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
    // vllm-sr/d3-turbo (26B, Qwen3.5 backbone + 255-way code readout) served by the d3_server.py
    // its Hugging Face package ships (tools/v3/servers/d3-turbo.sh). The model field is accepted
    // and ignored; one request runs at a time. Each question prompt may take 32,768 tokens (state
    // about 3,500, a described option about 120) and a question 255 options; 200 leaves margin.
    Service {
        provider: "d3",
        label: "d3-turbo (local)",
        base_url: "http://127.0.0.1:18100",
        url_var: "D3_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("d3-turbo"),
        openai_format: false,
        max_choices: 200,
    },
    // Base Labs' elephant-1 and mammoth-1 (open weights, Qwen3.5 backbones) served by the
    // decision-models runner's servers/baselabs_server.py: qev's own app around the model card's
    // loader, one request at a time. The model field must name the loaded checkpoint
    // (`baselabs/baselabs/elephant-1` sends `baselabs/elephant-1`), and a request over the engine's
    // limit (32,768 tokens per question) gets 422. The card's trained length is 16,384 tokens: a
    // state is at most about 2,400 tokens and a described option at most about 110 (the
    // checkpoint's tokenizer on stored League 1 requests), so 120 options stay within it.
    Service {
        provider: "baselabs",
        label: "Base Labs (local)",
        base_url: "http://127.0.0.1:18102",
        url_var: "BASELABS_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("baselabs/elephant-1"),
        openai_format: false,
        max_choices: 120,
    },
    // Nace.AI's hosted Drex models (drex-max-v1.1, drex-v2.0) through its System One endpoint
    // (console.nace.ai/docs/drex): the same request and answers, plus a `request_id`; output
    // tokens are reported but not billed. 529 (overloaded: the model missed Nace's 55-second
    // timeout) and 429 are retried. Nace takes up to 255 options per question; the Drex late
    // entries' protocol (Ümit, 2026-11-05) asks at most 25 per request, as the Deciders, with
    // longer lists split into groups and a final.
    Service {
        provider: "nace",
        label: "Nace.AI",
        base_url: "https://console.nace.ai",
        url_var: "NACE_BASE_URL",
        path: "/v1/systemone",
        key_vars: &["NACE_API_KEY", "NACEAI_API_KEY"],
        key_required: true,
        default_model: Some("drex-v2.0"),
        openai_format: false,
        max_choices: 25,
    },
    // Nace.AI's open Drex Max v1 weights (nace-ai/drex-max-v1) scored by Nace's own loader
    // (drex_max) behind the decision-models runner's servers/drex_max_server.py, one request at
    // a time; the model field must name the loaded checkpoint (drex-max-v1). At most 25 options
    // per request, as for the hosted Drex models (the loader's 16,384-token default limit would
    // allow 110 for League 1's prompts).
    Service {
        provider: "drex-max",
        label: "Drex Max (local)",
        base_url: "http://127.0.0.1:18104",
        url_var: "DREX_MAX_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("drex-max-v1"),
        openai_format: false,
        max_choices: 25,
    },
    // Nace.AI's open Drex 2.0 weights (nace-ai/drex-v2.0) behind the serve.py its checkpoint
    // ships (Nace's kev loader), which accepts and ignores the model field; at most 25 options
    // per request, as for the other Drex setups.
    Service {
        provider: "drex-local",
        label: "Drex 2.0 (local)",
        base_url: "http://127.0.0.1:18105",
        url_var: "DREX_LOCAL_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("drex-v2.0"),
        openai_format: false,
        max_choices: 25,
    },
    // REAX 1.3 (decisionmodels/REAX-1.3 @ fa4bf7e, Apache-2.0) on one of our GPUs behind the REAX
    // Engine's own server (reax13/serve.py of github.com/reaxlabs/reax-engine @ ff8f595, image
    // reax13-runtime): both FP8 parts on one GPU, each option's probability the 50/50 mean of
    // the two parts'. Requests are serialized by the server; the model field, when sent, must
    // be `reax13`, and only `model`, `state` and `questions` are accepted. Its card allows 2 to
    // 255 options per choice question and at most 32,000 proxy tokens (characters of the compact
    // request JSON / 4); the largest stored League 1 full-list requests (251 options) measure
    // 15,424, so the server's 255 is the cap and longer lists are split into groups and a final.
    Service {
        provider: "reax",
        label: "REAX 1.3",
        base_url: "http://127.0.0.1:18106",
        url_var: "REAX_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("reax13"),
        openai_format: false,
        max_choices: 255,
    },
];

pub fn service(provider: &str) -> Option<&'static Service> {
    SERVICES
        .iter()
        .find(|s| s.provider.eq_ignore_ascii_case(provider))
}

/// Nace.AI's unbilled error statuses: "Only a `200` response is debited. A request that ends
/// in `401`, `402`, `422`, `429`, `500`, or `529` costs nothing."
/// (https://console.nace.ai/docs/drex/reference/pricing, read 2026-11-05). Every other error
/// status keeps the attempt's worst case.
pub fn nace_unbilled(status: reqwest::StatusCode) -> bool {
    matches!(status.as_u16(), 401 | 402 | 422 | 429 | 500 | 529)
}

impl Service {
    /// Error statuses this service documents as unbilled, for the budget: Nace's list; none
    /// for the others, so a metered request answered with an error keeps its worst case.
    fn unbilled(&self) -> http::FreeStatus {
        match self.provider {
            "nace" => nace_unbilled,
            _ => |_| false,
        }
    }
}

pub struct DecisionClient {
    http: reqwest::Client,
    service: &'static Service,
    key: Option<String>,
    /// `None` when the service takes no `model` field.
    model: Option<String>,
    url: String,
    /// Hard spending cap: every attempt reserves its worst case before it is sent.
    budget: Option<Arc<Ledger>>,
    /// Fields merged into every request body (a player config's `request`), e.g.
    /// OpenRouter's `provider` routing.
    request: Option<Value>,
    /// A league's run guard naming this setup: its latch is checked before every attempt and,
    /// with an expected route, every reply's identity after it.
    guard: Option<Guarded>,
}

struct Guarded {
    guard: Arc<crate::guard::Guard>,
    route: Option<super::llm::ExpectRoute>,
}

impl DecisionClient {
    /// `model` overrides the service's default; it is ignored by services without a
    /// `model` field. `base_url` (a player config's) overrides the service's URL and its
    /// environment variable. `budget` meters every request attempt. Fails when a required
    /// API key is missing.
    pub fn new(
        http: reqwest::Client,
        service: &'static Service,
        model: Option<String>,
        base_url: Option<&str>,
        budget: Option<Arc<Ledger>>,
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
            budget,
            request: None,
            guard: None,
        })
    }

    /// Merges `request`'s fields into every request body (a null value removes a field).
    pub fn with_request(mut self, request: Option<Value>) -> Self {
        self.request = request;
        self
    }

    /// Puts the client under a league's run guard (`None`: none), with the identity the guard
    /// expects of `name`'s replies, if any.
    pub fn with_guard(mut self, guard: Option<Arc<crate::guard::Guard>>, name: &str) -> Self {
        self.guard = guard.map(|guard| Guarded {
            route: guard.route_for(name),
            guard,
        });
        self
    }

    pub fn max_choices(&self) -> usize {
        self.service.max_choices
    }

    /// Sends a two-option request until the service answers, so a cold start (e.g.
    /// Fastino's HTTP 425 "warming up") happens before a match instead of on a clock.
    /// Returns how long it took; fails after `WARM_UP_LIMIT`, or at once when the request is
    /// refused (a 4xx other than 425, e.g. 402 out of credit), which waiting does not cure.
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
                Err(error) if refused(&error) => {
                    return Err(
                        error.context(format!("{} refused the warm-up", self.service.label))
                    );
                }
                // A guard stop (identity, latch, cap) is not cured by waiting.
                Err(error) if self.guard.is_some() && crate::guard::is_stop(&error) => {
                    return Err(error.context(format!(
                        "{} warm-up stopped by the league guard",
                        self.service.label
                    )));
                }
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

    /// With a budget, each attempt (retries included) first reserves its worst case, and is
    /// refused before the call when spent + reserved + that would pass the cap. Worst case:
    /// one input token per byte of the JSON body plus `TEMPLATE_MARGIN` tokens, and as many
    /// output tokens as body bytes. A byte-level BPE tokenizer (the Qwen family Drex is
    /// built on) never makes a token of less than one byte of the UTF-8 text it encodes, and
    /// the body holds every byte of the state, instructions and options the model reads (JSON
    /// escaping only adds bytes); the margin covers the provider's own system prompt and chat
    /// template, which it does not publish. An answer with usage is booked at max(its list
    /// price, the provider's reported `usage.cost`); a 200 without readable usage, an error
    /// status the service does not document as unbilled (`Service::unbilled`), and an attempt
    /// without a response keep the worst case. Under a league guard nothing is sent while its
    /// latch is set, and a reply without the expected identity sets it (after its cost is
    /// booked) and fails with a `GuardStop`.
    async fn send(&self, body: &Value, retry: &RetryTime) -> Result<String> {
        if let Some(guarded) = &self.guard {
            guarded.guard.check()?;
        }
        let make = || {
            let request = self.http.post(&self.url).json(body);
            match &self.key {
                Some(key) => request.bearer_auth(key),
                None => request,
            }
        };
        let failed = |e: http::CallError| {
            e.into_anyhow()
                .context(format!("{} request failed", self.service.label))
        };
        let text = match &self.budget {
            None => http::send(make, retry).await.map_err(failed)?,
            Some(ledger) => {
                let bytes = body.to_string().len();
                let worst = ledger.worst_case(bytes + TEMPLATE_MARGIN, bytes as u64);
                let (text, hold) =
                    http::send_metered(make, retry, ledger, worst, self.service.unbilled())
                        .await
                        .map_err(failed)?;
                let value: Option<Value> = serde_json::from_str(&text).ok();
                let usage = |key: &str| {
                    value
                        .as_ref()
                        .and_then(|v| v.pointer(&format!("/usage/{key}")))
                };
                match usage("input_tokens").and_then(Value::as_u64) {
                    Some(input_tokens) => {
                        hold.settle(
                            Usage {
                                input_tokens,
                                cached_tokens: 0,
                                output_tokens: usage("output_tokens")
                                    .and_then(Value::as_u64)
                                    .unwrap_or(0),
                                reasoning_tokens: 0,
                            },
                            usage("cost").and_then(Value::as_f64),
                        );
                    }
                    None => hold.kept("200 without readable usage: booked at the worst case"),
                }
                text
            }
        };
        if let Some(Guarded {
            guard,
            route: Some(route),
        }) = &self.guard
            && let Err(reason) = super::llm::route_identity(&text, route)
        {
            let why = format!(
                "ROUTE CHECK ({}): {reason}; identity {}",
                self.service.label,
                super::llm::identity_fields(&text, route)
            );
            guard.latch(&why);
            let shown: String = text.chars().take(600).collect();
            return Err(anyhow::Error::new(crate::guard::GuardStop(format!(
                "{why}; the league guard is latched ({}): no further request is sent; response: {shown}",
                guard.config.latch.display()
            ))));
        }
        Ok(text)
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
        super::llm::merged(Value::Object(body), self.request.as_ref())
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
        let mut error = match (&value, refused, choice) {
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
            if self.map_checked() {
                let fault = map_fault(
                    &raw_entries(&text),
                    shown.iter().map(|&i| req.notations[i].as_str()),
                );
                if let Some(fault) = fault {
                    error = Some(fault);
                }
                // One failed map in any group of a split decision leaves the whole decision without probabilities.
                let failed = error.is_some()
                    || decision.exchanges.iter().any(|e| {
                        e.error
                            .as_deref()
                            .is_some_and(|e| e.starts_with("probability map rejected"))
                    });
                if failed {
                    decision.probabilities.clear();
                    decision.probability_source = None;
                }
            }
        }
        decision.exchanges.push(Exchange {
            request: body.to_string(),
            response: Some(text),
            error,
            latency_ms,
        });
        Ok(choice)
    }

    fn map_checked(&self) -> bool {
        self.service.provider == "openrouter-decisions"
            && self
                .model
                .as_deref()
                .is_some_and(|m| MAP_CHECKED_MODELS.contains(&m))
    }
}

/// Every probability entry of the play answer as the raw response text has it, in either format, read with a visitor
/// so a repeated key stays two entries (`serde_json::Value` keeps only the last): `None` for a value that is not a
/// number. Nothing is dropped or normalised; a response this cannot read gives no entries (every id then missing).
fn raw_entries(text: &str) -> Vec<(String, Option<f64>)> {
    use serde::Deserialize;
    use serde::de::{Deserializer, MapAccess, SeqAccess, Visitor};

    struct Entries(Vec<(String, Option<f64>)>);
    impl<'de> Deserialize<'de> for Entries {
        fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
            struct V;
            impl<'de> Visitor<'de> for V {
                type Value = Entries;
                fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
                    f.write_str("a probability object or list")
                }
                fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Entries, A::Error> {
                    let mut out = Vec::new();
                    while let Some((id, p)) = map.next_entry::<String, Value>()? {
                        out.push((id, p.as_f64()));
                    }
                    Ok(Entries(out))
                }
                fn visit_seq<A: SeqAccess<'de>>(self, mut seq: A) -> Result<Entries, A::Error> {
                    let mut out = Vec::new();
                    while let Some(p) = seq.next_element::<Value>()? {
                        let id = p.get("value").and_then(Value::as_str).unwrap_or("");
                        out.push((id.to_owned(), p.get("probability").and_then(Value::as_f64)));
                    }
                    Ok(Entries(out))
                }
            }
            d.deserialize_any(V)
        }
    }
    #[derive(Deserialize)]
    struct Answer {
        probabilities: Entries,
    }
    // QUESTION is "play": the answer's field name.
    #[derive(Deserialize)]
    struct Answers {
        play: Answer,
    }
    #[derive(Deserialize)]
    struct Response {
        answers: Answers,
    }
    serde_json::from_str::<Response>(text)
        .map(|r| r.answers.play.probabilities.0)
        .unwrap_or_default()
}

/// Why a probability map is not usable, or `None` when it is: exactly one entry per shown id (none missing, unknown
/// or repeated), every value a finite number in [0, 1], and the values summing to 1 within `SUM_TOLERANCE`.
fn map_fault<'a>(
    map: &[(String, Option<f64>)],
    shown: impl Iterator<Item = &'a str>,
) -> Option<String> {
    let shown: Vec<&str> = shown.collect();
    let count = |id: &str| map.iter().filter(|(p, _)| p == id).count();
    let ids = |pick: &dyn Fn(&(String, Option<f64>)) -> bool| -> Vec<&str> {
        map.iter()
            .filter(|e| pick(e))
            .map(|(p, _)| p.as_str())
            .collect()
    };
    let mut causes = Vec::new();
    let missing: Vec<&str> = shown.iter().copied().filter(|&id| count(id) == 0).collect();
    let repeated: Vec<&str> = shown.iter().copied().filter(|&id| count(id) > 1).collect();
    let unknown = ids(&|(p, _)| !shown.contains(&p.as_str()));
    let non_numeric = ids(&|(_, v)| v.is_none());
    let non_finite = ids(&|(_, v)| v.is_some_and(|v| !v.is_finite()));
    let below = ids(&|(_, v)| v.is_some_and(|v| v.is_finite() && v < 0.0));
    let above = ids(&|(_, v)| v.is_some_and(|v| v.is_finite() && v > 1.0));
    for (cause, list) in [
        ("missing", &missing),
        ("unknown", &unknown),
        ("repeated", &repeated),
        ("not a number", &non_numeric),
        ("not finite", &non_finite),
        ("below 0", &below),
        ("above 1", &above),
    ] {
        if !list.is_empty() {
            causes.push(format!("{cause} {list:?}"));
        }
    }
    let sum: f64 = map.iter().filter_map(|(_, v)| *v).sum();
    if map.iter().all(|(_, v)| v.is_some_and(f64::is_finite)) && (sum - 1.0).abs() > SUM_TOLERANCE {
        causes.push(format!("sum {sum} outside 1 +/- {SUM_TOLERANCE:e}"));
    }
    if causes.is_empty() {
        return None;
    }
    Some(format!(
        "probability map rejected ({MAP_CHECK}) over {} shown options: {}; the returned choice was played, no \
         probabilities stored (raw map in the response)",
        shown.len(),
        causes.join("; ")
    ))
}

/// Whether the service refused the request (a 4xx other than 425 Too Early).
fn refused(error: &anyhow::Error) -> bool {
    error.chain().any(|e| {
        e.downcast_ref::<http::StatusError>()
            .is_some_and(|s| s.status.is_client_error() && s.status.as_u16() != 425)
    })
}

#[cfg(test)]
mod tests {
    use std::io::{BufRead, BufReader, Read, Write};

    use super::*;
    use crate::board::Board;
    use crate::players::prompt::PromptVersion;

    #[test]
    fn baselabs_sends_the_checkpoint_name_to_the_configured_server() {
        let service = service("baselabs").expect("baselabs service");
        assert_eq!(service.max_choices, 120);
        assert!(!service.key_required && service.key_vars.is_empty());
        let client = DecisionClient::new(
            reqwest::Client::new(),
            service,
            Some("baselabs/mammoth-1".into()),
            Some("http://127.0.0.1:18103/"),
            None,
        )
        .unwrap();
        assert_eq!(client.url, "http://127.0.0.1:18103/v1/systemone");
        assert_eq!(client.max_choices(), 120);
        let plays = [
            ("13/11 6/5".to_owned(), "a".to_owned()),
            ("24/18".to_owned(), "b".to_owned()),
        ];
        let body = client.body("state", "pick", &plays);
        assert_eq!(body["model"], "baselabs/mammoth-1");
        let criteria = body
            .pointer(&format!("/questions/{QUESTION}/criteria"))
            .unwrap();
        assert_eq!(criteria.as_object().unwrap().len(), 2);
    }

    fn client(
        provider: &str,
        model: &str,
        base_url: Option<&str>,
        key: Option<&str>,
    ) -> DecisionClient {
        let service = service(provider).expect("service");
        let base = base_url.unwrap_or(service.base_url);
        DecisionClient {
            http: reqwest::Client::new(),
            service,
            key: key.map(str::to_owned),
            model: Some(model.to_owned()),
            url: format!("{}{}", base.trim_end_matches('/'), service.path),
            budget: None,
            request: None,
            guard: None,
        }
    }

    #[test]
    fn nace_is_the_hosted_system_one_endpoint_with_its_key() {
        let service = service("nace").expect("nace service");
        assert!(service.key_required);
        assert_eq!(service.key_vars, ["NACE_API_KEY", "NACEAI_API_KEY"]);
        assert_eq!(service.max_choices, 25);
        let client = client("nace", "drex-max-v1.1", None, Some("k"));
        assert_eq!(client.url, "https://console.nace.ai/v1/systemone");
        let plays = [
            ("8/2 6/2".to_owned(), "a".to_owned()),
            ("24/18".to_owned(), "b".to_owned()),
        ];
        assert_eq!(
            client.body("state", "pick", &plays)["model"],
            "drex-max-v1.1"
        );
        // Nace's answer: probabilities by option name, request_id beside the answers.
        let response = json!({"model": "drex-max-v1.1", "request_id": "req_1",
            "answers": {QUESTION: {"type": "choice", "choice": "24/18", "confidence": 0.9,
                "probabilities": {"8/2 6/2": 0.05, "24/18": 0.95}}},
            "usage": {"input_tokens": 3000, "output_tokens": 160}});
        let answer = client.answer(&response).expect("answer");
        let mut probabilities = client.probabilities(answer);
        probabilities.sort_by(|a, b| a.0.cmp(&b.0));
        assert_eq!(
            probabilities,
            [("24/18".to_owned(), 0.95), ("8/2 6/2".to_owned(), 0.05)]
        );
    }

    #[test]
    fn local_drex_servers_take_25_options_at_their_configured_url() {
        for (provider, model) in [("drex-max", "drex-max-v1"), ("drex-local", "drex-v2.0")] {
            let service = service(provider).expect("local drex service");
            assert_eq!(service.max_choices, 25);
            assert!(!service.key_required && service.key_vars.is_empty());
            assert_eq!(service.default_model, Some(model));
        }
        let client = client(
            "drex-max",
            "drex-max-v1",
            Some("http://127.0.0.1:18104/"),
            None,
        );
        assert_eq!(client.url, "http://127.0.0.1:18104/v1/systemone");
        let plays = [
            ("13/11 6/5".to_owned(), "a".to_owned()),
            ("24/18".to_owned(), "b".to_owned()),
        ];
        assert_eq!(client.body("state", "pick", &plays)["model"], "drex-max-v1");
    }

    #[test]
    fn reax_sends_only_model_state_and_questions_with_up_to_255_options() {
        let service = service("reax").expect("reax service");
        assert_eq!(service.max_choices, 255);
        assert!(!service.key_required && service.key_vars.is_empty());
        assert_eq!(service.default_model, Some("reax13"));
        let client = client("reax", "reax13", Some("http://127.0.0.1:18106/"), None);
        assert_eq!(client.url, "http://127.0.0.1:18106/v1/systemone");
        let plays = [
            ("13/11 6/5".to_owned(), "a".to_owned()),
            ("24/18".to_owned(), "b".to_owned()),
        ];
        let body = client.body("state", "pick", &plays);
        // serve.py's validate_request refuses any other top-level field.
        let mut fields: Vec<_> = body.as_object().unwrap().keys().cloned().collect();
        fields.sort();
        assert_eq!(fields, ["model", "questions", "state"]);
        assert_eq!(body["model"], "reax13");
        assert_eq!(body["questions"][QUESTION]["type"], "choice");
        // serve.py's answer: the choice and every option's probability, no usage.
        let response = json!({"model": "reax13",
            "answers": {QUESTION: {"type": "choice", "choice": "24/18",
                "probabilities": {"13/11 6/5": 0.25, "24/18": 0.75}}}});
        let answer = client.answer(&response).expect("answer");
        let mut probabilities = client.probabilities(answer);
        probabilities.sort_by(|a, b| a.0.cmp(&b.0));
        assert_eq!(
            probabilities,
            [("13/11 6/5".to_owned(), 0.25), ("24/18".to_owned(), 0.75)]
        );
    }

    /// A server answering every request 200 with `body`; returns its URL and request count.
    fn serve(body: &'static str) -> (String, Arc<std::sync::atomic::AtomicUsize>) {
        use std::io::{Read, Write};
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("http://{}", listener.local_addr().unwrap());
        let count = Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let seen = count.clone();
        std::thread::spawn(move || {
            for stream in listener.incoming() {
                let mut stream = stream.unwrap();
                let mut buffer = [0u8; 65536];
                let _ = stream.read(&mut buffer);
                seen.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                let _ = write!(
                    stream,
                    "HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{body}",
                    body.len()
                );
            }
        });
        (url, count)
    }

    /// The budget refuses a request before it is sent once spent + its worst case would pass
    /// the cap, and books an answered request at its reported usage.
    #[tokio::test]
    async fn budget_refuses_a_request_before_sending_it_past_the_cap() {
        let (url, count) = serve(
            r#"{"model":"drex-v2.0","answers":{"play":{"type":"choice","choice":"yes","probabilities":{"yes":0.9,"no":0.1}}},"usage":{"input_tokens":20,"output_tokens":5}}"#,
        );
        let dir = std::env::temp_dir().join(format!("decision-budget-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir).unwrap();
        let config = |cap| crate::budget::BudgetConfig {
            ledger: dir.join("ledger.db").to_string_lossy().into_owned(),
            cap_usd: cap,
            input_per_mtok: 10_000.0,
            cached_input_per_mtok: 10_000.0,
            output_per_mtok: 0.0,
        };
        let mut client = client("nace", "drex-v2.0", Some(&url), Some("k"));
        let plays = [
            ("yes".to_owned(), "yes".to_owned()),
            ("no".to_owned(), "no".to_owned()),
        ];
        let body = client.body("state", "pick", &plays);
        // Worst case of one attempt: every body byte an input token, plus the template margin,
        // at $10,000 per million.
        let worst = (body.to_string().len() + TEMPLATE_MARGIN) as f64 * 10_000.0 / 1e6;
        // Room for one worst case and 0.1 more; the answer costs 20 tokens = $0.2.
        let ledger = Ledger::open(&config(worst + 0.1), "Drex 2.0").unwrap();
        client.budget = Some(ledger);
        let retry = RetryTime::default();
        assert!(client.send(&body, &retry).await.is_ok());
        assert_eq!(count.load(std::sync::atomic::Ordering::SeqCst), 1);
        // Booked at its reported usage: 20 input tokens = $0.2.
        let (spent, reserved) = client.budget.as_ref().unwrap().totals().unwrap();
        assert!(
            (spent - 0.2).abs() < 1e-9 && reserved == 0.0,
            "{spent} {reserved}"
        );
        // $0.2 spent + the worst case passes the cap: refused, and nothing is sent.
        let error = client.send(&body, &retry).await.unwrap_err();
        assert!(format!("{error:#}").contains("BUDGET CAP"), "{error:#}");
        assert_eq!(count.load(std::sync::atomic::Ordering::SeqCst), 1);
        // Another process on the same ledger sees the same spend.
        let other = Ledger::open(&config(worst + 0.1), "other").unwrap();
        assert!(other.reserve(worst).is_err() && other.reserve(0.09).is_ok());
    }

    /// A 200 without readable usage is booked at the attempt's worst case.
    #[tokio::test]
    async fn budget_books_an_answer_without_usage_at_its_worst_case() {
        let (url, _) = serve(
            r#"{"model":"drex-v2.0","answers":{"play":{"type":"choice","choice":"yes","probabilities":{"yes":0.9,"no":0.1}}}}"#,
        );
        let dir = std::env::temp_dir().join(format!("decision-budget-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir).unwrap();
        let ledger = Ledger::open(
            &crate::budget::BudgetConfig {
                ledger: dir.join("ledger.db").to_string_lossy().into_owned(),
                cap_usd: 1.0,
                input_per_mtok: 0.06,
                cached_input_per_mtok: 0.06,
                output_per_mtok: 0.0,
            },
            "Drex 2.0",
        )
        .unwrap();
        let mut client = client("nace", "drex-v2.0", Some(&url), Some("k"));
        client.budget = Some(ledger);
        let plays = [
            ("yes".to_owned(), "yes".to_owned()),
            ("no".to_owned(), "no".to_owned()),
        ];
        let body = client.body("state", "pick", &plays);
        assert!(client.send(&body, &RetryTime::default()).await.is_ok());
        let worst = (body.to_string().len() + TEMPLATE_MARGIN) as f64 * 0.06 / 1e6;
        let (spent, reserved) = client.budget.as_ref().unwrap().totals().unwrap();
        assert!(
            (spent - worst).abs() < 1e-12 && reserved == 0.0,
            "{spent} {worst}"
        );
    }

    #[test]
    fn only_nace_documents_unbilled_error_statuses() {
        let nace = service("nace").unwrap().unbilled();
        for code in [401, 402, 422, 429, 500, 529] {
            assert!(nace(reqwest::StatusCode::from_u16(code).unwrap()), "{code}");
        }
        for code in [400, 403, 404, 408, 502, 503, 504] {
            assert!(
                !nace(reqwest::StatusCode::from_u16(code).unwrap()),
                "{code}"
            );
        }
        let local = service("drex-max").unwrap().unbilled();
        assert!(!local(reqwest::StatusCode::TOO_MANY_REQUESTS));
    }

    /// Answers one System One request as OpenRouter does (the third option at 0.7, with
    /// `id`, `provider` and `usage.cost`) and returns the request body; `tamper` edits the
    /// probability map before it is sent.
    fn openrouter_stub(
        tamper: fn(&[String], &mut Map<String, Value>),
    ) -> (String, std::thread::JoinHandle<Value>) {
        literal_stub(move |keys| {
            let rest = 0.3 / (keys.len() - 1) as f64;
            let mut probabilities: Map<String, Value> = keys
                .iter()
                .enumerate()
                .map(|(i, k)| (k.clone(), (if i == 2 { 0.7 } else { rest }).into()))
                .collect();
            tamper(keys, &mut probabilities);
            json!({
                "model": "google/gemini-decision-1-20261111", "provider": "Google AI Studio",
                "id": "gen-dec-stub",
                "answers": {QUESTION: {"type": "choice", "choice": keys[2], "probabilities": probabilities, "confidence": 0.6}},
                "usage": {"input_tokens": 2345, "output_tokens": 0, "cost": 0.0002345}
            })
            .to_string()
        })
    }

    /// Answers one request with the literal response text `respond` makes from the shown ids
    /// (the request's criteria keys, in order) and returns the request body.
    fn literal_stub(
        respond: impl FnOnce(&[String]) -> String + Send + 'static,
    ) -> (String, std::thread::JoinHandle<Value>) {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("http://{}", listener.local_addr().unwrap());
        let handle = std::thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut reader = BufReader::new(stream.try_clone().unwrap());
            let mut length = 0;
            loop {
                let mut line = String::new();
                reader.read_line(&mut line).unwrap();
                if line == "\r\n" {
                    break;
                }
                if let Some((name, value)) = line.split_once(':')
                    && name.eq_ignore_ascii_case("content-length")
                {
                    length = value.trim().parse().unwrap();
                }
            }
            let mut body = vec![0; length];
            reader.read_exact(&mut body).unwrap();
            let body: Value = serde_json::from_slice(&body).unwrap();
            let keys: Vec<String> = body["questions"][QUESTION]["criteria"]
                .as_object()
                .unwrap()
                .keys()
                .cloned()
                .collect();
            let answer = respond(&keys);
            write!(
                stream,
                "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{answer}",
                answer.len()
            )
            .unwrap();
            body
        });
        (url, handle)
    }

    /// A raw System One answer: `entries` written as given (so a key may repeat, or a value be
    /// a bare `NaN`), the third shown id chosen.
    fn raw_answer(keys: &[String], entries: &[(usize, &str)]) -> String {
        let map: Vec<String> = entries
            .iter()
            .map(|&(i, v)| format!("{}:{v}", serde_json::to_string(&keys[i]).unwrap()))
            .collect();
        format!(
            r#"{{"model":"google/gemini-decision-1-20261111","provider":"Google AI Studio","answers":{{"play":{{"type":"choice","choice":{},"probabilities":{{{}}},"confidence":0.6}}}},"usage":{{"input_tokens":2345,"output_tokens":0}}}}"#,
            serde_json::to_string(&keys[2]).unwrap(),
            map.join(",")
        )
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn openrouter_request_pins_the_provider_and_keeps_the_probabilities() {
        let mut board = Board::start();
        board.pts[12] = 3;
        board.pts[7] = 5;
        let plays = board.legal_plays(2, 1);
        let n = plays.len();
        assert!(n > 8, "{n}");
        let notations: Vec<String> = plays.iter().map(|p| p.notation()).collect();
        let order: Vec<usize> = (0..n).rev().collect();
        let retry = RetryTime::default();
        let req = DecisionRequest {
            board: &board,
            dice: (2, 1),
            plays: &plays,
            notations: &notations,
            my_score: 0,
            opp_score: 0,
            round: 1,
            rounds: 3,
            leg: 1,
            clock: None,
            my_clock: None,
            opp_clock: None,
            turn_no: 1,
            max_turns: None,
            player: 1,
            history: &[],
            order: &order,
            seed: 1,
            version: PromptVersion::BgV2,
            retry: &retry,
        };
        let (url, stub) = openrouter_stub(|_, _| {});
        let service = service("openrouter-decisions").unwrap();
        let pin = json!({"provider": {"only": ["google-ai-studio"], "allow_fallbacks": false}});
        let client = DecisionClient {
            http: reqwest::Client::new(),
            service,
            key: Some("test".into()),
            model: Some("google/gemini-decision-1".into()),
            url: format!("{url}{}", service.path),
            budget: None,
            request: None,
            guard: None,
        }
        .with_request(Some(pin.clone()));
        let mut decision = Decision::new(0);
        let choice = client.choose(&req, &order, &mut decision).await.unwrap();
        let body = stub.join().unwrap();
        assert_eq!(body["model"], "google/gemini-decision-1");
        assert_eq!(body["provider"], pin["provider"]);
        assert_eq!(body["state"], state(&req));
        let question = &body["questions"][QUESTION];
        assert_eq!(question["type"], "choice");
        let shown: Vec<&String> = question["criteria"].as_object().unwrap().keys().collect();
        let want: Vec<&String> = order.iter().map(|&i| &notations[i]).collect();
        assert_eq!(shown, want, "every option in the seeded order");
        assert_eq!(choice, Some(order[2]));
        assert_eq!(decision.probability_source, Some("decision"));
        assert_eq!(decision.probabilities.len(), n);
        assert!(decision.probabilities.contains(&(order[2], 0.7)));
        assert_eq!((decision.input_tokens, decision.output_tokens), (2345, 0));
        assert!(decision.exchanges[0].error.is_none());
        assert!(
            decision.exchanges[0]
                .request
                .contains("\"allow_fallbacks\":false")
        );

        // Without a config `request` the body carries no provider field, as before.
        let plain = DecisionClient {
            request: None,
            ..client
        };
        let body = plain.body(
            "s",
            "i",
            &[("a".into(), "a".into()), ("b".into(), "b".into())],
        );
        assert!(body.get("provider").is_none());

        // Gemini's maps must be exactly the shown ids, finite values in [0, 1], summing to 1
        // within 1e-6. A failed map: the returned choice is still played, the raw response
        // is kept, the exchange names the cause and the decision stores no probabilities.
        type Tamper = fn(&[String], &mut Map<String, Value>);
        let cases: [(&str, Tamper, &str); 7] = [
            ("valid control", |_, _| {}, ""),
            (
                "missing",
                |k, p| {
                    p.remove(k.last().unwrap());
                },
                "missing [",
            ),
            (
                "extra",
                |_, p| {
                    p.insert("24/1".into(), 0.0.into());
                },
                "unknown [\"24/1\"]",
            ),
            (
                "not a number",
                |k, p| {
                    p.insert(k[0].clone(), "0.1".into());
                },
                "not a number [",
            ),
            (
                "below 0",
                |k, p| {
                    p.insert(k[0].clone(), (-0.01).into());
                },
                "below 0 [",
            ),
            (
                "above 1",
                |k, p| {
                    p.insert(k[0].clone(), 1.5.into());
                },
                "above 1 [",
            ),
            (
                "sum",
                |_, p| {
                    p.values_mut()
                        .for_each(|v| *v = (v.as_f64().unwrap() * 0.99).into());
                },
                "outside 1 +/- 1e-6",
            ),
        ];
        for (name, tamper, cause) in cases {
            let (url, stub) = openrouter_stub(tamper);
            let client = DecisionClient {
                http: reqwest::Client::new(),
                service,
                key: Some("test".into()),
                model: Some("google/gemini-decision-1".into()),
                url: format!("{url}{}", service.path),
                budget: None,
                request: None,
                guard: None,
            };
            let mut decision = Decision::new(0);
            let choice = client.choose(&req, &order, &mut decision).await.unwrap();
            stub.join().unwrap();
            assert_eq!(
                choice,
                Some(order[2]),
                "{name}: the returned choice is played"
            );
            assert!(
                decision.exchanges[0].response.is_some(),
                "{name}: raw response kept"
            );
            assert_eq!(
                (decision.input_tokens, decision.output_tokens),
                (2345, 0),
                "{name}"
            );
            match decision.exchanges[0].error.as_deref() {
                None => {
                    assert!(cause.is_empty(), "{name}: not rejected");
                    assert_eq!(decision.probability_source, Some("decision"));
                    assert_eq!(decision.probabilities.len(), n);
                }
                Some(error) => {
                    assert!(
                        !cause.is_empty() && error.contains(cause),
                        "{name}: {error}"
                    );
                    assert!(error.contains("map-check v2"), "{error}");
                    assert_eq!(decision.probability_source, None, "{name}");
                    assert!(decision.probabilities.is_empty(), "{name}");
                }
            }
        }

        // Other models through the same route are not checked: a bad map is kept as before.
        let (url, stub) = openrouter_stub(|k, p| {
            p.remove(k.last().unwrap());
        });
        let mercury = DecisionClient {
            url: format!("{url}{}", service.path),
            model: Some("inception/mercury-decide".into()),
            ..plain
        };
        let mut decision = Decision::new(0);
        mercury.choose(&req, &order, &mut decision).await.unwrap();
        stub.join().unwrap();
        assert!(decision.exchanges[0].error.is_none());
        assert_eq!(decision.probabilities.len(), n - 1);
        assert_eq!(decision.probability_source, Some("decision"));

        // Raw response bytes through the real decode path. A repeated key (one of the two
        // entries at 0, so the sum stays 1): serde_json's map keeps only the last, the
        // map check still sees both entries and rejects the map.
        let gemini = |url: &str| DecisionClient {
            http: reqwest::Client::new(),
            service,
            key: Some("test".into()),
            model: Some("google/gemini-decision-1".into()),
            url: format!("{url}{}", service.path),
            budget: None,
            request: None,
            guard: None,
        };
        fn valid(n: usize) -> Vec<(usize, String)> {
            let rest = 0.3 / (n - 1) as f64;
            (0..n)
                .map(|i| (i, (if i == 2 { 0.7 } else { rest }).to_string()))
                .collect()
        }
        let (url, stub) = literal_stub(|keys| {
            let mut e = valid(keys.len());
            e.push((0, "0.0".into()));
            e.push((0, e[0].1.clone()));
            e.remove(0);
            let e: Vec<(usize, &str)> = e.iter().map(|(i, v)| (*i, v.as_str())).collect();
            raw_answer(keys, &e)
        });
        let mut decision = Decision::new(0);
        let choice = gemini(&url)
            .choose(&req, &order, &mut decision)
            .await
            .unwrap();
        stub.join().unwrap();
        let raw = decision.exchanges[0].response.as_deref().unwrap();
        let parsed: Value = serde_json::from_str(raw).unwrap();
        assert_eq!(
            parsed["answers"]["play"]["probabilities"]
                .as_object()
                .unwrap()
                .len(),
            n,
            "serde_json's map hides the repeat"
        );
        assert_eq!(choice, Some(order[2]), "the returned choice is played");
        let error = decision.exchanges[0].error.as_deref().unwrap();
        let first = &notations[order[0]];
        assert!(error.contains(&format!("repeated [{first:?}]")), "{error}");
        assert!(!error.contains("sum"), "{error}");
        assert_eq!(decision.probability_source, None);
        assert!(decision.probabilities.is_empty());

        // Bare NaN or Infinity tokens are not JSON: the whole response fails to parse, so the
        // answer is invalid (seeded random play by the caller), as for any unreadable reply.
        for token in ["NaN", "Infinity", "-Infinity"] {
            let (url, stub) = literal_stub(move |keys| {
                let mut e = valid(keys.len());
                e[0].1 = token.into();
                let e: Vec<(usize, &str)> = e.iter().map(|(i, v)| (*i, v.as_str())).collect();
                raw_answer(keys, &e)
            });
            let mut decision = Decision::new(0);
            let choice = gemini(&url)
                .choose(&req, &order, &mut decision)
                .await
                .unwrap();
            stub.join().unwrap();
            assert_eq!(choice, None, "{token}: invalid answer");
            assert_eq!(
                decision.exchanges[0].error.as_deref(),
                Some("response is not JSON"),
                "{token}"
            );
            assert!(
                decision.exchanges[0]
                    .response
                    .as_deref()
                    .unwrap()
                    .contains(token)
            );
            assert!(decision.probabilities.is_empty() && decision.probability_source.is_none());
        }
    }

    #[test]
    fn map_fault_needs_one_finite_probability_per_shown_id_summing_to_one() {
        let m = |e: &[(&str, f64)]| -> Vec<(String, Option<f64>)> {
            e.iter().map(|&(id, v)| (id.to_owned(), Some(v))).collect()
        };
        let shown = || ["a", "b"].into_iter();
        assert_eq!(
            map_fault(&m(&[("b", 0.25), ("a", 0.75)]), shown()),
            None,
            "valid control"
        );
        assert_eq!(
            map_fault(&m(&[("a", 0.5 + 4e-7), ("b", 0.5)]), shown()),
            None,
            "within 1e-6"
        );
        let fault = |e: Vec<(String, Option<f64>)>| map_fault(&e, shown()).unwrap();
        assert!(fault(m(&[("a", 1.0)])).contains("missing [\"b\"]"));
        assert!(fault(m(&[("a", 0.5), ("b", 0.5), ("c", 0.0)])).contains("unknown [\"c\"]"));
        assert!(fault(m(&[("a", 0.25), ("a", 0.25), ("b", 0.5)])).contains("repeated [\"a\"]"));
        assert!(fault(m(&[("a", f64::NAN), ("b", 0.5)])).contains("not finite [\"a\"]"));
        assert!(fault(m(&[("a", f64::INFINITY), ("b", 0.0)])).contains("not finite [\"a\"]"));
        assert!(
            fault(vec![("a".into(), None), ("b".into(), Some(1.0))])
                .contains("not a number [\"a\"]")
        );
        assert!(fault(m(&[("a", -0.5), ("b", 1.5)])).contains("below 0 [\"a\"]; above 1 [\"b\"]"));
        assert!(fault(m(&[("a", 0.5), ("b", 0.5 + 2e-6)])).contains("outside 1 +/- 1e-6"));
        // The list format's repeated ids reach the check as sent.
        let list = r#"{"answers":{"play":{"probabilities":[{"value":"a","probability":0.5},{"value":"a","probability":0.5}]}}}"#;
        assert!(fault(raw_entries(list)).contains("missing [\"b\"]; repeated"));
        // So do the object format's, which serde_json's map would collapse.
        let object = r#"{"answers":{"play":{"probabilities":{"a":0.5,"a":0.0,"b":0.5}}}}"#;
        assert!(fault(raw_entries(object)).contains("repeated [\"a\"]"));
    }
}
