#!/usr/bin/env python3
"""Highlights 2-6, DRAFT selection (Umit #3113, #3126/#3128/#3138). Read-only; no model call, no deploy, no test set.

    python3 mailbox/highlights-drafts/select_highlights.py          # from the repo root

Sources (all opened read-only):
  - League decisions, every legal play scored at GNUbg 2-ply: ~/.local/state/bg-site/plays/s*.db (table plays), joined
    to v3.db (file:v3.db?mode=ro) turns/games/matches for board, dice and stage. Valid staged matches only, every
    league plus late-entry matches; decided_by model or fallback.
  - Published League 3 decisions: ~/.local/state/bg-site/analysis/backgammon/decisions/league-3/*/N.json.gz.
  - Clear-risk Part 2 quiz: workspace/clearrisk-scratch (sample200.json, meta.json, items_*.jsonl, all3.json,
    roll_res.jsonl) and smoke/clearrisk-q.db (quiz_answers); answers parsed exactly as p2rep.py (the frozen scoring).
  - Learning pilot games only: smoke/learning-pilot.db (matches/games/turns/exchanges) and
    smoke/learning-pilot-plays.db (2-ply). The answers table (evaluations) and the test-set files are never opened.
Writes mailbox/highlights-drafts/facts.json and hl{2..6}-*.png (site board, light theme, headless Chrome).
"""
import glob
import gzip
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "tools/site"), str(ROOT / "tools/v3")]
import rules  # noqa: E402
from board import board_svg  # noqa: E402

STATE = Path.home() / ".local/state/bg-site"
SITE = STATE / "analysis/backgammon"
CR = ROOT / "workspace/clearrisk-scratch"
LABELS = json.load(open(ROOT / "tools/site/content/labels.json"))["renamed"]
NAME = lambda n: LABELS.get(n, {}).get("name", n)  # noqa: E731
PROGRAMS = {"GNUbg weak", "Safest", "Random"}
MARGIN = 0.001  # thresholds.json risk_margin
MOST = 0.70  # "most models" in slot 3 (Umit's 70%+)


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def play_call(shots, losses, i, margin=MARGIN):
    """Copy of tools/site/analysis.play_call (that module needs numpy)."""
    least = min(shots)
    if least == max(shots):
        return "none", None, None, 0
    stake = min(losses[j] for j, s in enumerate(shots) if s == least)
    cls = "safety" if stake < margin else "risk"
    if shots[i] > least:
        call = "needless" if cls == "safety" else ("right_risk" if stake - losses[i] >= margin else "wrong_risk")
    else:
        call = "missed" if cls == "risk" else "right_safety"
    return cls, call, stake, shots[i] - least


def pips(b):
    pts, bar, off = b
    return (sum(p * n for p, n in enumerate(pts, 1) if n > 0) + 25 * bar[0],
            sum((25 - p) * -n for p, n in enumerate(pts, 1) if n < 0) + 25 * bar[1])


def bdict(b):
    return {"points": list(b[0]), "bar": list(b[1]), "off": list(b[2])}


# ---------------------------------------------------------------- league decisions (all leagues + late entry)
P = {}
for f in glob.glob(str(STATE / "plays/s*.db")):
    for r in ro(f).execute("SELECT turn_id, league_id, model, chosen, data FROM plays"):
        P[r[0]] = r
V = ro(ROOT / "v3.db")
LEAGUE = {}
for r in V.execute("""SELECT t.id, t.game_id, t.turn_no, t.side, t.die1, t.die2, t.position, m.stage, m.id
        FROM turns t JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
        WHERE m.valid = 1 AND m.stage IS NOT NULL AND t.decided_by IN ('model', 'fallback')"""):
    if r[0] not in P:
        continue
    tid, lid, model, chosen, data = P[r[0]]
    data = json.loads(data)
    eq = [x[1] for x in data]
    best = max(eq)
    losses = [best - e for e in eq]
    shots = [x[2] for x in data]
    cls, call, stake, _ = play_call(shots, losses, chosen)
    b = rules.from_json(json.loads(r[6]), r[3])
    LEAGUE[tid] = dict(tid=tid, league=lid, stage=r[7], match=r[8], game=r[1], turn_no=r[2], side=r[3],
                       dice=[r[4], r[5]], model=model, name=NAME(model), chosen=chosen, data=data, cls=cls, call=call,
                       stake=stake, board=b, key=(str(rules.key(b)), tuple(sorted((r[4], r[5])))))
SAME = defaultdict(list)  # identical board (mover's side) and dice
for d in LEAGUE.values():
    if d["model"] not in PROGRAMS:
        SAME[d["key"]].append(d)


def best_safe_eq(d):
    least = min(x[2] for x in d["data"])
    return max(x[1] for x in d["data"] if x[2] == least)


# ---------------------------------------------------------------- Clear-risk Part 2 quiz
meta = {int(k): v for k, v in json.load(open(CR / "meta.json")).items()}
SAMPLE = {s["sid"]: s for s in json.load(open(CR / "sample200.json"))}
ALL3 = json.load(open(CR / "all3.json"))
ROLL = defaultdict(dict)
for l in open(CR / "roll_res.jsonl"):
    j = json.loads(l)
    ROLL[j["sid"]][j["which"]] = j
ITEMS = {}
for p in ("items_decision.jsonl", "items_chat.jsonl"):
    for l in open(CR / p):
        j = json.loads(l)
        ITEMS[j["id"]] = j
QM = ["Celeris-1 Decision", "Jev 1.14.0", "Liquid d1-ultra", "Claude Sonnet 5.5 (high)", "GPT-6.1 Sol (high)",
      "Kimi K3.1 Pro (off)", "GLM-5.3 (on)", "Claude Opus 5.5 (on)"]
QCHAT = QM[3:]
ANS = {(s, i): (ch, json.loads(p) if p else None, t, e) for s, i, ch, p, t, e in ro(ROOT / "smoke/clearrisk-q.db").execute(
    "SELECT setup, item_id, choice, probabilities, text, error FROM quiz_answers")}


def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def pick(model, item_id):
    """As p2rep.py: chosen option value, or None (missing, failed, invalid, exact tie at the top)."""
    a = ANS.get((model, item_id))
    if a is None or a[3] is not None:
        return None
    if model in QCHAT:
        j = parse_json(a[2])
        ch = j.get("choice") if isinstance(j, dict) else None
        vals = [v for v, _ in ITEMS[item_id]["options"]]
        labels = list("ABCD"[: len(vals)])
        return vals[labels.index(ch)] if ch in labels else None
    probs = a[1] or {}
    if a[0] is None or not probs:
        return None
    top = max(probs.values())
    return None if sum(p == top for p in probs.values()) > 1 else max(probs, key=probs.get)


def q1(sid, version):
    return {m: pick(m, f"{sid}:Q1:{version}") for m in QM}


def quiz_facts(sid):
    s, m = SAMPLE[sid], meta[sid]
    allp = ALL3[str(sid)]  # play -> [3-ply, 2-ply, hitting rolls]
    best = max(allp, key=lambda k: allp[k][1])
    b = rules.from_json(json.loads(s["position"]), s["side"])
    return dict(sid=sid, group=m["grp"], source_league=s["league"], source_decision=s["turn"],
                source_setup=NAME(s["model"]), source_play=s["chosen"], side=s["side"], dice=[s["d1"], s["d2"]],
                board=bdict(b), pips=pips(b), shown_order=m["q1"]["order"],
                safe=dict(play=s["safe"][0], eq2=s["safe"][1], hits=s["safe"][2], eq3=s["s3"],
                          rollout=ROLL[sid].get("safe", {}).get("eq"), rollout_se=ROLL[sid].get("safe", {}).get("se")),
                risk=dict(play=s["unsafe"][0], eq2=s["unsafe"][1], hits=s["unsafe"][2], eq3=s["u3"],
                          rollout=ROLL[sid].get("unsafe", {}).get("eq"), rollout_se=ROLL[sid].get("unsafe", {}).get("se")),
                gap2=s["gap"], gap3=s["g3"], legal=len(allp),
                engine_best=dict(play=best, eq2=allp[best][1], hits=allp[best][2]),
                answers={v: q1(sid, v) for v in ("board", "numbers")})


F = {}

# ---------------------------------------------------------------- slot 2: Sol (high), risk board-only, safe with numbers
c2 = []
for sid, m in meta.items():
    if m["grp"] != "Risk wins":
        continue
    b, n = pick("GPT-6.1 Sol (high)", f"{sid}:Q1:board"), pick("GPT-6.1 Sol (high)", f"{sid}:Q1:numbers")
    if b == m["q1"]["unsafe"] and n == m["q1"]["safe"]:
        c2.append((SAMPLE[sid]["gap"], sid))
c2.sort(reverse=True)
F["slot2"] = dict(rule="Risk wins item; Sol (high) Q1 board only = risky play, Q1 with numbers = safe play; max 2-ply gap",
                  n_meeting=len(c2), ranking=[(round(g, 4), s) for g, s in c2[:5]],
                  pick=quiz_facts(c2[0][1]), runner_up=quiz_facts(c2[1][1]))

# ---------------------------------------------------------------- slot 3: great risk vs >=70% safe, same position
c3q = []
for version in ("numbers", "board"):
    for sid, m in meta.items():
        if m["grp"] != "Risk wins":
            continue
        a = {k: v for k, v in q1(sid, version).items() if v is not None}
        safe = [k for k, v in a.items() if v == m["q1"]["safe"]]
        risk = [k for k, v in a.items() if v == m["q1"]["unsafe"]]
        if a and len(safe) / len(a) >= MOST and len(risk) == 1:
            c3q.append((SAMPLE[sid]["gap"], sid, version, len(a), len(safe), risk[0]))
c3q.sort(reverse=True)
c3l = []
for k, v in SAME.items():
    if v[0]["cls"] != "risk" or len(v) < 2:
        continue
    safe = [d for d in v if d["call"] == "missed"]
    rr = [d for d in v if d["call"] == "right_risk"]
    if len(safe) / len(v) >= MOST and len({d["model"] for d in rr}) == 1:
        gain = max(d["data"][d["chosen"]][1] - best_safe_eq(d) for d in rr)
        c3l.append((gain, rr[0]["tid"], len(v), len({d["model"] for d in v}), len(safe), rr[0]["name"],
                    rr[0]["data"][rr[0]["chosen"]][0], min(d["turn_no"] for d in v)))
c3l.sort(reverse=True)
F["slot3"] = dict(rule=f"Risk wins / Risk pays; >= {MOST:.0%} of same-position answers safe; exactly one model took the "
                       "risk; max gain (risk play - best safe play, 2-ply)",
                  quiz=[(round(g, 4), s, v, n, ns, r) for g, s, v, n, ns, r in c3q[:6]],
                  league=[(round(x[0], 4),) + x[1:] for x in c3l[:6]],
                  pick=quiz_facts(c3q[0][1]) | {"version": c3q[0][2]},
                  runner_up=quiz_facts(c3q[1][1]) | {"version": c3q[1][2]})

# ---------------------------------------------------------------- slot 4: largest League 3 loss; needless if within margin
L3 = []
for f in glob.glob(str(SITE / "decisions/league-3/*/*.json.gz")):
    if not os.path.basename(f).split(".")[0].isdigit():
        continue
    p = json.load(gzip.open(f))
    for d in p["decisions"]:
        if not d["program"] and not d["invalid"]:
            d.pop("prompt", None)
            L3.append(d | {"slug": p["slug"], "page": int(p["page"])})
L3.sort(key=lambda d: -d["plays"][d["chosen"]]["loss"])
need = [d for d in L3 if d["risk"] and d["risk"]["call"] == "needless"]
lossof = lambda d: d["plays"][d["chosen"]]["loss"]  # noqa: E731
F["slot4"] = dict(rule="League 3 non-program decisions; largest loss (the largest needless risk is listed as an "
                       "editorial alternative only)",
                  overall=[(d["id"], d["setup"], round(lossof(d), 4), d["risk"] and d["risk"]["call"]) for d in L3[:5]],
                  needless=[(d["id"], d["setup"], round(lossof(d), 4)) for d in need[:3]],
                  pick=L3[0], needless_alternative=need[0], second_overall=L3[1])

# ---------------------------------------------------------------- slot 5: decision model right risk, frontier safe
# "Most" = more than half of the named cohort's answers (2 of 3 counts). Two cohorts, both reported:
COHORTS = {"quiz5": ["Claude Sonnet 5.5 (high)", "GPT-6.1 Sol (high)", "Kimi K3.1 Pro (off)", "GLM-5.3 (on)",
                     "Claude Opus 5.5 (on)"],  # the five quiz chat models (v3 setup names)
           "league3": ["GPT-6.1 Sol (high)", "Kimi K3.1 Pro (off)", "Claude Opus 5.5 (on)"]}  # the League 3 ones
DM_L = {"Liquid d1-ultra", "Base Labs Mammoth-1", "Drex Max v1", "REAX 1.3"}
DM_Q = sorted(DM_L & set(QM))  # only Liquid d1-ultra took the quiz
S5 = {}
for cname, cohort in COHORTS.items():
    quiz = []
    for version in ("numbers", "board"):
        for sid, m in meta.items():
            if m["grp"] != "Risk wins":
                continue
            takers = [d for d in DM_Q if pick(d, f"{sid}:Q1:{version}") == m["q1"]["unsafe"]]
            a = {k: v for k, v in q1(sid, version).items() if k in cohort and v is not None}
            safe = [k for k, v in a.items() if v == m["q1"]["safe"]]
            if takers and a and 2 * len(safe) > len(a):
                quiz.append(dict(gap=round(SAMPLE[sid]["gap"], 4), item=sid, version=version, n=len(a),
                                 safe=len(safe), risk_takers_in_cohort=[NAME(k) for k in a if k not in safe],
                                 decision_models=takers))
    league = []
    for k, v in SAME.items():
        if v[0]["cls"] != "risk":
            continue
        dm = [d for d in v if d["model"] in DM_L and d["call"] == "right_risk"]
        co = [d for d in v if d["model"] in cohort]
        safe = [d for d in co if d["call"] == "missed"]
        if dm and co and 2 * len(safe) > len(co):
            league.append(dict(gap=round(max(d["data"][d["chosen"]][1] - best_safe_eq(d) for d in dm), 4),
                               dice=v[0]["dice"], turn_no=min(d["turn_no"] for d in v), n=len(co), safe=len(safe),
                               decision_models=sorted({(d["name"], d["tid"], d["data"][d["chosen"]][0]) for d in dm}),
                               cohort=[(d["name"], d["tid"], d["data"][d["chosen"]][0], d["call"]) for d in co]))
    S5[cname] = dict(quiz=sorted(quiz, key=lambda x: -x["gap"]), league=sorted(league, key=lambda x: -x["gap"]))
# Our criterion among qualifiers (not Umit's): the largest gap, over both cohorts and both populations.
best = max((x for c in S5.values() for x in c["quiz"]), key=lambda x: x["gap"])
F["slot5"] = dict(rule="Risk wins / Risk pays; a named decision model took the right risk; more than half of the "
                       "cohort's answers safe; cohorts: quiz5 and league3; our pick criterion: largest gap",
                  cohorts={k: [NAME(m) for m in v] for k, v in COHORTS.items()}, qualifiers=S5,
                  pick=quiz_facts(best["item"]) | {"version": best["version"]})

# ---------------------------------------------------------------- slot 6: learning pilot divergence points
LP, LPP = ro(ROOT / "smoke/learning-pilot.db"), ro(ROOT / "smoke/learning-pilot-plays.db")
FIN = {}
for mid, label, status in LP.execute("SELECT id, model1, status FROM matches"):
    _, arm, s = label.split(" | ")
    if status == "finished":
        FIN[(arm, int(s[1:]))] = mid
SC = {r[0]: r for r in LPP.execute("SELECT turn_id, chosen, data FROM plays")}


def pilot_turns(mid):
    out = defaultdict(list)
    for r in LP.execute("""SELECT t.id, g.round_no, g.leg, t.turn_no, t.side, t.player, t.die1, t.die2, t.position, t.move
            FROM turns t JOIN games g ON g.id = t.game_id WHERE g.match_id = ? ORDER BY g.round_no, g.leg, t.turn_no""",
                        (mid,)):
        out[2 * (r[1] - 1) + r[2]].append(r)
    return out


def prompt_lines(tid):
    req = LP.execute("SELECT request FROM exchanges WHERE turn_id = ? ORDER BY attempt LIMIT 1", (tid,)).fetchone()[0]
    txt = json.dumps(json.loads(req))
    return re.search(r"Score: you[^\\]*", txt).group(0), re.search(r"Match: round[^\\]*", txt).group(0)


c6 = []
for s in range(1, 11):
    C, L = pilot_turns(FIN[("control", s)]), pilot_turns(FIN[("lessons", s)])
    for g in range(1, 11):
        for tc, tl in zip(C[g], L[g]):
            assert tc[3:9] == tl[3:9], (s, g)  # same turn, side, mover, dice, position up to the first different play
            if tc[9] == tl[9]:
                continue
            if tc[5] == 1 and tc[0] in SC and tl[0] in SC:
                data = json.loads(SC[tc[0]][2])
                eq = [x[1] for x in data]
                best = max(eq)
                losses = [best - e for e in eq]
                shots = [x[2] for x in data]
                cc, cl = play_call(shots, losses, SC[tc[0]][1]), play_call(shots, losses, SC[tl[0]][1])
                if cl[1] == "right_risk" and cc[1] == "missed":
                    b = rules.from_json(json.loads(tc[8]), tc[4])
                    ib = eq.index(best)
                    c6.append(dict(series=s, game=g, turn_no=tc[3], side=tc[4], dice=[tc[6], tc[7]],
                                   control_turn=tc[0], lessons_turn=tl[0], board=bdict(b), pips=pips(b),
                                   control=dict(play=data[SC[tc[0]][1]][0], eq2=eq[SC[tc[0]][1]], hits=shots[SC[tc[0]][1]]),
                                   lessons=dict(play=data[SC[tl[0]][1]][0], eq2=eq[SC[tl[0]][1]], hits=shots[SC[tl[0]][1]]),
                                   engine_best=dict(play=data[ib][0], eq2=best, hits=shots[ib]), legal=len(data),
                                   gain=eq[SC[tl[0]][1]] - eq[SC[tc[0]][1]],
                                   prompt_control=prompt_lines(tc[0]), prompt_lessons=prompt_lines(tl[0])))
            break
c6.sort(key=lambda x: (not (x["series"] == 1 and x["game"] >= 4), -x["gain"]))
F["slot6"] = dict(rule="first different play of control vs lessons in the same series/game (identical history); "
                       "lessons right_risk, control missed; prefer series 1 game >= 4 (after the game-3 lesson), then gain",
                  n_meeting=len(c6), all=[(x["series"], x["game"], x["turn_no"], round(x["gain"], 4)) for x in c6],
                  pick=c6[0], runner_up=max(c6[1:], key=lambda x: x["gain"]))

json.dump(F, open(OUT / "facts.json", "w"), indent=1, default=str)

# ---------------------------------------------------------------- boards (site board_svg, light theme, headless Chrome)
CSS = "".join(f'<link rel="stylesheet" href="{(SITE / c).as_uri()}">' for c in
              ("suite-bar.css", "site.css", "bg.css", "decisions.css"))


def render(name, board, dice, pp, solid, dashed, legend):
    svg = board_svg(board, dice, pp, play=solid, alt=dashed, cls="bd hl-board")
    html = (f'<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8">{CSS}<style>'
            "body{margin:0;padding:16px 20px;background:var(--bg,#fff)} figure.hero-board{margin:0;width:900px;"
            "max-width:none} figure.hero-board svg{width:900px;max-width:none;height:auto;display:block}"
            ".lg{font:15px/1.4 system-ui,sans-serif;color:var(--text,#222);margin:8px 2px 0}"
            ".draft{font:700 13px system-ui,sans-serif;color:#b45309;letter-spacing:.08em}</style></head><body>"
            f'<div class="draft">DRAFT</div><figure class="hero-board">{svg}</figure>'
            f'<p class="lg">{legend}</p></body></html>')
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as t:
        t.write(html)
    png = OUT / f"{name}.png"
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", "--window-size=940,830", f"--screenshot={png}",
                    Path(t.name).as_uri()], check=True, capture_output=True)
    os.unlink(t.name)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


x = F["slot2"]["pick"]
render(f"hl2-sol-clearrisk-{x['sid']}", x["board"], x["dice"], x["pips"], x["risk"]["play"], x["safe"]["play"],
       f"Solid: {x['risk']['play']}, GPT-6.1 Sol (high)'s answer with the board only. "
       f"Dashed: {x['safe']['play']}, its answer once the numbers were shown.")
x = F["slot3"]["pick"]
risker = [m for m, v in x["answers"][x["version"]].items() if v == x["risk"]["play"]]
render(f"hl3-great-risk-clearrisk-{x['sid']}", x["board"], x["dice"], x["pips"], x["risk"]["play"], x["safe"]["play"],
       f"Solid: {x['risk']['play']}, the risk ({NAME(risker[0])}). Dashed: {x['safe']['play']}, the safe play "
       "chosen by the other seven.")
d = F["slot4"]["pick"]
render(f"hl4-frontier-blunder-{d['id']}", d["board"], d["dice"], d["pips"], d["plays"][d["best"]]["notation"],
       d["plays"][d["chosen"]]["notation"],
       f"Solid: the engine's best play, {d['plays'][d['best']]['notation']}. Dashed: {esc(d['setup'])}'s play, "
       f"{d['plays'][d['chosen']]['notation']}.")
x = F["slot5"]["pick"]
render(f"hl5-decision-model-clearrisk-{x['sid']}", x["board"], x["dice"], x["pips"], x["risk"]["play"],
       x["safe"]["play"], f"Solid: {x['risk']['play']}, Liquid d1-ultra's answer with the board only (the risk). "
       f"Dashed: {x['safe']['play']}, the safe play.")
x = F["slot6"]["pick"]
render(f"hl6-learning-pilot-s{x['series']:02d}g{x['game']:02d}", x["board"], x["dice"], x["pips"],
       x["lessons"]["play"], x["control"]["play"],
       f"Solid: {x['lessons']['play']}, the own-lessons arm (also the engine's best). "
       f"Dashed: {x['control']['play']}, the no-memory arm.")
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("pick", "runner_up", "second_overall",
                                                                  "majority_alternative")} for k, v in F.items()},
                 indent=1, default=str))
