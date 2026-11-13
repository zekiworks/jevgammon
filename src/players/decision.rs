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
    // PelaAI's KnowLine-31B-Gen1.5 (dense Gemma 4 31B fine-tune) behind the knowline_server.py its
    // Hugging Face repo ships, started by the repo's serve_knowline.sh (SGLang bf16 + the
    // /v1/systemone front end, served model name `m`, which the front end echoes and otherwise
    // ignores). One label token per option: at most 255 options per question (longer play lists
    // are split as for every 255-option service) and 64 questions per request. The front end
    // never truncates: SGLang (no --allow-auto-truncate) refuses a prompt longer than its context
    // or KV pool and the front end answers 422, which fails the decision. League 1's longest
    // single request, 251 options, is 27,849 Gemma 4 tokens; spark2's pool holds 53,181.
    Service {
        provider: "knowline",
        label: "KnowLine (local)",
        base_url: "http://127.0.0.1:19360",
        url_var: "KNOWLINE_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("m"),
        openai_format: false,
        max_choices: 255,
    },
    // StartLux-Decision v1.1 Instant checkpoints (startlux-models on Hugging Face) behind the
    // `startlux-decide serve --launch-vllm` server of their package (github.com/StartLuxLabs/
    // StartLux-Decision, vLLM with its plugin for the bidirectional prompt attention). It takes
    // no model field (the loaded folder answers) and reads one letter per option, 26 per pass;
    // longer lists are knocked out by the server itself (groups of at most 25, the 3 best of each
    // to a final pass; the rest share 0.001), so a question takes up to 255 options here like
    // every 255-option service. `serve` adds a hidden "None of the above" option to every pass
    // (none_check) and reports `none_probability`; the choice stays a listed option. It never
    // truncates: vLLM refuses a prompt over its context (131,072 tokens on spark2) and the server
    // answers 422, which fails the decision. League 1's longest stored request, 251 options, is
    // 27,462 tokens of the 2B's tokenizer as one prompt; its longest pass is 5,318.
    Service {
        provider: "startlux",
        label: "StartLux-Decision (local)",
        base_url: "http://127.0.0.1:19440",
        url_var: "STARTLUX_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: None,
        openai_format: false,
        max_choices: 255,
    },
    // Fastino's released small GLiDE checkpoints (fastino/GLiDE-0.8B @ 9eacdee, GLiDE-2B @
    // 00f122c) behind the server each repository ships (`python -m glide.server`,
    // GLIDE_MAX_BATCH=1), as GLiDE v1.2 runs locally but without Fastino's key: the server takes
    // no key and passes only `state` and `questions` to the model, so no model field is sent.
    // One readout code per option: 255 options per question. It never truncates: a question
    // prompt over GLIDE_MAX_LEN (40,000 tokens) is refused (422); League 1's longest stored
    // request, 251 options, is 28,323 tokens of their tokenizer with the card's prompt.
    Service {
        provider: "glide",
        label: "GLiDE (local)",
        base_url: "http://127.0.0.1:19330",
        url_var: "GLIDE_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: None,
        openai_format: false,
        max_choices: 255,
    },
    // fastino/GLiDE-0.4B @ 6bda7ab, the same server and request, but an encoder (ModernBERT) whose
    // model shortens any prompt over 7,999 tokens (the first 1,024 kept, then the tail) instead of
    // refusing it. Every League 1 stored request of at most 74 options fits (at most 7,833 encoder
    // tokens with the card's prompt); 77 or more never does. So longer play lists are split into
    // groups of at most 74, as for every limited service, and nothing is ever cut; the server runs
    // with GLIDE_MAX_LEN=8006, which refuses (422) any prompt the model would shorten.
    Service {
        provider: "glide-0.4b",
        label: "GLiDE 0.4B (local)",
        base_url: "http://127.0.0.1:19350",
        url_var: "GLIDE_04B_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: None,
        openai_format: false,
        max_choices: 74,
    },
    // OmniJev's OneJev1.6-0.8B (OmniJev/OneJev1.6-0.8B @ bcd88a3) behind Flide 0.1.11, the server
    // its card names (`flide serve --name OmniJev/OneJev1.6-0.8B`, format onejev-slot-v2): the
    // model field must be that name (or an alias); 255 options per question; it never truncates:
    // state plus a question over 32,768 tokens, or a request over 65,536, is refused (422).
    Service {
        provider: "onejev",
        label: "OneJev (Flide)",
        base_url: "http://127.0.0.1:19420",
        url_var: "ONEJEV_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("OmniJev/OneJev1.6-0.8B"),
        openai_format: false,
        max_choices: 255,
    },
    // knowledgator's GLiClass v4 Edge (knowledgator/gliclass-v4-edge @ 885af1a), a zero-shot
    // classifier, behind turkce's runner/servers/gliclass_server.py (the card's own System One
    // mapping: one gliclass 0.1.22 pass per choice question, the state as text, the instructions
    // as prompt, every option's description as a label). No option cap of its own: options,
    // instructions and state share one 16,384-token input, refused (422) above it, never cut.
    // League 1's worst case with its tokenizer: the longest state and instructions (2,197
    // tokens with [CLS], [SEP] and <<SEP>>) plus 218 options at the longest label (65 tokens
    // with <<LABEL>>) is 16,367; so longer play lists are split into groups of at most 218.
    // The model field must name the checkpoint (or be absent).
    Service {
        provider: "gliclass",
        label: "GLiClass (local)",
        base_url: "http://127.0.0.1:19480",
        url_var: "GLICLASS_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("knowledgator/gliclass-v4-edge"),
        openai_format: false,
        max_choices: 218,
    },
    // sthanika-ai's Sieve-31B-v3 (@ 8fcee85; Gemma 4 31B full fine-tune, letter readout) behind
    // the server its card names, sieve-serve of github.com/sthanika-ai/Sieve @ 1e64657 (0.5.1):
    // the same state and questions at /v1/decide, no model field (it would be ignored), text
    // only; answers rounded to 4 places, usage without token counts. Up to 255 options per
    // question (its label count; validate_questions refuses more with 422). It never
    // truncates; it has no token limit of its own as served (no max_tokens), the model's
    // context is 262,144. League 1's longest stored request (251 options) is a 28,271-token
    // pass with its tokenizer and renderer (each request runs in 2 option orders).
    Service {
        provider: "sieve",
        label: "Sieve (local)",
        base_url: "http://127.0.0.1:19370",
        url_var: "SIEVE_BASE_URL",
        path: "/v1/decide",
        key_vars: &[],
        key_required: false,
        default_model: None,
        openai_format: false,
        max_choices: 255,
    },
    // Turion AI's turion-jev-31b (@ 866c0fc; Gemma 4 31B LoRA merge, option-code readout)
    // behind the server its package ships (python -m turion_jev.serve, vLLM in process, FP8 at
    // load): the same request at /v1/systemone; the model field is ignored, so none is sent;
    // text only; probabilities rounded to 6 places, no confidence. 255 one-token codes per
    // question (more is refused, 422); a prompt over --max-len (65,536 tokens) is refused (422),
    // never cut.
    Service {
        provider: "turion-jev",
        label: "Turion Jev (local)",
        base_url: "http://127.0.0.1:19380",
        url_var: "TURION_JEV_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: None,
        openai_format: false,
        max_choices: 255,
    },
    // Liquid AI's open d1-2B (LiquidAI/d1-2B @ 10e7671; LFM3-VL-2B base, one forward pass,
    // option codes A..Z then AA..) behind logic's d1_server.py, the card's model.system_one
    // call unchanged (transformers, BF16, the snapshot's own code): the System One request at
    // /v1/systemone, the model field naming the checkpoint (another name is refused, 400).
    // 255 options per question get distinct single-token codes. Its context is 128,000
    // positions; nothing in its code shortens a prompt, and a request it cannot answer is
    // refused (400), never cut. League 1's longest stored request (251 options) is 20,759
    // tokens with its tokenizer and prompt.
    Service {
        provider: "d1-local",
        label: "Liquid d1 (local)",
        base_url: "http://127.0.0.1:19260",
        url_var: "D1_LOCAL_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: Some("LiquidAI/d1-2B"),
        openai_format: false,
        max_choices: 255,
    },
    // Strands Agents' strands-decider-2B-hobson-v21 (@ 2b52a62; LoRA and pointer head on
    // Qwen3.5-2B-Base) behind the server its package ships (strands-decider serve, BF16): the
    // System One request at /v1/systemone; the model field is ignored, so none is sent. Served
    // with --strict-window: a prompt over the checkpoint's 4,096-token window is refused (422),
    // never cut (without it the server cuts the state). With its tokenizer and renderer the
    // state plus the 13 longest options of any League 1 stored request is at most 4,025
    // tokens (14 can reach 4,143), so longer play lists are split into groups of at most 13.
    Service {
        provider: "strands",
        label: "Strands Decider (local)",
        base_url: "http://127.0.0.1:19270",
        url_var: "STRANDS_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: None,
        openai_format: false,
        max_choices: 13,
    },
    // Metask Lab's Metask-Jev-4B (wayfind/metask-jev-4b-policy-mix @ ea20fe8; Qwen3.5-4B with
    // its LoRA merged, one letter per option) behind logic's metask-jev server.py (the vendor's
    // jev_scorer and prompt, BF16): the System One request at /v1/systemone; the model field is
    // ignored, so none is sent. It never truncates: a prompt over 4,096 tokens or a list over 26
    // options is refused (400). With its tokenizer and prompt the state plus the 11 longest
    // options of any League 1 stored request is at most 4,008 tokens (12 can reach 4,135), so
    // longer play lists are split into groups of at most 11.
    Service {
        provider: "metask",
        label: "Metask-Jev (local)",
        base_url: "http://127.0.0.1:19250",
        url_var: "METASK_BASE_URL",
        path: "/v1/systemone",
        key_vars: &[],
        key_required: false,
        default_model: None,
        openai_format: false,
        max_choices: 11,
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

/// Whether the service refused the request (a 4xx other than 425 Too Early).
fn refused(error: &anyhow::Error) -> bool {
    error.chain().any(|e| {
        e.downcast_ref::<http::StatusError>()
            .is_some_and(|s| s.status.is_client_error() && s.status.as_u16() != 425)
    })
}
