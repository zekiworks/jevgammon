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

use crate::players::{Player, Setup};
use crate::runner::{Clock, Control, Event, MAX_SPEED, MatchSettings, Runner};

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
}

#[derive(Args)]
struct MatchArgs {
    /// First player: openai/<model>, anthropic/<model>, gemini/<model>, ollama/<model>,
    /// local/<model>, or a decision service: jev, fastino, openai-decisions, perplexity,
    /// liquid, clef, open-jev, cygnet, gemma, pplx-local (optionally /<model>).
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
    #[command(flatten)]
    common: Common,
}

#[derive(Args)]
struct LeagueArgs {
    /// Entrants as NAME=SPEC (or a bare SPEC, which is also its name), e.g.
    /// GLiDE=fastino "Decider 27B=perplexity".
    models: Vec<String>,
    /// Continue a stopped league from this database; its models, rounds, clock, and
    /// seed are the stored ones.
    #[arg(long, conflicts_with = "models")]
    resume: Option<i64>,
    /// League seed; fixes the fixture, every match's dice, and the playoffs. Random when
    /// omitted.
    #[arg(long, conflicts_with = "resume")]
    seed: Option<u64>,
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
    let start = match args.resume {
        Some(id) => league::Start::Resume(id),
        None => {
            let models: Vec<(String, String)> = args
                .models
                .iter()
                .map(|entry| match entry.split_once('=') {
                    Some((name, spec)) => (name.trim().to_owned(), spec.trim().to_owned()),
                    None => (entry.clone(), entry.clone()),
                })
                .collect();
            if models.len() < 2 {
                bail!("a league needs at least two models (NAME=SPEC ...), or --resume <id>");
            }
            for (i, (name, _)) in models.iter().enumerate() {
                if name.is_empty() || models[..i].iter().any(|(other, _)| other == name) {
                    bail!("model names must be non-empty and unique: `{name}`");
                }
            }
            league::Start::New {
                models,
                seed: args.seed.unwrap_or_else(random_seed),
                rounds: args.common.rounds,
                clock: args.common.clock(),
                max_turns: args.common.max_turns(),
                note: args.note,
            }
        }
    };
    league::run(args.common.db, &setup, start).await
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
    let rounds = args.common.rounds;
    let db = db::Db::open(&args.common.db)?;
    let clock = args.common.clock();
    let max_turns = args.common.max_turns();
    let match_id = db.create_match(&names[0], &names[1], seed, rounds, clock, max_turns)?;
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
        },
        events,
        control: control.clone(),
    };
    let handle = tokio::spawn(runner.run());

    if args.quiet {
        println!(
            "match #{match_id}: {} vs {} · {} rounds · clock {} · turn limit {} · seed {seed} · db {}",
            names[0],
            names[1],
            rounds,
            runner::describe_clock(clock),
            max_turns.map_or("off".to_owned(), |t| t.to_string()),
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
