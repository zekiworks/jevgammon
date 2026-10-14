//! Match orchestration: rounds of two mirrored legs sharing one dice seed.

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicU8, Ordering};
use std::time::{Duration, Instant};

use anyhow::{Result, bail};
use tokio::sync::{Notify, mpsc};

use crate::board::{Board, Side, WinKind};
use crate::db::{Db, DecisionLog, TurnRecord};
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

    /// Waits out the current speed's delay and any pause; returns early on cancel.
    async fn pace(&self, multiplier: u32) -> Result<()> {
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
    pub protocol: Arc<Protocol>,
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
    pub db: Db,
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

fn white_view(board: &Board, to_move: Side) -> Board {
    match to_move {
        Side::White => *board,
        Side::Black => board.flip(),
    }
}

impl Runner {
    /// Plays the match to completion and returns the result. On failure or
    /// cancellation the match is marked aborted and a `Failed` event is sent.
    pub async fn run(mut self) -> Result<MatchResult> {
        let result = self.play_match().await;
        if let Err(error) = &result {
            let message = format!("{error:#}");
            let _ = self.db.abort_match(self.settings.match_id, &message);
            let _ = self.events.send(Event::Failed(message));
        }
        result
    }

    async fn play_match(&mut self) -> Result<MatchResult> {
        let id = self.settings.match_id;
        let mut score = [0u32; 2];
        let mut games_won = [0u32; 2];
        let mut rounds = self.settings.rounds;
        let mut tie_break = false;
        let mut round = 1;
        while round <= rounds {
            let seed = round_seed(self.settings.seed, round);
            for leg in 1..=2u8 {
                let game = Game {
                    round,
                    rounds,
                    leg,
                    white_player: leg,
                };
                let (winner, kind) = self.play_game(&game, seed, score).await?;
                score[winner as usize - 1] += kind.points();
                games_won[winner as usize - 1] += 1;
                self.db.update_match_score(id, round, score)?;
                let _ = self.events.send(Event::GameOver {
                    round,
                    leg,
                    winner,
                    kind,
                    score,
                });
                self.control.pace(3).await?;
            }
            (rounds, tie_break) =
                rounds_after(round, rounds, score, tie_break, self.settings.decisive);
            round += 1;
        }
        let winner = match score[0].cmp(&score[1]) {
            std::cmp::Ordering::Greater => Some(1),
            std::cmp::Ordering::Less => Some(2),
            std::cmp::Ordering::Equal => None,
        };
        self.db.finish_match(id, winner)?;
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

    async fn play_game(
        &mut self,
        game: &Game,
        seed: u64,
        score: [u32; 2],
    ) -> Result<(u8, WinKind)> {
        let mut dice = Dice::new(seed);
        let opening = dice.opening();
        let game_id = self.db.create_game(
            self.settings.match_id,
            game.round,
            game.leg,
            game.white_player,
            seed,
            opening,
        )?;
        let mut side = if opening.0 > opening.1 {
            Side::White
        } else {
            Side::Black
        };
        let mut board = Board::start();
        let _ = self.events.send(Event::GameStarted {
            round: game.round,
            rounds: game.rounds,
            leg: game.leg,
            white_player: game.white_player,
            board,
            clocks: [self.settings.clock.map(|c| c.bank); 2],
        });
        let mut clocks: Clocks = [self.settings.clock.map(|c| c.bank); 2];
        let delay = self.settings.clock.map_or(Duration::ZERO, |c| c.delay);
        let mut turn_no = 1u32;
        let mut history: Vec<PastMove> = Vec::new();
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
                            let decision = decision?;
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
            self.db.record_turn(
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
            let finished = if decided_by == "timeout" {
                Some((3 - player, WinKind::Timeout))
            } else if let Some(kind) = board.mover_won() {
                Some((player, kind))
            } else if self.settings.max_turns == Some(turn_no) {
                Some((turn_limit_winner(&board, player), WinKind::TurnLimit))
            } else {
                None
            };
            if let Some((winner, kind)) = finished {
                self.db
                    .finish_game(game_id, winner, kind.name(), kind.points(), turn_no)?;
                return Ok((winner, kind));
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
