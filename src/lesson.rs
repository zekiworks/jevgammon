//! `jevgammon lesson` ("Did they improve?"): one free-text request through a chat-model
//! player's own route, login and reasoning setting (`llm::free_text_request`), with the
//! player's budget ledger, pacer and retries as in the leagues. Writes the answer text, the
//! reasoning, usage, cost and the exchange as one JSON file; nothing goes to a database.

use std::path::PathBuf;
use std::time::Instant;

use anyhow::{Context as _, Result};
use serde_json::json;

use crate::http::RetryTime;
use crate::players::{Player, PlayerConfig, Setup};

pub struct LessonArgs {
    /// One player's config (a `PlayerConfig` as JSON, as `--model1-config` takes).
    pub player: PathBuf,
    pub system: PathBuf,
    pub user: PathBuf,
    pub out: PathBuf,
}

pub async fn lesson(args: LessonArgs, setup: &Setup) -> Result<()> {
    let text = std::fs::read_to_string(&args.player)
        .with_context(|| format!("reading {}", args.player.display()))?;
    let config: PlayerConfig = serde_json::from_str(&text)
        .with_context(|| format!("player config {}", args.player.display()))?;
    let system = std::fs::read_to_string(&args.system)
        .with_context(|| format!("reading {}", args.system.display()))?;
    let user = std::fs::read_to_string(&args.user)
        .with_context(|| format!("reading {}", args.user.display()))?;
    let player = Player::from_config(&config, setup)
        .await
        .with_context(|| format!("{} ({})", config.name, config.spec))?;
    let retry = RetryTime::default();
    let started = Instant::now();
    let (decision, answer, reasoning) = player.free_text(&system, &user, &retry).await?;
    let wall_ms = started.elapsed().as_millis() as u64;
    let out = json!({
        "setup": config.name,
        "spec": player.spec,
        "provider": player.provider,
        "reasoning_setting": player.reasoning,
        "text": answer,
        "reasoning": reasoning,
        "input_tokens": decision.input_tokens,
        "output_tokens": decision.output_tokens,
        "reasoning_tokens": decision.reasoning_tokens,
        "reported_cost_usd": decision.reported_cost,
        "cost_usd": player.cost(&decision),
        "in_flight": decision.in_flight,
        "wall_ms": wall_ms,
        "retry_ms": retry.get().as_millis() as u64,
        "exchanges": decision.exchanges.iter().map(|e| json!({
            "request": e.request,
            "response": e.response,
            "error": e.error,
            "latency_ms": e.latency_ms,
        })).collect::<Vec<_>>(),
        "created_at": chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true),
    });
    let tmp = args.out.with_extension("json.tmp");
    std::fs::write(&tmp, serde_json::to_string_pretty(&out)?)
        .with_context(|| format!("writing {}", tmp.display()))?;
    std::fs::rename(&tmp, &args.out)?;
    Ok(())
}
