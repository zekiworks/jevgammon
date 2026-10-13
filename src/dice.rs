//! Deterministic dice. A round's seed fixes every roll, so both legs of a round
//! see the identical sequence regardless of the moves played.
//!
//! SplitMix64 is implemented here (not taken from a crate) so a stored seed keeps
//! reproducing the same rolls across dependency upgrades.

pub struct Dice {
    state: u64,
}

fn mix(mut z: u64) -> u64 {
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

/// Seed of round `round` within a match seeded with `match_seed`.
pub fn round_seed(match_seed: u64, round: u32) -> u64 {
    mix(match_seed ^ mix(0x6A09_E667_F3BC_C909 ^ round as u64))
}

/// Seed of the sub-stream named `label` (a league fixture) within `seed`.
pub fn derive_seed(seed: u64, label: &str) -> u64 {
    // FNV-1a: stable across Rust releases, unlike `std::hash`.
    let hash = label.bytes().fold(0xCBF2_9CE4_8422_2325u64, |h, b| {
        (h ^ b as u64).wrapping_mul(0x0100_0000_01B3)
    });
    mix(seed ^ mix(hash))
}

impl Dice {
    pub fn new(seed: u64) -> Self {
        Dice { state: seed }
    }

    fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        mix(self.state)
    }

    fn die(&mut self) -> u8 {
        loop {
            // Top three bits, rejecting 6 and 7, keep the die unbiased.
            let value = (self.next_u64() >> 61) as u8;
            if value < 6 {
                return value + 1;
            }
        }
    }

    /// Opening roll: one die per side, rerolled on ties. Returns `(white, black)`.
    pub fn opening(&mut self) -> (u8, u8) {
        loop {
            let (white, black) = (self.die(), self.die());
            if white != black {
                return (white, black);
            }
        }
    }

    pub fn roll(&mut self) -> (u8, u8) {
        (self.die(), self.die())
    }

    /// Uniform in `0..n`, for draws such as the league fixture.
    pub fn below(&mut self, n: usize) -> usize {
        let n = n as u64;
        let zone = u64::MAX - u64::MAX % n;
        loop {
            let value = self.next_u64();
            if value < zone {
                return (value % n) as usize;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn same_seed_same_rolls_and_all_faces_appear() {
        let mut a = Dice::new(round_seed(42, 1));
        let mut b = Dice::new(round_seed(42, 1));
        let mut seen = [0u32; 6];
        assert_eq!(a.opening(), b.opening());
        for _ in 0..6000 {
            let roll = a.roll();
            assert_eq!(roll, b.roll());
            seen[roll.0 as usize - 1] += 1;
        }
        assert!(seen.iter().all(|&n| (800..1200).contains(&n)), "{seen:?}");
        assert_ne!(round_seed(42, 1), round_seed(42, 2));
    }
}
