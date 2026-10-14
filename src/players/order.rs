//! Seeded option order: the legal plays of a position are shown in a fixed random order
//! drawn from a published seed, never in move-generation or engine order. The same
//! algorithm lives in `tools/v3/order.py`; `tools/v3/order_vectors.json` pins both.
//!
//! position_key = GNUbg position ID + ":" + dice high then low + ":" + side to move, e.g.
//! `4HPwATDgc/ABMA:65:white`. The permutation is a Fisher-Yates shuffle (i = n-1 down to
//! 1, j = next() % (i + 1)) of `0..n`, driven by SplitMix64 seeded with the first 8 bytes
//! (big-endian) of SHA-256(`"{seed}:{position_key}"`). `order[k]` is the index into the
//! legal play list of the play shown k-th (option letter k).

use base64::Engine as _;
use sha2::{Digest, Sha256};

use crate::board::{Board, Side};

struct SplitMix64(u64);

impl SplitMix64 {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
}

/// The presentation order of `n` options at `position_key` under `seed`.
pub fn option_order(seed: u64, position_key: &str, n: usize) -> Vec<usize> {
    let digest = Sha256::digest(format!("{seed}:{position_key}").as_bytes());
    let mut state = [0u8; 8];
    state.copy_from_slice(&digest[..8]);
    let mut rng = SplitMix64(u64::from_be_bytes(state));
    let mut order: Vec<usize> = (0..n).collect();
    for i in (1..n).rev() {
        let j = (rng.next() % (i as u64 + 1)) as usize;
        order.swap(i, j);
    }
    order
}

/// `board` from the mover's side (as everywhere in the runner), the dice as rolled, and the
/// mover's colour.
pub fn position_key(board: &Board, dice: (u8, u8), side: Side) -> String {
    let (high, low) = (dice.0.max(dice.1), dice.0.min(dice.1));
    format!("{}:{high}{low}:{}", gnubg_position_id(board), side.name())
}

/// GNUbg's 14-character position ID with the mover on roll: the opponent's checkers are
/// encoded first, then the mover's, each as points 1-24 in that player's own numbering and
/// then the bar, one 1-bit per checker followed by a 0-bit; the 80 bits are packed
/// little-endian and base64-encoded without padding.
pub fn gnubg_position_id(board: &Board) -> String {
    let opponent = board.flip();
    let mut key = [0u8; 10];
    let mut bit = 0usize;
    for view in [&opponent, board] {
        let counts = (0..24)
            .map(|i| view.pts[i].max(0) as u8)
            .chain(std::iter::once(view.bar[0]));
        for count in counts {
            for _ in 0..count {
                key[bit / 8] |= 1 << (bit % 8);
                bit += 1;
            }
            bit += 1;
        }
    }
    base64::engine::general_purpose::STANDARD_NO_PAD.encode(key)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn gnubg_ids_match_gnubg() {
        // Both values printed by gnubg 1.08's `gnubg.positionid`.
        assert_eq!(gnubg_position_id(&Board::start()), "4HPwATDgc/ABMA");
        // Mover played 24/21 from the start; the opponent has one checker on the bar and
        // four on its 6-point.
        let mut opponent = Board::start();
        opponent.pts[5] = 4;
        opponent.bar[0] = 1;
        let mut board = opponent.flip();
        board.pts[23] = 1;
        board.pts[20] = 1;
        assert_eq!(gnubg_position_id(&board), "4Dn4AFjgc/ABIg");
        assert_eq!(
            position_key(&Board::start(), (1, 2), Side::Black),
            "4HPwATDgc/ABMA:21:black"
        );
    }

    #[test]
    fn order_is_a_seeded_permutation() {
        let a = option_order(7, "4HPwATDgc/ABMA:21:white", 15);
        let mut sorted = a.clone();
        sorted.sort_unstable();
        assert_eq!(sorted, (0..15).collect::<Vec<_>>());
        assert_eq!(a, option_order(7, "4HPwATDgc/ABMA:21:white", 15));
        assert_ne!(a, option_order(8, "4HPwATDgc/ABMA:21:white", 15));
        assert_eq!(option_order(1, "x", 0), Vec::<usize>::new());
        assert_eq!(option_order(1, "x", 1), vec![0]);
    }

    /// The vectors Python's `tools/v3/order.py` must reproduce.
    #[test]
    fn order_matches_published_vectors() {
        let text = include_str!("../../tools/v3/order_vectors.json");
        let cases: Vec<serde_json::Value> = serde_json::from_str(text).unwrap();
        assert_eq!(cases.len(), 10);
        for case in cases {
            let seed = case["seed"].as_u64().unwrap();
            let key = case["position_key"].as_str().unwrap();
            let n = case["n"].as_u64().unwrap() as usize;
            let order: Vec<usize> = case["order"]
                .as_array()
                .unwrap()
                .iter()
                .map(|v| v.as_u64().unwrap() as usize)
                .collect();
            assert_eq!(option_order(seed, key, n), order, "{case}");
        }
    }
}
