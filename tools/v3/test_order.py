"""order.py must give the same permutations as src/players/order.rs (tools/v3/order_vectors.json).

    python3 tools/v3/test_order.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from order import option_order, position_key  # noqa: E402


def test_vectors():
    with open(os.path.join(HERE, "order_vectors.json")) as f:
        vectors = json.load(f)
    assert len(vectors) >= 10
    for v in vectors:
        assert option_order(v["seed"], v["position_key"], v["n"]) == v["order"], v


def test_position_key():
    assert position_key("4HPwATDgc/ABMA", 5, 6, "white") == "4HPwATDgc/ABMA:65:white"
    assert position_key("4HPwATDgc/ABMA", 3, 3, "black") == "4HPwATDgc/ABMA:33:black"


if __name__ == "__main__":
    test_vectors()
    test_position_key()
    print("order: 2 tests passed")
