#!/usr/bin/env python3
"""Reproducibility repeats of four League 1 setups (Ümit via Zeki, bus #4663, #4666, #4667, #4671): each repeat plays
the original's own League 1 field again, one match at a time, each pair pinned (league config pinned_pairs, runner
branch pinned-pairs, Zeki #4710) to its original match's seed (dice) and seating, with the
same option-order seed, prompt, rules and setup settings, under a separate held name ('<original> [repeat 1]') whose
matches carry stage 'late-entry' (late_entry_stage trigger) and are held off every page, table and league computation
(tools/site/content/held_setups.json). Published rows are never changed. Run from anywhere; v3.db is the main
checkout's (JEVGAMMON_DB overrides).

  repeats.py manifest                 writes mailbox/repeats/manifest-2026-11-11.json from v3.db (read-only)
  repeats.py configs                  writes tools/v3/repeats/leagues/ID.json from the manifest
  repeats.py plan ID                  opponents to play, in order: NAME|KIND|MiB|START|STOP|BLOCKED (read-only)
  repeats.py check ID                 fail-closed preflight (read-only): config pins, trigger, held name, runner build
  repeats.py env ID                   shell assignments for run.sh (NAME KIND BIN ENTRANT_MIB START STOP HEALTH ...)
  repeats.py trigger ID               WRITES v3.db: adds the repeat name to the late_entry_stage trigger
  repeats.py league-id ID             the repeat's league id, or nothing (read-only)
  repeats.py pending ID [OPPONENT...] pairs without a finished valid repeat match (read-only)
  repeats.py billed ID                dollars billed in the repeat's matches (read-only)
  repeats.py results                  writes tools/site/content/repeat_results.json (status per repeat, read-only)
"""
import argparse
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MAIN = Path("/home/cbasaran/code/jevgammon")
DB = Path(os.environ.get("JEVGAMMON_DB", MAIN / "v3.db"))
MANIFEST = REPO / "mailbox" / "repeats" / "manifest-2026-11-11.json"
RESULTS = REPO / "tools" / "site" / "content" / "repeat_results.json"
TRIGGER = re.compile(r"p\.name IN \((.*?)\)\)", re.S)
MASK = 2**64 - 1

# The 19 setups of the original League 1 table (workspace/reax/reax.py FIELD, league_web.league_origins).
API = ["Celeris-1 Decision", "Fastino GLiDE", "GPT-6 Luna", "Jev 1.13.0", "Jev 1.14.0", "Liquid d1-ultra",
       "Mercury Decide", "SubQ Snap Preview"]
PROGRAMS = ["GNUbg weak", "Random", "Safest"]
S = "/home/cbasaran/code/jevgammon/tools/v3/servers"
# name: (MiB it held alone on a card, start with the GPU in $g, stop): measured on bariton GPU 2 right after each start in
# REAX's locals run (workspace/reax/state/locals.log, 2026-11-07; Cygnet at CYGNET_UTIL=0.34). Small ones first.
LOCAL = {
    "Decider Flash v1.2": (9370, f"DECIDER_V12_GPU=$g {S}/decider-v1.2.sh flash start", f"{S}/decider-v1.2.sh flash stop"),
    "Winnow-12B": (13394, f"WINNOW_GPU=$g {S}/winnow.sh start", f"{S}/winnow.sh stop"),
    "Cygnet (Gemma 4 12B)": (32584, f"CYGNET_GPU=$g CYGNET_UTIL=0.34 {S}/cygnet.sh start", f"{S}/cygnet.sh stop"),
    "Decider v1.1 27B": (50384, f"DECIDER_GPU=$g {S}/decider.sh start", f"{S}/decider.sh stop"),
    "Decider v1.2 27B": (50384, f"DECIDER_V12_GPU=$g {S}/decider-v1.2.sh 27b start", f"{S}/decider-v1.2.sh 27b stop"),
    "Fastino GLiDE v1.2 (local)": (52810, f"GLIDE_GPU=$g {S}/glide-v12.sh start", f"{S}/glide-v12.sh stop"),
    "Open-Jev 27B v1.1": (53052, f"OPEN_JEV_GPU=$g {S}/open-jev.sh start", f"{S}/open-jev.sh stop"),
    "Clef": (53144, f"CLEF_GPU=$g {S}/clef.sh start", f"{S}/clef.sh stop"),
}
FIELD = sorted(API + PROGRAMS + list(LOCAL))
GPU_MIB = 97887  # one RTX PRO 6000 Blackwell (nvidia-smi memory.total on bariton)
MARGIN_MIB = 2000
# Paid opponents are billed at their recorded cost_usd; Fastino GLiDE records none: $0.04 per million input tokens (as
# every late entry's guard). Mercury Decide bills OpenRouter (the $40 floor).
BILLED = set(API)
FASTINO_RATE = 0.04
BLOCKED_TODAY = {
    "GPT-6 Luna": ("no credit: OpenAI Decisions answers 429 'no credits remaining' (Drex #829/#835/#846/#886, REAX, "
                   "Muse Ember and KnowLine runs: deferred); a top-up needs Can"),
    "Mercury Decide": ("no OpenRouter endpoint: 404 'No endpoints found for inception/mercury-decide' at warm-up "
                       "(Muse Ember #932, 2026-11-10 15:57 UTC; KnowLine #946, 2026-11-10 23:55 UTC)"),
}
WRITTEN_FOR = "Ümit via Zeki, bus #4663, #4666, #4667 (protocol), #4671 (d1-ultra)"
LOGIC_REAX = dict(container="logic-dm-reax13", url="http://127.0.0.1:19100",
                  image="sha256:9622cace6607ea35516dfae16c1d2c0cc191a7da735be0a7966e06a0dd839938")
# The runner every repeat uses: the pinned-pairs build (league config pinned_pairs; Zeki #4710).
RUNNER = dict(binary=str(MAIN / "target/pinned/release/jevgammon"), tree="/home/cbasaran/code/jevgammon-pinned-pairs",
              commit="4ca4f08")
RUNNER_DIFFERENCE = ("Runner: the pinned-pairs build " + RUNNER["commit"] + " (the pins are its only change for "
                     "these leagues), where the original ran %s; the same prompt version, option-order seed and "
                     "rules.")


def repeat_note(rid: str, extra: str = "") -> str:
    return (f" Reproducibility repeat 1 ({rid}; tools/v3/repeats, mailbox/repeats/manifest-2026-11-11.json): the "
            "original's League 1 field again, one match at a time, each pair with its original match's seed and seats; "
            "held: in no standings, table, Cup input or other setup's numbers." + extra)


# Per repeat: the original setup, where its original matches are, the runner that played them, its server.
REPEATS = {
    "mammoth-1-r1": dict(
        original="Base Labs Mammoth-1", original_league=14, original_stage="late-entry",
        runner=RUNNER, original_runner="104103a9dfd5ecaf141f699b363148ebbb490855",
        server=dict(kind="ours", mib=59000, start="MAMMOTH_GPU=$g /home/cbasaran/code/jevgammon/workspace/late3/baselabs.sh mammoth start",
                    stop="/home/cbasaran/code/jevgammon/workspace/late3/baselabs.sh mammoth stop",
                    health="http://127.0.0.1:18103/", health_any_status=True,
                    smoke="python3 /home/cbasaran/code/jevgammon/workspace/late3/late3.py smoke http://127.0.0.1:18103 baselabs/mammoth-1 --max-options 120",
                    provenance=("image baselabs-serve:81ce62f (sha256:874276ff…, built 2026-11-01 16:14 UTC), "
                                "decision-models runner/servers/baselabs_server.py last changed 12a2ea1 (2026-11-01), "
                                "snapshot baselabs/mammoth-1 @ 61cec44, bf16; unchanged since the original (checked "
                                "2026-11-11)"),
                    measured="57-59 GB on GPU 0 at its smoke test (mailbox/Late entries 3 - status 2026-11-02.md)"),
        settings_change=dict(),
        rules=dict(mirror_concurrent=True), differences=[RUNNER_DIFFERENCE % "104103a (clean)"]),
    "drex-max-v1-r1": dict(
        original="Drex Max v1", original_league=17, original_stage="late-entry",
        runner=RUNNER, original_runner="e58fc6c255304c085bdb5eb8dec34b83c473573a",
        server=dict(kind="ours", mib=53000, start="DREX_MAX_GPU=$g /home/cbasaran/code/jevgammon/workspace/drex/drexmax.sh start",
                    stop="/home/cbasaran/code/jevgammon/workspace/drex/drexmax.sh stop",
                    health="http://127.0.0.1:18104/health", health_any_status=False,
                    smoke="python3 /home/cbasaran/code/jevgammon/workspace/drex/drex.py smoke http://127.0.0.1:18104 drex-max-v1 --max-options 25",
                    provenance=("drex_max_server.py last changed 61f3824 (2026-10-31), Nace loader "
                                "~/code/drex-decision-models @ e206b27 (.venv-drex-max), snapshot nace-ai/drex-max-v1 "
                                "@ cac65e1, bf16; unchanged since the original (checked 2026-11-11)"),
                    measured="about 50-53 GB on GPU 0 (state of workspace/drex/state/servers.log, 2026-11-06)"),
        settings_change=dict(),
        rules=dict(mirror_concurrent=True), differences=[RUNNER_DIFFERENCE % "e58fc6c (clean)"]),
    "reax-1.3-r1": dict(
        original="REAX 1.3", original_league=19, original_stage="late-entry",
        runner=RUNNER, original_runner="acfd89cdcc710846d7173e475ce8546af7febac1",
        status="held",
        hold=("Held (Zeki #4710): the plan to use logic's container (outbound network open) is dropped; the repeat "
              "needs the original's offline setup (reax13-late on the internal network reax13-offline, no outbound "
              "route; workspace/reax/reax.sh) and Can's no-new-privileges exception renewed for it, or a new "
              "approval. Its server settings below are logic's and are not used until then."),
        server=dict(kind="logic", mib=75000, start=None, stop=None,
                    health=LOGIC_REAX["url"] + "/healthz", health_any_status=False,
                    smoke=f"python3 /home/cbasaran/code/jevgammon/workspace/reax/reax.py smoke {LOGIC_REAX['url']} reax13",
                    provenance=("logic's unit logic-dm-reax13 (~/code/benchmark/decision/servers.sh, started by Main "
                                "on bariton GPU 0 under his reservation, Logic & Math repeat first): the same image "
                                "reax13-runtime (sha256:9622cace…, built 2026-11-06 21:57 UTC, before the original), "
                                "engine ~/code/reax-engine @ ff8f595, Decision Index kit @ 25c6ec7, weights "
                                "model-repo unchanged since 2026-11-06, the card's serve.py with /engine/reax13.json "
                                "(FP8 per that config), the same env -i variables"),
                    measured="about 62 GB loaded, 74.7 GB peak on GPU 0 (mailbox/Late entries REAX - status 2026-11-07.md)"),
        settings_change=dict(
            base_url=LOGIC_REAX["url"],
            device=("RTX PRO 6000 (bariton GPU 0), one GPU for both parts (logic's servers.sh unit logic-dm-reax13, "
                    "loopback port 19100)")),
        rules=dict(mirror_concurrent=True),
        differences=[
            RUNNER_DIFFERENCE % "acfd89c (clean)",
            ("Server: logic's container logic-dm-reax13 on Docker's default bridge, its API published on the host's "
             "loopback (outbound network open; offline Hugging Face variables set as before), where the original ran "
             "reax13-late on the internal network reax13-offline (no outbound route), reached on the container's "
             "address; logic's env lacks HF_HUB_DISABLE_IMPLICIT_TOKEN=1 (offline either way). Same image, engine, "
             "kit, weights, config and serve.py arguments."),
            ("no-new-privileges: the original ran without it under Can's one-run exception (#2199); logic's server "
             "drops it only with REAX_NO_NNP_EXCEPTION=1 and its own approval, otherwise it does not start."),
        ]),
    "d1-ultra-r1": dict(
        original="Liquid d1-ultra", original_league=1, original_stage="league",
        # Its League 1 matches (2026-10-19 to 2026-10-22, before ladder round 1 moved it to League 2).
        original_matches=[180, 181, 182, 184, 190, 191, 192, 223, 264, 265, 268, 275, 280, 283, 365, 376, 399, 490],
        runner=RUNNER, original_runner="six builds: 17f3b8e, 2421d9e, 6425197, 356e32a (uncommitted changes), bef3ec8, ec555d6",
        server=dict(kind="api", mib=0, start=None, stop=None, health=None, smoke=None,
                    provenance="Liquid AI decisions API, paid tier (spec liquid/d1-ultra, LIQUIDAI_API_KEY in ~/.keys)",
                    measured="none (hosted)"),
        settings_change=dict(),
        rules=dict(mirror_concurrent=False),
        differences=[
            ("Runner: its 18 League 1 matches were played by six runner builds (17f3b8e, 2421d9e, 6425197, 356e32a "
             "with uncommitted changes; bef3ec8, ec555d6 clean); the repeat uses the pinned-pairs build "
             f"{RUNNER['commit']}. Same prompt version bg-v2, option-order seed and rules; mirror games off as in its "
             "originals."),
            ("Opponent hardware: Clef (#180), Cygnet (#184) and Decider v1.1 27B (#182) answered from DGX Spark (GB10) "
             "servers then; they now run on our RTX PRO 6000 cards with the same checkpoints and arguments (their "
             "players.device records the move and its 20-request replays: same play 20/20, 20/20 and 19/20)."),
            ("Hosted model: d1-ultra is served by Liquid; whether the hosted model behind liquid/d1-ultra changed since "
             "2026-10-19 cannot be checked from here."),
        ]),
}
DISPLAY = {"mammoth-1-r1": "Mammoth-1", "drex-max-v1-r1": "Drex Max v1", "reax-1.3-r1": "REAX 1.3",
           "d1-ultra-r1": "Liquid d1-ultra"}


def ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    return conn


def repeat_name(rid: str) -> str:
    return f"{REPEATS[rid]['original']} [repeat 1]"


def u64(x: int) -> str:
    return str(x & MASK)


def kind_of(name: str) -> str:
    return "api" if name in API else "program" if name in PROGRAMS else "local"


def original_pairs(conn, rid: str) -> list[dict]:
    """The original's matches against its field: one valid match per opponent (status as stored)."""
    r = REPEATS[rid]
    me = conn.execute("SELECT id FROM players WHERE name = ?", (r["original"],)).fetchone()["id"]
    if "original_matches" in r:
        ids = r["original_matches"]
        rows = [conn.execute("SELECT * FROM matches WHERE id = ?", (i,)).fetchone() for i in ids]
    else:
        rows = conn.execute(
            """SELECT * FROM matches WHERE valid = 1 AND stage = ? AND ? IN (player1, player2) ORDER BY id""",
            (r["original_stage"], me)).fetchall()
    names = {x["id"]: x["name"] for x in conn.execute("SELECT id, name FROM players")}
    out = []
    for m in rows:
        if not m["valid"] or me not in (m["player1"], m["player2"]):
            sys.exit(f"{rid}: match #{m['id']} is not a valid match of {r['original']}")
        first = m["player1"] == me
        opp = names[m["player2"] if first else m["player1"]]
        games = conn.execute("SELECT round_no, leg, white_player, dice_seed, opening_white, opening_black, result, "
                             "points, turns FROM games WHERE match_id = ? ORDER BY round_no, leg", (m["id"],)).fetchall()
        seat = 1 if first else 2
        agg = {t["player"]: t for t in conn.execute(
            """SELECT t.player, SUM(t.decided_by IN ('model', 'fallback')) AS decisions, SUM(COALESCE(t.cost_usd, 0)) AS
                      cost, SUM(t.input_tokens) AS tokens
               FROM turns t JOIN games g ON g.id = t.game_id WHERE g.match_id = ? GROUP BY t.player""", (m["id"],))}
        mine, theirs = agg.get(seat), agg.get(3 - seat)
        opp_billed = None
        if opp in BILLED and theirs:
            opp_billed = (theirs["tokens"] or 0) * FASTINO_RATE / 1e6 if opp == "Fastino GLiDE" else theirs["cost"]
        out.append(dict(
            opponent=opp, kind=kind_of(opp), original_match=m["id"], status=m["status"],
            error=(m["error"] or "")[:300] or None,
            seed=m["seed"], seed_u64=u64(m["seed"]), original_is_player1=first,
            model1=names[m["player1"]], model2=names[m["player2"]],
            rules=dict(rounds=m["rounds_planned"], clock_seconds=m["clock_seconds"], delay_seconds=m["delay_seconds"],
                       max_turns=m["max_turns"], prompt_version=m["prompt_version"], order_seed=m["order_seed"],
                       order_seed_u64=u64(m["order_seed"]), mirror_concurrent=bool(m["mirror_concurrent"]),
                       start_position=m["start_position"]),
            harness=dict(commit=m["harness_commit"], dirty=bool(m["harness_dirty"])),
            started=m["started_at"], finished=m["finished_at"],
            minutes=round((datetime.fromisoformat(m["finished_at"].replace("Z", "+00:00"))
                           - datetime.fromisoformat(m["started_at"].replace("Z", "+00:00"))).total_seconds() / 60, 1)
            if m["finished_at"] and m["status"] == "finished" else None,
            score_for=m["score1"] if first else m["score2"], score_against=m["score2"] if first else m["score1"],
            games=[dict(round=g["round_no"], leg=g["leg"], white_player=g["white_player"], dice_seed=g["dice_seed"],
                        dice_seed_u64=u64(g["dice_seed"]), opening=[g["opening_white"], g["opening_black"]],
                        result=g["result"], points=g["points"], turns=g["turns"]) for g in games],
            decisions=dict(original=(mine["decisions"] if mine else 0), opponent=(theirs["decisions"] if theirs else 0)),
            billed_usd=dict(opponent=round(opp_billed, 4) if opp_billed is not None else None,
                            original=round(mine["cost"], 4) if mine and r["server"]["kind"] == "api" else None),
            blocked_today=BLOCKED_TODAY.get(opp)))
    return out


def manifest(args) -> None:
    conn = ro()
    late = json.loads((REPO / "tools/site/content/late_entries.json").read_text())["not_played"]
    out = dict(
        _about=("Reproducibility repeats (prepared, not started): per repeat, the original's per-opponent match id, "
                "seed and seats, game dice, option-order seed, prompt, rules and settings, its coverage, today's "
                "blockers, the paid gates, cost basis, GPU plan and start commands. Written by tools/v3/repeats/"
                "repeats.py manifest from v3.db (read-only)."),
        written=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), requested_by=WRITTEN_FOR,
        seed_mechanism=dict(
            finding=("The original runner builds have no per-pair seed field: a new pair's seed and seating come from "
                     "the two player names and the rules hash (Rules::pair_seed, Rules::sides), so a renamed repeat "
                     "would get other dice. The late entries' seeds are exactly that (checked for #780, #807, #818, "
                     "#845, #867, #905, #920); Liquid d1-ultra's League 1 seeds are not (older rule)."),
            used=(f"Runner change on branch pinned-pairs, commit {RUNNER['commit']} (Zeki #4710): league config field "
                  "pinned_pairs {opponent: {seed: u64, seat_first: bool}} for the only_pairs_of setup, stored in the "
                  "new column leagues.pinned_pairs and read wherever fixtures are derived (resume, league-add and a "
                  "running league keep them); league-add --pin. Every game's dice follow from the match seed and every "
                  "option order from the option-order seed and the position, never from names: a test replays #808, "
                  "#856, #905 and #190 under a renamed repeat and gets every game's dice and every turn's option order "
                  "of the original. Each repeat's league config carries a pin for every opponent of its original."),
            migration=("leagues.pinned_pairs is added (ALTER TABLE ADD COLUMN, NULL) by the new build's ensure_schema "
                       "the first time it opens a database; not applied to production v3.db yet (nothing has run it "
                       "there); no existing row is edited, and NULL means no pins, so older builds and every existing "
                       "league are unaffected."),
            not_used="The voided-placeholder route (pin --apply) is dropped (Zeki #4710)."),
        blockers_today=[dict(opponent=k, reason=v) for k, v in BLOCKED_TODAY.items()],
        gates=dict(paid_cap_usd_per_repeat=5.0, openrouter_floor_usd=40.0, openrouter_unreadable_stop=3,
                   note=("Each repeat's guard (tools/v3/repeats/run.sh): stops the league when its billed spend "
                         "(paid opponents, and Liquid d1-ultra itself in its repeat) reaches $5, when OpenRouter's "
                         "balance is under $40 or unreadable 3 times in a row, or when the entrant's server fails 3 "
                         "health checks in a row.")),
        gpu_card=dict(name="NVIDIA RTX PRO 6000 Blackwell Workstation Edition", mib=GPU_MIB, margin_mib=MARGIN_MIB),
        repeats=[])
    for rid, r in REPEATS.items():
        name = repeat_name(rid)
        row = conn.execute("SELECT id, settings FROM players WHERE name = ?", (r["original"],)).fetchone()
        settings = json.loads(row["settings"])
        rep = dict(settings, name=name, max_matches=1, **r["settings_change"])
        rep["note"] = (settings.get("note") or "") + repeat_note(rid)
        diff = [k for k in sorted(set(settings) | set(rep)) if settings.get(k) != rep.get(k)]
        pairs = original_pairs(conn, rid)
        field = sorted(set(FIELD) - {r["original"]})
        played = [p for p in pairs if p["status"] == "finished"]
        missing = [o for o in field if o not in {p["opponent"] for p in played}]
        reasons = {x["opponent"]: x["reason"] for x in late if x["entrant"] == r["original"]}
        playable = [p for p in pairs if p["status"] == "finished" and not p["blocked_today"]]
        dropped = [p["opponent"] for p in played if p["blocked_today"]]
        unpinned = [o for o in missing if o not in {p["opponent"] for p in pairs}]
        srv = r["server"]
        big = [o for o in LOCAL if srv["mib"] + LOCAL[o][0] + MARGIN_MIB > GPU_MIB]
        rules = {k: v for k, v in pairs[0]["rules"].items()}
        for p in pairs:
            if p["rules"] != rules:
                sys.exit(f"{rid}: rules differ between its original matches (#{p['original_match']})")
        paid = [p for p in playable if p["billed_usd"]["opponent"] is not None or p["billed_usd"]["original"]]
        est_opp = sum(p["billed_usd"]["opponent"] or 0 for p in playable)
        est_own = sum(p["billed_usd"]["original"] or 0 for p in playable)
        mins = {k: round(sum(p["minutes"] or 0 for p in playable if p["kind"] == k), 1) for k in ("program", "api", "local")}
        out["repeats"].append(dict(
            id=rid, run_id=f"repeat-2026-11-11-{rid}", name=name, display=DISPLAY[rid], original=r["original"],
            original_player_id=row["id"], original_league=r["original_league"], original_stage=r["original_stage"],
            status=r.get("status", "queued"), hold=r.get("hold"), prepared="2026-11-11", started=None, finished=None,
            league_config=f"tools/v3/repeats/leagues/{rid}.json",
            status_file=f"mailbox/repeats/{rid} - status.md",
            runner=dict(r["runner"], original=r["original_runner"]),
            rules=dict(rules, mirror_concurrent=r["rules"]["mirror_concurrent"]),
            settings_original=settings, settings_repeat=rep, settings_changed=diff,
            server={k: v for k, v in srv.items() if k not in ("start", "stop", "health_any_status")}
            | dict(start=srv["start"], stop=srv["stop"]),
            coverage_original=dict(
                played=len(played), of=len(field),
                not_played=[dict(opponent=o, match=next((p["original_match"] for p in pairs if p["opponent"] == o), None),
                                 reason=reasons.get(o, "no match")) for o in missing]),
            coverage_repeat_today=dict(
                playable=len(playable), of=len(field),
                blocked=[dict(opponent=p["opponent"], reason=p["blocked_today"]) for p in pairs if p["blocked_today"]
                         and p["status"] == "finished"],
                not_in_original=[dict(opponent=o, reason=reasons.get(o, "no original match"),
                                      today=BLOCKED_TODAY.get(o)) for o in missing],
                unpinned=unpinned),
            cost_basis=dict(
                method=("Each playable pair's billed cost in the original match: the paid opponent's recorded "
                        "cost_usd (Fastino GLiDE: input tokens x $0.04/M), plus Liquid d1-ultra's own cost_usd in its "
                        "repeat; local setups and programs bill nothing."),
                pairs={p["opponent"]: p["billed_usd"] for p in paid},
                estimate_usd=round(est_opp + est_own, 4), opponents_usd=round(est_opp, 4), entrant_usd=round(est_own, 4),
                cap_usd=5.0),
            time=dict(
                method=("Sum of each playable pair's original match duration (start to finish; the originals ran "
                        "several matches at once, so one at a time is about this or less), plus server starts."),
                minutes_matches=mins, minutes_total_matches=round(sum(mins.values()), 1),
                server_starts=("entrant: Mammoth-1 1-2 min, Drex Max v1 about 1 min, REAX 1.3 already up (logic), "
                               "d1-ultra none; each local opponent 1-5 min (state logs of the originals)")),
            gpu_plan=dict(
                entrant_mib=srv["mib"], entrant_measured=srv["measured"],
                fits_beside_entrant=[o for o in LOCAL if o not in big],
                needs_second_gpu=big,
                note=("One card: the entrant's server (none for d1-ultra) stays up for the whole repeat; the opponent "
                      "servers run one at a time beside it, smallest first. A pair needs both servers at once, so the "
                      "opponents in needs_second_gpu (entrant + opponent + 2 GB over 97,887 MiB) wait for a second "
                      "card (OPP_GPU) or stay unplayed.")),
            differences=["Name: '<original> [repeat 1]', a new players row; settings otherwise as the original's (the "
                         "changed fields are listed under Settings); one match at a time, where the original played "
                         "several at once."]
                        + r.get("differences", []) + (
                [f"Not replayable today, though played in the original: {', '.join(dropped)} (blockers today); "
                 "their seed pins are kept so they replay with the original seeds once unblocked."] if dropped else []),
            start=start_commands(rid),
            pairs=pairs))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"{MANIFEST.relative_to(REPO)}: {len(out['repeats'])} repeats")


def start_commands(rid: str) -> list[str]:
    run = f"/home/cbasaran/code/jevgammon/tools/v3/repeats/run.sh {rid}"
    unit = f"systemd-run --user --unit=repeat-{rid} --working-directory=/home/cbasaran/code/jevgammon"
    gpu = {"ours": "-E GPU=0 -E OPP_GPU=0", "logic": "-E GPU=0 -E OPP_GPU=0", "api": "-E OPP_GPU=0"}[REPEATS[rid]["server"]["kind"]]
    if REPEATS[rid].get("status") == "held":
        return []
    return [f"{unit} {gpu} -E RES=<reservation> {run}"]


def load() -> dict:
    return {r["id"]: r for r in json.loads(MANIFEST.read_text())["repeats"]}


def configs(args) -> None:
    conn = ro()
    out = HERE / "leagues"
    out.mkdir(exist_ok=True)
    for rid, m in load().items():
        r = m["rules"]
        progs = [json.loads(conn.execute("SELECT settings FROM players WHERE name = ?", (n,)).fetchone()[0])
                 for n in PROGRAMS]
        cfg = dict(
            note=(f"Reproducibility repeat 1 of {m['original']} ({WRITTEN_FOR}, #4710; run {m['run_id']}): {m['name']} "
                  f"plays {m['original']}'s original League 1 field again, one match at a time, each pair pinned to its "
                  "original match's seed and seating (pinned_pairs), the same option-order seed, prompt, rules and "
                  "settings. Hidden league; matches stage 'late-entry' and the name held "
                  "(tools/site/content/held_setups.json): in no standings, table, Cup input or other setup's numbers. "
                  "mailbox/repeats/manifest-2026-11-11.json"),
            prompt_version=r["prompt_version"], seed=conn.execute("SELECT seed FROM leagues WHERE id = 1").fetchone()[0],
            order_seed=r["order_seed"], rounds=r["rounds"], clock=0, delay=30, max_turns=r["max_turns"],
            mirror_concurrent=r["mirror_concurrent"], only_pairs_of=m["name"], hidden=True,
            pinned_pairs=wanted_pins(m), players=[m["settings_repeat"]] + progs)
        if r["clock_seconds"] is not None or r["start_position"] is not None:
            sys.exit(f"{rid}: originals ran with a clock or another start; not covered")
        path = out / f"{rid}.json"
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
        print(f"{path.relative_to(REPO)}: {m['name']} v {', '.join(PROGRAMS)} (the rest by league-add)")


def shell_env(args) -> None:
    m = load()[args.id]
    s, r = REPEATS[args.id]["server"], m["runner"]
    for k, v in dict(NAME=m["name"], RUN_ID=m["run_id"], KIND=s["kind"], BIN=r["binary"], ENTRANT_MIB=s["mib"],
                     START=s["start"] or "", STOP=s["stop"] or "", HEALTH=s["health"] or "",
                     HEALTH_ANY=int(bool(s.get("health_any_status"))), SMOKE=s["smoke"] or "",
                     STATUS=str(MAIN / m["status_file"]), CAP=m["cost_basis"]["cap_usd"]).items():
        print(f"{k}={shlex.quote(str(v))}")


def plan(args) -> None:
    m = load()[args.id]
    order = {"program": 0, "api": 1, "local": 2}
    local_rank = list(LOCAL)
    pairs = sorted((p for p in m["pairs"] if p["status"] == "finished"),
                   key=lambda p: (order[p["kind"]], local_rank.index(p["opponent"]) if p["kind"] == "local" else 0,
                                  p["opponent"]))
    for p in pairs:
        mib, start, stop = LOCAL.get(p["opponent"], (0, "", ""))
        print("|".join([p["opponent"], p["kind"], str(mib), start, stop, "blocked" if p["blocked_today"] else ""]))


def wanted_pins(m) -> dict:
    """The pin of every opponent of the original: its match's seed (u64) and whether the original sat first."""
    return {p["opponent"]: dict(seed=int(p["seed_u64"]), seat_first=p["original_is_player1"]) for p in m["pairs"]}


def trigger_names(conn) -> list[str]:
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = 'late_entry_stage'").fetchone()
    if not sql:
        sys.exit("v3.db has no late_entry_stage trigger")
    return [n.replace("''", "'") for n in re.findall(r"'((?:[^']|'')*)'", TRIGGER.search(sql[0]).group(1))]


def check(args) -> None:
    """Fail closed: the league config pins every opponent to its original seed and seating (and the league, once it
    exists, holds the same pins), the name is in the trigger and held in the main checkout's committed site code, the
    runner tree is clean at the pinned-pairs commit and its binary present; a held repeat never passes."""
    m = load()[args.id]
    conn = ro()
    bad = [f"held: {m['hold']}"] if m["status"] == "held" else []
    want = wanted_pins(m)
    if json.loads((HERE / "leagues" / f"{args.id}.json").read_text()).get("pinned_pairs") != want:
        bad.append("league config pins differ from the manifest's original seeds and seats")
    lid = league_id(conn, m["name"])
    if lid is not None:
        stored = conn.execute("SELECT pinned_pairs FROM leagues WHERE id = ?", (lid,)).fetchone()[0]
        if json.loads(stored or "{}") != want:
            bad.append(f"league #{lid} holds other pins")
    if m["name"] not in trigger_names(conn):
        bad.append("not in the late_entry_stage trigger")
    held = json.loads(subprocess.run(["git", "-C", str(MAIN), "show", "HEAD:tools/site/content/held_setups.json"],
                                     capture_output=True, text=True).stdout or "{}").get("held", {})
    if m["name"] not in held:
        bad.append("not held in the main checkout's committed tools/site/content/held_setups.json")
    rn = m["runner"]
    head = subprocess.run(["git", "-C", rn["tree"], "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", rn["tree"], "status", "--porcelain", "--untracked-files=no", "--", "src"],
                           capture_output=True, text=True).stdout.strip()
    built = subprocess.run(["git", "-C", rn["tree"], "merge-base", "--is-ancestor", rn["commit"], "HEAD"]).returncode
    if built or dirty:
        bad.append(f"runner tree {rn['tree']} at {head[:7]}{' dirty' if dirty else ''} lacks {rn['commit']}")
    if not os.access(rn["binary"], os.X_OK):
        bad.append(f"no runner {rn['binary']}")
    if bad:
        sys.exit(f"{args.id}: " + "; ".join(bad))
    print(f"{args.id}: {len(want)} pairs pinned in its config, trigger and held name in place, runner "
          f"{rn['commit']} (tree {head[:7]})")


def trigger(args) -> None:
    name = load()[args.id]["name"]
    conn = sqlite3.connect(DB, timeout=120)
    conn.execute("BEGIN IMMEDIATE")
    names = trigger_names(conn)
    if name in names:
        conn.rollback()
        print("trigger already names", name)
        return
    listed = ", ".join("'" + n.replace("'", "''") + "'" for n in names + [name])
    conn.execute("DROP TRIGGER late_entry_stage")
    conn.execute(f"""CREATE TRIGGER late_entry_stage AFTER INSERT ON matches
WHEN EXISTS (SELECT 1 FROM players p WHERE p.id IN (NEW.player1, NEW.player2)
             AND p.name IN ({listed}))
BEGIN
  UPDATE matches SET stage = 'late-entry' WHERE id = NEW.id;
END""")
    conn.commit()
    print("late_entry_stage now names:", listed)


def league_id(conn, name: str):
    row = conn.execute("SELECT id FROM leagues WHERE only_pairs_of = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
    return row[0] if row else None


def repeat_matches(conn, m, finished=True):
    return conn.execute(
        f"""SELECT m.*, a.name AS a, b.name AS b FROM matches m JOIN players a ON a.id = m.player1
            JOIN players b ON b.id = m.player2
            WHERE m.valid = 1 AND m.stage = 'late-entry' AND ? IN (a.name, b.name)
              {"AND m.status = 'finished'" if finished else ""} ORDER BY m.id""", (m["name"],)).fetchall()


def pending(args) -> None:
    m = load()[args.id]
    conn = ro()
    done = {(r["b"] if r["a"] == m["name"] else r["a"]) for r in repeat_matches(conn, m)}
    want = args.opponents or [p["opponent"] for p in m["pairs"] if p["status"] == "finished"]
    print(sum(o not in done for o in want))


def billed_usd(conn, m) -> float:
    total = 0.0
    for r in conn.execute(
            """SELECT p.name, SUM(COALESCE(t.cost_usd, 0)) AS cost, SUM(t.input_tokens) AS tokens FROM turns t
               JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
               JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
               JOIN players a ON a.id = m.player1 JOIN players b ON b.id = m.player2
               WHERE m.stage = 'late-entry' AND ? IN (a.name, b.name) GROUP BY p.name""", (m["name"],)):
        if r["name"] == "Fastino GLiDE":
            total += (r["tokens"] or 0) * FASTINO_RATE / 1e6
        elif r["name"] in BILLED or (r["name"] == m["name"] and m["original"] in BILLED):
            total += r["cost"]
    return total


def billed(args) -> None:
    print(f"{billed_usd(ro(), load()[args.id]):.4f}")


def results(args) -> None:
    """Status per repeat: queued (no league yet), running, or played (run.sh ended its loop: workspace/repeats/ID/done);
    the dates and match counts from v3.db. The site computes the measures of a played repeat from its snapshot, on the
    pairs it played, with the original's on the same pairs (analysis.repeat_originals)."""
    conn = ro()
    out = {}
    for rid, m in load().items():
        lid = league_id(conn, m["name"])
        played = repeat_matches(conn, m)
        playable = [p for p in m["pairs"] if p["status"] == "finished" and not p["blocked_today"]]
        done = (MAIN / "workspace/repeats" / rid / "done").exists()
        state = ("held" if m["status"] == "held" else "queued" if lid is None else "played" if done else "running")
        out[rid] = dict(status=state, league=lid, played=len(played), playable=len(playable),
                        first_match=played[0]["id"] if played else None,
                        started=played[0]["started_at"] if played else None,
                        finished=played[-1]["finished_at"] if played and state == "played" else None)
    RESULTS.write_text(json.dumps(dict(
        _about=("Repeat checks' status (Experiments page), written by tools/v3/repeats/repeats.py results from v3.db "
                "and run.sh's done flag; the site computes a played repeat's risk judgement, error rate and decisions, "
                "and its original's on the same pairs, from its snapshot."),
        results=out), indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest").set_defaults(fn=manifest)
    sub.add_parser("configs").set_defaults(fn=configs)
    sub.add_parser("results").set_defaults(fn=results)
    for cmd, fn in (("plan", plan), ("check", check), ("trigger", trigger), ("billed", billed), ("env", shell_env)):
        p = sub.add_parser(cmd)
        p.add_argument("id", choices=list(REPEATS))
        p.set_defaults(fn=fn)
    p = sub.add_parser("league-id")
    p.add_argument("id", choices=list(REPEATS))
    p.set_defaults(fn=lambda a: print(league_id(ro(), load()[a.id]["name"]) or ""))
    p = sub.add_parser("pending")
    p.add_argument("id", choices=list(REPEATS))
    p.add_argument("opponents", nargs="*")
    p.set_defaults(fn=pending)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
