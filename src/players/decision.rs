//! Decision models: TypeSafe's System One format (Jev and the services that copy it) and
//! OpenAI's Decisions API. The legal plays become the options of one `choice` question, in
//! the seeded option order, and the service returns its probability for each.

use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

use anyhow::{Context as _, Result, bail};
use serde::{Deserialize, Serialize};
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

    /// Routes that can never carry a notes/examples block: Clef cuts the state's tail silently
    /// (`state_ids[: max_length - fixed_length]`), Open-Jev limits each candidate prompt to
    /// 4,096 tokens. A player with a block on them fails at start.
    fn takes_blocks(&self) -> bool {
        !matches!(self.provider, "clef" | "open-jev")
    }
}

/// "Did they improve?" (decision models): the per-request context gate, checked before every
/// request is sent. On failure (or the service's own refusal) the player stops: nothing is
/// shortened and resent.
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum ContextGate {
    /// Hosted routes: our conservative context guard (a heuristic policy, not proof that the
    /// whole input is read). Upper bound = request body bytes counted as tokens + the
    /// documented wrapper allowance (`wrapper_tokens`; undocumented: 4,096) + `output_tokens`;
    /// refused when above `limit_tokens`. No documented limit: every request is refused (fails
    /// closed).
    Client {
        limit_tokens: Option<u64>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        wrapper_tokens: Option<u64>,
        #[serde(default)]
        output_tokens: u64,
    },
    /// Local routes: the server's own pre-inference gate refuses an over-limit request (400 or
    /// 422) before the model runs; that refusal stops the player.
    Server,
    /// Learning pilot (decision mode): the server's own pre-inference gate refuses an over-limit
    /// request (400, 413 or 422); that request is an invalid answer (no option named, as an
    /// unparseable reply) and the player goes on. Nothing is shortened and resent.
    ServerInvalid,
}

impl ContextGate {
    /// `Ok` when a request of `body_bytes` may be sent, else why not.
    pub fn admits(&self, body_bytes: usize) -> std::result::Result<(), String> {
        let ContextGate::Client {
            limit_tokens,
            wrapper_tokens,
            output_tokens,
        } = self
        else {
            return Ok(());
        };
        let Some(limit) = limit_tokens else {
            return Err("the route has no documented limit (fails closed)".into());
        };
        let wrapper = wrapper_tokens.unwrap_or(TEMPLATE_MARGIN as u64);
        let bound = body_bytes as u64 + wrapper + output_tokens;
        if bound > *limit {
            return Err(format!(
                "conservative context guard: upper bound {bound} tokens ({body_bytes} request \
                 bytes + {wrapper} wrapper + {output_tokens} output) > documented limit {limit}"
            ));
        }
        Ok(())
    }
}

/// The "Did they improve?" settings of a decision player (all `None` in the leagues).
#[derive(Clone, Debug, Default)]
pub struct Extras {
    pub prompt_note: Option<String>,
    pub prompt_note_file: Option<PathBuf>,
    pub context_gate: Option<ContextGate>,
    pub expect_route: Option<super::llm::ExpectRoute>,
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
    extras: Extras,
    /// Set by a failed context gate, a context refusal or a failed route check: no further
    /// request is sent.
    stopped: AtomicBool,
}

impl DecisionClient {
    /// `model` overrides the service's default; it is ignored by services without a
    /// `model` field. `base_url` (a player config's) overrides the service's URL and its
    /// environment variable. `budget` meters every request attempt. Fails when a required
    /// API key is missing, or when a block (`prompt_note`/`prompt_note_file`) is set on a
    /// route that cannot carry one or without a context gate fit for the route.
    pub fn new(
        http: reqwest::Client,
        service: &'static Service,
        model: Option<String>,
        base_url: Option<&str>,
        budget: Option<Arc<Ledger>>,
        extras: Extras,
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
        let url = format!("{}{}", base.trim_end_matches('/'), service.path);
        check_extras(service, &url, &extras)?;
        Ok(DecisionClient {
            http,
            service,
            key,
            model: service
                .default_model
                .map(|default| model.unwrap_or_else(|| default.to_owned())),
            url,
            budget,
            extras,
            stopped: AtomicBool::new(false),
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

    /// With a budget, each attempt (retries included) first reserves its worst case, and is
    /// refused before the call when spent + reserved + that would pass the cap. Worst case:
    /// one input token per byte of the JSON body plus `TEMPLATE_MARGIN` tokens, and as many
    /// output tokens as body bytes. A byte-level BPE tokenizer (the Qwen family Drex is
    /// built on) never makes a token of less than one byte of the UTF-8 text it encodes, and
    /// the body holds every byte of the state, instructions and options the model reads (JSON
    /// escaping only adds bytes); the margin covers the provider's own system prompt and chat
    /// template, which it does not publish. An answer with usage is booked at it; a 200
    /// without readable usage, an error status the service does not document as unbilled
    /// (`Service::unbilled`), and an attempt without a response keep the worst case.
    async fn send(&self, body: &Value, retry: &RetryTime) -> Result<String> {
        if self.stopped.load(Ordering::SeqCst) {
            bail!(
                // Worded without the CONTEXT GATE / CONTEXT REFUSAL / ROUTE CHECK markers (the
                // harness finds the first request's own marker; SQLite LIKE ignores case).
                "STOPPED: an earlier request of {} failed a pre-send or reply check; no further \
                 request is sent",
                self.service.label
            );
        }
        let bytes = body.to_string().len();
        if let Some(gate) = &self.extras.context_gate
            && let Err(reason) = gate.admits(bytes)
        {
            self.stopped.store(true, Ordering::SeqCst);
            bail!(
                "CONTEXT GATE: {} request refused before sending: {reason}",
                self.service.label
            );
        }
        let make = || {
            let request = self.http.post(&self.url).json(body);
            match &self.key {
                Some(key) => request.bearer_auth(key),
                None => request,
            }
        };
        let guard = http::Guard {
            stop: Some(&self.stopped),
            quota_fatal: false,
        };
        let failed = |e: http::CallError| {
            let error = e
                .into_anyhow()
                .context(format!("{} request failed", self.service.label));
            // Under a stopping context gate, the service's own refusal (400/413/422) is the second
            // gate: the player stops; nothing is shortened and resent.
            if matches!(
                self.extras.context_gate,
                Some(ContextGate::Client { .. } | ContextGate::Server)
            ) && context_refusal(&error)
            {
                self.stopped.store(true, Ordering::SeqCst);
                return error.context("CONTEXT REFUSAL: the service refused the request");
            }
            error
        };
        let Some(ledger) = &self.budget else {
            let text = http::send(make, retry, guard).await.map_err(failed)?;
            return self.check_identity(body, text);
        };
        let worst = ledger.worst_case(bytes + TEMPLATE_MARGIN, bytes as u64);
        let (text, hold) =
            http::send_metered(make, retry, ledger, worst, self.service.unbilled(), guard)
                .await
                .map_err(failed)?;
        let value: Option<Value> = serde_json::from_str(&text).ok();
        let tokens = |key: &str| {
            value
                .as_ref()
                .and_then(|v| v.pointer(&format!("/usage/{key}")))
                .and_then(Value::as_u64)
        };
        match tokens("input_tokens") {
            Some(input_tokens) => {
                hold.settle(
                    Usage {
                        input_tokens,
                        cached_tokens: 0,
                        output_tokens: tokens("output_tokens").unwrap_or(0),
                        reasoning_tokens: 0,
                    },
                    None,
                );
            }
            None => hold.kept("200 without readable usage: booked at the worst case"),
        }
        self.check_identity(body, text)
    }

    /// "Did they improve?": the reply must name a frozen model id (`expect_route`) before it is
    /// used; a reply that does not (or carries no identity) stops the player and is logged.
    fn check_identity(&self, body: &Value, text: String) -> Result<String> {
        let Some(expect) = &self.extras.expect_route else {
            return Ok(text);
        };
        if let Err(reason) = super::llm::route_identity(&text, expect) {
            self.stopped.store(true, Ordering::SeqCst);
            let fields = super::llm::identity_fields(&text, expect);
            if let Some(log) = &expect.reject_log {
                let line = json!({"at": chrono::Utc::now().to_rfc3339(), "identity": fields,
                    "reason": reason, "request": body, "response": text});
                use std::io::Write as _;
                let written = std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(log)
                    .and_then(|mut f| writeln!(f, "{line}"));
                if let Err(error) = written {
                    eprintln!("route check: rejection log {}: {error}", log.display());
                }
            }
            let shown: String = text.chars().take(1500).collect();
            bail!("ROUTE CHECK: {reason}; identity {fields}; response: {shown}");
        }
        Ok(text)
    }

    /// The notes/examples block for this request: the file's text when it is not empty
    /// (re-read every request: it changes between games), else `prompt_note`.
    fn block(&self) -> Result<Option<String>> {
        if let Some(path) = &self.extras.prompt_note_file {
            let text = std::fs::read_to_string(path)
                .with_context(|| format!("prompt_note_file {}", path.display()))?;
            if !text.trim().is_empty() {
                return Ok(Some(text));
            }
        }
        Ok(self
            .extras
            .prompt_note
            .clone()
            .filter(|t| !t.trim().is_empty()))
    }

    /// The league state with the block, if any, at its start (System One `state`, OpenAI
    /// `input`), separated by a blank line; the block is never shortened.
    fn state_with_block(&self, state: &str) -> Result<String> {
        Ok(match self.block()? {
            Some(block) => format!("{}\n\n{state}", block.trim_end()),
            None => state.to_owned(),
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
        let state = self.state_with_block(&state(req))?;
        let body = self.body(&state, instructions(req), &plays);
        let started = Instant::now();
        let retry_before = req.retry.get();
        let text = match self.send(&body, req.retry).await {
            Ok(text) => text,
            // server_invalid: the refusal is this question's invalid answer, kept with its error.
            Err(error)
                if self.extras.context_gate == Some(ContextGate::ServerInvalid)
                    && context_refusal(&error) =>
            {
                decision.exchanges.push(Exchange {
                    request: body.to_string(),
                    response: None,
                    error: Some(format!("CONTEXT REFUSAL (invalid answer): {error:#}")),
                    latency_ms: started.elapsed().as_millis() as u64,
                    identity: None,
                });
                return Ok(None);
            }
            Err(error) => return Err(error),
        };
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
            identity: None,
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

/// Whether the service refused the request as too long or malformed (400, 413, 422): under a
/// context gate, the route's documented refusal of an over-limit request.
fn context_refusal(error: &anyhow::Error) -> bool {
    error.chain().any(|e| {
        e.downcast_ref::<http::StatusError>()
            .is_some_and(|s| matches!(s.status.as_u16(), 400 | 413 | 422))
    })
}

/// Start-up checks of a decision player's "Did they improve?" settings: a block needs a route
/// that can carry one and a context gate; a hosted route (an `https` URL; our local servers
/// are plain `http`) needs our pre-send guard (`Client`), never only its own.
pub fn check_extras(service: &Service, url: &str, extras: &Extras) -> Result<()> {
    let has_block = extras.prompt_note.is_some() || extras.prompt_note_file.is_some();
    if has_block && !service.takes_blocks() {
        bail!(
            "{}: this route cannot carry a notes/examples block (not tested)",
            service.label
        );
    }
    if has_block && extras.context_gate.is_none() {
        bail!(
            "{}: a decision player with a block needs a context_gate",
            service.label
        );
    }
    if url.starts_with("https://")
        && matches!(
            extras.context_gate,
            Some(ContextGate::Server | ContextGate::ServerInvalid)
        )
    {
        bail!(
            "{}: a hosted route needs our pre-send guard (context_gate kind client)",
            service.label
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

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
            Extras::default(),
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
            extras: Extras::default(),
            stopped: AtomicBool::new(false),
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

    /// A server answering every request with `status` and `body`, keeping each request body
    /// whole (read to its content-length); returns its URL and the bodies.
    fn serve_capture(status: u16, body: String) -> (String, Arc<parking_lot::Mutex<Vec<String>>>) {
        use std::io::{BufRead, BufReader, Read, Write};
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("http://{}", listener.local_addr().unwrap());
        let bodies = Arc::new(parking_lot::Mutex::new(Vec::new()));
        let seen = bodies.clone();
        std::thread::spawn(move || {
            for stream in listener.incoming() {
                let mut stream = stream.unwrap();
                let mut reader = BufReader::new(stream.try_clone().unwrap());
                let mut length = 0usize;
                loop {
                    let mut line = String::new();
                    reader.read_line(&mut line).unwrap();
                    if line == "\r\n" || line.is_empty() {
                        break;
                    }
                    if let Some((name, value)) = line.split_once(':')
                        && name.eq_ignore_ascii_case("content-length")
                    {
                        length = value.trim().parse().unwrap();
                    }
                }
                let mut request = vec![0u8; length];
                reader.read_exact(&mut request).unwrap();
                seen.lock().push(String::from_utf8(request).unwrap());
                let _ = write!(
                    stream,
                    "HTTP/1.1 {status} X\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{body}",
                    body.len()
                );
            }
        });
        (url, bodies)
    }

    struct Position {
        board: crate::board::Board,
        plays: Vec<crate::board::Play>,
        notations: Vec<String>,
        order: Vec<usize>,
        retry: RetryTime,
    }

    impl Position {
        fn new() -> Self {
            let mut board = crate::board::Board::start();
            board.pts[12] = 3;
            board.pts[7] = 5;
            let plays = board.legal_plays(2, 1);
            let notations = plays.iter().map(|p| p.notation()).collect();
            let order = (0..plays.len()).collect();
            Position {
                board,
                plays,
                notations,
                order,
                retry: RetryTime::default(),
            }
        }

        fn request(&self) -> DecisionRequest<'_> {
            DecisionRequest {
                board: &self.board,
                dice: (2, 1),
                plays: &self.plays,
                notations: &self.notations,
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
                order: &self.order,
                seed: 7,
                version: crate::players::prompt::PromptVersion::BgV2,
                retry: &self.retry,
            }
        }
    }

    fn gate(limit: Option<u64>) -> ContextGate {
        ContextGate::Client {
            limit_tokens: limit,
            wrapper_tokens: None,
            output_tokens: 0,
        }
    }

    /// A ~60 kB notes block with a marker at each end: nothing in it may be cut.
    fn long_block() -> String {
        let mut block = String::from(
            "=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ===\nFIRST-LINE-MARKER\n",
        );
        for k in 0..1500 {
            block.push_str(&format!(
                "- lesson {k}: keep the blot count low when the opponent has a strong board.\n"
            ));
        }
        block.push_str("LAST-LINE-MARKER\n=== END OF NOTES ===\n");
        block
    }

    /// The block (re-read from its file before every request) reaches the start of `state`
    /// (System One) or `input` (OpenAI) whole; the league state, instructions and every
    /// option follow byte-identical; the stored exchange is the exact body sent.
    #[tokio::test]
    async fn the_block_reaches_the_start_of_state_untruncated_in_both_formats() {
        let position = Position::new();
        let req = position.request();
        let shown: Vec<usize> = (0..position.plays.len().min(5)).collect();
        let dir = std::env::temp_dir().join(format!("decision-block-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&dir).unwrap();
        let file = dir.join("note.txt");
        let block = long_block();
        for (provider, model, field, response) in [
            (
                "drex-max",
                "drex-max-v1",
                "/state",
                json!({"model": "drex-max-v1", "answers": {QUESTION: {"type": "choice", "choice": position.notations[shown[1]]}}}),
            ),
            (
                "openai-decisions",
                "gpt-6-luna",
                "/input",
                json!({"model": "gpt-6-luna", "answers": [{"name": QUESTION, "type": "choice", "choice": position.notations[shown[1]]}]}),
            ),
        ] {
            let (url, bodies) = serve_capture(200, response.to_string());
            let mut client = client(provider, model, Some(&url), Some("k"));
            client.extras = Extras {
                prompt_note: None,
                prompt_note_file: Some(file.clone()),
                context_gate: Some(gate(Some(1_000_000))),
                expect_route: None,
            };
            // An empty file: the league request, unchanged.
            std::fs::write(&file, "").unwrap();
            let mut decision = Decision::default();
            assert_eq!(
                client.choose(&req, &shown, &mut decision).await.unwrap(),
                Some(shown[1])
            );
            // The block written between requests is read for the next one.
            std::fs::write(&file, &block).unwrap();
            assert_eq!(
                client.choose(&req, &shown, &mut decision).await.unwrap(),
                Some(shown[1])
            );
            let sent = bodies.lock().clone();
            assert_eq!(sent.len(), 2, "{provider}");
            let plain: Value = serde_json::from_str(&sent[0]).unwrap();
            let noted: Value = serde_json::from_str(&sent[1]).unwrap();
            let league = state(&req);
            assert_eq!(
                plain.pointer(field).unwrap(),
                &Value::from(league.clone()),
                "{provider}"
            );
            let expected = format!("{}\n\n{league}", block.trim_end());
            assert_eq!(
                noted.pointer(field).unwrap(),
                &Value::from(expected),
                "{provider}"
            );
            let text = noted.pointer(field).unwrap().as_str().unwrap();
            assert!(
                text.starts_with("=== NOTES FROM YOUR EARLIER GAMES")
                    && text.contains("LAST-LINE-MARKER")
            );
            // Everything but the state is the league request's.
            let strip = |mut v: Value| {
                v.as_object_mut().unwrap().remove(&field[1..]);
                v
            };
            assert_eq!(strip(plain), strip(noted.clone()), "{provider}");
            // The stored request is the exact body sent.
            assert_eq!(decision.exchanges[1].request, sent[1], "{provider}");
        }
    }

    /// The pre-send gate: no documented limit refuses (fails closed), an upper bound over the
    /// limit refuses, and either stops the player; nothing reaches the server.
    #[tokio::test]
    async fn the_context_gate_fails_closed_and_stops_the_player() {
        let position = Position::new();
        let req = position.request();
        let shown: Vec<usize> = (0..position.plays.len().min(5)).collect();
        let ok = json!({"model": "jev-1.14.0", "answers": {QUESTION: {"type": "choice", "choice": position.notations[shown[0]]}}});
        for limit in [None, Some(4_096 + 100)] {
            let (url, bodies) = serve_capture(200, ok.to_string());
            let mut client = client("jev", "jev-1.14.0", Some(&url), Some("k"));
            client.extras = Extras {
                prompt_note: Some("=== NOTES ===\nnote\n=== END ===".into()),
                prompt_note_file: None,
                context_gate: Some(gate(limit)),
                expect_route: None,
            };
            let error = client
                .choose(&req, &shown, &mut Decision::default())
                .await
                .unwrap_err();
            assert!(format!("{error:#}").contains("CONTEXT GATE"), "{error:#}");
            // Stopped: even a request that would fit is not sent.
            client.extras.context_gate = Some(gate(Some(10_000_000)));
            let error = client
                .choose(&req, &shown, &mut Decision::default())
                .await
                .unwrap_err();
            assert!(format!("{error:#}").contains("STOPPED"), "{error:#}");
            assert!(bodies.lock().is_empty());
        }
        // The bound: request bytes as tokens + wrapper (default 4,096) + output.
        assert!(gate(Some(5_096)).admits(1_000).is_ok());
        assert!(gate(Some(5_095)).admits(1_000).is_err());
        let documented = ContextGate::Client {
            limit_tokens: Some(32_000),
            wrapper_tokens: Some(100),
            output_tokens: 10,
        };
        assert!(documented.admits(31_890).is_ok() && documented.admits(31_891).is_err());
        // No empirical token-per-byte ratio is accepted (Zeki #3725).
        assert!(
            serde_json::from_str::<ContextGate>(
                r#"{"kind":"client","limit_tokens":32000,"tokens_per_byte":0.5}"#
            )
            .is_err()
        );
        assert!(ContextGate::Server.admits(usize::MAX).is_ok());
        // Config form.
        let parsed: ContextGate =
            serde_json::from_str(r#"{"kind":"client","limit_tokens":32000}"#).unwrap();
        assert_eq!(parsed, gate(Some(32_000)));
        assert!(serde_json::from_str::<ContextGate>(r#"{"kind":"client","limit":32000}"#).is_err());
    }

    /// The service's own refusal (422 too long) under a gate stops the player, marked as a
    /// context refusal; nothing is resent.
    #[tokio::test]
    async fn a_context_refusal_stops_the_player() {
        let position = Position::new();
        let req = position.request();
        let shown: Vec<usize> = (0..position.plays.len().min(5)).collect();
        let (url, bodies) = serve_capture(422, r#"{"error":"request too long"}"#.into());
        let mut client = client("drex-max", "drex-max-v1", Some(&url), None);
        client.extras.context_gate = Some(ContextGate::Server);
        let error = client
            .choose(&req, &shown, &mut Decision::default())
            .await
            .unwrap_err();
        assert!(
            format!("{error:#}").contains("CONTEXT REFUSAL"),
            "{error:#}"
        );
        let error = client
            .choose(&req, &shown, &mut Decision::default())
            .await
            .unwrap_err();
        assert!(format!("{error:#}").contains("STOPPED"), "{error:#}");
        assert_eq!(bodies.lock().len(), 1);
    }

    /// server_invalid (learning pilot, decision mode): the service's refusal is an invalid
    /// answer with its error kept; the player is not stopped and the next request is sent.
    #[tokio::test]
    async fn a_refusal_under_server_invalid_is_an_invalid_answer() {
        let position = Position::new();
        let req = position.request();
        let shown: Vec<usize> = (0..position.plays.len().min(5)).collect();
        let (url, bodies) = serve_capture(422, r#"{"error":"request too long"}"#.into());
        let mut client = client("drex-max", "drex-max-v1", Some(&url), None);
        client.extras.context_gate = Some(ContextGate::ServerInvalid);
        for _ in 0..2 {
            let mut decision = Decision::default();
            let chosen = client.choose(&req, &shown, &mut decision).await.unwrap();
            assert_eq!(chosen, None);
            let error = decision.exchanges[0].error.as_deref().unwrap();
            assert!(error.contains("CONTEXT REFUSAL (invalid answer)"), "{error}");
        }
        assert_eq!(bodies.lock().len(), 2);
        let parsed: ContextGate = serde_json::from_str(r#"{"kind":"server_invalid"}"#).unwrap();
        assert_eq!(parsed, ContextGate::ServerInvalid);
    }

    /// A reply naming a model outside the frozen ids stops the player and is logged.
    #[tokio::test]
    async fn a_reply_with_another_model_id_stops_the_player() {
        let position = Position::new();
        let req = position.request();
        let shown: Vec<usize> = (0..position.plays.len().min(5)).collect();
        let reply = json!({"model": "celeris-1.1-decision", "answers": {QUESTION: {"type": "choice", "choice": position.notations[shown[0]]}}});
        let (url, bodies) = serve_capture(200, reply.to_string());
        let log =
            std::env::temp_dir().join(format!("decision-reject-{}.jsonl", uuid::Uuid::new_v4()));
        let mut client = client("celeris", "celeris-1-decision", Some(&url), Some("k"));
        client.extras.expect_route = Some(super::super::llm::ExpectRoute {
            models: vec!["celeris-1-decision".into()],
            provider: None,
            model_pointer: None,
            provider_pointer: None,
            reject_log: Some(log.clone()),
            allow_dated: false,
        });
        let error = client
            .choose(&req, &shown, &mut Decision::default())
            .await
            .unwrap_err();
        assert!(format!("{error:#}").contains("ROUTE CHECK"), "{error:#}");
        assert!(
            std::fs::read_to_string(&log)
                .unwrap()
                .contains("celeris-1.1-decision")
        );
        assert!(
            client
                .choose(&req, &shown, &mut Decision::default())
                .await
                .is_err()
        );
        assert_eq!(bodies.lock().len(), 1);
    }

    #[test]
    fn a_block_needs_a_route_that_takes_it_and_a_fitting_gate() {
        let with_block = |gate| Extras {
            prompt_note: Some("notes".into()),
            prompt_note_file: None,
            context_gate: gate,
            expect_route: None,
        };
        let jev = service("jev").unwrap();
        let hosted = "https://api.typesafe.ai/v1/systemone";
        let local = "http://127.0.0.1:18104/v1/systemone";
        assert!(check_extras(jev, hosted, &with_block(None)).is_err());
        assert!(check_extras(jev, hosted, &with_block(Some(ContextGate::Server))).is_err());
        assert!(check_extras(jev, hosted, &with_block(Some(gate(Some(32_000))))).is_ok());
        for provider in ["clef", "open-jev"] {
            let s = service(provider).unwrap();
            assert!(check_extras(s, local, &with_block(Some(ContextGate::Server))).is_err());
        }
        // A local server reached through a keyed service (Fastino GLiDE v1.2 behind `fastino`)
        // keeps its own pre-inference gate.
        let fastino = service("fastino").unwrap();
        assert!(check_extras(fastino, local, &with_block(Some(ContextGate::Server))).is_ok());
        let drex = service("drex-max").unwrap();
        assert!(check_extras(drex, local, &with_block(Some(ContextGate::Server))).is_ok());
        assert!(check_extras(jev, hosted, &Extras::default()).is_ok());
    }
}
