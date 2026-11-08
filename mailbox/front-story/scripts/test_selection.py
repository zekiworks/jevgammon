"""Regression tests for Zeki #2737 on the front-story tools/site (no build, no compute, no model or statistics run).
S is rebuilt from a branch render's published data files (data/v3/league-N.json, data/setups.json) and the
worktree's content files (nack_paired_results.json): the same inputs home.nack_views and story.best_settings read.
    python3 test_selection.py TOOLS_SITE_DIR RENDER_DIR
(a) a Nackgammon setup whose metadata has no model_type fails the build; (b) an unknown model_type fails it;
(c) for every model, the Nackgammon per-model view's setup equals the leaderboard's selected setup (identities);
(d) a synthetic case, the same setup in two leagues and a tie, decided by the one shared rule."""
import copy
import json
import re
import sys
from pathlib import Path

tools, render = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(tools))
import home as H  # noqa: E402
import story  # noqa: E402

fails = 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} {name}{': ' + detail if detail else ''}")


def raises(fn):
    try:
        fn()
    except ValueError as e:
        return str(e)
    return None


data = render / "data"
leagues = []
for i in (1, 2, 3):
    lg = json.loads((data / "v3" / f"league-{i}.json").read_text())
    lg.pop("version", None)
    leagues.append(lg)
meta = {(m["dataset"], m["name"]): m for m in json.loads((data / "setups.json").read_text())["setups"]}
S = dict(leagues=leagues, setups_meta=meta, nack=json.loads((tools / "content/nack_paired_results.json").read_text()))

# (a) metadata object without model_type -> build error.
Sa = copy.deepcopy(S)
victim = next(n for n in S["nack"]["setups"] if any(x == n for (_, x) in meta) and n not in ("Random", "GNUbg weak"))
for k, m in Sa["setups_meta"].items():
    if k[1] == victim:
        m.pop("model_type", None)
err = raises(lambda: H.nack_views(Sa))
check("(a) no model_type fails", bool(err), f"setup {victim!r} without model_type -> {err!r}")

# (b) unknown model type string -> build error (it would have filed under Chat through kind()).
Sb = copy.deepcopy(S)
for k, m in Sb["setups_meta"].items():
    if k[1] == victim:
        m["model_type"] = "chatbot, free text"
err = raises(lambda: H.nack_views(Sb))
check("(b) unknown model_type fails", bool(err), f"model_type 'chatbot, free text' -> {err!r}; "
      f"kind() would have said {H.kind({'model_type': 'chatbot, free text'})!r}")

# (c) every model: the per-model view's setup = the leaderboard's selected setup.
kinds, chosen = H.nack_views(S)
headline = {H.model_of(S, lg["dataset"], n): (lg["dataset"], n) for lg, n, r in story.best_settings(S)}
nack_names = set(S["nack"]["setups"])
rows = []
for n in chosen:
    lg = next((d for (d, x) in meta if x == n and d.startswith("league-")), None)
    model = H.model_of(S, lg, n) if lg else n
    hl = headline.get(model)
    if hl is None:
        rows.append((model, n, "-", "no leaderboard row (played in no league)", n not in headline))
    elif hl[1] in nack_names:
        rows.append((model, n, f"{hl[1]} ({hl[0]})", "equal" if hl[1] == n else "DIFFERENT", hl[1] == n))
    else:
        # The leaderboard's setting was not asked in this test: the same rule over the asked settings.
        sub = H.best_per_model(S, lambda lg_, x: x in nack_names).get(model)
        rows.append((model, n, f"{hl[1]} ({hl[0]}), not asked", f"same rule over the asked settings: {sub[1]}",
                     sub is not None and sub[1] == n))
for model, n, hl, how, ok in sorted(rows):
    print(f"   {model:32} nack: {n:34} leaderboard: {hl:42} {how}")
check("(c) per-model view = leaderboard selection, every model", all(r[4] for r in rows), f"{len(rows)} models")
# The rendered page (the branch render before this fix) against the fixed rule, for the record.
page = (render / "index.html").read_text()
m = re.search(r'data-nack-chosen="([^"]*)"', page)
old = set(json.loads(m.group(1).replace("&quot;", '"'))) if m else set()
print(f"   rendered page's per-model view (old rule) vs fixed rule: only old {sorted(old - set(chosen))}, "
      f"only new {sorted(set(chosen) - old)}")

# (d) synthetic: model M; setup C in League 1 (75) and League 2 (50); A in League 1 (70) and B in League 2 (70), a tie.
def lg_(ds, i, js):
    return dict(dataset=ds, id=i, references={}, setups={n: dict(risk=dict(main=dict(judgement=j)), quality={})
                                                         for n, j in js.items()})


Sd = dict(leagues=[lg_("league-1", 1, {"A": 70.0, "C": 75.0}), lg_("league-2", 2, {"B": 70.0, "C": 50.0})],
          setups_meta={(d, n): dict(dataset=d, name=n, slug=n.lower(), model="M", model_type="chat model, one letter")
                       for d, ns in (("league-1", "AC"), ("league-2", "BC")) for n in ns},
          nack=dict(setups={"A": {}, "B": {}, "C": {}}))
_, ch = H.nack_views(Sd)
hl = [(lg["dataset"], n) for lg, n, r in story.best_settings(Sd)]
old_judged = {n: r["judgement"] for lg, n, r, ref in H.all_rows(Sd) if not ref}
old = max("ABC", key=lambda x: (old_judged.get(x) or 0, x))
check("(d) synthetic: C (League 1, 75) beats its own League 2 row (50) and the A/B tie at 70",
      ch == ["C"] and hl == [("league-1", "C")], f"nack {ch}, leaderboard {hl}; the old name-keyed rule picked {old!r}")
Sd["leagues"][0]["setups"]["C"]["risk"]["main"]["judgement"] = 60.0
_, ch = H.nack_views(Sd)
hl = [(lg["dataset"], n) for lg, n, r in story.best_settings(Sd)]
old_judged = {n: r["judgement"] for lg, n, r, ref in H.all_rows(Sd) if not ref}
old = max("ABC", key=lambda x: (old_judged.get(x) or 0, x))
check("(d) synthetic tie A (League 1) = B (League 2) = 70: the first in league order, A",
      ch == ["A"] and hl == [("league-1", "A")], f"nack {ch}, leaderboard {hl}; the old rule picked {old!r}")
print(f"{fails} failure(s)")
sys.exit(1 if fails else 0)
