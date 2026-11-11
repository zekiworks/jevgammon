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
    /// Fields merged into every request body (a player config's `request`), e.g.
    /// OpenRouter's `provider` routing.
    request: Option<Value>,
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
            request: None,
        })
    }

    /// Merges `request`'s fields into every request body (a null value removes a field).
    pub fn with_request(mut self, request: Option<Value>) -> Self {
        self.request = request;
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
                    &answer.map(raw_map).unwrap_or_default(),
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

/// Every probability entry of an answer as sent, in either format: `None` for a value that is not a number. Nothing
/// is dropped or normalised.
fn raw_map(answer: &Value) -> Vec<(String, Option<f64>)> {
    match answer.get("probabilities") {
        Some(Value::Array(list)) => list
            .iter()
            .map(|p| {
                let id = p
                    .get("value")
                    .and_then(Value::as_str)
                    .unwrap_or("")
                    .to_owned();
                (id, p.get("probability").and_then(Value::as_f64))
            })
            .collect(),
        Some(Value::Object(map)) => map.iter().map(|(id, p)| (id.clone(), p.as_f64())).collect(),
        _ => Vec::new(),
    }
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

    /// Answers one System One request as OpenRouter does (the third option at 0.7, with
    /// `id`, `provider` and `usage.cost`) and returns the request body; `tamper` edits the
    /// probability map before it is sent.
    fn openrouter_stub(
        tamper: fn(&[String], &mut Map<String, Value>),
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
            let rest = 0.3 / (keys.len() - 1) as f64;
            let mut probabilities: Map<String, Value> = keys
                .iter()
                .enumerate()
                .map(|(i, k)| (k.clone(), (if i == 2 { 0.7 } else { rest }).into()))
                .collect();
            tamper(&keys, &mut probabilities);
            let answer = json!({
                "model": "google/gemini-decision-1-20261111", "provider": "Google AI Studio",
                "id": "gen-dec-stub",
                "answers": {QUESTION: {"type": "choice", "choice": keys[2], "probabilities": probabilities, "confidence": 0.6}},
                "usage": {"input_tokens": 2345, "output_tokens": 0, "cost": 0.0002345}
            })
            .to_string();
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
            request: None,
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
                request: None,
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
        let list = json!({"probabilities": [{"value": "a", "probability": 0.5}, {"value": "a", "probability": 0.5}]});
        assert!(fault(raw_map(&list)).contains("missing [\"b\"]; repeated"));
    }
}
