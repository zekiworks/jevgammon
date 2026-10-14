//! Baseline players that need no model: `random` plays a uniformly random legal play,
//! `safest` the play that leaves the opponent the fewest hitting rolls.

use crate::board::Play;
use crate::dice::{Dice, derive_seed};

use super::{Decision, DecisionRequest, Engine};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Baseline {
    Random,
    Safest,
}

impl Engine for Baseline {
    fn decide(&self, req: &DecisionRequest<'_>) -> anyhow::Result<Decision> {
        let index = match self {
            Baseline::Random => random_play(req.seed, req.plays.len()),
            Baseline::Safest => safest_play(req.plays, req.order),
        };
        Ok(Decision::new(index))
    }
}

/// Uniform in `0..count`, reproducible from the decision's seed (match, round, leg, turn).
pub fn random_play(seed: u64, count: usize) -> usize {
    Dice::new(derive_seed(seed, "random")).below(count)
}

/// What `safest` minimises, in order: the opponent's hitting rolls (the "hits with N of
/// 36 rolls" of the prompt), then blots, then the pip lead given up.
fn danger(play: &Play) -> (u32, usize, i64) {
    let after = &play.result;
    let lead = after.opponent_pips() as i64 - after.mover_pips() as i64;
    (after.flip().hitting_rolls(), after.blots(), -lead)
}

/// The play leaving the fewest hitting rolls; ties go to fewer blots, then the larger pip
/// lead, then the earlier play in the shown option `order` (indices into `plays`).
pub fn safest_play(plays: &[Play], order: &[usize]) -> usize {
    let mut best: Option<(usize, (u32, usize, i64))> = None;
    for &index in order {
        let key = danger(&plays[index]);
        if best.is_none_or(|(_, best_key)| key < best_key) {
            best = Some((index, key));
        }
    }
    best.map_or(0, |(index, _)| index)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::board::Board;

    /// Mover's and opponent's checkers by point in the mover's numbering; the rest are off.
    fn board(mine: &[(usize, i8)], theirs: &[(usize, i8)]) -> Board {
        let mut pts = [0i8; 24];
        for &(point, n) in mine {
            pts[point - 1] = n;
        }
        for &(point, n) in theirs {
            pts[point - 1] = -n;
        }
        let on_board = |side: &[(usize, i8)]| side.iter().map(|&(_, n)| n as u8).sum::<u8>();
        Board {
            pts,
            bar: [0, 0],
            off: [15 - on_board(mine), 15 - on_board(theirs)],
        }
    }

    fn in_order(plays: &[Play]) -> Vec<usize> {
        (0..plays.len()).collect()
    }

    #[test]
    fn safest_leaves_no_shot() {
        // Blots on 9 and 8 facing two opponent back checkers on our 1 point: with 2-1 only
        // 9/7 8/7 leaves nothing to hit.
        let b = board(&[(9, 1), (8, 1), (6, 2)], &[(1, 2)]);
        let plays = b.legal_plays(2, 1);
        let chosen = &plays[safest_play(&plays, &in_order(&plays))];
        assert_eq!(chosen.result.pts[6], 2, "{}", chosen.notation());
        assert_eq!(chosen.result.flip().hitting_rolls(), 0);
        assert!(plays.iter().filter(|p| p.result.flip().hitting_rolls() == 0).count() == 1);
        assert!(plays.iter().any(|p| p.result.flip().hitting_rolls() > 0));
    }

    #[test]
    fn safest_breaks_ties_on_blots_then_option_order() {
        // No contact, so nothing can be hit and every play moves 3 pips: 8/6 7/6 is the
        // only play without a blot.
        let b = board(&[(8, 1), (7, 1)], &[(20, 2)]);
        assert!(!b.contact());
        let plays = b.legal_plays(2, 1);
        let chosen = &plays[safest_play(&plays, &in_order(&plays))];
        assert_eq!(chosen.result.pts[5], 2, "{}", chosen.notation());

        // Two checkers on 8 with 2-1: 8/6 8/7 and 8/5 both leave two blots and lose 3
        // pips, so the option order decides.
        let b = board(&[(8, 2)], &[(20, 2)]);
        let plays = b.legal_plays(2, 1);
        assert_eq!(plays.len(), 2);
        assert_eq!(danger(&plays[0]), danger(&plays[1]));
        assert_eq!(safest_play(&plays, &[0, 1]), 0);
        assert_eq!(safest_play(&plays, &[1, 0]), 1);
    }

    #[test]
    fn random_is_reproducible_and_uniform() {
        let mut seen = [0u32; 7];
        for seed in 0..7000u64 {
            let index = random_play(seed, 7);
            assert_eq!(index, random_play(seed, 7));
            seen[index] += 1;
        }
        assert!(seen.iter().all(|&n| (800..1200).contains(&n)), "{seen:?}");
    }
}
