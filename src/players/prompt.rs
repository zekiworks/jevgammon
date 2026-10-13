//! What every model sees: `PROMPT.md` (rules, strategy, match rules), then the score, the
//! turn and clocks, the position, the race, and the dice. Every legal play is described by
//! what it leads to, computed here: hits, points made, blots left and the opponent's
//! hitting rolls, points held, prime length, and pip counts. LLMs get the plays as a
//! numbered list in the same message; decision models get them as the options of the
//! choice question.

use std::fmt::Write as _;

use serde_json::Value;

use super::DecisionRequest;
use crate::board::{Board, Play};
use crate::runner::format_clock;

/// Rules, strategy and match rules, with `{rounds}`, `{max_turns}`, `{delay}` and `{bank}`
/// filled in for this match.
const PROMPT: &str = include_str!("../../PROMPT.md");

/// `PROMPT.md` sections left out for decision models: self-hosted ones accept only 4096
/// tokens, and these sections either explain terms or describe the LLM reply format.
const DECISION_SKIP: &[&str] = &[
    "## Dictionary",
    "## Game plans",
    "## Your turn",
    "## Expected output",
    "## Example",
];

/// `PROMPT.md` for this match; `full` = false drops `DECISION_SKIP`.
fn context(req: &DecisionRequest<'_>, full: bool) -> String {
    let mut out = String::with_capacity(PROMPT.len());
    let mut skipping = false;
    for line in PROMPT.lines() {
        if line.starts_with("## ") {
            skipping = !full && DECISION_SKIP.contains(&line);
        }
        if skipping {
            continue;
        }
        // Drop match rules this match doesn't have.
        if (req.max_turns.is_none() && line.starts_with("- **Turn limit:**"))
            || (req.clock.is_none() && line.starts_with("- **Thinking time:**"))
        {
            continue;
        }
        out.push_str(line);
        out.push('\n');
    }
    let mut out = out.trim_end().replace("{rounds}", &req.rounds.to_string());
    if let Some(limit) = req.max_turns {
        out = out.replace("{max_turns}", &limit.to_string());
    }
    if let Some(clock) = req.clock {
        out = out
            .replace("{delay}", &format_clock(clock.delay))
            .replace("{bank}", &format_clock(clock.bank));
    }
    out
}

pub const JEV_INSTRUCTIONS: &str = "Choose the strongest backgammon play for the side to move \
(\"you\") with the given dice, following the rules in the state and taking the match score \
into account. Each choice is a complete legal play in your numbering (from/to per checker, \
`bar` enters from the bar, `off` bears off, `*` hits an opponent blot), followed by what the \
position looks like after it.";

fn standing(req: &DecisionRequest<'_>) -> String {
    match req.my_score.cmp(&req.opp_score) {
        std::cmp::Ordering::Greater => format!("you lead by {}", req.my_score - req.opp_score),
        std::cmp::Ordering::Less => format!("you trail by {}", req.opp_score - req.my_score),
        std::cmp::Ordering::Equal => "tied".to_owned(),
    }
}

fn checker_list(counts: impl Iterator<Item = (usize, i8)>) -> String {
    let mut out = String::new();
    for (point, count) in counts {
        if !out.is_empty() {
            out.push(' ');
        }
        let _ = write!(out, "{point}:{count}");
    }
    if out.is_empty() { "none".into() } else { out }
}

fn mine(board: &Board) -> impl Iterator<Item = (usize, i8)> + '_ {
    (1..=24)
        .rev()
        .filter(|&p| board.pts[p - 1] > 0)
        .map(|p| (p, board.pts[p - 1]))
}

fn theirs(board: &Board) -> impl Iterator<Item = (usize, i8)> + '_ {
    (1..=24)
        .filter(|&p| board.pts[p - 1] < 0)
        .map(|p| (p, -board.pts[p - 1]))
}

/// Score, turn and clocks, position, and dice.
fn turn(req: &DecisionRequest<'_>) -> String {
    let b = req.board;
    let mut out = String::new();
    let _ = writeln!(
        out,
        "Score: you {}, opponent {} ({}).",
        req.my_score,
        req.opp_score,
        standing(req)
    );
    let _ = writeln!(
        out,
        "Match: round {} of {}, game {} of 2 in this round.",
        req.round, req.rounds, req.leg
    );
    match req.max_turns {
        Some(limit) => {
            let _ = writeln!(out, "Turn {} of at most {limit} in this game.", req.turn_no);
        }
        None => {
            let _ = writeln!(out, "Turn {} of this game.", req.turn_no);
        }
    }
    if let (Some(clock), Some(mine)) = (req.clock, req.my_clock) {
        let opponent = req.opp_clock.map_or("-".to_owned(), format_clock);
        let _ = writeln!(
            out,
            "Clock: {} free delay for this decision, then your bank: {} of {} left in this game \
             (opponent {}). If your bank runs out, you lose this game.",
            format_clock(clock.delay),
            format_clock(mine),
            format_clock(clock.bank),
            opponent
        );
    }
    let _ = writeln!(out, "\nPosition (your numbering; you move 24 -> 1):");
    let _ = writeln!(out, "  your checkers:     {}", checker_list(mine(b)));
    let _ = writeln!(out, "  opponent checkers: {}", checker_list(theirs(b)));
    let _ = writeln!(out, "  on the bar: you {}, opponent {}", b.bar[0], b.bar[1]);
    let _ = writeln!(out, "  borne off:  you {}, opponent {}", b.off[0], b.off[1]);
    let _ = writeln!(
        out,
        "  pip count:  you {}, opponent {}",
        b.mover_pips(),
        b.opponent_pips()
    );
    let _ = writeln!(out, "{}", race(b));
    let _ = writeln!(out, "{}", recent_moves(req));
    let _ = write!(out, "Dice: {}-{}\n\n{QUESTION}", req.dice.0, req.dice.1);
    out
}

/// Turns of this game shown before the dice: enough to follow the plan, few enough that
/// Open-Jev's 4,096 tokens (prompt plus one option) still fit.
const RECENT_TURNS: usize = 10;

/// The last `RECENT_TURNS` turns of this game, oldest first, in the mover's numbering.
fn recent_moves(req: &DecisionRequest<'_>) -> String {
    let start = req.history.len().saturating_sub(RECENT_TURNS);
    let shown = &req.history[start..];
    if shown.is_empty() {
        return "Moves so far: none, this is the first move of the game.".to_owned();
    }
    let mut out = format!(
        "Last {} moves of this game (oldest first, your numbering):",
        shown.len()
    );
    for past in shown {
        let mine = past.player == req.player;
        let notation = if past.notation.is_empty() {
            "no legal move".to_owned()
        } else if mine {
            past.notation.clone()
        } else {
            flip_notation(&past.notation)
        };
        let _ = write!(
            out,
            "\n  turn {}, {} rolled {}-{}: {notation}",
            past.turn_no,
            if mine { "you" } else { "opponent" },
            past.dice.0,
            past.dice.1
        );
    }
    out
}

/// A play in the opponent's numbering rewritten in ours: point p is 25 - p; `bar`, `off`
/// and `*` stay.
fn flip_notation(notation: &str) -> String {
    let flip = |point: &str| match point.parse::<u8>() {
        Ok(p) => (25 - p).to_string(),
        Err(_) => point.to_owned(),
    };
    notation
        .split(' ')
        .map(|step| {
            let (step, hit) = step.strip_suffix('*').map_or((step, ""), |s| (s, "*"));
            match step.split_once('/') {
                Some((from, to)) => format!("{}/{}{hit}", flip(from), flip(to)),
                None => step.to_owned(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// Pip lead and whether the checkers have passed each other.
fn race(b: &Board) -> String {
    let (mine, theirs) = (b.mover_pips(), b.opponent_pips());
    let lead = match mine.cmp(&theirs) {
        std::cmp::Ordering::Less => format!("you lead by {} pips", theirs - mine),
        std::cmp::Ordering::Greater => format!("you trail by {} pips", mine - theirs),
        std::cmp::Ordering::Equal => "pip counts are level".to_owned(),
    };
    if b.contact() {
        format!("Race: {lead}; the checkers are still in contact.")
    } else {
        format!("Race: {lead}; no contact, so this is a pure race and nobody can hit.")
    }
}

/// One legal play and the position it leads to, from the mover's side, e.g.
/// `13/7 8/7: hits 0; makes the 7 point; leaves 1 blot, the opponent hits with 11 of 36
/// rolls; you hold 4 points (2 in your home board), longest prime 2; pips: you 159,
/// opponent 167`.
pub fn describe(board: &Board, play: &Play) -> String {
    let after = &play.result;
    let mut out = play.notation();
    let hits = play.steps.iter().filter(|s| s.hit).count();
    let _ = write!(out, ": hits {hits}; ");
    let new: Vec<String> = (1..=24)
        .filter(|&p| after.made(p) && !board.made(p))
        .map(|p| p.to_string())
        .collect();
    match new.as_slice() {
        [] => out.push_str("makes no new point; "),
        [one] => {
            let _ = write!(out, "makes the {one} point; ");
        }
        many => {
            let _ = write!(out, "makes the {} points; ", many.join(", "));
        }
    }
    let blots = after.blots();
    let shots = after.flip().hitting_rolls();
    let _ = write!(
        out,
        "leaves {blots} blot{}, the opponent hits with {shots} of 36 rolls; ",
        if blots == 1 { "" } else { "s" }
    );
    let held = (1..=24).filter(|&p| after.made(p)).count();
    let home = (1..=6).filter(|&p| after.made(p)).count();
    let _ = write!(
        out,
        "you hold {held} points ({home} in your home board), longest prime {}; \
         pips: you {}, opponent {}",
        after.longest_prime(),
        after.mover_pips(),
        after.opponent_pips()
    );
    if after.off[0] > board.off[0] {
        let _ = write!(out, "; borne off {}", after.off[0]);
    }
    out
}

/// `describe` for every legal play, in order.
pub fn descriptions(req: &DecisionRequest<'_>) -> Vec<String> {
    req.plays
        .iter()
        .map(|play| describe(req.board, play))
        .collect()
}

/// Asked right before the legal plays (LLMs) or the options (decision models).
const QUESTION: &str = "Which of the following moves makes a point in front of the opponent's \
checkers, or reduces your single pieces, or gets you closer to your home?";

pub fn llm_user(req: &DecisionRequest<'_>) -> String {
    let mut out = turn(req);
    let _ = writeln!(out, "\n\nLegal plays:");
    for (i, text) in descriptions(req).iter().enumerate() {
        let _ = writeln!(out, "{}. {text}", i + 1);
    }
    let _ = write!(
        out,
        "\nReply with JSON only: {{\"choice\": N}} with N from 1 to {}.",
        req.notations.len()
    );
    out
}

pub fn llm_system(req: &DecisionRequest<'_>) -> String {
    context(req, true)
}

/// Decision models' `state` (OpenAI Decisions: `input`): the short prompt, then this turn.
pub fn jev_state(req: &DecisionRequest<'_>) -> Value {
    Value::String(format!("{}\n\n{}", context(req, false), turn(req)))
}

/// Extracts the 1-based choice from a model reply and converts it to a 0-based index.
pub fn parse_choice(text: &str, count: usize) -> Result<usize, String> {
    let mut text = text.trim();
    if let Some(end) = text.rfind("</think>") {
        text = text[end + "</think>".len()..].trim();
    }
    let text = text
        .trim_start_matches("```json")
        .trim_start_matches("```")
        .trim_end_matches("```")
        .trim();
    let choice = serde_json::from_str::<Value>(text)
        .ok()
        .and_then(|v| {
            v.get("choice")
                .and_then(Value::as_u64)
                .or_else(|| v.as_u64())
        })
        .or_else(|| {
            let start = text.rfind('{')?;
            let end = start + text[start..].find('}')?;
            serde_json::from_str::<Value>(&text[start..=end])
                .ok()?
                .get("choice")?
                .as_u64()
        })
        .ok_or_else(|| "reply is not {\"choice\": N}".to_owned())?;
    match usize::try_from(choice) {
        Ok(n) if (1..=count).contains(&n) => Ok(n - 1),
        _ => Err(format!("choice {choice} is outside 1..={count}")),
    }
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use super::{DecisionRequest, jev_state, parse_choice};
    use crate::board::Board;
    use crate::players::PastMove;
    use crate::runner::Clock;

    #[test]
    fn parses_json_fenced_thinking_and_rejects_out_of_range() {
        assert_eq!(parse_choice("{\"choice\": 3}", 5), Ok(2));
        assert_eq!(parse_choice("```json\n{\"choice\":1}\n```", 5), Ok(0));
        assert_eq!(
            parse_choice("<think>maybe {\"choice\": 9}</think>{\"choice\": 2}", 5),
            Ok(1)
        );
        assert_eq!(parse_choice("I pick {\"choice\": 4} because", 5), Ok(3));
        assert!(parse_choice("{\"choice\": 6}", 5).is_err());
        assert!(parse_choice("{\"choice\": 0}", 5).is_err());
        assert!(parse_choice("play 24/18", 5).is_err());
    }

    #[test]
    fn decision_state_fits_self_hosted_context_and_ends_with_the_turn() {
        let board = Board::start();
        let plays = board.legal_plays(6, 3);
        let notations: Vec<String> = plays.iter().map(|p| p.notation()).collect();
        // 12 turns of 4 long steps each; only the last 10 are shown.
        let history: Vec<PastMove> = (1..=12)
            .map(|turn_no| PastMove {
                turn_no,
                player: if turn_no % 2 == 0 { 1 } else { 2 },
                dice: (6, 6),
                notation: "bar/19* 24/18 13/7* 8/off".to_owned(),
            })
            .collect();
        let req = DecisionRequest {
            board: &board,
            dice: (6, 3),
            plays: &plays,
            notations: &notations,
            my_score: 4,
            opp_score: 4,
            round: 3,
            rounds: 3,
            leg: 2,
            clock: Some(Clock {
                delay: Duration::from_secs(30),
                bank: Duration::from_secs(300),
            }),
            my_clock: Some(Duration::from_secs(300)),
            opp_clock: Some(Duration::from_secs(300)),
            turn_no: 299,
            max_turns: Some(300),
            player: 1,
            history: &history,
        };
        let state = jev_state(&req);
        let state = state.as_str().unwrap();
        // Open-Jev and Cygnet take 4096 tokens; PROMPT.md runs about 3.4 chars per token.
        assert!(
            state.len() < 10_000,
            "decision state is {} chars",
            state.len()
        );
        assert!(state.contains("## Rules") && state.contains("## Match rules"));
        assert!(!state.contains("## Dictionary") && !state.contains("## Example"));
        assert!(!state.contains("{rounds}") && !state.contains("{max_turns}"));
        assert!(state.ends_with(&format!("Dice: 6-3\n\n{}", super::QUESTION)));
        // Turns 3-12: the opponent's (odd) turns flipped to our numbering, ours as played.
        assert!(!state.contains("turn 2,") && state.contains("turn 3,"));
        assert!(state.contains("turn 3, opponent rolled 6-6: bar/6* 1/7 12/18* 17/off"));
        assert!(state.contains("turn 12, you rolled 6-6: bar/19* 24/18 13/7* 8/off"));
    }
}
