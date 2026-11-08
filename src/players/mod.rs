//! AI players. A player receives the legal plays in the seeded option order and returns
//! one of them; an invalid answer is replaced by a random legal play.

pub mod baseline;
mod decision;
pub mod gnubg;
mod llm;
pub mod order;
pub mod prompt;

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::{Duration, Instant};

use anyhow::{Result, bail};
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::auth::{self, Credentials, Subscription};
use crate::board::{Board, Play};
use crate::db::Exchange;
use crate::dice::{Dice, derive_seed};
use crate::http::RetryTime;
use crate::runner::Clock;
use prompt::PromptVersion;

pub struct DecisionRequest<'a> {
    /// Mover's perspective.
    pub board: &'a Board,
    pub dice: (u8, u8),
    /// The legal plays and their notations, same order (move generation).
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
    /// Seeded option order: `order[k]` is the index into `plays` shown k-th (letter k).
    pub order: &'a [usize],
    /// Seed of this decision (unique per match, round, game and turn), for the random play
    /// that replaces an invalid answer and for random players.
    pub seed: u64,
    pub version: PromptVersion,
    /// Failed attempts and backoff waits of this decision, kept off the clock.
    pub retry: &'a RetryTime,
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

#[derive(Debug, Default)]
pub struct Decision {
    /// Index into `DecisionRequest::plays` (move-generation order, not the shown order).
    pub index: usize,
    /// The answer named no option (unparseable reply, a letter outside the options, a
    /// refusal); `index` is then a uniformly random legal play seeded per decision.
    pub invalid: bool,
    pub exchanges: Vec<Exchange>,
    pub input_tokens: u64,
    pub output_tokens: u64,
    /// `(index into plays, probability)` for every option of the deciding request; empty
    /// when the player gives none.
    pub probabilities: Vec<(usize, f64)>,
    /// Where `probabilities` came from: `logprobs` (answer-letter token probabilities),
    /// `decision` (a decision model's own distribution), or `choice_only` (one letter, no
    /// probabilities: the chosen play gets 1).
    pub probability_source: Option<&'static str>,
    /// Options per request when the play list was split into groups (more legal plays than
    /// the player takes at once); `None` for a single request.
    pub group_size: Option<usize>,
    /// Reasoning tokens over the decision's requests, when the provider reports them.
    pub reasoning_tokens: Option<u64>,
    /// Dollars the provider reported for the decision's requests (OpenRouter).
    pub reported_cost: Option<f64>,
}

impl Decision {
    pub fn new(index: usize) -> Self {
        Decision {
            index,
            ..Decision::default()
        }
    }
}

/// A player that decides locally (baselines, GNUbg); may block.
pub trait Engine: Send + Sync {
    fn decide(&self, req: &DecisionRequest<'_>) -> Result<Decision>;
}

/// API list price per million tokens, for `turns.cost_usd`.
#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq)]
pub struct Price {
    pub input_per_mtok: f64,
    pub output_per_mtok: f64,
}

/// One entrant: a name, a spec (`provider/model`), and the settings that the spec alone
/// cannot carry. Stored in `players.settings`; old entries hold only `name` and `spec`.
#[derive(Clone, Debug, Default, Serialize, Deserialize, PartialEq)]
pub struct PlayerConfig {
    pub name: String,
    pub spec: String,
    /// Logged per decision; defaults to the spec's provider prefix.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,
    /// Logged per decision, e.g. `FP8`; `None` when unknown.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub quantization: Option<String>,
    /// OpenAI-compatible server for `openai-compatible/<model>` (and to override
    /// `--local-url` for `local/<model>`, or a decision service's URL and its environment
    /// variable), e.g. `https://api.example.com/v1`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub base_url: Option<String>,
    /// Environment variable holding that server's API key.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub api_key_env: Option<String>,
    /// Reasoning effort (`low`, `high`, ...). Chat models then reason first and the
    /// letter probabilities are read afterwards; `None` = reasoning off (subscription
    /// models: the provider's default).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reasoning: Option<String>,
    /// Fields merged into every chat-model request body, e.g.
    /// `{"chat_template_kwargs": {"thinking": true}}`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub request: Option<Value>,
    /// Output token limit of a chat-model answer (the reasoning request included).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
    /// Log-probabilities asked per answer token (default 20; Fireworks allows 5).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub top_logprobs: Option<u32>,
    /// `prefill` (default: continue a prefilled `Answer:`) or `answer` (read the answer
    /// letter's log-probabilities from the ordinary response), for OpenAI-compatible
    /// servers.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub letter_readout: Option<String>,
    /// Prefill readout with reasoning off: the assistant text the letter continues (default
    /// `Answer:`), e.g. `<think></think>Answer:` for a model whose chat template opens a
    /// reasoning block on every answer and has no switch to turn it off.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub answer_prefix: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub price: Option<Price>,
    /// Free text kept with the roster (how the setup was pinned, what a level means).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub note: Option<String>,
    /// Hardware the player's server runs on (free text, for the record), e.g. when a
    /// self-hosted model moves to another machine during a league.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub device: Option<String>,
    /// Decisions in flight at once, over all the player's matches and their games (more
    /// queue; the wait is logged as retry time, off the clock); default unlimited, and 4
    /// for `jevgammon ask`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parallel: Option<usize>,
    /// League matches this player plays at once; default 4, unlimited for the local
    /// engines (random, safest, gnubg-weak).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_matches: Option<usize>,
    /// Most chat-model requests started per minute (provider rate limits, e.g. OpenRouter's
    /// 20 per minute per model for new accounts), shared by every player of the same
    /// `rate_group` (default: base URL and spec); default unlimited. Waits for a slot are
    /// logged as retry time.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rpm: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub rate_group: Option<String>,
    /// Hard spending cap with a shared ledger (OpenAI-compatible servers only).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub budget: Option<crate::budget::BudgetConfig>,
}

impl PlayerConfig {
    pub fn new(name: &str, spec: &str) -> Self {
        PlayerConfig {
            name: name.to_owned(),
            spec: spec.to_owned(),
            ..PlayerConfig::default()
        }
    }
}

/// A prebuilt question (Clear-risk Part 2): the decision-service form (`name`, `state`,
/// `instructions`, `options` as `(value, text)`) and the chat form (`system`, `user`, answer
/// `schema` named `schema_name`).
pub struct QuizQuestion<'a> {
    pub name: &'a str,
    pub state: &'a str,
    pub instructions: &'a str,
    pub options: &'a [(String, String)],
    pub system: &'a str,
    pub user: &'a str,
    pub schema: &'a serde_json::Value,
    pub schema_name: &'a str,
}

/// A decision service's chosen value (`None` = invalid) and probabilities by value, or a
/// chat model's answer text.
pub enum QuizReply {
    Choice {
        value: Option<String>,
        probabilities: Vec<(String, f64)>,
    },
    Text(String),
}

pub struct Player {
    pub spec: String,
    pub provider: String,
    pub quantization: Option<String>,
    /// Reasoning effort from the config, as logged with stored-position answers.
    pub reasoning: Option<String>,
    pub price: Option<Price>,
    /// Permits for decisions in flight (`PlayerConfig::parallel`); `None` = unlimited.
    requests: Option<tokio::sync::Semaphore>,
    backend: Backend,
}

enum Backend {
    Llm(llm::LlmClient),
    Decision(decision::DecisionClient),
    Engine(Box<dyn Engine>),
    /// Answers each request with the next scripted shown position (`None` = invalid;
    /// position 0 when the script runs out) and records the groups asked.
    #[cfg(test)]
    Scripted {
        max: usize,
        answers: parking_lot::Mutex<Vec<Option<usize>>>,
        asked: parking_lot::Mutex<Vec<Vec<usize>>>,
    },
}

/// Shared inputs for building players.
pub struct Setup {
    pub http: reqwest::Client,
    pub qfork_root: PathBuf,
    pub local_url: String,
    pub openai: Arc<Credentials>,
    pub anthropic: Arc<Credentials>,
    pub antigravity: Arc<Credentials>,
    pub xai: Arc<Credentials>,
    /// Request pacers by rate-limit group, shared by every player of the group.
    pacers: parking_lot::Mutex<HashMap<String, Arc<Pacer>>>,
}

/// Spaces the requests of a rate-limit group (e.g. both setups of one OpenRouter model) at
/// least `interval` apart.
pub struct Pacer {
    interval: Duration,
    next: tokio::sync::Mutex<Instant>,
}

impl Pacer {
    /// Waits for this request's slot; returns how long it waited.
    pub async fn wait(&self) -> Duration {
        let started = Instant::now();
        let mut next = self.next.lock().await;
        tokio::time::sleep_until((*next).into()).await;
        *next = Instant::now() + self.interval;
        started.elapsed()
    }
}

impl Setup {
    /// The shared pacer of `group` at `rpm` requests per minute.
    fn pacer(&self, group: String, rpm: u32) -> Arc<Pacer> {
        self.pacers
            .lock()
            .entry(group)
            .or_insert_with(|| {
                Arc::new(Pacer {
                    interval: Duration::from_secs_f64(60.0 / f64::from(rpm)),
                    next: tokio::sync::Mutex::new(Instant::now()),
                })
            })
            .clone()
    }

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
            antigravity: Arc::new(Credentials::new(
                Subscription::Antigravity,
                qfork_root.clone(),
                http.clone(),
            )),
            xai: Arc::new(Credentials::new(
                Subscription::Xai,
                qfork_root.clone(),
                http.clone(),
            )),
            http,
            qfork_root,
            local_url,
            pacers: parking_lot::Mutex::new(HashMap::new()),
        }
    }
}

/// Close choices, stage B: what a chat-model player would be sent for one position, built
/// from its config alone (no credentials, no network): the route, the model id, the play
/// call (`Player::decide`'s constrained letter request, as in the leagues) and the
/// prediction call (`LlmClient::predict`), each as sent (configured extra fields merged in).
/// `shown` is the option order (at most 26). OpenAI-compatible servers' play calls (letter
/// probabilities in two steps) are not rendered here: `play` is null for them.
pub fn render_stage_b(config: &PlayerConfig, req: &DecisionRequest<'_>, shown: &[usize]) -> Result<Value> {
    use serde_json::json;
    let spec = config.spec.as_str();
    let Some((provider, model)) = spec.split_once('/').filter(|(_, m)| !m.is_empty()) else {
        bail!("{}: `{spec}` is not a chat model (no prediction call)", config.name);
    };
    let (route, model) = match provider.to_ascii_lowercase().as_str() {
        "openai" => (llm::Route::OpenAiSubscription, model.to_ascii_lowercase()),
        "anthropic" | "claude" => (llm::Route::AnthropicSubscription, model.to_owned()),
        "gemini" | "google" => (llm::Route::Gemini, model.to_owned()),
        "antigravity" | "google-antigravity" => (
            llm::Route::Antigravity,
            llm::antigravity_model(model, config.reasoning.as_deref()),
        ),
        "xai" | "xai-oauth" | "grok" => (llm::Route::Xai, model.to_owned()),
        "local" | "openai-compatible" | "ollama" => (llm::Route::OpenAiCompatible, model.to_owned()),
        other => bail!("{}: provider `{other}` is not a chat model (no prediction call)", config.name),
    };
    if shown.len() > prompt::LETTERS.len() {
        bail!("{}: {} options, more than one request holds", config.name, shown.len());
    }
    let options = llm::Options {
        reasoning: config.reasoning.clone(),
        request: config.request.clone(),
        max_tokens: config.max_tokens,
        top_logprobs: config.top_logprobs,
        readout: llm::Readout::parse(config.letter_readout.as_deref())?,
        answer_prefix: config.answer_prefix.clone(),
        pacer: None,
        budget: None,
    };
    let play_user = prompt::letter_user(req, shown);
    let prediction_user = prompt::prediction_user(req, shown);
    let play = (route != llm::Route::OpenAiCompatible).then(|| {
        llm::as_sent(
            llm::constrained_request(route, &model, &options, &play_user, llm::Answer::Letter(shown.len())),
            &options,
        )
    });
    let prediction = llm::as_sent(
        llm::constrained_request(route, &model, &options, &prediction_user, llm::Answer::Prediction),
        &options,
    );
    Ok(json!({
        "route": route.id(),
        "model": model,
        "play": {"system": prompt::letter_system(), "user": play_user, "body": play},
        "prediction": {"system": prompt::prediction_system(), "user": prediction_user, "body": prediction},
    }))
}

/// Index of a uniformly random legal play, seeded per decision.
pub fn random_play(req: &DecisionRequest<'_>) -> usize {
    Dice::new(derive_seed(req.seed, "invalid answer")).below(req.plays.len())
}

impl Player {
    /// A local engine player (baselines, GNUbg).
    pub fn engine(spec: &str, engine: Box<dyn Engine>) -> Self {
        Player {
            spec: spec.to_owned(),
            provider: "local".to_owned(),
            quantization: None,
            reasoning: None,
            price: None,
            requests: None,
            backend: Backend::Engine(engine),
        }
    }

    /// `from_config` with nothing but a spec.
    pub async fn from_spec(spec: &str, setup: &Setup) -> Result<Self> {
        Self::from_config(&PlayerConfig::new(spec, spec), setup).await
    }

    /// Parses `provider/model` (or a bare decision provider such as `jev`), resolves its
    /// credentials, and limits its decisions in flight to `config.parallel`.
    pub async fn from_config(config: &PlayerConfig, setup: &Setup) -> Result<Self> {
        let mut player = Self::build(config, setup).await?;
        player.requests = config
            .parallel
            .map(|n| tokio::sync::Semaphore::new(n.max(1)));
        Ok(player)
    }

    /// Whether the player decides locally (random, safest, gnubg-weak), not by request.
    pub fn is_engine(&self) -> bool {
        matches!(self.backend, Backend::Engine(_))
    }

    async fn build(config: &PlayerConfig, setup: &Setup) -> Result<Self> {
        let spec = config.spec.as_str();
        let (provider, model) = match spec.split_once('/') {
            Some((provider, model)) if !model.is_empty() => (provider, Some(model.to_owned())),
            _ => (spec, None),
        };
        let http = setup.http.clone();
        let need_model = |model: Option<String>| match model {
            Some(model) => Ok(model),
            None => bail!("model spec `{spec}` needs a model name: {provider}/<model>"),
        };
        let options = llm::Options {
            reasoning: config.reasoning.clone(),
            request: config.request.clone(),
            max_tokens: config.max_tokens,
            top_logprobs: config.top_logprobs,
            readout: llm::Readout::parse(config.letter_readout.as_deref())?,
            answer_prefix: config.answer_prefix.clone(),
            pacer: config.rpm.filter(|&rpm| rpm > 0).map(|rpm| {
                let group = config.rate_group.clone().unwrap_or_else(|| {
                    format!("{}|{spec}", config.base_url.as_deref().unwrap_or(""))
                });
                setup.pacer(group, rpm)
            }),
            budget: match &config.budget {
                Some(budget) if provider.eq_ignore_ascii_case("openai-compatible") => {
                    Some(crate::budget::Ledger::open(budget, &config.name)?)
                }
                Some(_) => bail!("{}: a budget needs an openai-compatible spec", config.name),
                None => None,
            },
        };
        let player = |backend| Player {
            spec: spec.to_owned(),
            provider: config
                .provider
                .clone()
                .unwrap_or_else(|| provider.to_ascii_lowercase()),
            quantization: config.quantization.clone(),
            reasoning: config.reasoning.clone(),
            price: config.price,
            requests: None,
            backend,
        };
        if let Some(service) = decision::service(provider) {
            return Ok(player(Backend::Decision(decision::DecisionClient::new(
                http,
                service,
                model,
                config.base_url.as_deref(),
            )?)));
        }
        let backend = match provider.to_ascii_lowercase().as_str() {
            "random" if model.is_none() => {
                return Ok(Player::engine(spec, Box::new(baseline::Baseline::Random)));
            }
            "safest" if model.is_none() => {
                return Ok(Player::engine(spec, Box::new(baseline::Baseline::Safest)));
            }
            "gnubg-weak" if model.is_none() => {
                return Ok(Player::engine(
                    spec,
                    Box::new(gnubg::GnubgPlayer::start(gnubg::WEAK)?),
                ));
            }
            "openai" => {
                // Fail at startup, not on the first move, when no login exists.
                setup.openai.token().await?;
                // Codex model ids are lowercase (`openai/gpt-5.6-Sol` → `gpt-5.6-sol`).
                let model = need_model(model)?.to_ascii_lowercase();
                Backend::Llm(llm::LlmClient::openai_subscription(
                    http,
                    model,
                    setup.openai.clone(),
                    options,
                ))
            }
            "anthropic" | "claude" => {
                setup.anthropic.token().await?;
                Backend::Llm(llm::LlmClient::anthropic_subscription(
                    http,
                    need_model(model)?,
                    setup.anthropic.clone(),
                    options,
                ))
            }
            "gemini" | "google" => Backend::Llm(llm::LlmClient::gemini(
                http,
                need_model(model)?,
                auth::gemini_api_key(&setup.qfork_root)?,
                options,
            )),
            "antigravity" | "google-antigravity" => {
                setup.antigravity.token().await?;
                Backend::Llm(llm::LlmClient::antigravity(
                    http,
                    llm::antigravity_model(&need_model(model)?, config.reasoning.as_deref()),
                    setup.antigravity.clone(),
                    options,
                ))
            }
            "xai" | "xai-oauth" | "grok" => {
                setup.xai.token().await?;
                Backend::Llm(llm::LlmClient::xai(
                    http,
                    need_model(model)?,
                    setup.xai.clone(),
                    options,
                ))
            }
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
                    options,
                ))
            }
            "local" => Backend::Llm(llm::LlmClient::openai_compatible(
                http,
                need_model(model)?,
                config
                    .base_url
                    .as_deref()
                    .unwrap_or(&setup.local_url)
                    .trim_end_matches('/')
                    .to_owned(),
                api_key(
                    config.api_key_env.as_deref().unwrap_or("LOCAL_API_KEY"),
                    false,
                )?,
                options,
            )),
            "openai-compatible" => {
                let Some(base_url) = &config.base_url else {
                    bail!("`{spec}` needs `base_url` in its player config");
                };
                let key = match config.api_key_env.as_deref() {
                    Some(var) => api_key(var, true)?,
                    None => None,
                };
                Backend::Llm(llm::LlmClient::openai_compatible(
                    http,
                    need_model(model)?,
                    base_url.trim_end_matches('/').to_owned(),
                    key,
                    options,
                ))
            }
            other => {
                let decision: Vec<&str> = decision::SERVICES.iter().map(|s| s.provider).collect();
                bail!(
                    "unknown provider `{other}` in `{spec}`; use openai/, anthropic/, gemini/, antigravity/, xai/, ollama/, local/, openai-compatible/, random, safest, gnubg-weak, or a decision service: {}",
                    decision.join(", ")
                )
            }
        };
        Ok(player(backend))
    }

    /// Most options one request can carry: 26 letters for chat models.
    fn max_choices(&self) -> usize {
        match &self.backend {
            Backend::Llm(_) => prompt::LETTERS.len(),
            Backend::Decision(client) => client.max_choices(),
            Backend::Engine(_) => usize::MAX,
            #[cfg(test)]
            Backend::Scripted { max, .. } => *max,
        }
    }

    /// One request over `shown` (indices into the plays, in the shown order); `None` for
    /// an invalid answer.
    async fn choose(
        &self,
        req: &DecisionRequest<'_>,
        shown: &[usize],
        decision: &mut Decision,
    ) -> Result<Option<usize>> {
        match &self.backend {
            Backend::Llm(client) => client.choose(req, shown, decision).await,
            Backend::Decision(client) => client.choose(req, shown, decision).await,
            Backend::Engine(_) => unreachable!("engines decide in one call"),
            #[cfg(test)]
            Backend::Scripted { answers, asked, .. } => {
                asked.lock().push(shown.to_vec());
                let mut answers = answers.lock();
                let answer = if answers.is_empty() {
                    Some(0)
                } else {
                    answers.remove(0)
                };
                Ok(answer.map(|position| shown[position]))
            }
        }
    }

    /// Asks for a play over the options in `req.order`, once a request slot is free (the
    /// wait counts as retry time). Above the player's option limit, the options are split
    /// into equal groups, a winner is picked per group, then among the winners. An invalid
    /// answer anywhere ends the decision with a random legal play.
    /// Close choices, stage B: one prediction call over the play call's options in its order
    /// (chat models only, at most 26 options). The decision holds the exchange and tokens
    /// (`index` unused); the parse is `Ok(feature ids)` (empty = "none") or `Err(reason)`.
    pub async fn predict(
        &self,
        req: &DecisionRequest<'_>,
    ) -> Result<(Decision, Result<Vec<&'static str>, String>)> {
        let _slot = match &self.requests {
            Some(slots) => {
                let started = Instant::now();
                let slot = slots.acquire().await.expect("the semaphore is never closed");
                req.retry.add(started.elapsed());
                Some(slot)
            }
            None => None,
        };
        let Backend::Llm(client) = &self.backend else {
            bail!("{}: not a chat model, no prediction call", self.spec);
        };
        if req.order.len() > prompt::LETTERS.len() {
            bail!("{} options: more than one request holds", req.order.len());
        }
        let mut decision = Decision::default();
        let parsed = client.predict(req, req.order, &mut decision).await?;
        Ok((decision, parsed))
    }

    /// Clear-risk Part 2: one prebuilt question, once a request slot is free. Decision
    /// services get `name`, `state`, `instructions` and `options` natively and answer with a
    /// choice and probabilities; chat models get `system` and `user` with the answer
    /// constrained to `schema`, and their answer text is returned unparsed.
    pub async fn quiz(&self, question: &QuizQuestion<'_>, retry: &RetryTime) -> Result<(Decision, QuizReply)> {
        let _slot = match &self.requests {
            Some(slots) => Some(slots.acquire().await.expect("the semaphore is never closed")),
            None => None,
        };
        let mut decision = Decision::default();
        let reply = match &self.backend {
            Backend::Decision(client) => {
                let (value, probabilities) = client
                    .ask(
                        question.name,
                        question.state,
                        question.instructions,
                        question.options,
                        retry,
                        &mut decision,
                    )
                    .await?;
                QuizReply::Choice { value, probabilities }
            }
            Backend::Llm(client) => QuizReply::Text(
                client
                    .ask_schema(question.system, question.user, question.schema_name, question.schema, retry, &mut decision)
                    .await?,
            ),
            _ => bail!("{}: only decision services and chat models answer quiz questions", self.spec),
        };
        Ok((decision, reply))
    }

    pub async fn decide(&self, req: &DecisionRequest<'_>) -> Result<Decision> {
        let _slot = match &self.requests {
            Some(slots) => {
                let started = Instant::now();
                let slot = slots
                    .acquire()
                    .await
                    .expect("the semaphore is never closed");
                req.retry.add(started.elapsed());
                Some(slot)
            }
            None => None,
        };
        if let Backend::Engine(engine) = &self.backend {
            return tokio::task::block_in_place(|| engine.decide(req));
        }
        let mut decision = Decision::default();
        let max = self.max_choices();
        let mut candidates: Vec<usize> = req.order.to_vec();
        if candidates.len() > max {
            let groups = candidates.len().div_ceil(max);
            decision.group_size = Some(candidates.len().div_ceil(groups));
        }
        while candidates.len() > 1 {
            let groups = candidates.len().div_ceil(max);
            let size = candidates.len().div_ceil(groups);
            let mut winners = Vec::with_capacity(groups);
            for group in candidates.chunks(size) {
                if let [only] = group {
                    winners.push(*only);
                    continue;
                }
                match self.choose(req, group, &mut decision).await? {
                    Some(index) => winners.push(index),
                    None => {
                        decision.invalid = true;
                        decision.index = random_play(req);
                        decision.probabilities.clear();
                        decision.probability_source = None;
                        return Ok(decision);
                    }
                }
            }
            candidates = winners;
        }
        decision.index = candidates[0];
        Ok(decision)
    }

    /// Dollars for this decision: what the provider reported, else the tokens at the
    /// configured list price; `None` with neither.
    pub fn cost(&self, decision: &Decision) -> Option<f64> {
        decision.reported_cost.or_else(|| {
            self.price.map(|p| {
                (decision.input_tokens as f64 * p.input_per_mtok
                    + decision.output_tokens as f64 * p.output_per_mtok)
                    / 1e6
            })
        })
    }

    /// Makes sure the model answers before a match starts, so a cold start never runs
    /// on its clock. Decision services get a two-option request until they answer; other
    /// players need none. Returns the time it took.
    pub async fn warm_up(&self) -> Result<Duration> {
        match &self.backend {
            Backend::Decision(client) => client.warm_up().await,
            _ => Ok(Duration::ZERO),
        }
    }
}

/// The API key in environment variable `var`; an error when `required` and unset.
fn api_key(var: &str, required: bool) -> Result<Option<String>> {
    match std::env::var(var).ok().filter(|k| !k.is_empty()) {
        Some(key) => Ok(Some(key)),
        None if required => bail!("set {var} to the API key"),
        None => Ok(None),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::board::Board;

    fn scripted(max: usize, answers: Vec<Option<usize>>) -> Player {
        Player {
            spec: "scripted".into(),
            provider: "test".into(),
            quantization: None,
            reasoning: None,
            price: None,
            requests: None,
            backend: Backend::Scripted {
                max,
                answers: parking_lot::Mutex::new(answers),
                asked: parking_lot::Mutex::new(Vec::new()),
            },
        }
    }

    fn asked(player: &Player) -> Vec<Vec<usize>> {
        match &player.backend {
            Backend::Scripted { asked, .. } => asked.lock().clone(),
            _ => unreachable!(),
        }
    }

    fn request<'a>(
        board: &'a Board,
        plays: &'a [Play],
        notations: &'a [String],
        order: &'a [usize],
        seed: u64,
        retry: &'a RetryTime,
    ) -> DecisionRequest<'a> {
        DecisionRequest {
            board,
            dice: (6, 6),
            plays,
            notations,
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
            order,
            seed,
            version: PromptVersion::BgV2,
            retry,
        }
    }

    #[tokio::test]
    async fn invalid_answer_plays_a_seeded_uniform_random_legal_play() {
        let mut board = Board::start();
        board.pts[12] = 3;
        board.pts[7] = 5;
        let plays = board.legal_plays(2, 1);
        assert!(plays.len() > 5);
        let notations: Vec<String> = plays.iter().map(|p| p.notation()).collect();
        let order: Vec<usize> = (0..plays.len()).rev().collect();
        let retry = RetryTime::default();

        let req = request(&board, &plays, &notations, &order, 11, &retry);
        let a = scripted(26, vec![None]).decide(&req).await.unwrap();
        let b = scripted(26, vec![None]).decide(&req).await.unwrap();
        assert!(a.invalid && b.invalid);
        assert_eq!(a.index, b.index, "same decision seed, same play");
        assert_eq!(a.index, random_play(&req));

        // Over many decision seeds every legal play comes up, roughly equally often.
        let mut seen = vec![0u32; plays.len()];
        for seed in 0..(plays.len() as u64 * 400) {
            let req = request(&board, &plays, &notations, &order, seed, &retry);
            seen[random_play(&req)] += 1;
        }
        assert!(seen.iter().all(|&n| (300..500).contains(&n)), "{seen:?}");

        // A valid answer maps the shown position back to the play index; one request
        // carries every option in the seeded order.
        let player = scripted(26, vec![Some(2)]);
        let ok = player.decide(&req).await.unwrap();
        assert!(!ok.invalid && ok.group_size.is_none());
        assert_eq!(ok.index, order[2]);
        assert_eq!(asked(&player), vec![order.clone()]);
    }

    #[tokio::test]
    async fn long_lists_are_split_into_equal_groups() {
        let mut board = Board::start();
        board.pts[12] = 3;
        board.pts[7] = 5;
        let plays = board.legal_plays(2, 1);
        let n = plays.len();
        assert!(n > 8, "{n}");
        let notations: Vec<String> = plays.iter().map(|p| p.notation()).collect();
        let order: Vec<usize> = (0..n).rev().collect();
        let retry = RetryTime::default();
        let req = request(&board, &plays, &notations, &order, 1, &retry);
        // At most 4 options per request: ceil(n / 4) equal groups, then the winners.
        let player = scripted(4, vec![Some(1)]);
        let decision = player.decide(&req).await.unwrap();
        let groups = n.div_ceil(4);
        let size = n.div_ceil(groups);
        assert_eq!(decision.group_size, Some(size));
        let groups_asked = asked(&player);
        assert_eq!(groups_asked[0], order[..size].to_vec());
        assert!(groups_asked.iter().all(|group| group.len() <= 4));
        // The first group's answer was its second option; every later answer the first.
        assert_eq!(decision.index, order[1]);
        assert!(!decision.invalid);

        // An invalid answer in any group ends the decision with the random play.
        let player = scripted(4, vec![Some(0), None]);
        let decision = player.decide(&req).await.unwrap();
        assert!(decision.invalid);
        assert_eq!(decision.index, random_play(&req));
        assert_eq!(asked(&player).len(), 2);
    }

    #[test]
    fn cost_uses_the_price_table() {
        let player = Player {
            spec: "x".into(),
            provider: "x".into(),
            quantization: None,
            reasoning: None,
            price: Some(Price {
                input_per_mtok: 2.0,
                output_per_mtok: 10.0,
            }),
            requests: None,
            backend: Backend::Engine(Box::new(baseline::Baseline::Random)),
        };
        let mut decision = Decision::new(0);
        decision.input_tokens = 1_000_000;
        decision.output_tokens = 500;
        assert!((player.cost(&decision).unwrap() - 2.005).abs() < 1e-12);
        let free = Player::engine("random", Box::new(baseline::Baseline::Random));
        assert_eq!(free.cost(&decision), None);
    }

    #[test]
    fn old_league_entries_still_parse() {
        let old: PlayerConfig =
            serde_json::from_str(r#"{"name":"Cygnet","spec":"cygnet"}"#).unwrap();
        assert_eq!(old, PlayerConfig::new("Cygnet", "cygnet"));
        let text = serde_json::to_string(&old).unwrap();
        assert_eq!(text, r#"{"name":"Cygnet","spec":"cygnet"}"#);
    }
}
