mod ask;
mod auth;
mod board;
mod db;
mod dice;
mod http;
mod league;
mod players;
mod runner;
mod ui;

use std::path::PathBuf;
use std::process::ExitCode;
use std::sync::Arc;
use std::time::Duration;

use anyhow::{Context, Result, bail};
use clap::{Args, Parser, Subcommand};
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
    /// parallel, then playoffs for ties among the first three places.
    League(LeagueArgs),
    /// Prints what a model is sent for stored positions: reads JSON lines (one position
    /// each) from --input or stdin and writes one JSON line per position with the state,
    /// instructions, letter prompt, and options in the seeded order.
    Render(RenderArgs),
    /// Sends stored positions to the players of a league config and stores every answer
    /// with the per-decision fields (shared positions, smoke tests).
    Ask(AskArgs),
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
    /// qfork/Glyph credential root read for subscription logins and API keys.
    #[arg(long, env = "JEVGAMMON_QFORK_ROOT")]
    qfork_root: Option<PathBuf>,
}

#[derive(Args)]
struct MatchArgs {
    /// First player: openai/<model>, anthropic/<model>, gemini/<model>, ollama/<model>,
    /// local/<model>, random, safest, gnubg-weak, or a decision service: jev, fastino,
    /// openai-decisions, perplexity, liquid, clef, open-jev, cygnet, gemma, pplx-local
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
    /// request fields and price, plus optional seed, order_seed, prompt_version, rounds,
    /// clock, delay, max_turns and note, which override the command line.
    #[arg(long, conflicts_with_all = ["models", "resume"])]
    config: Option<PathBuf>,
    /// Continue a stopped league from this database; its models, rounds, clock, seeds and
    /// prompt version are the stored ones.
    #[arg(long, conflicts_with = "models")]
    resume: Option<i64>,
    /// League seed; fixes the fixture, every match's dice, and the playoffs. Random when
    /// omitted.
    #[arg(long, conflicts_with = "resume")]
    seed: Option<u64>,
    /// Option-order seed; random when omitted.
    #[arg(long, conflicts_with = "resume")]
    order_seed: Option<u64>,
    /// What this league tests, e.g. "move metrics in options; d1 removed"; shown in the
    /// league history on the web page.
    #[arg(long, conflicts_with = "resume")]
    note: Option<String>,
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
        Some(Command::Ask(args)) => {
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
                rounds: config.rounds.unwrap_or(common.rounds),
                clock: (bank > 0).then(|| Clock {
                    bank: Duration::from_secs(bank),
                    delay: Duration::from_secs(delay),
                }),
                max_turns: (max_turns > 0).then_some(max_turns),
                note: config.note.or(args.note),
                version: match &config.prompt_version {
                    Some(id) => PromptVersion::parse(id)?,
                    None => common.prompt_version,
                },
                order_seed: config
                    .order_seed
                    .or(args.order_seed)
                    .unwrap_or_else(random_seed),
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
                rounds: args.common.rounds,
                clock: args.common.clock(),
                max_turns: args.common.max_turns(),
                note: args.note,
                version: args.common.prompt_version,
                order_seed: args.order_seed.unwrap_or_else(random_seed),
            }
        }
    };
    league::run(args.common.db, &setup, start, Harness::detect()).await
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
        db,
        players: [player1, player2],
        settings: MatchSettings {
            match_id,
            seed,
            rounds,
            clock,
            max_turns,
            decisive: false,
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
