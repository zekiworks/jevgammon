"""Regression tests for the leaderboard's selection rule (Zeki #2790 items 1 and 2) on the branch's story.py, from the
retained computed state (no compute, no statistics, no model): each test edits a deep copy of S in memory.
    python3 test_rules.py TOOLS_SITE_DIR S_PICKLE
(a) the representative at the top setting is score-free: two setups of one model at the same setting, the first by
    league order then name is chosen even when the other has the higher stored judgement;
(b) raising the dated checkpoint's judgement above the original's does not move the DeepSeek V4.1 Flash row;
(c) a dated suffix not on the approved list (content/model_identity.json) stays its own model;
(d) the approved list is exactly DeepSeek V4.1 Flash 1017 -> DeepSeek V4.1 Flash, and that row holds all four setups;
(e) an unknown reasoning setting fails the build.
Exits 1 if any test fails."""
import copy
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1])))
S0 = pickle.load(open(sys.argv[2], "rb"))
import story  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")


def row(S, model):
    return next(t for t in story.leaderboard_rows(S)[0] if t[2] == model)


def setup(S, ds, name):
    lg = next(lg for lg in S["leagues"] if lg["dataset"] == ds)
    return lg["setups"][name]


# (a) Gemma 4 31B: (on) 64.5 and (off) 62.6 in League 2; with (off) marked "on" too, both are at the top setting and
# "Gemma 4 31B (off)" comes first by name although its judgement is lower.
S = copy.deepcopy(S0)
S["setups_meta"][("league-2", "Gemma 4 31B (off)")]["setting"] = "on"
x = row(S, "Gemma 4 31B")[0]
j_off = setup(S, "league-2", "Gemma 4 31B (off)")["risk"]["main"]["judgement"]
j_on = setup(S, "league-2", "Gemma 4 31B (on)")["risk"]["main"]["judgement"]
check("(a) same setting twice: first by league order then name, not the higher score",
      x["name"] == "Gemma 4 31B (off)" and j_off < j_on, f"chosen {x['name']} ({j_off:.1f}) over the (on) setup ({j_on:.1f})")

# (b) The checkpoint's judgement raised above the original's: the row keeps the original's setup.
S = copy.deepcopy(S0)
setup(S, "league-2", "DeepSeek V4.1 Flash 1017 (low)")["risk"]["main"]["judgement"] = 99.0
x = row(S, "DeepSeek V4.1 Flash")[0]
check("(b) the checkpoint's score does not move the DeepSeek row", x["name"] == "DeepSeek V4.1 Flash (low)", x["name"])

# (c) A dated suffix not on the list: Grok 4.7 (low)'s model renamed "Grok 4.7 1101" stays its own row.
S = copy.deepcopy(S0)
key = next(k for k in S["setups_meta"] if k[1] == "Grok 4.7 (low)" and k[0].startswith("league-"))
for k in [k for k in S["setups_meta"] if k[1] == "Grok 4.7 (low)"]:
    S["setups_meta"][k]["model"] = "Grok 4.7 1101"
names = [t[2] for t in story.leaderboard_rows(S)[0]]
check("(c) an unlisted dated suffix is its own model", "Grok 4.7 1101" in names and "Grok 4.7" in names,
      f"{len(names)} rows; Grok rows: {[n for n in names if n.startswith('Grok')]}")

# (d) The approved list and the DeepSeek family.
g = row(S0, "DeepSeek V4.1 Flash")
check("(d) approved list exactly one pair; the DeepSeek row holds its 4 setups",
      story.SAME_MODEL == {"DeepSeek V4.1 Flash 1017": "DeepSeek V4.1 Flash"} and len(g[3]) == 4
      and g[0]["name"] == "DeepSeek V4.1 Flash (low)", f"{[y['name'] for y in g[3]]}")

# (e) An unknown setting fails.
S = copy.deepcopy(S0)
S["setups_meta"][("league-2", "Gemma 4 31B (off)")]["setting"] = "turbo"
try:
    story.leaderboard_rows(S)
    check("(e) an unknown setting fails the build", False, "no error")
except ValueError as e:
    check("(e) an unknown setting fails the build", True, str(e))

print(f"test_rules: {fails} failure(s)")
sys.exit(1 if fails else 0)
