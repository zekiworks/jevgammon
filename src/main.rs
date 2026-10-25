mod ask;
mod auth;
mod board;
mod budget;
mod db;
mod dice;
mod http;
mod league;
mod migrate;
mod players;
mod runner;
mod scores;
mod ui;

use std::path::PathBuf;
use std::process::ExitCode;
use std::sync::Arc;
use std::time::Duration;

use anyhow::{Context, Result, bail};
use clap::{Args, Parser, Subcommand};
use sha2::Digest as _;
use tokio::sync::mpsc;

use crate::players::prompt::PromptVersion;
use crate::players::{Player, PlayerConfig, Setup};
use crate::runner::{Clock, Control, Event, Harness, MAX_SPEED, MatchSettings, Protocol, Runner};

/// Backgammon between two AI models. Every round is played twice with seats
/// swapped and identical dice; everything is recorded in SQLite.
#[derive(Parser)]
#[command(
    name = "jevgammon",
    version,
    args_conflicts_with_subcommands = true,
    subcommand_negates_reqs = true
)]
struct Cli {
    #[command(subcommand)]
    command: Option<Command>,
    #[command(flatten)]
    game: MatchArgs,
}

#[derive(Subcommand)]
enum Command {
    /// Round-robin league between models on a random fixture, matchdays played in
    /// parallel; ranked by points, games won, fewer games lost, then the lower error rate.
    League(LeagueArgs),
    /// Prints what a model is sent for stored positions: reads JSON lines (one position
    /// each) from --input or stdin and writes one JSON line per position with the state,
    /// instructions, letter prompt, and options in the seeded order.
    Render(RenderArgs),
    /// Sends stored positions to the players of a league config and stores every answer
    /// with the per-decision fields (shared positions, smoke tests).
    Ask(AskArgs),
    /// Close choices, stage B, offline: prints the play call and the prediction call each
    /// chosen player would be sent for every stored position (built from the config, no
    /// credentials, no request), with the sha256 of each request body. One JSON line each.
    RenderStageB(RenderStageBArgs),
    /// Close choices, stage B: one prediction call per chosen player and stored position
    /// (table `predictions`); a stored row (valid, invalid or failed) is never asked again.
    Predict(PredictArgs),
    /// Adds a player to an existing league, running or finished: a participant (its
    /// `players` row is created, or reused when the name is known with the same settings),
    /// a note, and an entry in the additions freeze log. Its pairs with every current
    /// participant that it has not played anywhere are played: a running league picks them
    /// up within 30 s; otherwise `league --resume` plays them.
    LeagueAdd(LeagueAddArgs),
    /// Ends a player's participation in a league: its matches stay in the database (and
    /// count wherever the same pair meets again) but leave the table, its unplayed pairs
    /// leave the fixture.
    LeagueRemove(LeagueRemoveArgs),
    /// Voids a match: no table counts it any more and its pair is played again with the
    /// same seed (by a running league within 30 s, or `league --resume`).
    Void(VoidArgs),
    /// Converts a database from the old league layout (leagues.models, league_matches) to
    /// players, league_players and matches.valid, and compares every league's table before
    /// and after.
    Migrate(migrate::MigrateArgs),
    /// Ranks finished leagues again (points, games won, fewer games lost, then the lower
    /// error rate from the site's GNUbg scores) and stores the ranking; prints the stored
    /// and the new ranking.
    Rank(RankArgs),
}

#[derive(Args)]
struct RankArgs {
    #[arg(long)]
    db: PathBuf,
    /// League id; default: every finished league.
    #[arg(long)]
    league: Option<i64>,
    /// The site's GNUbg score shards (s*.db); default: $XDG_STATE_HOME/bg-site/plays.
    #[arg(long, env = "JEVGAMMON_SCORES")]
    scores: Option<PathBuf>,
    /// Print only; store nothing.
    #[arg(long)]
    dry_run: bool,
}

#[derive(Args)]
struct LeagueRemoveArgs {
    #[arg(long)]
    db: PathBuf,
    #[arg(long)]
    league: i64,
    /// Player name.
    #[arg(long)]
    player: String,
    /// Why it leaves; kept with the participation and appended to the league note.
    #[arg(long)]
    reason: String,
}

#[derive(Args)]
struct VoidArgs {
    #[arg(long)]
    db: PathBuf,
    /// Match id (`matches.id`).
    #[arg(long = "match")]
    match_id: i64,
    /// Why the match does not count; kept in `matches.void_reason`.
    #[arg(long)]
    reason: String,
}

#[derive(Args)]
struct LeagueAddArgs {
    #[arg(long)]
    db: PathBuf,
    #[arg(long)]
    league: i64,
    /// NAME=SPEC (or a bare spec, also the name).
    #[arg(long, conflicts_with_all = ["entry", "config"])]
    player: Option<String>,
    /// A player config entry as JSON, e.g. '{"name": "Jev 1.13.0", "spec": "jev/jev-1.13.0"}'.
    #[arg(long, conflicts_with = "config")]
    entry: Option<String>,
    /// League config file holding the player (with --name).
    #[arg(long, requires = "name")]
    config: Option<PathBuf>,
    #[arg(long)]
    name: Option<String>,
    /// JSON array the addition is appended to; default freeze/league<ID>-additions.json.
    #[arg(long)]
    freeze_log: Option<PathBuf>,
    /// qfork/Glyph credential root read for subscription logins and API keys.
    #[arg(long, env = "JEVGAMMON_QFORK_ROOT")]
    qfork_root: Option<PathBuf>,
    /// Base URL of the OpenAI-compatible server behind `local/<model>`.
    #[arg(
        long,
        env = "JEVGAMMON_LOCAL_URL",
        default_value = "http://localhost:8080/v1"
    )]
    local_url: String,
}

#[derive(Args)]
struct RenderArgs {
    /// JSON lines, one position each (the format of positions/*.jsonl: "position" as in
    /// turns.position, "dice" in the order the legal plays are generated, optional "id",
    /// "prompt", "turn", score, round, clock and history fields); stdin when omitted.
    #[arg(long)]
    input: Option<PathBuf>,
    /// Prompt version; default: the row's "prompt", else bg-v2.
    #[arg(long)]
    prompt_version: Option<PromptVersion>,
    /// Option-order seed.
    #[arg(long)]
    order_seed: u64,
}

#[derive(Args)]
struct RenderStageBArgs {
    /// League config file holding the players (its order_seed, prompt_version, rounds, clock
    /// and max_turns, as for `ask`).
    #[arg(long)]
    config: PathBuf,
    /// Positions file (JSON lines, as for `render`).
    #[arg(long)]
    positions: PathBuf,
    /// Player name in the config (repeatable); default: every player.
    #[arg(long = "setup")]
    setups: Vec<String>,
}

#[derive(Args)]
struct PredictArgs {
    /// League config file whose players answer (as for `ask`).
    #[arg(long)]
    config: PathBuf,
    /// Positions file (JSON lines, as for `render`).
    #[arg(long)]
    positions: PathBuf,
    /// SQLite file for the predictions (tables predictions, prediction_exchanges).
    #[arg(long)]
    out: PathBuf,
    /// Player name in the config (repeatable); default: every player.
    #[arg(long = "setup")]
    setups: Vec<String>,
    /// Longest wall-clock seconds per prediction; a longer one is stored as timed out.
    #[arg(long)]
    time_limit: Option<u64>,
    /// At most this many retries of network and server errors per call, counted over every
    /// send of the call (default: 3 per send, as in the leagues).
    #[arg(long)]
    retries: Option<u32>,
    /// qfork/Glyph credential root read for subscription logins and API keys.
    #[arg(long, env = "JEVGAMMON_QFORK_ROOT")]
    qfork_root: Option<PathBuf>,
}

#[derive(Args)]
struct AskArgs {
    /// League config file whose players answer (see `league --config`); its order_seed,
    /// prompt_version, rounds, clock and max_turns set the option order and the match
    /// context shown.
    #[arg(long)]
    config: PathBuf,
    /// Positions file (JSON lines, as for `render`).
    #[arg(long)]
    positions: PathBuf,
    /// SQLite file for the answers (tables answers, answer_exchanges); a rerun asks only
    /// what is missing or failed.
    #[arg(long, default_value = "answers.db")]
    out: PathBuf,
    /// Player name in the config (repeatable); default: every player.
    #[arg(long = "setup")]
    setups: Vec<String>,
    /// Only the first N positions.
    #[arg(long)]
    limit: Option<usize>,
    /// Times each position is asked.
    #[arg(long, default_value_t = 1)]
    repeats: u32,
    /// Prompt version for every position; default: the row's "prompt", else the config's.
    #[arg(long)]
    prompt_version: Option<PromptVersion>,
    /// A setup takes no new positions once its answers cost more than this many dollars.
    #[arg(long)]
    max_cost: Option<f64>,
    /// Longest wall-clock seconds per decision; a decision that takes longer is stored as
    /// timed out (not invalid) and not asked again.
    #[arg(long)]
    time_limit: Option<u64>,
    /// One-shot: a stored answer, failed included, is never asked again (close choices,
    /// stage B: no rerun, no re-ask).
    #[arg(long)]
    once: bool,
    /// At most this many retries of network and server errors per call, counted over every
    /// send of the call (default: 3 per send, as in the leagues).
    #[arg(long)]
    retries: Option<u32>,
    /// qfork/Glyph credential root read for subscription logins and API keys.
    #[arg(long, env = "JEVGAMMON_QFORK_ROOT")]
    qfork_root: Option<PathBuf>,
}

#[derive(Args)]
struct MatchArgs {
    /// First player: openai/<model>, anthropic/<model>, gemini/<model>, antigravity/<model>,
    /// xai/<model>, ollama/<model>, local/<model>, random, safest, gnubg-weak, or a decision service: jev, fastino,
    /// openai-decisions, perplexity, liquid, clef, open-jev, cygnet, gemma, pplx-local, d3
    /// (optionally /<model>). Reasoning, prices and other providers need a league --config.
    #[arg(long, required = true)]
    model1: Option<String>,
    /// Second player (same forms as --model1).
    #[arg(long, required = true)]
    model2: Option<String>,
    /// Initial speed: 1 (slowest) to 6, or `max` (no board, fastest).
    #[arg(long, default_value = "4", value_parser = parse_speed)]
    speed: u8,
    /// No interface: play as fast as possible and print the score when it changes.
    #[arg(long, visible_alias = "quite")]
    quiet: bool,
    /// Match seed; fixes every roll. Random when omitted.
    #[arg(long)]
    seed: Option<u64>,
    /// Option-order seed; random when omitted.
    #[arg(long)]
    order_seed: Option<u64>,
    #[command(flatten)]
    common: Common,
}

#[derive(Args)]
struct LeagueArgs {
    /// Entrants as NAME=SPEC (or a bare SPEC, which is also its name), e.g.
    /// GLiDE=fastino "Decider 27B=perplexity".
    models: Vec<String>,
    /// League config file (JSON): players with spec, provider, quantization, reasoning,
    /// request fields, price, parallel and max_matches, plus optional seed, order_seed,
    /// prompt_version, rounds, clock, delay, max_turns, mirror_concurrent and note, which
    /// override the command line.
    #[arg(long, conflicts_with_all = ["models", "resume"])]
    config: Option<PathBuf>,
    /// Continue a stopped league from this database; its models, rounds, clock, seeds and
    /// prompt version are the stored ones, and unfinished matches resume from their last
    /// stored turn.
    #[arg(long, conflicts_with = "models")]
    resume: Option<i64>,
    /// League seed; fixes the order of the founders' round robin. Random when omitted.
    /// (Dice come from the two player names and the rules.)
    #[arg(long, conflicts_with = "resume")]
    seed: Option<u64>,
    /// Option-order seed; random when omitted.
    #[arg(long, conflicts_with = "resume")]
    order_seed: Option<u64>,
    /// What this league tests, e.g. "move metrics in options; d1 removed"; shown in the
    /// league history on the web page.
    #[arg(long, conflicts_with = "resume")]
    note: Option<String>,
    /// Play the two games of each round at once; both then show the score at the start of
    /// the round (game 2 otherwise starts after game 1 and shows the score after it).
    #[arg(long, conflicts_with = "resume")]
    mirror_concurrent: bool,
    /// The site's GNUbg score shards (s*.db) for the error-rate tiebreak; default:
    /// $XDG_STATE_HOME/bg-site/plays.
    #[arg(long, env = "JEVGAMMON_SCORES")]
    scores: Option<PathBuf>,
    #[command(flatten)]
    common: Common,
}

#[derive(Args)]
struct Common {
    /// Rounds per match; each round is two games. The match ends after the round in which a
    /// player reaches 5 points, if someone leads. A tie adds one extra round.
    #[arg(long, default_value_t = 5, value_parser = clap::value_parser!(u32).range(1..))]
    rounds: u32,
    /// SQLite database file.
    #[arg(long, default_value = "jevgammon.db")]
    db: PathBuf,
    /// Thinking-time bank per player per game, in seconds (Simple Delay clock); a player
    /// whose bank runs out while deciding loses that game for 1 point. 0 disables the clock.
    #[arg(long, default_value_t = 300)]
    clock: u64,
    /// Free delay per decision, in seconds, used before the bank and not accumulated.
    #[arg(long, default_value_t = 30)]
    delay: u64,
    /// A game still running after this many turns (both sides counted) is won by the
    /// lower pip count, or with equal pips by the side due to roll next. 0 = no limit.
    #[arg(long, default_value_t = 300)]
    max_turns: u32,
    /// qfork/Glyph credential root read for subscription logins and API keys.
    #[arg(long, env = "JEVGAMMON_QFORK_ROOT")]
    qfork_root: Option<PathBuf>,
    /// Base URL of the OpenAI-compatible server behind `local/<model>`.
    #[arg(
        long,
        env = "JEVGAMMON_LOCAL_URL",
        default_value = "http://localhost:8080/v1"
    )]
    local_url: String,
    /// Prompt version: bg-v2 (League #8's format), bg-v2-notation, bg-v2-history, or
    /// nack-v2 (no opening table).
    #[arg(long, default_value = "bg-v2")]
    prompt_version: PromptVersion,
}

impl Common {
    fn setup(&self) -> Setup {
        Setup::new(
            self.qfork_root
                .clone()
                .unwrap_or_else(auth::default_qfork_root),
            self.local_url.clone(),
        )
    }

    fn clock(&self) -> Option<Clock> {
        (self.clock > 0).then(|| Clock {
            bank: Duration::from_secs(self.clock),
            delay: Duration::from_secs(self.delay),
        })
    }

    fn max_turns(&self) -> Option<u32> {
        (self.max_turns > 0).then_some(self.max_turns)
    }
}

fn parse_speed(value: &str) -> Result<u8, String> {
    if value.eq_ignore_ascii_case("max") {
        return Ok(MAX_SPEED);
    }
    match value.parse::<u8>() {
        Ok(n) if (1..=MAX_SPEED).contains(&n) => Ok(n),
        _ => Err(format!("speed must be 1-{} or max", MAX_SPEED - 1)),
    }
}

fn random_seed() -> u64 {
    uuid::Uuid::new_v4().as_u64_pair().0 >> 1
}

#[tokio::main]
async fn main() -> ExitCode {
    let cli = Cli::parse();
    let result = match cli.command {
        Some(Command::League(args)) => run_league(args).await,
        Some(Command::Render(args)) => ask::render(
            args.input.as_deref().unwrap_or(std::path::Path::new("-")),
            args.prompt_version,
            args.order_seed,
        ),
        Some(Command::LeagueAdd(args)) => league_add(args).await,
        Some(Command::LeagueRemove(args)) => league_remove(args),
        Some(Command::Void(args)) => void(args),
        Some(Command::Migrate(args)) => migrate::run(&args),
        Some(Command::Rank(args)) => rank(args),
        Some(Command::RenderStageB(args)) => {
            ask::render_stage_b(&args.config, &args.positions, &args.setups)
        }
        Some(Command::Predict(args)) => {
            if let Some(retries) = args.retries {
                http::limit_retries_per_call(retries);
            }
            let setup = Setup::new(
                args.qfork_root
                    .clone()
                    .unwrap_or_else(auth::default_qfork_root),
                "http://localhost:8080/v1".to_owned(),
            );
            ask::predict(
                ask::PredictArgs {
                    config: args.config,
                    positions: args.positions,
                    out: args.out,
                    setups: args.setups,
                    time_limit: args.time_limit.map(std::time::Duration::from_secs),
                },
                &setup,
            )
            .await
        }
        Some(Command::Ask(args)) => {
            if let Some(retries) = args.retries {
                http::limit_retries_per_call(retries);
            }
            let setup = Setup::new(
                args.qfork_root
                    .clone()
                    .unwrap_or_else(auth::default_qfork_root),
                "http://localhost:8080/v1".to_owned(),
            );
            ask::ask(
                ask::AskArgs {
                    config: args.config,
                    positions: args.positions,
                    out: args.out,
                    setups: args.setups,
                    limit: args.limit,
                    repeats: args.repeats,
                    version: args.prompt_version,
                    max_cost: args.max_cost,
                    time_limit: args.time_limit.map(std::time::Duration::from_secs),
                    once: args.once,
                },
                &setup,
            )
            .await
        }
        None => run_match(cli.game).await,
    };
    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("jevgammon: {error:#}");
            ExitCode::FAILURE
        }
    }
}

async fn run_league(args: LeagueArgs) -> Result<()> {
    let setup = args.common.setup();
    let start = match (args.resume, &args.config) {
        (Some(id), _) => league::Start::Resume(id),
        (None, Some(path)) => {
            let config = league::LeagueConfig::load(path)?;
            let common = &args.common;
            let bank = config.clock.unwrap_or(common.clock);
            let delay = config.delay.unwrap_or(common.delay);
            let max_turns = config.max_turns.unwrap_or(common.max_turns);
            league::Start::New {
                models: checked(config.players)?,
                seed: config.seed.or(args.seed).unwrap_or_else(random_seed),
                rules: db::Rules::new(
                    config.rounds.unwrap_or(common.rounds),
                    (bank > 0).then(|| Clock {
                        bank: Duration::from_secs(bank),
                        delay: Duration::from_secs(delay),
                    }),
                    (max_turns > 0).then_some(max_turns),
                    match &config.prompt_version {
                        Some(id) => PromptVersion::parse(id)?,
                        None => common.prompt_version,
                    }
                    .id(),
                    config
                        .order_seed
                        .or(args.order_seed)
                        .unwrap_or_else(random_seed),
                    config.mirror_concurrent.unwrap_or(args.mirror_concurrent),
                ),
                note: config.note.or(args.note),
            }
        }
        (None, None) => {
            let models: Vec<PlayerConfig> = args
                .models
                .iter()
                .map(|entry| match entry.split_once('=') {
                    Some((name, spec)) => PlayerConfig::new(name.trim(), spec.trim()),
                    None => PlayerConfig::new(entry, entry),
                })
                .collect();
            league::Start::New {
                models: checked(models)?,
                seed: args.seed.unwrap_or_else(random_seed),
                rules: db::Rules::new(
                    args.common.rounds,
                    args.common.clock(),
                    args.common.max_turns(),
                    args.common.prompt_version.id(),
                    args.order_seed.unwrap_or_else(random_seed),
                    args.mirror_concurrent,
                ),
                note: args.note,
            }
        }
    };
    league::run(
        args.common.db,
        &setup,
        start,
        Harness::detect(),
        args.scores.unwrap_or_else(scores::default_dir),
    )
    .await
}

/// `jevgammon rank`.
fn rank(args: RankArgs) -> Result<()> {
    let db = db::Db::open(&args.db)?;
    let scores = args.scores.unwrap_or_else(scores::default_dir);
    let leagues: Vec<(i64, String, Option<String>)> = {
        let mut statement = db.conn().prepare(
            "SELECT id, status, ranking FROM leagues WHERE ?1 IS NULL OR id = ?1 ORDER BY id",
        )?;
        statement
            .query_map([args.league], |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)))?
            .collect::<rusqlite::Result<_>>()?
    };
    if leagues.is_empty() {
        bail!("no such league");
    }
    for (id, status, stored) in leagues {
        if status != "finished" {
            println!("\nleague #{id} is {status}: its ranking is stored when it finishes");
            continue;
        }
        let ranked = league::rank_league(&db, id, &scores)?;
        let stored: Vec<String> = stored
            .map(|s| serde_json::from_str(&s))
            .transpose()?
            .unwrap_or_default();
        println!("\nleague #{id}: stored ranking | new ranking");
        for i in 0..stored.len().max(ranked.ranking.len()) {
            let (old, new) = (stored.get(i), ranked.ranking.get(i));
            println!(
                "  {:40} | {}{}",
                old.map_or("-", String::as_str),
                new.map_or("-", String::as_str),
                if old == new { "" } else { "   <-- changed" }
            );
        }
        if !ranked.unscored.is_empty() {
            println!(
                "league #{id}: decisions not scored yet (partial error rates): {}",
                ranked
                    .unscored
                    .iter()
                    .map(|(name, n)| format!("{name} ({n})"))
                    .collect::<Vec<_>>()
                    .join(", ")
            );
        }
        if args.dry_run {
            println!("league #{id}: dry run, nothing stored");
        } else if stored == ranked.ranking {
            println!("league #{id}: ranking unchanged");
        } else {
            db.store_ranking(id, &ranked.ranking)?;
            println!("league #{id}: new ranking stored");
        }
    }
    Ok(())
}

/// `jevgammon league-add`.
async fn league_add(args: LeagueAddArgs) -> Result<()> {
    let config = match (&args.player, &args.entry, &args.config) {
        (Some(entry), _, _) => match entry.split_once('=') {
            Some((name, spec)) => PlayerConfig::new(name.trim(), spec.trim()),
            None => PlayerConfig::new(entry, entry),
        },
        (_, Some(json), _) => serde_json::from_str(json).context("--entry")?,
        (_, _, Some(path)) => {
            let name = args.name.as_deref().expect("required by clap");
            league::LeagueConfig::load(path)?
                .players
                .into_iter()
                .find(|p| p.name == name)
                .with_context(|| format!("no player `{name}` in {}", path.display()))?
        }
        _ => {
            bail!("give the player: --player NAME=SPEC, --entry JSON, or --config FILE --name NAME")
        }
    };
    // Credentials and settings are checked now, not when its first match starts.
    let setup = Setup::new(
        args.qfork_root
            .clone()
            .unwrap_or_else(auth::default_qfork_root),
        args.local_url.clone(),
    );
    Player::from_config(&config, &setup)
        .await
        .with_context(|| format!("{} ({})", config.name, config.spec))?;
    let harness = Harness::detect();
    let now = chrono::Utc::now();
    let mut db = db::Db::open(&args.db)?;
    let addition = league::add_player(
        &mut db,
        args.league,
        &config,
        &now.format("%Y-%m-%d").to_string(),
    )?;
    let entry_json = serde_json::to_string(&config)?;
    let log = args
        .freeze_log
        .clone()
        .unwrap_or_else(|| PathBuf::from(format!("freeze/league{}-additions.json", args.league)));
    let mut entries: Vec<serde_json::Value> = match std::fs::read_to_string(&log) {
        Ok(text) => {
            serde_json::from_str(&text).with_context(|| format!("parsing {}", log.display()))?
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Vec::new(),
        Err(error) => return Err(error).with_context(|| format!("reading {}", log.display())),
    };
    entries.push(serde_json::json!({
        "added_at": now.to_rfc3339_opts(chrono::SecondsFormat::Secs, true),
        "league": args.league,
        "db": args.db.display().to_string(),
        "name": config.name,
        "harness_commit": harness.commit,
        "harness_dirty": harness.dirty,
        "entry": config,
        "entry_sha256": hex::encode(sha2::Sha256::digest(entry_json.as_bytes())),
        "fixtures": addition.fixtures,
    }));
    if let Some(dir) = log.parent().filter(|d| !d.as_os_str().is_empty()) {
        std::fs::create_dir_all(dir)?;
    }
    std::fs::write(&log, serde_json::to_string_pretty(&entries)? + "\n")?;
    println!(
        "{} joins league #{} with {} matches; note: \"{}\"; logged in {}",
        config.name,
        args.league,
        addition.fixtures.len(),
        addition.note,
        log.display()
    );
    for label in &addition.fixtures {
        println!("  {label}");
    }
    who_plays(&db, args.league, &args.db, "these matches")
}

/// Tells who plays league `id`'s changed fixture: its running process, or `--resume`.
fn who_plays(db: &db::Db, id: i64, path: &std::path::Path, what: &str) -> Result<()> {
    let activity = db.league_activity(id)?;
    if activity.pickup_runner() {
        println!("the running league process picks {what} up within 30 s");
    } else if activity.playing() {
        println!(
            "an older runner without pick-up is playing this league (last turn {}): let it finish, \
             or stop it with Ctrl-C, then run `jevgammon league --resume {id} --db {}`",
            league::ago(activity.running_turn_secs),
            path.display()
        );
    } else {
        println!(
            "no process is playing this league: `jevgammon league --resume {id} --db {}` plays {what}",
            path.display()
        );
    }
    Ok(())
}

/// `jevgammon league-remove`.
fn league_remove(args: LeagueRemoveArgs) -> Result<()> {
    let mut db = db::Db::open(&args.db)?;
    let open = league::remove_player(&mut db, args.league, &args.player, &args.reason)?;
    println!(
        "{} left league #{}: {open} unplayed pairs dropped from the fixture; its matches stay \
         in the database",
        args.player, args.league
    );
    who_plays(&db, args.league, &args.db, "the change")
}

/// `jevgammon void`.
fn void(args: VoidArgs) -> Result<()> {
    let mut db = db::Db::open(&args.db)?;
    let leagues = db.void_match(args.match_id, &args.reason)?;
    println!(
        "match #{} voided ({}); counted in league{} {:?}, which play the pair again with the \
         same seed",
        args.match_id,
        args.reason,
        if leagues.len() == 1 { "" } else { "s" },
        leagues
    );
    for id in leagues {
        who_plays(&db, id, &args.db, "the replay")?;
    }
    Ok(())
}

/// At least two entrants with non-empty, unique names.
fn checked(models: Vec<PlayerConfig>) -> Result<Vec<PlayerConfig>> {
    if models.len() < 2 {
        bail!("a league needs at least two models (NAME=SPEC ..., or --config), or --resume <id>");
    }
    for (i, model) in models.iter().enumerate() {
        if model.name.is_empty() || models[..i].iter().any(|other| other.name == model.name) {
            bail!("model names must be non-empty and unique: `{}`", model.name);
        }
    }
    Ok(models)
}

async fn run_match(args: MatchArgs) -> Result<()> {
    let setup = args.common.setup();
    let (Some(model1), Some(model2)) = (args.model1, args.model2) else {
        bail!("--model1 and --model2 are required");
    };
    let player1 = Arc::new(
        Player::from_spec(&model1, &setup)
            .await
            .context("--model1")?,
    );
    let player2 = Arc::new(
        Player::from_spec(&model2, &setup)
            .await
            .context("--model2")?,
    );
    let names = [player1.spec.clone(), player2.spec.clone()];
    for (name, player) in names.iter().zip([&player1, &player2]) {
        player
            .warm_up()
            .await
            .with_context(|| format!("warming up {name}"))?;
    }
    let seed = args.seed.unwrap_or_else(random_seed);
    let protocol = Arc::new(Protocol {
        version: args.common.prompt_version,
        order_seed: args.order_seed.unwrap_or_else(random_seed),
        harness: Harness::detect(),
    });
    let rounds = args.common.rounds;
    let db = db::Db::open(&args.common.db)?;
    let clock = args.common.clock();
    let max_turns = args.common.max_turns();
    let match_id = db.create_match(
        &names[0], &names[1], seed, rounds, clock, max_turns, &protocol,
    )?;
    let control = Arc::new(Control::new(if args.quiet {
        MAX_SPEED
    } else {
        args.speed
    }));
    let (events, mut receiver) = mpsc::unbounded_channel();
    let runner = Runner {
        db: parking_lot::Mutex::new(db),
        players: [player1, player2],
        settings: MatchSettings {
            match_id,
            seed,
            rounds,
            clock,
            max_turns,
            // The board view follows one game at a time.
            concurrent_mirror: false,
            protocol: protocol.clone(),
        },
        events,
        control: control.clone(),
    };
    let handle = tokio::spawn(runner.run());

    if args.quiet {
        println!(
            "match #{match_id}: {} vs {} · {} rounds · clock {} · turn limit {} · seed {seed} · \
             prompt {} · option-order seed {} · db {}",
            names[0],
            names[1],
            rounds,
            runner::describe_clock(clock),
            max_turns.map_or("off".to_owned(), |t| t.to_string()),
            protocol.version.id(),
            protocol.order_seed,
            args.common.db.display()
        );
        let interrupt = control.clone();
        tokio::spawn(async move {
            if tokio::signal::ctrl_c().await.is_ok() {
                interrupt.cancel();
            }
        });
        while let Some(event) = receiver.recv().await {
            match event {
                Event::GameOver {
                    round,
                    leg,
                    winner,
                    kind,
                    score,
                } => println!(
                    "round {round} leg {leg}: {} wins {} (+{}) · score {} {} - {} {}",
                    names[winner as usize - 1],
                    kind.describe(),
                    kind.points(),
                    names[0],
                    score[0],
                    score[1],
                    names[1]
                ),
                Event::MatchOver {
                    score,
                    winner,
                    rounds,
                } => println!(
                    "final after {rounds} rounds: {} {} - {} {} · {}",
                    names[0],
                    score[0],
                    score[1],
                    names[1],
                    winner.map_or("draw".to_owned(), |w| format!(
                        "winner {}",
                        names[w as usize - 1]
                    ))
                ),
                _ => {}
            }
        }
    } else {
        let delay = clock.map_or(Duration::ZERO, |c| c.delay);
        let app = ui::App::new(names, match_id, seed, rounds, delay, control.clone());
        let mut terminal = ratatui::init();
        let result = tokio::task::block_in_place(|| ui::run(&mut terminal, app, receiver));
        ratatui::restore();
        result?;
    }
    handle.await?.map(|_| ())
}
