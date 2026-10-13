//! Backgammon rules: positions, legal full-turn plays, and game results.
//!
//! A [`Board`] is always stored from the perspective of the side to move: the mover
//! travels from point 24 toward point 1 and bears off past point 1. [`Board::flip`]
//! hands the position to the opponent.

use std::collections::HashSet;
use std::fmt::Write as _;

pub const CHECKERS: u8 = 15;
/// Source index used for a checker entering from the bar.
pub const BAR: u8 = 25;
/// Destination index used for a checker borne off.
pub const OFF: u8 = 0;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Side {
    White,
    Black,
}

impl Side {
    pub fn other(self) -> Self {
        match self {
            Side::White => Side::Black,
            Side::Black => Side::White,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Side::White => "white",
            Side::Black => "black",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Board {
    /// `pts[i]` holds point `i + 1` in the mover's numbering: positive counts are the
    /// mover's checkers, negative counts the opponent's.
    pub pts: [i8; 24],
    /// `[mover, opponent]` checkers on the bar.
    pub bar: [u8; 2],
    /// `[mover, opponent]` checkers borne off.
    pub off: [u8; 2],
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Step {
    /// 1..=24, or [`BAR`].
    pub from: u8,
    /// 1..=24, or [`OFF`].
    pub to: u8,
    pub die: u8,
    pub hit: bool,
}

#[derive(Clone, Debug)]
pub struct Play {
    pub steps: Vec<Step>,
    /// Position after the play, still from the mover's perspective.
    pub result: Board,
}

impl Play {
    /// Standard notation in the mover's numbering, e.g. `bar/22 13/11*`.
    pub fn notation(&self) -> String {
        let mut out = String::new();
        for (index, step) in self.steps.iter().enumerate() {
            if index > 0 {
                out.push(' ');
            }
            let from = if step.from == BAR {
                "bar".to_owned()
            } else {
                step.from.to_string()
            };
            let to = if step.to == OFF {
                "off".to_owned()
            } else {
                step.to.to_string()
            };
            let _ = write!(out, "{from}/{to}{}", if step.hit { "*" } else { "" });
        }
        out
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WinKind {
    Single,
    Gammon,
    Backgammon,
    /// The opponent's clock ran out while it was deciding; always worth one point.
    Timeout,
    /// The game reached the turn limit and was decided on pip count; one point.
    TurnLimit,
}

impl WinKind {
    pub fn points(self) -> u32 {
        match self {
            WinKind::Single | WinKind::Timeout | WinKind::TurnLimit => 1,
            WinKind::Gammon => 2,
            WinKind::Backgammon => 3,
        }
    }

    /// Stored in `games.result`.
    pub fn name(self) -> &'static str {
        match self {
            WinKind::Single => "single",
            WinKind::Gammon => "gammon",
            WinKind::Backgammon => "backgammon",
            WinKind::Timeout => "timeout",
            WinKind::TurnLimit => "turn_limit",
        }
    }

    /// Shown after "wins", e.g. "wins a gammon", "wins on time".
    pub fn describe(self) -> &'static str {
        match self {
            WinKind::Single => "a single game",
            WinKind::Gammon => "a gammon",
            WinKind::Backgammon => "a backgammon",
            WinKind::Timeout => "on time",
            WinKind::TurnLimit => "at the turn limit",
        }
    }
}

impl Board {
    pub fn start() -> Self {
        let mut pts = [0i8; 24];
        for (point, count) in [(24, 2), (13, 5), (8, 3), (6, 5)] {
            pts[point - 1] = count;
            pts[24 - point] = -count;
        }
        Board {
            pts,
            bar: [0, 0],
            off: [0, 0],
        }
    }

    /// The same position seen by the opponent.
    pub fn flip(&self) -> Self {
        let mut pts = [0i8; 24];
        for (i, slot) in pts.iter_mut().enumerate() {
            *slot = -self.pts[23 - i];
        }
        Board {
            pts,
            bar: [self.bar[1], self.bar[0]],
            off: [self.off[1], self.off[0]],
        }
    }

    pub fn mover_pips(&self) -> u32 {
        let board: u32 = self
            .pts
            .iter()
            .enumerate()
            .filter(|&(_, &n)| n > 0)
            .map(|(i, &n)| (i as u32 + 1) * n as u32)
            .sum();
        board + 25 * self.bar[0] as u32
    }

    pub fn opponent_pips(&self) -> u32 {
        self.flip().mover_pips()
    }

    /// The mover has borne off all checkers; returns the kind of win if so.
    pub fn mover_won(&self) -> Option<WinKind> {
        if self.off[0] < CHECKERS {
            return None;
        }
        if self.off[1] > 0 {
            return Some(WinKind::Single);
        }
        let in_winner_home = self.pts[..6].iter().any(|&n| n < 0);
        if self.bar[1] > 0 || in_winner_home {
            Some(WinKind::Backgammon)
        } else {
            Some(WinKind::Gammon)
        }
    }

    fn all_home(&self) -> bool {
        self.bar[0] == 0 && self.pts[6..].iter().all(|&n| n <= 0)
    }

    /// Moves one checker from `from` by `die` pips, or returns `None` when illegal.
    fn step(&self, from: u8, die: u8) -> Option<(Board, Step)> {
        let mut next = *self;
        if from == BAR {
            if self.bar[0] == 0 {
                return None;
            }
            next.bar[0] -= 1;
        } else {
            if self.bar[0] > 0 || self.pts[from as usize - 1] <= 0 {
                return None;
            }
            next.pts[from as usize - 1] -= 1;
        }
        let target = from as i8 - die as i8;
        if target >= 1 {
            let slot = &mut next.pts[target as usize - 1];
            if *slot < -1 {
                return None;
            }
            let hit = *slot == -1;
            if hit {
                *slot = 0;
                next.bar[1] += 1;
            }
            *slot += 1;
            return Some((
                next,
                Step {
                    from,
                    to: target as u8,
                    die,
                    hit,
                },
            ));
        }
        if from == BAR || !self.all_home() {
            return None;
        }
        // Overshooting bear-off is only allowed from the highest occupied point.
        if target < 0 && self.pts[from as usize..6].iter().any(|&n| n > 0) {
            return None;
        }
        next.off[0] += 1;
        Some((
            next,
            Step {
                from,
                to: OFF,
                die,
                hit: false,
            },
        ))
    }

    fn sources(&self) -> impl Iterator<Item = u8> + '_ {
        let bar = (self.bar[0] > 0).then_some(BAR);
        let points = (1..=24u8)
            .rev()
            .filter(move |&p| self.bar[0] == 0 && self.pts[p as usize - 1] > 0);
        bar.into_iter().chain(points)
    }

    fn search(&self, dice: &[u8], steps: &mut Vec<Step>, leaves: &mut Vec<Play>) {
        let Some((&die, rest)) = dice.split_first() else {
            leaves.push(Play {
                steps: steps.clone(),
                result: *self,
            });
            return;
        };
        let mut moved = false;
        for from in self.sources() {
            if let Some((next, step)) = self.step(from, die) {
                moved = true;
                steps.push(step);
                next.search(rest, steps, leaves);
                steps.pop();
            }
        }
        if !moved {
            leaves.push(Play {
                steps: steps.clone(),
                result: *self,
            });
        }
    }

    /// Every legal full-turn play for the roll, deduplicated by resulting position.
    /// Empty when the mover cannot move at all.
    pub fn legal_plays(&self, d1: u8, d2: u8) -> Vec<Play> {
        let mut leaves = Vec::new();
        let mut steps = Vec::with_capacity(4);
        if d1 == d2 {
            self.search(&[d1; 4], &mut steps, &mut leaves);
        } else {
            self.search(&[d1, d2], &mut steps, &mut leaves);
            self.search(&[d2, d1], &mut steps, &mut leaves);
        }
        let max_len = leaves.iter().map(|p| p.steps.len()).max().unwrap_or(0);
        if max_len == 0 {
            return Vec::new();
        }
        leaves.retain(|p| p.steps.len() == max_len);
        // With only one die playable, the higher die must be used when possible.
        if d1 != d2 && max_len == 1 {
            let high = d1.max(d2);
            if leaves.iter().any(|p| p.steps[0].die == high) {
                leaves.retain(|p| p.steps[0].die == high);
            }
        }
        let mut seen = HashSet::with_capacity(leaves.len());
        leaves.retain(|p| seen.insert(p.result));
        leaves
    }

    /// How many of the 36 rolls give the mover a legal play that hits a blot.
    pub fn hitting_rolls(&self) -> u32 {
        if !self.pts.contains(&-1) {
            return 0;
        }
        let mut rolls = 0;
        for d1 in 1..=6u8 {
            for d2 in d1..=6u8 {
                let hits = self
                    .legal_plays(d1, d2)
                    .iter()
                    .any(|play| play.steps.iter().any(|step| step.hit));
                if hits {
                    rolls += if d1 == d2 { 1 } else { 2 };
                }
            }
        }
        rolls
    }

    /// Points (1..=24) holding two or more of the mover's checkers.
    pub fn made(&self, point: usize) -> bool {
        self.pts[point - 1] >= 2
    }

    /// The mover's points holding exactly one checker.
    pub fn blots(&self) -> usize {
        self.pts.iter().filter(|&&n| n == 1).count()
    }

    /// Most consecutive made points.
    pub fn longest_prime(&self) -> usize {
        let (mut best, mut run) = (0, 0);
        for point in 1..=24 {
            run = if self.made(point) { run + 1 } else { 0 };
            best = best.max(run);
        }
        best
    }

    /// Some checker can still hit or be hit: the mover's rearmost checker is behind the
    /// opponent's rearmost one (a checker on the bar counts as furthest back).
    pub fn contact(&self) -> bool {
        let mine = if self.bar[0] > 0 {
            25
        } else {
            (1..=24).rev().find(|&p| self.pts[p - 1] > 0).unwrap_or(0)
        };
        let theirs = if self.bar[1] > 0 {
            0
        } else {
            (1..=24).find(|&p| self.pts[p - 1] < 0).unwrap_or(25)
        };
        mine > theirs
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn empty() -> Board {
        Board {
            pts: [0; 24],
            bar: [0, 0],
            off: [0, 0],
        }
    }

    fn notations(board: &Board, d1: u8, d2: u8) -> Vec<String> {
        let mut out: Vec<_> = board
            .legal_plays(d1, d2)
            .iter()
            .map(Play::notation)
            .collect();
        out.sort();
        out
    }

    #[test]
    fn opening_position_is_symmetric_with_167_pips() {
        let board = Board::start();
        assert_eq!(board.mover_pips(), 167);
        assert_eq!(board.opponent_pips(), 167);
        assert_eq!(board.flip(), board);
    }

    #[test]
    fn hitting_rolls_match_the_standard_shot_counts() {
        // One checker on 13 aiming at a blot: 6 away is 11 rolls with a 6 plus 5-1, 4-2,
        // 3-3, 2-2 (17); 1 away is any 1 (11); 7 away needs 6-1, 5-2, 4-3 (6).
        for (distance, expected) in [(6, 17), (1, 11), (7, 6)] {
            let mut board = empty();
            board.pts[12] = 1;
            board.pts[12 - distance] = -1;
            assert_eq!(board.hitting_rolls(), expected, "{distance} away");
        }
        // An opponent point 3 away (on 10) blocks 3-3, the only path through it: 16.
        let mut board = empty();
        board.pts[12] = 1;
        board.pts[6] = -1;
        board.pts[9] = -2;
        assert_eq!(board.hitting_rolls(), 16);
    }

    #[test]
    fn opening_six_five_has_exactly_seven_distinct_plays() {
        // 19 and 1 are held by the opponent, so 24/19 and 6/1 are blocked.
        let n = notations(&Board::start(), 6, 5);
        assert_eq!(n.len(), 7, "{n:?}");
        for expected in [
            "24/18 18/13",
            "24/18 13/8",
            "24/18 8/3",
            "13/7 13/8",
            "13/7 8/3",
            "8/2 8/3",
        ] {
            assert!(
                n.contains(&expected.to_owned()),
                "missing {expected} in {n:?}"
            );
        }
        // 13/8 8/2 and 13/7 7/2 reach the same position and are listed once.
        assert_eq!(
            n.iter()
                .filter(|p| p.contains("/2") && !p.contains("8/3"))
                .count(),
            1
        );
    }

    #[test]
    fn checker_on_bar_must_enter_first_and_blocked_points_are_closed() {
        let mut board = empty();
        board.bar[0] = 1;
        board.pts[5] = 14;
        for point in [19, 20, 21, 22, 23] {
            board.pts[point - 1] = -2;
        }
        board.pts[18] = -1; // point 19: a blot that can be hit from the bar with a 6
        // 6 enters on 19 (hitting); 5 would need point 20, which is blocked.
        let plays = board.legal_plays(6, 5);
        assert!(plays.iter().all(|p| p.steps[0].from == BAR));
        assert!(
            notations(&board, 6, 5)
                .iter()
                .any(|n| n.starts_with("bar/19*"))
        );
        // Every entry point closed: no legal play.
        board.pts[18] = -2;
        board.pts[23] = -2;
        assert!(board.legal_plays(6, 5).is_empty());
    }

    #[test]
    fn higher_die_is_forced_when_only_one_die_can_be_played() {
        let mut board = empty();
        board.pts[23] = 1; // single checker on 24
        board.pts[17] = -2; // 18 blocked: 6 from 24
        board.pts[18] = -2; // 19 blocked: 5 from 24
        board.pts[12] = -2; // 13 blocked
        board.pts[13] = -2; // 14 blocked: 24-6-4 and 24-4-6
        // 24/20 (4) then 20/14 (6) blocked; 6 blocked from 24. Only the 4 plays.
        assert_eq!(notations(&board, 6, 4), vec!["24/20"]);

        let mut board = empty();
        board.pts[9] = 1; // single checker on 10
        board.pts[3] = -2; // 4 blocked: 10-6 and 10-2-4...
        board.pts[1] = -2; // 2 blocked: 10-6-2 and 10-2-6
        // 10/8 or 10/4: the 6 is blocked, the 2 lands on 8; after 10/8, 8-6=2 blocked.
        assert_eq!(notations(&board, 6, 2), vec!["10/8"]);

        let mut board = empty();
        board.pts[9] = 1; // either die alone is playable, but not both: must play the 6
        board.pts[1] = -2; // 2 blocked (10-6-2 and 10-2-6 both land on 2)
        assert_eq!(notations(&board, 6, 2), vec!["10/4"]);
    }

    #[test]
    fn bear_off_rules() {
        let mut board = empty();
        board.pts[4] = 1; // 5
        board.pts[1] = 1; // 2
        board.off[0] = 13;
        // The 6 bears off the 5; from the 2 it would overshoot past an occupied 5.
        assert_eq!(notations(&board, 6, 1), vec!["5/4 4/off", "5/off 2/1"]);
        // Bearing off needs every checker home: the 1 can leave only after 7/5.
        let mut board = empty();
        board.pts[6] = 1;
        board.pts[0] = 1;
        assert_eq!(notations(&board, 1, 2), vec!["7/5 1/off", "7/6 6/4"]);
    }

    #[test]
    fn doubles_play_up_to_four_steps() {
        let board = Board::start();
        for play in board.legal_plays(2, 2) {
            assert_eq!(play.steps.len(), 4);
        }
    }

    #[test]
    fn win_kinds() {
        let mut board = empty();
        board.off = [15, 1];
        board.pts[20] = -14;
        assert_eq!(board.mover_won(), Some(WinKind::Single));
        board.off = [15, 0];
        board.pts[20] = -15;
        assert_eq!(board.mover_won(), Some(WinKind::Gammon));
        board.pts[20] = -14;
        board.pts[2] = -1;
        assert_eq!(board.mover_won(), Some(WinKind::Backgammon));
        board.pts[2] = 0;
        board.bar[1] = 1;
        assert_eq!(board.mover_won(), Some(WinKind::Backgammon));
        board.off[0] = 14;
        assert_eq!(board.mover_won(), None);
    }

    #[test]
    fn plays_preserve_checker_counts() {
        let board = Board::start();
        for d1 in 1..=6 {
            for d2 in 1..=6 {
                for play in board.legal_plays(d1, d2) {
                    let r = play.result;
                    let mine: i32 = r
                        .pts
                        .iter()
                        .filter(|&&n| n > 0)
                        .map(|&n| n as i32)
                        .sum::<i32>()
                        + r.bar[0] as i32
                        + r.off[0] as i32;
                    let theirs: i32 = r
                        .pts
                        .iter()
                        .filter(|&&n| n < 0)
                        .map(|&n| -n as i32)
                        .sum::<i32>()
                        + r.bar[1] as i32
                        + r.off[1] as i32;
                    assert_eq!((mine, theirs), (15, 15));
                }
            }
        }
    }
}
