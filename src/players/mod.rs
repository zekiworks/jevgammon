//! AI players. A player receives the legal play list and returns one index.

mod decision;
mod llm;
pub mod prompt;

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

use anyhow::{Result, bail};

use crate::auth::{self, Credentials, Subscription};
use crate::board::{Board, Play};
use crate::db::Exchange;
use crate::runner::Clock;

pub struct DecisionRequest<'a> {
    /// Mover's perspective.
    pub board: &'a Board,
    pub dice: (u8, u8),
    /// The legal plays and their notations, same order.
    pub plays: &'a [Play],
    pub notations: &'a [String],
    pub my_score: u32,
    pub opp_score: u32,
    pub round: u32,
    pub rounds: u32,
    /// 1 or 2: game within the round; game 2 swaps seats and repeats game 1's dice.
    pub leg: u8,
    /// Simple Delay clock; `None` when the match has no clock.
    pub clock: Option<Clock>,
    /// Bank left in this game.
    pub my_clock: Option<Duration>,
    pub opp_clock: Option<Duration>,
    /// 1-based turn of this game, both sides counted.
    pub turn_no: u32,
    /// The game is decided on pip count after this turn; `None` = no limit.
    pub max_turns: Option<u32>,
    /// The deciding player (1 or 2), to tell its own moves in `history` from the opponent's.
    pub player: u8,
    /// Every turn of this game so far, oldest first.
    pub history: &'a [PastMove],
}

/// One turn already played in the current game.
pub struct PastMove {
    pub turn_no: u32,
    /// 1 or 2.
    pub player: u8,
    pub dice: (u8, u8),
    /// In the mover's own numbering; empty when it had no legal move.
    pub notation: String,
}

pub struct Decision {
    pub index: usize,
    /// No valid answer (every LLM reply rejected, or a decision service refused); the
    /// first legal play was used.
    pub fallback: bool,
    pub exchanges: Vec<Exchange>,
    pub input_tokens: u64,
    pub output_tokens: u64,
}

pub struct Player {
    pub spec: String,
    backend: Backend,
}

enum Backend {
    Llm(llm::LlmClient),
    Decision(decision::DecisionClient),
}

/// Shared inputs for building players.
pub struct Setup {
    pub http: reqwest::Client,
    pub qfork_root: PathBuf,
    pub local_url: String,
    pub openai: Arc<Credentials>,
    pub anthropic: Arc<Credentials>,
}

impl Setup {
    pub fn new(qfork_root: PathBuf, local_url: String) -> Self {
        let http = crate::http::client();
        Setup {
            openai: Arc::new(Credentials::new(
                Subscription::OpenAi,
                qfork_root.clone(),
                http.clone(),
            )),
            anthropic: Arc::new(Credentials::new(
                Subscription::Anthropic,
                qfork_root.clone(),
                http.clone(),
            )),
            http,
            qfork_root,
            local_url,
        }
    }
}

impl Player {
    /// Parses `provider/model` (or a bare decision provider such as `jev`) and resolves
    /// its credentials.
    pub async fn from_spec(spec: &str, setup: &Setup) -> Result<Self> {
        let (provider, model) = match spec.split_once('/') {
            Some((provider, model)) if !model.is_empty() => (provider, Some(model.to_owned())),
            _ => (spec, None),
        };
        let http = setup.http.clone();
        let need_model = |model: Option<String>| match model {
            Some(model) => Ok(model),
            None => bail!("model spec `{spec}` needs a model name: {provider}/<model>"),
        };
        if let Some(service) = decision::service(provider) {
            return Ok(Player {
                spec: spec.to_owned(),
                backend: Backend::Decision(decision::DecisionClient::new(http, service, model)?),
            });
        }
        let backend = match provider.to_ascii_lowercase().as_str() {
            "openai" => {
                // Fail at startup, not on the first move, when no login exists.
                setup.openai.token().await?;
                // Codex model ids are lowercase (`openai/gpt-5.6-Sol` → `gpt-5.6-sol`).
                let model = need_model(model)?.to_ascii_lowercase();
                Backend::Llm(llm::LlmClient::openai_subscription(
                    http,
                    model,
                    setup.openai.clone(),
                ))
            }
            "anthropic" | "claude" => {
                setup.anthropic.token().await?;
                Backend::Llm(llm::LlmClient::anthropic_subscription(
                    http,
                    need_model(model)?,
                    setup.anthropic.clone(),
                ))
            }
            "gemini" | "google" => Backend::Llm(llm::LlmClient::gemini(
                http,
                need_model(model)?,
                auth::gemini_api_key(&setup.qfork_root)?,
            )),
            "ollama" => {
                let host = std::env::var("OLLAMA_HOST")
                    .unwrap_or_else(|_| "http://localhost:11434".into());
                let host = if host.contains("://") {
                    host
                } else {
                    format!("http://{host}")
                };
                Backend::Llm(llm::LlmClient::openai_compatible(
                    http,
                    need_model(model)?,
                    format!("{}/v1", host.trim_end_matches('/')),
                    None,
                ))
            }
            "local" => Backend::Llm(llm::LlmClient::openai_compatible(
                http,
                need_model(model)?,
                setup.local_url.trim_end_matches('/').to_owned(),
                std::env::var("LOCAL_API_KEY")
                    .ok()
                    .filter(|k| !k.is_empty()),
            )),
            other => {
                let decision: Vec<&str> = decision::SERVICES.iter().map(|s| s.provider).collect();
                bail!(
                    "unknown provider `{other}` in `{spec}`; use openai/, anthropic/, gemini/, ollama/, local/, or a decision service: {}",
                    decision.join(", ")
                )
            }
        };
        Ok(Player {
            spec: spec.to_owned(),
            backend,
        })
    }

    pub async fn decide(&self, req: &DecisionRequest<'_>) -> Result<Decision> {
        match &self.backend {
            Backend::Llm(client) => client.decide(req).await,
            Backend::Decision(client) => client.decide(req).await,
        }
    }

    /// Makes sure the model answers before a match starts, so a cold start never runs
    /// on its clock. Decision services get a two-option request until they answer; LLM
    /// players need none. Returns the time it took.
    pub async fn warm_up(&self) -> Result<Duration> {
        match &self.backend {
            Backend::Llm(_) => Ok(Duration::ZERO),
            Backend::Decision(client) => client.warm_up().await,
        }
    }
}
