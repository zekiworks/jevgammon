//! Match orchestration: rounds of two mirrored legs sharing one dice seed. A match cut off
//! part-way resumes from its stored games and turns with the dice it would have rolled.

use std::collections::HashMap;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicU8, Ordering};
use std::time::{Duration, Instant};

use anyhow::{Context as _, Result, bail};
use parking_lot::Mutex;
use tokio::sync::{Notify, mpsc};

use crate::board::{Board, Side, WinKind};
use crate::db::{Db, DecisionLog, StoredGame, TurnRecord};
use crate::dice::{Dice, derive_seed, round_seed};
use crate::http::RetryTime;
use crate::players::order::{option_order, position_key};
use crate::players::prompt::PromptVersion;
use crate::players::{DecisionRequest, PastMove, Player};

/// Delay after each move per speed level (1-based); the last level is max speed.
pub const SPEED_DELAYS_MS: [u64; 7] = [3000, 1500, 800, 400, 150, 50, 0];
pub const MAX_SPEED: u8 = SPEED_DELAYS_MS.len() as u8;
/// A player at this many points after a full round (the mirror game is always played)
/// wins the match if ahead; a tie goes to the tie-break round.
pub const FIRST_TO: u32 = 5;

pub struct Control {
    speed: AtomicU8,
    paused: AtomicBool,
    cancelled: AtomicBool,
    cancel: Notify,
}

impl Control {
    pub fn new(speed: u8) -> Self {
        Control {
            speed: AtomicU8::new(speed.clamp(1, MAX_SPEED)),
            paused: AtomicBool::new(false),
            cancelled: AtomicBool::new(false),
            cancel: Notify::new(),
        }
    }

    pub fn speed(&self) -> u8 {
        self.speed.load(Ordering::Relaxed)
    }

    pub fn set_speed(&self, speed: u8) {
        self.speed
            .store(speed.clamp(1, MAX_SPEED), Ordering::Relaxed);
    }

    pub fn paused(&self) -> bool {
        self.paused.load(Ordering::Relaxed)
    }

    pub fn toggle_pause(&self) {
        self.paused.fetch_xor(true, Ordering::Relaxed);
    }

    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::Relaxed);
        self.cancel.notify_waiters();
    }

    pub fn is_cancelled(&self) -> bool {
        self.cancelled.load(Ordering::Relaxed)
    }

    pub async fn cancelled(&self) {
        let notified = self.cancel.notified();
        if !self.is_cancelled() {
            notified.await;
        }
    }

    /// Waits out the current speed's delay and any pause; returns early on cancel. Yields
    /// at least once, so the other game of a round gets its turn even at full speed.
    async fn pace(&self, multiplier: u32) -> Result<()> {
        tokio::task::yield_now().await;
        let started = Instant::now();
        loop {
            if self.is_cancelled() {
                bail!("cancelled");
            }
            let delay = Duration::from_millis(
                SPEED_DELAYS_MS[self.speed() as usize - 1] * multiplier as u64,
            );
            if !self.paused() && started.elapsed() >= delay {
                return Ok(());
            }
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
    }
}

/// Bank left per player (index 0 = `--model1`) in the current game; `None` when the
/// match has no clock.
pub type Clocks = [Option<Duration>; 2];

/// Simple Delay thinking time (WBGF Tournament Rules 3.5): each decision first uses a
/// free delay that does not accumulate; only time beyond it comes out of the player's
/// bank, which is full again at the start of every game.
#[derive(Clone, Copy, Debug)]
pub struct Clock {
    pub delay: Duration,
    pub bank: Duration,
}

/// `m:ss`, rounded down.
pub fn format_clock(left: Duration) -> String {
    let seconds = left.as_secs();
    format!("{}:{:02}", seconds / 60, seconds % 60)
}

/// E.g. "0:30 delay + 5:00 bank per game", or "off".
pub fn describe_clock(clock: Option<Clock>) -> String {
    clock.map_or("off".to_owned(), |c| {
        format!(
            "{} delay + {} bank per game",
            format_clock(c.delay),
            format_clock(c.bank)
        )
    })
}

#[derive(Clone, Debug)]
pub enum Event {
    GameStarted {
        round: u32,
        rounds: u32,
        leg: u8,
        white_player: u8,
        board: Board,
        clocks: Clocks,
    },
    /// A game cut off part-way continues after its stored turns (the match resumed).
    Resumed {
        round: u32,
        rounds: u32,
        leg: u8,
        white_player: u8,
        /// The next turn to play.
        turn_no: u32,
        /// White's perspective, before that turn.
        board: Board,
        clocks: Clocks,
        score: [u32; 2],
    },
    /// A model was asked to choose a play for this roll.
    Thinking {
        player: u8,
        side: Side,
        dice: (u8, u8),
        /// Clocks when the model was asked; the mover's is now running.
        clocks: Clocks,
    },
    Moved {
        turn_no: u32,
        side: Side,
        player: u8,
        dice: (u8, u8),
        notation: String,
        /// White's perspective, after the move.
        board: Board,
        decided_by: &'static str,
        latency_ms: u64,
        clocks: Clocks,
    },
    GameOver {
        round: u32,
        leg: u8,
        winner: u8,
        kind: WinKind,
        score: [u32; 2],
    },
    MatchOver {
        score: [u32; 2],
        winner: Option<u8>,
        rounds: u32,
    },
    Failed(String),
}

/// The runner's commit, read once at startup: `git rev-parse HEAD` in the source tree,
/// and whether tracked files differed from it.
#[derive(Clone, Debug, Default)]
pub struct Harness {
    /// `None` when git or the repository is unavailable.
    pub commit: Option<String>,
    pub dirty: bool,
}

impl Harness {
    pub fn detect() -> Self {
        let git = |args: &[&str]| {
            std::process::Command::new("git")
                .args(args)
                .current_dir(env!("CARGO_MANIFEST_DIR"))
                .output()
                .ok()
                .filter(|out| out.status.success())
                .map(|out| String::from_utf8_lossy(&out.stdout).trim().to_owned())
        };
        Harness {
            commit: git(&["rev-parse", "HEAD"]).filter(|c| !c.is_empty()),
            dirty: git(&["status", "--porcelain", "--untracked-files=no"])
                .is_some_and(|s| !s.is_empty()),
        }
    }
}

/// What every decision of a run shares: prompt version, option-order seed, and harness.
#[derive(Clone, Debug)]
pub struct Protocol {
    pub version: PromptVersion,
    pub order_seed: u64,
    pub harness: Harness,
}

pub struct MatchSettings {
    pub match_id: i64,
    pub seed: u64,
    pub rounds: u32,
    /// Simple Delay clock; a player whose bank runs out while deciding loses the game.
    /// `None` disables the clock.
    pub clock: Option<Clock>,
    /// A game still running after this many turns (both sides counted) is won by the
    /// lower pip count, or with equal pips by the side due to roll next.
    pub max_turns: Option<u32>,
    /// A tie after the planned rounds adds rounds until one player leads; otherwise
    /// exactly one extra round is played and a tie after it is a draw.
    pub decisive: bool,
    /// Plays the two games of a round at once, both showing the score at the start of the
    /// round; otherwise game 2 starts after game 1 and shows the score after it.
    pub concurrent_mirror: bool,
    pub protocol: Arc<Protocol>,
}

/// Context of a match error one player caused (its decision failed): a league backs that
/// player off, not its opponent.
#[derive(Clone, Copy, Debug)]
pub struct PlayerFault(pub u8);

impl std::fmt::Display for PlayerFault {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "player {}", self.0)
    }
}

/// How a finished match ended; index 0 = `--model1`.
#[derive(Clone, Copy, Debug)]
pub struct MatchResult {
    pub score: [u32; 2],
    pub games_won: [u32; 2],
    /// `None` for a draw.
    pub winner: Option<u8>,
}

pub struct Runner {
    /// Locked for each write: the two games of a round may be played at once.
    pub db: Mutex<Db>,
    pub players: [Arc<Player>; 2],
    pub settings: MatchSettings,
    pub events: mpsc::UnboundedSender<Event>,
    pub control: Arc<Control>,
}

struct Game {
    round: u32,
    rounds: u32,
    leg: u8,
    white_player: u8,
}

impl Game {
    fn player(&self, side: Side) -> u8 {
        match side {
            Side::White => self.white_player,
            Side::Black => 3 - self.white_player,
        }
    }
}

/// How a game ended, and whether it had ended before this run (and was reported then).
struct GameEnd {
    winner: u8,
    kind: WinKind,
    stored: bool,
}

fn white_view(board: &Board, to_move: Side) -> Board {
    match to_move {
        Side::White => *board,
        Side::Black => board.flip(),
    }
}

impl Runner {
    /// Plays the match to completion, after its stored games and turns when it was cut off
    /// before, and returns the result. On failure or cancellation the match is marked
    /// aborted (a later run resumes it) and a `Failed` event is sent.
    pub async fn run(self) -> Result<MatchResult> {
        let result = self.play_match().await;
        if let Err(error) = &result {
            let message = format!("{error:#}");
            let _ = self.db.lock().abort_match(self.settings.match_id, &message);
            let _ = self.events.send(Event::Failed(message));
        }
        result
    }

    async fn play_match(&self) -> Result<MatchResult> {
        let id = self.settings.match_id;
        let mut stored: HashMap<(u32, u8), StoredGame> = self
            .db
            .lock()
            .stored_games(id)?
            .into_iter()
            .map(|game| ((game.round, game.leg), game))
            .collect();
        let mut score = [0u32; 2];
        let mut games_won = [0u32; 2];
        let mut rounds = self.settings.rounds;
        let mut tie_break = false;
        let mut round = 1;
        while round <= rounds {
            let seed = round_seed(self.settings.seed, round);
            let [first, second] = [1u8, 2].map(|leg| {
                let game = Game {
                    round,
                    rounds,
                    leg,
                    white_player: leg,
                };
                (game, stored.remove(&(round, leg)))
            });
            if self.settings.concurrent_mirror {
                let (one, two) = tokio::try_join!(
                    self.play_game(&first.0, seed, score, first.1),
                    self.play_game(&second.0, seed, score, second.1),
                )?;
                let played = !one.stored || !two.stored;
                self.count(&first.0, &one, &mut score, &mut games_won);
                self.count(&second.0, &two, &mut score, &mut games_won);
                self.db.lock().update_match_score(id, round, score)?;
                if played {
                    self.control.pace(3).await?;
                }
            } else {
                for (game, stored) in [first, second] {
                    let end = self.play_game(&game, seed, score, stored).await?;
                    self.count(&game, &end, &mut score, &mut games_won);
                    self.db.lock().update_match_score(id, round, score)?;
                    if !end.stored {
                        self.control.pace(3).await?;
                    }
                }
            }
            (rounds, tie_break) =
                rounds_after(round, rounds, score, tie_break, self.settings.decisive);
            round += 1;
        }
        if let Some(game) = stored.values().next() {
            bail!(
                "match #{id} has a stored game (round {} game {}) after the end of the match",
                game.round,
                game.leg
            );
        }
        let winner = match score[0].cmp(&score[1]) {
            std::cmp::Ordering::Greater => Some(1),
            std::cmp::Ordering::Less => Some(2),
            std::cmp::Ordering::Equal => None,
        };
        self.db.lock().finish_match(id, winner)?;
        let _ = self.events.send(Event::MatchOver {
            score,
            winner,
            rounds,
        });
        Ok(MatchResult {
            score,
            games_won,
            winner,
        })
    }

    /// Adds a finished game to the score; reports it unless that happened before the match
    /// was cut off.
    fn count(&self, game: &Game, end: &GameEnd, score: &mut [u32; 2], games_won: &mut [u32; 2]) {
        score[end.winner as usize - 1] += end.kind.points();
        games_won[end.winner as usize - 1] += 1;
        if !end.stored {
            let _ = self.events.send(Event::GameOver {
                round: game.round,
                leg: game.leg,
                winner: end.winner,
                kind: end.kind,
                score: *score,
            });
        }
    }

    /// The winner and how, when turn `turn_no` by `player` ended the game; `board` is the
    /// position after it from the mover's side.
    fn game_over(
        &self,
        decided_by: &str,
        board: &Board,
        player: u8,
        turn_no: u32,
    ) -> Option<(u8, WinKind)> {
        if decided_by == "timeout" {
            Some((3 - player, WinKind::Timeout))
        } else if let Some(kind) = board.mover_won() {
            Some((player, kind))
        } else if self.settings.max_turns == Some(turn_no) {
            Some((turn_limit_winner(board, player), WinKind::TurnLimit))
        } else {
            None
        }
    }

    /// Plays one game. A `stored` game is taken as it ended, or replayed turn by turn
    /// (each stored roll, position, and play checked against the seed) and continued with
    /// the same dice stream, banks, and history.
    async fn play_game(
        &self,
        game: &Game,
        seed: u64,
        score: [u32; 2],
        stored: Option<StoredGame>,
    ) -> Result<GameEnd> {
        let mut dice = Dice::new(seed);
        let opening = dice.opening();
        let mut side = if opening.0 > opening.1 {
            Side::White
        } else {
            Side::Black
        };
        let mut board = Board::start();
        let mut clocks: Clocks = [self.settings.clock.map(|c| c.bank); 2];
        let mut turn_no = 1u32;
        let mut history: Vec<PastMove> = Vec::new();
        let id = self.settings.match_id;
        let (game_id, resumed) = match stored {
            Some(stored) => {
                if stored.white_player != game.white_player
                    || stored.dice_seed != seed
                    || stored.opening != opening
                {
                    bail!(
                        "match #{id} round {} game {}: the stored game does not follow from \
                         the match seed",
                        game.round,
                        game.leg
                    );
                }
                if let Some((winner, kind)) = stored.result {
                    return Ok(GameEnd {
                        winner,
                        kind,
                        stored: true,
                    });
                }
                for turn in stored.turns {
                    let roll = if turn_no == 1 { opening } else { dice.roll() };
                    let player = game.player(side);
                    let plays = board.legal_plays(roll.0, roll.1);
                    let replays = turn.turn_no == turn_no
                        && turn.side == side
                        && turn.player == player
                        && turn.dice == roll
                        && turn.board == board
                        && match turn.chosen_index {
                            Some(i) => plays.get(i).is_some_and(|p| p.notation() == turn.notation),
                            None => plays.is_empty() || turn.decided_by == "timeout",
                        };
                    if !replays {
                        bail!(
                            "match #{id} round {} game {} turn {turn_no}: the stored turn differs \
                             from a replay of the match seed",
                            game.round,
                            game.leg
                        );
                    }
                    if let Some(i) = turn.chosen_index {
                        board = plays[i].result;
                    }
                    if let Some(ms) = turn.clock_ms {
                        clocks[player as usize - 1] = Some(Duration::from_millis(ms));
                    }
                    history.push(PastMove {
                        turn_no,
                        player,
                        dice: roll,
                        notation: turn.notation,
                    });
                    // Cut off after storing the game's last turn, before closing the game.
                    if let Some((winner, kind)) =
                        self.game_over(&turn.decided_by, &board, player, turn_no)
                    {
                        self.db.lock().finish_game(
                            stored.id,
                            winner,
                            kind.name(),
                            kind.points(),
                            turn_no,
                        )?;
                        return Ok(GameEnd {
                            winner,
                            kind,
                            stored: false,
                        });
                    }
                    board = board.flip();
                    side = side.other();
                    turn_no += 1;
                }
                (stored.id, true)
            }
            None => {
                let game_id = self.db.lock().create_game(
                    id,
                    game.round,
                    game.leg,
                    game.white_player,
                    seed,
                    opening,
                )?;
                (game_id, false)
            }
        };
        let _ = self.events.send(if resumed {
            Event::Resumed {
                round: game.round,
                rounds: game.rounds,
                leg: game.leg,
                white_player: game.white_player,
                turn_no,
                board: white_view(&board, side),
                clocks,
                score,
            }
        } else {
            Event::GameStarted {
                round: game.round,
                rounds: game.rounds,
                leg: game.leg,
                white_player: game.white_player,
                board,
                clocks,
            }
        });
        let delay = self.settings.clock.map_or(Duration::ZERO, |c| c.delay);
        loop {
            let roll = if turn_no == 1 { opening } else { dice.roll() };
            let player = game.player(side);
            let me = player as usize - 1;
            let plays = board.legal_plays(roll.0, roll.1);
            let notations: Vec<String> = plays.iter().map(|p| p.notation()).collect();
            let started = Instant::now();
            let retry = RetryTime::default();
            let mover = self.players[me].clone();
            let protocol = self.settings.protocol.clone();
            let order = option_order(
                protocol.order_seed,
                &position_key(&board, roll, side),
                plays.len(),
            );
            let (chosen, decided_by, decision) = match plays.len() {
                0 => (None, "no_move", None),
                1 => (Some(0), "forced", None),
                _ => {
                    let _ = self.events.send(Event::Thinking {
                        player,
                        side,
                        dice: roll,
                        clocks,
                    });
                    let request = DecisionRequest {
                        board: &board,
                        dice: roll,
                        plays: &plays,
                        notations: &notations,
                        my_score: score[me],
                        opp_score: score[1 - me],
                        round: game.round,
                        rounds: game.rounds,
                        leg: game.leg,
                        clock: self.settings.clock,
                        my_clock: clocks[me],
                        opp_clock: clocks[1 - me],
                        turn_no,
                        max_turns: self.settings.max_turns,
                        player,
                        history: &history,
                        order: &order,
                        seed: derive_seed(seed, &format!("decision:{}:{turn_no}", game.leg)),
                        version: protocol.version,
                        retry: &retry,
                    };
                    let decide = mover.decide(&request);
                    let budget = clocks[me].map(|bank| bank + delay);
                    let retried = &retry;
                    // `None` means the bank ran out before the model answered. Retry time
                    // extends the deadline: it is not charged to the clock.
                    let timed = async move {
                        let Some(budget) = budget else {
                            return Some(decide.await);
                        };
                        tokio::pin!(decide);
                        loop {
                            let deadline = started + budget + retried.get();
                            tokio::select! {
                                outcome = &mut decide => return Some(outcome),
                                _ = tokio::time::sleep_until(deadline.into()) => {
                                    if Instant::now() >= started + budget + retried.get() {
                                        return None;
                                    }
                                }
                            }
                        }
                    };
                    let outcome = tokio::select! {
                        outcome = timed => outcome,
                        _ = self.control.cancelled() => bail!("cancelled"),
                    };
                    // Only time beyond the delay, retries excluded, comes out of the bank.
                    if let Some(bank) = &mut clocks[me] {
                        let used = started.elapsed().saturating_sub(retry.get());
                        *bank = bank.saturating_sub(used.saturating_sub(delay));
                    }
                    match outcome {
                        None => (None, "timeout", None),
                        Some(decision) => {
                            let decision = decision.context(PlayerFault(player))?;
                            let by = if decision.invalid {
                                "fallback"
                            } else {
                                "model"
                            };
                            (Some(decision.index), by, Some(decision))
                        }
                    }
                }
            };
            let latency = started.elapsed();
            let retry_spent = retry.get().min(latency);
            let notation = chosen.map(|i| notations[i].clone()).unwrap_or_default();
            let log = (plays.len() > 1).then(|| DecisionLog {
                protocol: &protocol,
                provider: &mover.provider,
                quantization: mover.quantization.as_deref(),
                option_order: &order,
                probabilities: decision
                    .as_ref()
                    .filter(|d| !d.probabilities.is_empty())
                    .map(|d| {
                        order
                            .iter()
                            .map(|i| {
                                d.probabilities
                                    .iter()
                                    .find(|(j, _)| j == i)
                                    .map(|&(_, p)| p)
                            })
                            .collect()
                    }),
                probability_source: decision.as_ref().and_then(|d| d.probability_source),
                request_ms: (latency - retry_spent).as_millis() as u64,
                retry_ms: retry_spent.as_millis() as u64,
                cost_usd: decision.as_ref().and_then(|d| mover.cost(d)),
                invalid: decision.as_ref().is_some_and(|d| d.invalid),
                group_size: decision.as_ref().and_then(|d| d.group_size),
                reasoning_tokens: decision.as_ref().and_then(|d| d.reasoning_tokens),
            });
            let (input_tokens, output_tokens) = decision
                .as_ref()
                .map_or((0, 0), |d| (d.input_tokens, d.output_tokens));
            let latency_ms = latency.as_millis() as u64;
            self.db.lock().record_turn(
                &TurnRecord {
                    game_id,
                    turn_no,
                    side,
                    player,
                    dice: roll,
                    position: &white_view(&board, side),
                    legal_count: plays.len(),
                    chosen_index: chosen,
                    notation: &notation,
                    decided_by,
                    latency_ms,
                    input_tokens,
                    output_tokens,
                    clock_ms: clocks[me].map(|left| left.as_millis() as u64),
                    decision: log,
                },
                decision.as_ref().map_or(&[][..], |d| &d.exchanges),
            )?;
            if let Some(index) = chosen {
                board = plays[index].result;
            }
            history.push(PastMove {
                turn_no,
                player,
                dice: roll,
                notation: notation.clone(),
            });
            let _ = self.events.send(Event::Moved {
                turn_no,
                side,
                player,
                dice: roll,
                notation,
                board: white_view(&board, side),
                decided_by,
                latency_ms,
                clocks,
            });
            if let Some((winner, kind)) = self.game_over(decided_by, &board, player, turn_no) {
                self.db
                    .lock()
                    .finish_game(game_id, winner, kind.name(), kind.points(), turn_no)?;
                return Ok(GameEnd {
                    winner,
                    kind,
                    stored: false,
                });
            }
            self.control.pace(1).await?;
            board = board.flip();
            side = side.other();
            turn_no += 1;
        }
    }
}

/// Winner of a game stopped at the turn limit, from `board` as `player` (the side that
/// just moved) sees it: the lower pip count, or with equal pips the side due to roll next.
fn turn_limit_winner(board: &Board, player: u8) -> u8 {
    if board.mover_pips() < board.opponent_pips() {
        player
    } else {
        3 - player
    }
}

/// The last round to play and whether the tie-break has started, after `round` ended with
/// `score`. Regular play ends after the planned rounds, or after the round (mirror game
/// included) in which a player reached `FIRST_TO`; a leader then wins, and a tie earns one
/// extra round, or as many as it takes in a decisive match.
fn rounds_after(
    round: u32,
    rounds: u32,
    score: [u32; 2],
    tie_break: bool,
    decisive: bool,
) -> (u32, bool) {
    if round < rounds && score.iter().all(|&s| s < FIRST_TO) {
        (rounds, tie_break)
    } else if score[0] == score[1] && (!tie_break || decisive) {
        (round + 1, true)
    } else {
        (round, tie_break)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::players::baseline::Baseline;
    use crate::players::{Decision, Engine};
    use std::path::{Path, PathBuf};
    use std::sync::atomic::AtomicUsize;

    /// Plays like `inner`, but its `fail_at`-th decision (1-based; 0 = none) fails like a
    /// dropped connection.
    struct Cut {
        inner: Baseline,
        decisions: AtomicUsize,
        fail_at: usize,
    }

    impl Engine for Cut {
        fn decide(&self, req: &DecisionRequest<'_>) -> Result<Decision> {
            if self.decisions.fetch_add(1, Ordering::Relaxed) + 1 == self.fail_at {
                bail!("connection reset");
            }
            self.inner.decide(req)
        }
    }

    fn temp_db(name: &str) -> PathBuf {
        let path = std::env::temp_dir().join(format!("jevgammon-{name}-{}.db", std::process::id()));
        let _ = std::fs::remove_file(&path);
        path
    }

    const SEED: u64 = 20_261_016;

    /// Plays (or resumes) random v safest, three rounds; player `n`'s `fail_at[n - 1]`-th
    /// decision fails.
    async fn play(
        path: &Path,
        match_id: Option<i64>,
        concurrent_mirror: bool,
        fail_at: [usize; 2],
    ) -> (i64, Result<MatchResult>) {
        let db = Db::open(path).unwrap();
        let protocol = Arc::new(Protocol {
            version: PromptVersion::BgV2,
            order_seed: 3,
            harness: Harness::default(),
        });
        let match_id = match_id.unwrap_or_else(|| {
            db.create_match("random", "safest", SEED, 3, None, Some(300), &protocol)
                .unwrap()
        });
        let players = [
            (Baseline::Random, fail_at[0]),
            (Baseline::Safest, fail_at[1]),
        ]
        .map(|(inner, fail_at)| {
            Arc::new(Player::engine(
                "cut",
                Box::new(Cut {
                    inner,
                    decisions: AtomicUsize::new(0),
                    fail_at,
                }),
            ))
        });
        let (events, _receiver) = mpsc::unbounded_channel();
        let runner = Runner {
            db: Mutex::new(db),
            players,
            settings: MatchSettings {
                match_id,
                seed: SEED,
                rounds: 3,
                clock: None,
                max_turns: Some(300),
                decisive: false,
                concurrent_mirror,
                protocol,
            },
            events,
            control: Arc::new(Control::new(MAX_SPEED)),
        };
        (match_id, runner.run().await)
    }

    /// Every stored turn of a match: round, leg, turn, side, player, dice, position,
    /// chosen play, move, how it was decided.
    type TurnRow = (
        u32,
        u8,
        u32,
        String,
        u8,
        u8,
        u8,
        String,
        Option<i64>,
        String,
        String,
    );

    fn turns(path: &Path, match_id: i64) -> Vec<TurnRow> {
        let conn = rusqlite::Connection::open(path).unwrap();
        let mut statement = conn
            .prepare(
                "SELECT g.round_no, g.leg, t.turn_no, t.side, t.player, t.die1, t.die2,
                        t.position, t.chosen_index, t.move, t.decided_by
                 FROM turns t JOIN games g ON g.id = t.game_id
                 WHERE g.match_id = ?1 ORDER BY g.round_no, g.leg, t.turn_no",
            )
            .unwrap();
        statement
            .query_map([match_id], |r| {
                Ok((
                    r.get(0)?,
                    r.get(1)?,
                    r.get(2)?,
                    r.get(3)?,
                    r.get(4)?,
                    r.get(5)?,
                    r.get(6)?,
                    r.get(7)?,
                    r.get(8)?,
                    r.get(9)?,
                    r.get(10)?,
                ))
            })
            .unwrap()
            .collect::<rusqlite::Result<_>>()
            .unwrap()
    }

    /// Games (round, leg, winner, result, points, turns) and the match's status, rounds
    /// played, score, and winner.
    #[allow(clippy::type_complexity)]
    fn outcome(
        path: &Path,
        match_id: i64,
    ) -> (
        Vec<(u32, u8, Option<u8>, Option<String>, Option<u32>, u32)>,
        (String, u32, u32, u32, Option<u8>),
    ) {
        let conn = rusqlite::Connection::open(path).unwrap();
        let mut statement = conn
            .prepare(
                "SELECT round_no, leg, winner_player, result, points, turns FROM games
                 WHERE match_id = ?1 ORDER BY round_no, leg",
            )
            .unwrap();
        let games = statement
            .query_map([match_id], |r| {
                Ok((
                    r.get(0)?,
                    r.get(1)?,
                    r.get(2)?,
                    r.get(3)?,
                    r.get(4)?,
                    r.get(5)?,
                ))
            })
            .unwrap()
            .collect::<rusqlite::Result<_>>()
            .unwrap();
        let status = conn
            .query_row(
                "SELECT status, rounds_played, score1, score2, winner FROM matches WHERE id = ?1",
                [match_id],
                |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?, r.get(4)?)),
            )
            .unwrap();
        (games, status)
    }

    /// A match cut off at many points (its own failing decision, which also drops the
    /// other game of a concurrent round mid-way) and resumed records exactly the turns,
    /// dice, games, and score of an uninterrupted run: same match id, no duplicate turns.
    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn an_interrupted_match_resumes_with_the_same_dice_and_moves() {
        for concurrent in [false, true] {
            let reference = temp_db(&format!("resume-reference-{concurrent}"));
            let (id, result) = play(&reference, None, concurrent, [0, 0]).await;
            result.unwrap();
            let expected_turns = turns(&reference, id);
            let expected = outcome(&reference, id);
            assert_eq!(expected.1.0, "finished");
            assert!(expected.0.len() >= 2);
            for player in [1u8, 2] {
                let decisions = expected_turns
                    .iter()
                    .filter(|t| t.4 == player && t.10 == "model")
                    .count();
                assert!(decisions > 10, "player {player}: {decisions} decisions");
                for cut in [1, 2, decisions / 3, decisions / 2, decisions - 1, decisions] {
                    let path = temp_db(&format!("resume-{concurrent}-{player}-{cut}"));
                    let mut fail_at = [0, 0];
                    fail_at[player as usize - 1] = cut;
                    let (id, cut_off) = play(&path, None, concurrent, fail_at).await;
                    let error = format!("{:#}", cut_off.unwrap_err());
                    assert_eq!(error, format!("player {player}: connection reset"));
                    assert_eq!(outcome(&path, id).1.0, "aborted");
                    let stored = turns(&path, id).len();
                    assert!(stored < expected_turns.len());
                    let (resumed_id, result) = play(&path, Some(id), concurrent, [0, 0]).await;
                    result.unwrap();
                    assert_eq!(resumed_id, id);
                    assert_eq!(
                        turns(&path, id),
                        expected_turns,
                        "{concurrent} {player} {cut}"
                    );
                    assert_eq!(outcome(&path, id), expected);
                    let _ = std::fs::remove_file(&path);
                }
            }
            let _ = std::fs::remove_file(&reference);
        }
    }

    /// The two games of a round played at once record the same turns as played one after
    /// the other (deterministic players do not look at the score), and really interleave.
    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn concurrent_and_sequential_mirror_games_record_the_same_turns() {
        let sequential = temp_db("mirror-sequential");
        let concurrent = temp_db("mirror-concurrent");
        let (one, result) = play(&sequential, None, false, [0, 0]).await;
        result.unwrap();
        let (two, result) = play(&concurrent, None, true, [0, 0]).await;
        result.unwrap();
        assert_eq!(turns(&sequential, one), turns(&concurrent, two));
        assert_eq!(outcome(&sequential, one), outcome(&concurrent, two));
        // Turn ids follow the order the turns were played in.
        let conn = rusqlite::Connection::open(&concurrent).unwrap();
        let (first_of_game_2, last_of_game_1): (i64, i64) = conn
            .query_row(
                "SELECT (SELECT MIN(t.id) FROM turns t JOIN games g ON g.id = t.game_id
                         WHERE g.match_id = ?1 AND g.round_no = 1 AND g.leg = 2),
                        (SELECT MAX(t.id) FROM turns t JOIN games g ON g.id = t.game_id
                         WHERE g.match_id = ?1 AND g.round_no = 1 AND g.leg = 1)",
                [two],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .unwrap();
        assert!(
            first_of_game_2 < last_of_game_1,
            "the games of round 1 interleave"
        );
        let _ = std::fs::remove_file(&sequential);
        let _ = std::fs::remove_file(&concurrent);
    }

    /// Cut off after the game's last turn was stored but before the game and the match
    /// were closed: the resumed run closes them from the stored turns without asking a
    /// player again.
    #[tokio::test(flavor = "multi_thread", worker_threads = 2)]
    async fn a_match_cut_after_its_last_stored_turn_finishes_without_asking() {
        let path = temp_db("resume-closing");
        let (id, result) = play(&path, None, false, [0, 0]).await;
        result.unwrap();
        let expected_turns = turns(&path, id);
        let expected = outcome(&path, id);
        let conn = rusqlite::Connection::open(&path).unwrap();
        conn.execute(
            "UPDATE games SET finished_at = NULL, winner_player = NULL, result = NULL,
                              points = NULL, turns = 0
             WHERE id = (SELECT MAX(id) FROM games WHERE match_id = ?1)",
            [id],
        )
        .unwrap();
        conn.execute(
            "UPDATE matches SET status = 'running', finished_at = NULL, winner = NULL,
                                score1 = 0, score2 = 0
             WHERE id = ?1",
            [id],
        )
        .unwrap();
        drop(conn);
        // Both players would fail their first decision.
        let (_, result) = play(&path, Some(id), false, [1, 1]).await;
        let result = result.unwrap();
        assert_eq!(turns(&path, id), expected_turns);
        assert_eq!(outcome(&path, id), expected);
        assert_eq!(
            (result.score[0], result.score[1], result.winner),
            (expected.1.2, expected.1.3, expected.1.4)
        );
        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn turn_limit_goes_to_lower_pips_and_ties_to_the_side_on_roll() {
        let level = Board::start();
        assert_eq!(turn_limit_winner(&level, 1), 2);
        assert_eq!(turn_limit_winner(&level, 2), 1);
        // The mover runs one back checker 24/18: 161 pips against 167.
        let mut ahead = Board::start();
        ahead.pts[23] -= 1;
        ahead.pts[17] += 1;
        assert_eq!(turn_limit_winner(&ahead, 2), 2);
        assert_eq!(turn_limit_winner(&ahead.flip(), 1), 2);
    }

    #[test]
    fn first_to_five_ends_after_the_round_unless_tied() {
        // Not reached, rounds left: keep going.
        assert_eq!(rounds_after(1, 3, [4, 2], false, false), (3, false));
        // 5 reached and ahead after the mirror game: match over this round.
        assert_eq!(rounds_after(1, 3, [5, 3], false, false), (1, false));
        // The trailing player overtakes in the mirror game: still over, they lead.
        assert_eq!(rounds_after(2, 3, [5, 6], false, false), (2, false));
        // Level at 5: one extra round, then a draw.
        assert_eq!(rounds_after(1, 3, [5, 5], false, false), (2, true));
        assert_eq!(rounds_after(2, 2, [6, 6], true, false), (2, true));
        // A decisive match keeps adding rounds.
        assert_eq!(rounds_after(2, 2, [6, 6], true, true), (3, true));
        // Planned rounds done below 5: leader wins, tie earns an extra round.
        assert_eq!(rounds_after(3, 3, [4, 2], false, false), (3, false));
        assert_eq!(rounds_after(3, 3, [3, 3], false, false), (4, true));
    }
}
