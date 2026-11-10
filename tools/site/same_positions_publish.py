#!/usr/bin/env python3
"""Same positions (Zeki #4287, Ümit #4282 item 5): the stored E1 answers of "Did they improve?" (200-position
empty-context test) for the ranked leaderboard models, read only. No model call, no write outside /tmp/job5.

    python3 /tmp/job5/same_positions.py   ->  /tmp/job5/same_positions.json, /tmp/job5/same_positions_cost.md

Sources (all opened read-only):
  ranked rows      STATE/analysis/backgammon/index.html (the built leaderboard, tools/site/story.py leaderboard_rows)
  E1 answers       ROOT/smoke/improve/*.db, ROOT/smoke/improve/decision/*.db  (answers.setup '... | improve | E1')
  E1 settings      ROOT/workspace/improve/runs/<key>/E1/test-E1.json, runs/decision/<key>/E1/test-E1.json
  league prompts   STATE/prompts.db (seen: context + separator + requests[].text, per league turn)
  league settings  STATE/snap.db players.settings; league timing/cost: snap.db turns (decided_by='model')
  test set         ROOT/workspace/learning-pilot/test_set.json (losses per legal play, GNUbg 2-ply)
  best-play rule   tools/site/content/thresholds.json best_play_loss_below (0.001)
"""
import glob, json, math, os, re, sqlite3, statistics
from itertools import combinations
from pathlib import Path

ROOT = Path("/home/cbasaran/code/jevgammon")
STATE = Path.home() / ".local/state/bg-site"
OUT = Path("/tmp/job5")
POSITIONS = 200
BEST = json.loads((ROOT / "tools/site/content/thresholds.json").read_text())["best_play_loss_below"]
UNAVAILABLE = {  # Ümit #4282 / assignment: flagged unavailable now
    "openai-decisions": "no OpenAI API credit",
    "claude-subscription": "Claude subscription limit",
    "chatgpt-subscription": "ChatGPT subscription quota until 13 Nov",
}
SERVERS = {  # league player -> tools/v3/servers script (README.md tables)
    "Gemma 4 31B": "gemma4-31b.sh", "Qwen3.8-27B": "qwen38-27b.sh", "LFM2.5-24B-A2B": "lfm25-24b.sh",
    "Cygnet (Gemma 4 12B)": "cygnet.sh", "Clef": "clef.sh", "Open-Jev 27B v1.1": "open-jev.sh",
    "Decider v1.1 27B": "decider.sh", "Decider v1.2 27B": "decider-v1.2.sh 27b",
    "Decider Flash v1.2": "decider-v1.2.sh flash", "Winnow-12B": "winnow.sh",
    "Fastino GLiDE v1.2 (local)": "glide-v12.sh",
}
SETTING_KEYS = ("spec", "provider", "quantization", "base_url", "reasoning", "request", "top_logprobs",
                "letter_readout", "max_tokens", "temperature", "device")


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def ranked_rows():
    h = (STATE / "analysis/backgammon/index.html").read_text()
    out = []
    for r in re.findall(r'<tr[^>]*>(?:(?!</tr>).)*?hl-judgement(?:(?!</tr>).)*</tr>', h, re.S):
        rank = re.search(r'<td class="num">(\d+)</td>', r)
        if not rank:
            continue  # a row's other settings and the programs: not ranked
        ds, sl = re.search(r'data-dataset="([^"]*)" data-setup="([^"]*)"', r).groups()
        out.append(dict(rank=int(rank.group(1)), dataset=ds, slug=sl,
                        display=re.search(r'<p><strong>([^<]*)</strong>', r).group(1)))
    return out


def walk_strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from walk_strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk_strings(v)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    snap = ro(STATE / "snap.db")
    players = {n: (i, json.loads(s), prov) for i, n, s, prov in snap.execute("select id,name,settings,provider from players")}
    by_slug = {slug(n): n for n in players}
    ranked = ranked_rows()
    for r in ranked:
        r["player"] = by_slug.get(r["slug"])
    ts = {p["id"]: p for p in json.loads((ROOT / "workspace/learning-pilot/test_set.json").read_text())["positions"]}
    assert len(ts) == POSITIONS
    P = ro(STATE / "prompts.db")
    ctxs = {}

    def league_prompt(tid):
        r = P.execute("select context,separator,requests,format from seen where turn_id=?", (tid,)).fetchone()
        if not r:
            return None, None
        if r[0] not in ctxs:
            ctxs[r[0]] = P.execute("select text from contexts where hash=?", (r[0],)).fetchone()[0]
        return r[3], [(q.get("system"), ctxs[r[0]] + r[1] + q["text"]) for q in json.loads(r[2])]

    # E1 answer sets, one per (model, arm)
    e1 = []
    for db in sorted(glob.glob(str(ROOT / "smoke/improve/*.db")) + glob.glob(str(ROOT / "smoke/improve/decision/*.db"))):
        if db.endswith("-plays.db"):
            continue
        key = Path(db).stem
        con = ro(db)
        con.row_factory = sqlite3.Row
        for (setup,) in con.execute("select distinct setup from answers where setup like '% | improve | E1'"):
            rows = {}
            for a in con.execute("select * from answers where setup=? order by id", (setup,)):
                rows[a["position_id"]] = dict(a)  # latest per position, as pilot.py eval_answers
            base = setup.split(" | ")[0]
            model, _, arm = base.partition(" · ")
            run = ROOT / "workspace/improve/runs" / ("decision/" if "/decision/" in db else "") / key / "E1/test-E1.json"
            cfg = json.loads(run.read_text())["players"][0] if run.exists() else None
            # prompt identity: every league request text (and system) of the same turn found verbatim among the
            # strings of E1's stored requests (all exchanges of the answer: a split list sends one request per group,
            # then a final request among the group winners, which depends on the model's own group answers).
            # prompts.db holds one prompt per turn, in the format of the league player that played it: letters (chat)
            # or decision; only the turns of E1's own format are comparable.
            kind = "decision" if "/decision/" in db else "letters"
            same = group_final_differs = invalid_stopped = differ = other_format = no_league = 0
            for pid, a in rows.items():
                fmt, lp = league_prompt(int(pid.split("-")[1]))
                reqs = [q for (q,) in con.execute("select request from answer_exchanges where answer_id=?", (a["id"],))]
                if lp is None or not reqs:
                    no_league += 1
                    continue
                if fmt != kind:
                    other_format += 1
                    continue
                strs = set()
                for q in reqs:
                    try:
                        strs |= set(walk_strings(json.loads(q)))
                    except ValueError:
                        strs.add(q)
                blob = "\n".join(strs)
                found = [t in blob and (s is None or s in blob) for s, t in lp]
                k = found.index(False) if False in found else len(found)
                if all(found):
                    same += 1
                elif len(lp) > 1 and all(found[:-1]):
                    group_final_differs += 1
                elif a["invalid"] and k > 0 and not any(found[k:]):
                    invalid_stopped += 1  # an invalid group answer ended the split before its later requests
                else:
                    differ += 1
            e1.append(dict(model=model, arm=arm or None, setup=setup, db=db, cfg=cfg, cfg_path=str(run), rows=rows,
                           prompt=dict(format=kind, same=same, split_final_differs=group_final_differs,
                                       invalid_stopped=invalid_stopped, differ=differ, other_format=other_format,
                                       no_league_prompt=no_league)))

    def score(rows):
        v = {}
        for pid, p in ts.items():
            a = rows.get(pid)
            ok = (a is not None and not a["error"] and not a["invalid"] and a["chosen_index"] is not None
                  and p["losses"][a["chosen_index"]] < BEST)
            v[pid] = ok
        return v

    # decision lane: compare arms; collapse when identical
    groups = {}
    for x in e1:
        groups.setdefault(x["model"], []).append(x)
    models, arm_notes, settings_diff = [], [], {}
    by_player = {r["player"]: r for r in ranked}
    for model, xs in groups.items():
        if len(xs) > 1:
            ref = {p: a["chosen_index"] for p, a in xs[0]["rows"].items()}
            for y in xs[1:]:
                d = sum(ref.get(p) != a["chosen_index"] for p, a in y["rows"].items())
                arm_notes.append(f'{model}: arm "{y["arm"]}" vs "{xs[0]["arm"]}": {d} of {POSITIONS} E1 answers differ')
        x = xs[0]
        rows = x["rows"]
        complete = len(rows) == POSITIONS and all(not a["error"] for a in rows.values())
        lr = by_player.get(model)
        league_cfg = players[model][1] if model in players else None
        if x["cfg"] and league_cfg:
            settings_diff[model] = {k: [league_cfg.get(k), x["cfg"].get(k)] for k in SETTING_KEYS
                                    if league_cfg.get(k) != x["cfg"].get(k)}
        v = score(rows)
        models.append(dict(name=lr["display"] if lr else model, setup=x["setup"], arms=[y["arm"] for y in xs if y["arm"]],
                           source=f'{x["db"]} (answers where setup={x["setup"]!r})', ranked=lr is not None,
                           rank=lr["rank"] if lr else None, n=len(rows), complete=complete,
                           correct=sum(v.values()), invalid=sum(1 for a in rows.values() if a["invalid"] or a["chosen_index"] is None),
                           failed=sum(1 for a in rows.values() if a["error"]),
                           prompt=x["prompt"], settings_vs_league=settings_diff.get(model), _v=v))
    tested = [m for m in models if m["complete"] and m["ranked"]]
    tested.sort(key=lambda m: -m["correct"])

    def mcnemar(b, c):
        n = b + c
        if n == 0:
            return 1.0
        k = min(b, c)
        return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)

    pairs = []
    for a, b in combinations(tested, 2):
        b01 = sum(a["_v"][p] and not b["_v"][p] for p in ts)  # a right, b wrong
        b10 = sum(b["_v"][p] and not a["_v"][p] for p in ts)
        pairs.append(dict(a=a["name"], b=b["name"], b01=b01, b10=b10, p=mcnemar(b01, b10)))
    # Holm over all pairs
    order = sorted(range(len(pairs)), key=lambda i: pairs[i]["p"])
    m, run_max = len(pairs), 0.0
    for rank, i in enumerate(order):
        run_max = max(run_max, min(1.0, (m - rank) * pairs[i]["p"]))
        pairs[i]["p_holm"] = run_max
        pairs[i]["sig"] = run_max < 0.05
    sig = {frozenset((q["a"], q["b"])): q["sig"] for q in pairs}
    # tiers: the best untiered model leads a tier; every untiered model not significantly different from it joins
    left, tier = [m["name"] for m in tested], 0
    tiers = {}
    while left:
        tier += 1
        lead = left[0]
        members = [n for n in left if n == lead or not sig[frozenset((lead, n))]]
        for n in members:
            tiers[n] = tier
        left = [n for n in left if n not in members]
    for m_ in tested:
        m_["tier"] = tiers[m_["name"]]

    # missing ranked models: league cost and time per decision (snap.db turns)
    have = {m["name"] for m in tested}
    missing = []
    for r in ranked:
        if r["display"] in have:
            continue
        pid, cfg, prov = players[r["player"]]
        own = ("from turns t join games g on g.id=t.game_id join matches m on m.id=g.match_id where m.valid=1 and "
               "t.decided_by='model' and (case t.player when 1 then m.player1 else m.player2 end)=?")
        q = snap.execute("select count(*), avg(t.cost_usd), avg(t.input_tokens), avg(t.output_tokens), "
                         "sum(t.cost_usd is null) " + own, (pid,)).fetchone()
        lat = [x for (x,) in snap.execute("select coalesce(t.request_ms, t.latency_ms) " + own, (pid,))]
        med = statistics.median(lat) / 1000 if lat else None
        p = (prov or "").lower()
        route = ("subscription" if "subscription" in p else
                 "local GPU" if p.startswith("local") else "hosted API")
        unavailable = next((v for k, v in UNAVAILABLE.items() if k == p), None)
        part = next((m for m in models if m["name"] == r["display"] or m["setup"].startswith(r["player"] + " |")), None)
        missing.append(dict(name=r["display"], rank=r["rank"], player=r["player"], provider=prov, route=route,
                            server=(SERVERS.get(r["player"]) or SERVERS.get(re.sub(r" \((on|off|low|high)\)$", "", r["player"])))
                            if route == "local GPU" else None,
                            decisions=q[0], cost_per_decision=q[1], in_tok=q[2], out_tok=q[3], cost_null=q[4],
                            median_s=med, unavailable=unavailable,
                            partial=f'{part["n"]}/{POSITIONS} stored E1 answers' if part else None))
    prompt_eq = all(m["prompt"]["differ"] == 0 for m in tested)
    setting_eq = all(not m["settings_vs_league"] for m in tested)
    doc = dict(
        prompt_equals_league=prompt_eq and setting_eq,
        prompt_note=("Per answer, the league prompt of the same League 2 turn (STATE/prompts.db seen: context + "
                     "separator + each request's text, and its system) looked up verbatim among the strings of E1's "
                     "stored requests (answer_exchanges.request, all exchanges). prompts.db holds the prompt in the "
                     "format of the league player that played the turn (letters for chat, decision for decision "
                     "models), so only same-format turns compare; split lists (over 25 options) send a final request "
                     "among the model's own group winners, and an invalid group answer stops a split early. Counts "
                     "(same / split-final differs / invalid-stopped / differ / other-format turn / no stored league "
                     "prompt): " + "; ".join(
                         f'{m["name"]}: {p["same"]}/{p["split_final_differs"]}/{p["invalid_stopped"]}/{p["differ"]}/'
                         f'{p["other_format"]}/{p["no_league_prompt"]}' for m in tested for p in [m["prompt"]])
                     + ". Settings (E1 test-E1.json player vs snap.db league player, keys " + ", ".join(SETTING_KEYS)
                     + "): " + "; ".join(f'{m["name"]}: {"same" if not m["settings_vs_league"] else m["settings_vs_league"]}'
                                         for m in tested)
                     + ". Arms: " + ("; ".join(arm_notes) or "single arm each")),
        correctness_rule=(f"correct = valid answer whose play lost < {BEST} equity against GNUbg's best (test_set.json "
                          "losses, GNUbg 2-ply; tools/site thresholds.json best_play_loss_below, the site's 'Engine's best "
                          "play'); invalid and failed answers count as wrong. The improve pipeline itself scores error "
                          "rate / risks found / right safety (workspace/learning-pilot/pilot.py eval_metrics), no "
                          "correct/incorrect rule."),
        tier_rule=("Holm-adjusted (all pairs, alpha 0.05) two-sided exact McNemar. Tier 1: the most-correct model and "
                   "every model not significantly different from it; then the most-correct model left leads tier 2 "
                   "with every remaining model not significantly different from it; and so on."),
        models=[{k: v for k, v in m.items() if not k.startswith("_")} | dict(tier=m.get("tier")) for m in
                sorted(models, key=lambda m: (not (m["complete"] and m["ranked"]), -m["correct"]))],
        pairs=pairs, missing_ranked=[m["name"] for m in missing], missing_detail=missing, arm_notes=arm_notes)
    # cost / time of a 200-position run for each missing ranked model
    prices = json.loads((ROOT / "tools/site/content/model_prices.json").read_text())["models"]
    for x in missing:
        if x["route"] == "hosted API":
            if x["cost_per_decision"] is not None:
                x["usd_per_decision"], x["usd_source"] = x["cost_per_decision"], "league turns.cost_usd (list price x tokens)"
            else:
                pr = prices.get(re.sub(r" \([^()]*\)$", "", x["player"]), {}).get("input_per_mtok")
                x["usd_per_decision"] = pr * x["in_tok"] / 1e6 if pr is not None and x["in_tok"] else None
                x["usd_source"] = f"model_prices.json ${pr}/Mtok input x mean league input tokens (output free)"
        else:
            x["usd_per_decision"] = 0.0
            x["usd_source"] = (f"$0 marginal; list-equivalent ${x['cost_per_decision']:.4f}" if x["route"] == "subscription"
                               else "$0 API (own GPU)")
        x["usd_200"] = x["usd_per_decision"] * POSITIONS if x["usd_per_decision"] is not None else None
        x["hours_200"] = x["median_s"] * POSITIONS / 3600 if x["median_s"] is not None else None
        x["gpu_hours"] = x["hours_200"] if x["route"] == "local GPU" else 0.0
    f = lambda v, d: "n/a" if v is None else f"{v:.{d}f}"  # noqa: E731
    lines = ["| # | Site name | Route | GPU (server) | $ / decision (source) | $ for 200 | Median s / decision "
             "(league n) | Hours for 200 | Available now |", "|---|---|---|---|---|---|---|---|---|"]
    for x in missing:
        gpu = (f'yes ({x["server"] or "not under tools/v3/servers; " + (x["provider"] or "")})'
               if x["route"] == "local GPU" else "no")
        avail = f'no: {x["unavailable"]}' if x["unavailable"] else "yes"
        if x["partial"]:
            avail += f'; {x["partial"]}'
        lines.append(f'| {x["rank"]} | {x["name"]} | {x["route"]} ({x["provider"]}) | {gpu} | '
                     f'{f(x["usd_per_decision"], 5)} ({x["usd_source"]}) | {f(x["usd_200"], 3)} | '
                     f'{f(x["median_s"], 2)} ({x["decisions"]:,}) | {f(x["hours_200"], 2)} | {avail} |')
    hosted = sum(x["usd_200"] or 0 for x in missing if x["route"] == "hosted API")
    hosted_ok = sum(x["usd_200"] or 0 for x in missing if x["route"] == "hosted API" and not x["unavailable"])
    lines.append(f'| | **Total ({len(missing)} models)** | | GPU hours {sum(x["gpu_hours"] or 0 for x in missing):.2f} | | '
                 f'**${hosted:.2f}** hosted (${hosted_ok:.2f} available now) | | '
                 f'**{sum(x["hours_200"] or 0 for x in missing):.2f} h** sequential | '
                 f'{sum(1 for x in missing if x["unavailable"])} unavailable now |')
    (OUT / "same_positions_cost.md").write_text("\n".join(lines) + "\n")
    (OUT / "same_positions.json").write_text(json.dumps(doc, indent=1))
    print(doc["prompt_equals_league"], doc["prompt_note"], sep="\n")
    for m in tested:
        print(m["name"], m["n"], m["correct"], m["invalid"], m["tier"])
    print(f'{sum(q["sig"] for q in pairs)} of {len(pairs)} pairs significant after Holm')
    print("\n".join(lines))


if __name__ == "__main__":
    main()
