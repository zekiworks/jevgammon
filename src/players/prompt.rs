//! What every model sees, by prompt version (`prompts/`). The state is the rules text of the
//! version (rules, strategy, match rules) followed by the score, the turn and clocks, the
//! position, the race, (bg-v2-history only) the last moves, the dice and the question. Every
//! legal play is an option, described by what it leads to (hits, points made, blots left and
//! the opponent's hitting rolls, points held, prime length, pip counts) except in
//! bg-v2-notation, which shows the notation only. Decision models get the state and the
//! options natively; chat models get Cygnet's letter prompt: the state, the instructions and
//! the options lettered A, B, C... in the seeded option order.

use std::fmt::Write as _;

use anyhow::{Result, bail};
use serde_json::{Value, json};

use super::DecisionRequest;
use crate::board::{Board, Play};
use crate::runner::format_clock;

/// Rules, strategy and match rules, with `{rounds}`, `{max_turns}`, `{delay}` and `{bank}`
/// filled in for the match. bg-v2 is League #8's text; nack-v2 drops its opening table. The
/// Nackgammon paired test's pair (Method spec 2026-10-24 §10) drops the table too and differs
/// only in the line naming the starting setup.
const BG_RULES: &str = include_str!("../../prompts/bg-v2.md");
const NACK_RULES: &str = include_str!("../../prompts/nack-v2.md");
const V3_STD_NOTABLE_RULES: &str = include_str!("../../prompts/bg-v3-std-notable.md");
const V3_NACK_RULES: &str = include_str!("../../prompts/bg-v3-nack.md");
const INSTRUCTIONS: &str = include_str!("../../prompts/instructions.txt");
const NOTATION_INSTRUCTIONS: &str = include_str!("../../prompts/instructions-notation.txt");
const QUESTION: &str = include_str!("../../prompts/question.txt");
/// Cygnet's system prompt for the letter readout (`~/code/cygnet/shim/cygnet_shim.py`).
const LETTER_SYSTEM: &str = include_str!("../../prompts/letter-system.txt");
/// Close choices, stage B: the prediction question (verbatim from the request) and the
/// approved format line, sent in place of the letter instruction.
const PREDICTION: &str = include_str!("../../prompts/prediction.txt");
/// Close choices, stage B (Method §9.13): the prediction call's neutral system prompt, in place of
/// the letter readout's (whose format sentences ask for one letter). The play call keeps its own.
const PREDICTION_SYSTEM: &str = include_str!("../../prompts/prediction-system.txt");
/// The four features a prediction may name, as the format line spells them, with their ids
/// in the site's close-choice analysis (Method §9.5).
pub const PREDICTION_FEATURES: [(&str, &str); 4] = [
    ("hitting risk", "hitting"),
    ("making a point", "points"),
    ("the race", "race"),
    ("the prime", "prime"),
];
/// The word for "no feature".
pub const PREDICTION_NONE: &str = "none";

pub const LETTERS: &[u8; 26] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ";

/// A prompt version; its id is logged with every decision.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PromptVersion {
    /// League #8's format: no move history, every play with its consequences.
    BgV2,
    /// bg-v2 with the plays as bare notation (harness ablation A2).
    BgV2Notation,
    /// bg-v2 plus the last 10 moves of the game (League #13's format; ablation A2).
    BgV2History,
    /// bg-v2 without the opening table: Nackgammon and the opening control.
    NackV2,
    /// Nackgammon paired test, standard side: bg-v2 without the opening table, the setup line
    /// naming the standard starting position.
    BgV3StdNoTable,
    /// Nackgammon paired test, Nackgammon side: bg-v3-std-notable with the setup line naming
    /// the Nackgammon starting position, nothing else.
    BgV3Nack,
}

impl PromptVersion {
    pub const ALL: [PromptVersion; 6] = [
        PromptVersion::BgV2,
        PromptVersion::BgV2Notation,
        PromptVersion::BgV2History,
        PromptVersion::NackV2,
        PromptVersion::BgV3StdNoTable,
        PromptVersion::BgV3Nack,
    ];

    pub fn id(self) -> &'static str {
        match self {
            PromptVersion::BgV2 => "bg-v2",
            PromptVersion::BgV2Notation => "bg-v2-notation",
            PromptVersion::BgV2History => "bg-v2-history",
            PromptVersion::NackV2 => "nack-v2",
            PromptVersion::BgV3StdNoTable => "bg-v3-std-notable",
            PromptVersion::BgV3Nack => "bg-v3-nack",
        }
    }

    pub fn parse(id: &str) -> Result<Self> {
        match Self::ALL.into_iter().find(|v| v.id() == id) {
            Some(version) => Ok(version),
            None => bail!(
                "unknown prompt version `{id}`; use one of: {}",
                Self::ALL.map(Self::id).join(", ")
            ),
        }
    }

    fn rules(self) -> &'static str {
        match self {
            PromptVersion::NackV2 => NACK_RULES,
            PromptVersion::BgV3StdNoTable => V3_STD_NOTABLE_RULES,
            PromptVersion::BgV3Nack => V3_NACK_RULES,
            _ => BG_RULES,
        }
    }

    fn history(self) -> bool {
        self == PromptVersion::BgV2History
    }

    fn consequences(self) -> bool {
        self != PromptVersion::BgV2Notation
    }
}

impl std::str::FromStr for PromptVersion {
    type Err = anyhow::Error;

    fn from_str(id: &str) -> Result<Self> {
        Self::parse(id)
    }
}

/// The version's rules text for this match.
fn context(req: &DecisionRequest<'_>) -> String {
    let rules = req.version.rules();
    let mut out = String::with_capacity(rules.len());
    for line in rules.lines() {
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

/// Score, turn and clocks, position, race, (bg-v2-history) recent moves, dice, question.
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
    if req.version.history() {
        let _ = writeln!(out, "{}", recent_moves(req));
    }
    let _ = write!(
        out,
        "Dice: {}-{}\n\n{}",
        req.dice.0,
        req.dice.1,
        QUESTION.trim_end()
    );
    out
}

/// Turns of this game shown before the dice in bg-v2-history: enough to follow the plan,
/// few enough that Open-Jev's 4,096 tokens (prompt plus one option) still fit.
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

/// The state: the version's rules text, then this turn.
pub fn state(req: &DecisionRequest<'_>) -> String {
    format!("{}\n\n{}", context(req), turn(req))
}

/// The question's instructions (decision models' `instructions`; the letter prompt's line
/// between the state and the options).
pub fn instructions(req: &DecisionRequest<'_>) -> &'static str {
    if req.version.consequences() {
        INSTRUCTIONS.trim_end()
    } else {
        NOTATION_INSTRUCTIONS.trim_end()
    }
}

/// The option text of legal play `index`: described, or bare notation in bg-v2-notation.
pub fn option_text(req: &DecisionRequest<'_>, index: usize) -> String {
    if req.version.consequences() {
        describe(req.board, &req.plays[index])
    } else {
        req.notations[index].clone()
    }
}

pub fn letter_system() -> &'static str {
    LETTER_SYSTEM.trim_end()
}

pub fn prediction_system() -> &'static str {
    PREDICTION_SYSTEM.trim_end()
}

pub fn letter(position: usize) -> char {
    LETTERS[position] as char
}

/// Cygnet's `build_prompt`: the state, the instructions, then `shown` (indices into the
/// legal plays, at most 26) lettered A, B, C... in that order.
pub fn letter_user(req: &DecisionRequest<'_>, shown: &[usize]) -> String {
    let mut out = lettered_options(req, shown);
    out.push_str("\n\nAnswer with the letter of exactly one option, and nothing else:");
    out
}

/// The state, the instructions and the lettered options: the letter prompt without its last
/// line.
fn lettered_options(req: &DecisionRequest<'_>, shown: &[usize]) -> String {
    let mut out = format!(
        "{}\n\n{}\n\nOptions:",
        state(req).trim_end(),
        instructions(req)
    );
    for (position, &index) in shown.iter().enumerate() {
        let _ = write!(out, "\n{}. {}", letter(position), option_text(req, index));
    }
    out
}

/// Close choices, stage B (Method §9.9): the letter prompt of the play call with its last
/// line (the letter instruction) replaced by the prediction question and the format line.
/// Same system prompt, state, instructions and options in the same order.
pub fn prediction_user(req: &DecisionRequest<'_>, shown: &[usize]) -> String {
    format!(
        "{}\n\n{}",
        lettered_options(req, shown),
        PREDICTION.trim_end()
    )
}

/// A parsed prediction: the named features' ids (`hitting`, `points`, `race`, `prime`) in
/// that fixed order, empty for a valid "none"; `Err` with the reason for an invalid answer.
/// Valid answers are JSON: `{"features": [...]}` (the constrained form) or a bare array,
/// optionally after reasoning in `<think>` tags or inside a ```json fence; each item must be
/// one of the four feature words or `none` (case and outer spaces ignored, nothing else
/// mapped); duplicates collapse; `none` alone or an empty list is the empty set; `none` with
/// a feature, an unknown item, a non-string item, prose, a refusal or an empty reply is
/// invalid. No repair.
pub fn parse_prediction(text: &str) -> Result<Vec<&'static str>, String> {
    let mut text = text.trim();
    if let Some(end) = text.rfind("</think>") {
        text = text[end + "</think>".len()..].trim();
    }
    let text = text
        .trim_start_matches("```json")
        .trim_start_matches("```")
        .trim_end_matches("```")
        .trim();
    if text.is_empty() {
        return Err("empty reply".into());
    }
    let value: Value = serde_json::from_str(text).map_err(|_| "not JSON".to_owned())?;
    let items = match &value {
        Value::Array(items) => items,
        Value::Object(fields) => match (fields.get("features"), fields.len()) {
            (Some(Value::Array(items)), 1) => items,
            _ => return Err("not {\"features\": [...]}".into()),
        },
        _ => return Err("not a list of features".into()),
    };
    let mut named = [false; 4];
    let mut none = false;
    for item in items {
        let Some(word) = item.as_str() else {
            return Err(format!("item {item} is not a string"));
        };
        let word = word.trim().to_ascii_lowercase();
        if word == PREDICTION_NONE {
            none = true;
            continue;
        }
        match PREDICTION_FEATURES.iter().position(|(w, _)| *w == word) {
            Some(k) => named[k] = true,
            None => return Err(format!("unknown feature `{word}`")),
        }
    }
    if none && named.iter().any(|&n| n) {
        return Err("none together with a feature".into());
    }
    Ok(PREDICTION_FEATURES
        .iter()
        .zip(named)
        .filter(|(_, n)| *n)
        .map(|((_, id), _)| *id)
        .collect())
}

/// The position (0-based) of the option letter in a constrained one-letter reply: `C`,
/// `{"choice": "C"}`, possibly after reasoning in `<think>` tags. `None` when the reply is
/// not one of the first `count` letters.
pub fn parse_letter(text: &str, count: usize) -> Option<usize> {
    let mut text = text.trim();
    if let Some(end) = text.rfind("</think>") {
        text = text[end + "</think>".len()..].trim();
    }
    let text = text
        .trim_start_matches("```json")
        .trim_start_matches("```")
        .trim_end_matches("```")
        .trim();
    let parsed = serde_json::from_str::<Value>(text).ok();
    let answer = match &parsed {
        Some(value) => match value.get("choice").and_then(Value::as_str) {
            Some(choice) => choice,
            None => value.as_str()?,
        },
        None => text,
    };
    let answer = answer.trim().trim_end_matches('.');
    match answer.as_bytes() {
        [byte] => LETTERS[..count.min(26)]
            .iter()
            .position(|l| *l == byte.to_ascii_uppercase()),
        _ => None,
    }
}

/// Probability per option letter from the top log-probabilities of the answer token,
/// summed over surface forms (`C`, ` C`, `C.`) and normalised over the first `count`
/// letters, as Cygnet's `letter_probs`. `None` when no option letter appears.
pub fn letter_probabilities(top: &[(String, f64)], count: usize) -> Option<Vec<f64>> {
    let count = count.min(26);
    let mut mass = vec![0.0; count];
    let mut any = false;
    for (token, logprob) in top {
        let core = token
            .trim_start_matches(|c: char| c.is_whitespace() || "([{'\"".contains(c))
            .trim_end_matches(|c: char| c.is_whitespace() || ".,:)]}'\"".contains(c));
        let [byte] = core.as_bytes() else {
            continue;
        };
        if !byte.is_ascii_alphabetic() {
            continue;
        }
        let position = (byte.to_ascii_uppercase() - b'A') as usize;
        if position < count {
            mass[position] += logprob.exp();
            any = true;
        }
    }
    let total: f64 = mass.iter().sum();
    if !any || total <= 0.0 {
        return None;
    }
    Some(mass.into_iter().map(|m| m / total).collect())
}

/// Everything a model would be sent for this request, for `jevgammon render`: the state,
/// the instructions, the letter prompt and the options in the seeded order.
pub fn render(req: &DecisionRequest<'_>) -> Value {
    let options: Vec<Value> = req
        .order
        .iter()
        .enumerate()
        .map(|(position, &index)| {
            json!({
                "letter": (position < 26).then(|| letter(position).to_string()),
                "index": index,
                "notation": req.notations[index],
                "text": option_text(req, index),
            })
        })
        .collect();
    let letters = (req.order.len() <= 26).then(|| letter_user(req, req.order));
    json!({
        "version": req.version.id(),
        "state": state(req),
        "instructions": instructions(req),
        "system": letter_system(),
        "user": letters,
        "order": req.order,
        "options": options,
    })
}

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use serde_json::Value;

    use super::*;
    use crate::board::{Board, Side};
    use crate::players::PastMove;
    use crate::runner::Clock;

    struct Fixture {
        board: Board,
        plays: Vec<Play>,
        notations: Vec<String>,
        history: Vec<PastMove>,
        order: Vec<usize>,
        retry: crate::http::RetryTime,
    }

    impl Fixture {
        fn new(board: Board, dice: (u8, u8)) -> Self {
            let plays = board.legal_plays(dice.0, dice.1);
            let notations: Vec<String> = plays.iter().map(|p| p.notation()).collect();
            let order = (0..plays.len()).rev().collect();
            Fixture {
                board,
                plays,
                notations,
                history: Vec::new(),
                order,
                retry: crate::http::RetryTime::default(),
            }
        }

        fn request(&self, version: PromptVersion, dice: (u8, u8)) -> DecisionRequest<'_> {
            DecisionRequest {
                board: &self.board,
                dice,
                plays: &self.plays,
                notations: &self.notations,
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
                history: &self.history,
                order: &self.order,
                seed: 1,
                version,
                retry: &self.retry,
            }
        }
    }

    /// bg-v2 reproduces League #8 exactly: a stored decision-model request (exchange
    /// #113082 of league.db) has the same state, instructions, and option texts.
    #[test]
    fn bg_v2_is_league_8() {
        let fixture: Value =
            serde_json::from_str(include_str!("testdata/league8_request.json")).unwrap();
        let (board, side) = crate::db::parse_position(&fixture["position"]).unwrap();
        assert_eq!(side, Side::Black);
        let n = |key: &str| fixture[key].as_u64().unwrap();
        let dice = (
            fixture["dice"][0].as_u64().unwrap() as u8,
            fixture["dice"][1].as_u64().unwrap() as u8,
        );
        let plays = board.legal_plays(dice.0, dice.1);
        let notations: Vec<String> = plays.iter().map(|p| p.notation()).collect();
        let order: Vec<usize> = (0..plays.len()).collect();
        let req = DecisionRequest {
            board: &board,
            dice,
            plays: &plays,
            notations: &notations,
            my_score: n("my_score") as u32,
            opp_score: n("opp_score") as u32,
            round: n("round") as u32,
            rounds: n("rounds") as u32,
            leg: n("leg") as u8,
            clock: Some(Clock {
                bank: Duration::from_secs(n("clock_seconds")),
                delay: Duration::from_secs(n("delay_seconds")),
            }),
            my_clock: Some(Duration::from_millis(n("my_clock_ms"))),
            opp_clock: Some(Duration::from_millis(n("opp_clock_ms"))),
            turn_no: n("turn_no") as u32,
            max_turns: Some(n("max_turns") as u32),
            player: n("player") as u8,
            history: &[],
            order: &order,
            seed: 0,
            version: PromptVersion::BgV2,
            retry: &crate::http::RetryTime::default(),
        };
        let stored = &fixture["request"];
        assert_eq!(state(&req), stored["state"].as_str().unwrap());
        let question = &stored["questions"]["play"];
        assert_eq!(
            instructions(&req),
            question["instructions"].as_str().unwrap()
        );
        let criteria = question["criteria"].as_object().unwrap();
        assert_eq!(criteria.len(), plays.len());
        for (index, notation) in notations.iter().enumerate() {
            assert_eq!(
                option_text(&req, index),
                criteria[notation].as_str().unwrap(),
                "{notation}"
            );
        }
        // The letter prompt is Cygnet's build_prompt over that state.
        let user = letter_user(&req, &order);
        assert!(user.starts_with(stored["state"].as_str().unwrap().trim_end()));
        assert!(user.contains(&format!(
            "\n\n{}\n\nOptions:\nA. {}\nB. ",
            question["instructions"].as_str().unwrap(),
            criteria[&notations[0]].as_str().unwrap()
        )));
        assert!(
            user.ends_with("\n\nAnswer with the letter of exactly one option, and nothing else:")
        );
    }

    #[test]
    fn versions_differ_only_where_designed() {
        let mut fixture = Fixture::new(Board::start(), (6, 3));
        // 12 turns of 4 long steps each; only the last 10 are shown.
        fixture.history = (1..=12)
            .map(|turn_no| PastMove {
                turn_no,
                player: if turn_no % 2 == 0 { 1 } else { 2 },
                dice: (6, 6),
                notation: "bar/19* 24/18 13/7* 8/off".to_owned(),
            })
            .collect();
        let dice = (6, 3);
        let bg = fixture.request(PromptVersion::BgV2, dice);
        let history = fixture.request(PromptVersion::BgV2History, dice);
        let notation = fixture.request(PromptVersion::BgV2Notation, dice);
        let nack = fixture.request(PromptVersion::NackV2, dice);

        let bg_state = state(&bg);
        assert!(bg_state.contains("## Rules") && bg_state.contains("## Match rules"));
        assert!(bg_state.contains("## Opening rolls"));
        assert!(!bg_state.contains("## Dictionary") && !bg_state.contains("## Example"));
        assert!(!bg_state.contains("{rounds}") && !bg_state.contains("{max_turns}"));
        assert!(!bg_state.contains("moves of this game"));
        assert!(bg_state.ends_with(&format!("Dice: 6-3\n\n{}", QUESTION.trim_end())));
        // Open-Jev and Cygnet take 4096 tokens; the text runs about 3.4 chars per token.
        assert!(state(&history).len() < 10_000);

        // History: the last 10 turns before the dice, the opponent's flipped to our numbering.
        let history_state = state(&history);
        assert!(!history_state.contains("turn 2,") && history_state.contains("turn 3,"));
        assert!(history_state.contains("turn 3, opponent rolled 6-6: bar/6* 1/7 12/18* 17/off"));
        assert!(history_state.contains("turn 12, you rolled 6-6: bar/19* 24/18 13/7* 8/off"));
        let without: String = history_state
            .lines()
            .filter(|l| !l.starts_with("Last 10 moves") && !l.starts_with("  turn "))
            .collect::<Vec<_>>()
            .join("\n");
        assert_eq!(without, bg_state);

        // Notation only: same state, bare options, instructions without the description.
        assert_eq!(state(&notation), bg_state);
        assert_eq!(option_text(&notation, 0), fixture.notations[0]);
        assert!(option_text(&bg, 0).starts_with(&format!("{}: hits ", fixture.notations[0])));
        assert!(instructions(&bg).ends_with("followed by what the position looks like after it."));
        assert!(!instructions(&notation).contains("followed by"));

        // Nackgammon: bg-v2 without the opening table, nothing else.
        let nack_state = state(&nack);
        assert!(!nack_state.contains("## Opening rolls") && !nack_state.contains("| 6-5 |"));
        assert!(nack_state.contains("## Strategy principles"));
        let start = bg_state.find("## Opening rolls").unwrap();
        let end = bg_state.find("## Match rules").unwrap();
        assert_eq!(
            nack_state,
            format!("{}{}", &bg_state[..start], &bg_state[end..])
        );

        // Nackgammon paired test: both sides drop the opening table; the two differ only in
        // the line naming the starting setup.
        let std_state = state(&fixture.request(PromptVersion::BgV3StdNoTable, dice));
        let nack3_state = state(&fixture.request(PromptVersion::BgV3Nack, dice));
        assert!(!std_state.contains("## Opening rolls") && !nack3_state.contains("## Opening rolls"));
        let differ: Vec<(&str, &str)> = std_state
            .lines()
            .zip(nack3_state.lines())
            .filter(|(a, b)| a != b)
            .collect();
        assert_eq!(std_state.lines().count(), nack3_state.lines().count());
        assert_eq!(differ.len(), 1);
        assert!(differ[0].0.contains("in the standard starting position: two on the 24-point, five"));
        assert!(differ[0].1.contains("in the Nackgammon starting position: two on the 24-point, two on the 23-point"));

        // Letters follow the request's order.
        let user = letter_user(&bg, bg.order);
        let last = fixture.plays.len() - 1;
        assert!(user.contains(&format!("\nA. {}: hits", fixture.notations[last])));
        for version in PromptVersion::ALL {
            assert_eq!(PromptVersion::parse(version.id()).unwrap(), version);
        }
        assert!(PromptVersion::parse("bg-v1").is_err());
    }

    #[test]
    fn parses_letters_and_probabilities() {
        assert_eq!(parse_letter("C", 5), Some(2));
        assert_eq!(parse_letter(" {\"choice\": \"b\"} ", 5), Some(1));
        assert_eq!(parse_letter("<think>A or B</think>E.", 5), Some(4));
        assert_eq!(parse_letter("F", 5), None);
        assert_eq!(parse_letter("The answer is A", 5), None);
        assert_eq!(parse_letter("{\"choice\": 3}", 5), None);
        let top: Vec<(String, f64)> = [
            (" C", 0.75f64),
            ("C", 0.05),
            (" A", 0.1),
            (" the", 0.05),
            (" Z", 0.05),
        ]
        .iter()
        .map(|(t, p)| (t.to_string(), p.ln()))
        .collect();
        let probs = letter_probabilities(&top, 3).unwrap();
        assert!((probs[2] - 0.8 / 0.9).abs() < 1e-9);
        assert!((probs[0] - 0.1 / 0.9).abs() < 1e-9);
        assert_eq!(probs[1], 0.0);
        assert!(letter_probabilities(&[(" the".into(), -0.1)], 3).is_none());
    }

    /// The prediction prompt is the letter prompt with only its last line replaced.
    #[test]
    fn prediction_prompt_replaces_only_the_letter_instruction() {
        let fixture = Fixture::new(Board::start(), (6, 3));
        let req = fixture.request(PromptVersion::BgV2, (6, 3));
        let letter = letter_user(&req, req.order);
        let prediction = prediction_user(&req, req.order);
        let tail = "\n\nAnswer with the letter of exactly one option, and nothing else:";
        let common = letter.strip_suffix(tail).unwrap();
        let asked = prediction.strip_prefix(common).unwrap();
        assert_eq!(
            asked,
            "\n\nIf you answered this position again independently, on which features might your \
             chosen plays differ: hitting risk, making a point, the race or the prime? You may name \
             several, or none.\nAnswer with the features you name, using only these words: hitting \
             risk, making a point, the race, the prime; or the single word none."
        );
    }

    /// Synthetic answers: the validity rules of Method §9.9 and the stage B plan (B1).
    #[test]
    fn parses_predictions() {
        let ok = |text: &str| parse_prediction(text).unwrap();
        let bad = |text: &str| parse_prediction(text).unwrap_err();
        let empty: Vec<&str> = Vec::new();
        assert_eq!(
            ok(r#"{"features": ["the prime", "hitting risk"]}"#),
            ["hitting", "prime"]
        );
        assert_eq!(
            ok(r#"{"features": ["hitting risk", "making a point", "the race", "the prime"]}"#),
            ["hitting", "points", "race", "prime"]
        );
        assert_eq!(ok(r#"{"features": ["the race", "the race"]}"#), ["race"]);
        assert_eq!(ok(r#"{"features": [" The Race "]}"#), ["race"]);
        assert_eq!(ok(r#"["making a point"]"#), ["points"]);
        assert_eq!(ok(r#"{"features": ["none"]}"#), empty);
        assert_eq!(ok(r#"{"features": ["none", "none"]}"#), empty);
        assert_eq!(ok(r#"{"features": []}"#), empty);
        assert_eq!(ok("[]"), empty);
        assert_eq!(
            ok("<think>maybe the race</think>{\"features\": [\"the race\"]}"),
            ["race"]
        );
        assert_eq!(
            ok("```json\n{\"features\": [\"the prime\"]}\n```"),
            ["prime"]
        );
        assert_eq!(
            bad(r#"{"features": ["none", "the race"]}"#),
            "none together with a feature"
        );
        assert_eq!(bad(r#"{"features": ["race"]}"#), "unknown feature `race`");
        assert_eq!(bad(r#"{"features": ["blots"]}"#), "unknown feature `blots`");
        assert_eq!(bad(r#"{"features": [1]}"#), "item 1 is not a string");
        assert_eq!(
            bad(r#"{"features": "the race"}"#),
            "not {\"features\": [...]}"
        );
        assert_eq!(
            bad(r#"{"features": [], "why": "x"}"#),
            "not {\"features\": [...]}"
        );
        assert_eq!(bad(r#"{"choice": "A"}"#), "not {\"features\": [...]}");
        assert_eq!(bad(r#""none""#), "not a list of features");
        assert_eq!(bad("none"), "not JSON");
        assert_eq!(bad("the race, the prime"), "not JSON");
        assert_eq!(bad("I can't help with that."), "not JSON");
        assert_eq!(bad("   "), "empty reply");
        assert_eq!(bad("<think>long thought</think>"), "empty reply");
    }
}
