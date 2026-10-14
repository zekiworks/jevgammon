"""Seeded option order for the v3 benchmark; the same algorithm as `src/players/order.rs`.

`option_order(seed, position_key, n)` returns a permutation of range(n): `order[k]` is the index,
in move-generation order, of the play shown k-th (letter k). The SHA-256 of
f"{seed}:{position_key}" seeds a SplitMix64 stream (first 8 bytes, big-endian) that drives a
Fisher-Yates shuffle from the identity, i = n-1 down to 1, j = next() % (i + 1).

position_key is f"{gnubg_position_id}:{hi}{lo}:{side}", e.g. "4HPwATDgc/ABMA:65:white": the GNUbg
position ID with the side to move on roll, the dice high then low, and "white" or "black".

Standard library only, so it runs both in plain Python and inside gnubg.
"""

import hashlib

MASK = (1 << 64) - 1


def position_key(position_id, d1, d2, side):
    hi, lo = max(d1, d2), min(d1, d2)
    return f"{position_id}:{hi}{lo}:{side}"


def splitmix64(state):
    """Yields the SplitMix64 stream from `state`."""
    while True:
        state = (state + 0x9E3779B97F4A7C15) & MASK
        z = state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        yield z ^ (z >> 31)


def option_order(seed, position_key, n):
    digest = hashlib.sha256(f"{seed}:{position_key}".encode()).digest()
    stream = splitmix64(int.from_bytes(digest[:8], "big"))
    order = list(range(n))
    for i in range(n - 1, 0, -1):
        j = next(stream) % (i + 1)
        order[i], order[j] = order[j], order[i]
    return order
