#!/usr/bin/env python3
"""Reproducibility repeats of seven League 1 setups (Ümit via Zeki, bus #4663, #4666, #4667, #4671; #4838 Drex Max 1.1
and Fastino GLiDE v1.2 (local); #5359 Gemini Decision 1): each repeat plays
the original's own League 1 field again, one match at a time, each pair pinned (league config pinned_pairs, runner
branch pinned-pairs, Zeki #4710) to its original match's seed (dice) and seating, with the
same option-order seed, prompt, rules and setup settings, under a separate held name ('<original> [repeat 1]') whose
matches carry stage 'late-entry' (late_entry_stage trigger) and are held off every page, table and league computation
(tools/site/content/held_setups.json). Published rows are never changed. Run from anywhere; v3.db is the main
checkout's (JEVGAMMON_DB overrides).

  repeats.py manifest                 writes mailbox/repeats/manifest-2026-11-11.json from v3.db (read-only)
  repeats.py configs                  writes tools/v3/repeats/leagues/ID.json from the manifest
  repeats.py plan ID                  opponents to play, in order: NAME|KIND|MiB|START|STOP|BLOCKED (read-only)
  repeats.py check ID                 fail-closed preflight (read-only): held, config pins and settings, a recorded
                                      attempt's league exactly as recorded, held name on the site, runner binary and
                                      build inputs (sha256), every client admitted by that runner and the settings it
                                      admitted those v3.db holds now, trigger; exit 3 = only the trigger lacks the name,
                                      1 = anything else; on success the last line is the admitted-settings record
  repeats.py bound ID FILE            the league config and v3.db's settings are those of check's admitted-settings
                                      record FILE, else exit 1 (read-only; run_league.sh before the league starts)
  repeats.py entry ID NAME FILE       a pinned opponent's settings text as admitted in FILE, for league-add --entry
                                      (read-only; exit 1 when anything differs from FILE)
  repeats.py env ID                   shell assignments for run.sh (NAME KIND BIN ENTRANT_MIB START STOP HEALTH ...)
  repeats.py trigger ID               WRITES v3.db: adds the repeat name to the late_entry_stage trigger (refused unless
                                      that is check's only failure)
  repeats.py league-id ID             the repeat's current league id (never a recorded attempt's), or nothing (read-only)
  repeats.py pending ID [OPPONENT...] pairs without a finished valid repeat match (read-only)
  repeats.py billed ID                dollars billed in the repeat's matches (read-only)
  repeats.py results                  writes tools/site/content/repeat_results.json (status per repeat, read-only)
"""
import argparse
import hashlib
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
# Entrants billed by the input token at another rate than their recorded cost_usd: Nace bills Drex Max 1.1 its $0.03 per
# million launch price (its settings.budget; turns.cost_usd records the $0.06 list price).
ENTRANT_RATE = {"Drex Max 1.1": 0.03}
NACE_LEDGER = "/home/cbasaran/code/jevgammon/workspace/drex/state/nace-budget.db"
BLOCKED_TODAY = {
    "GPT-6 Luna": ("no credit: OpenAI Decisions answers 429 'no credits remaining' (Drex #829/#835/#846/#886, REAX, "
                   "Muse Ember and KnowLine runs: deferred); a top-up needs Can"),
    "Mercury Decide": ("no OpenRouter endpoint: 404 'No endpoints found for inception/mercury-decide' at warm-up "
                       "(Muse Ember #932, 2026-11-10 15:57 UTC; KnowLine #946, 2026-11-10 23:55 UTC)"),
}
WRITTEN_FOR = "Ümit via Zeki, bus #4663, #4666, #4667 (protocol), #4671 (d1-ultra)"
LOGIC_REAX = dict(container="logic-dm-reax13", url="http://127.0.0.1:19100",
                  image="sha256:9622cace6607ea35516dfae16c1d2c0cc191a7da735be0a7966e06a0dd839938")
# The pinned-pairs build 4ca4f08 (league config pinned_pairs; Zeki #4710), bound by sha256 (Zeki #4737): built on
# origin/main's runner line, which has no reax, baselabs, drex-max or nace client. REAX 1.3's first attempt ran it
# (league #24, 0 matches: "unknown provider `reax`"); kept as that attempt's runner identity (REPEATS attempts), never
# run again (Zeki #4886).
RUNNER_4CA4F08 = dict(
    binary=str(MAIN / "target/pinned/release/jevgammon"),
    binary_sha256="53816d53b3a020eb9f858ccb44b7e7782d74609f0f8c7312c55f0cd5347a7098",
    tree="/home/cbasaran/code/jevgammon-runner-4ca4f08", commit="4ca4f08",
    commit_full="4ca4f08c8aed7bea2c87e43ccda2521e4c08cdbe", src_tree="b41757b8899fb70573ce9c5d11ad0972e10cf179",
    build=dict(
        command=("cd /home/cbasaran/code/jevgammon-runner-4ca4f08 && CARGO_TARGET_DIR=/home/cbasaran/code/jevgammon/"
                 "target/pinned cargo build --release --locked"),
        toolchain="rustc 1.97.1 (8bab26f4f 2026-07-14), cargo 1.97.1 (c980f4866 2026-06-30)",
        built="2026-11-11T12:44Z",
        tree=("git worktree add --detach /home/cbasaran/code/jevgammon-runner-4ca4f08 "
              "4ca4f08c8aed7bea2c87e43ccda2521e4c08cdbe (clean; only the untracked METADATA.worktree added)")),
    inputs={
        "Cargo.toml": "bf64a9f15bd33cd3f5d517dc984140ff38fb9ec93c5d3a50eb0971f658c0ed4b",
        "Cargo.lock": "d7048551c8907fd02c85f7ac8d8d2ffdc088ae4848bf313fc3c0f6e070d88494",
        "tools/gnubg_player.py": "085601d706df41ddec7f1732428a2366c157aa58bb8e514b1cf1dd1b0f3f3aab",
        "tools/v3/engine.py": "511ab4b2490732632f7e810f2e3da616fb5da4cd91d75eb2cf1ac4604e50e046",
        "tools/v3/rules.py": "18dd032837ff061f64d2af32a5e7e813ad187b64f28a5a6e139f7695202f8480",
        "tools/v3/order_vectors.json": "9efbb3ada083c02c51bdf74e539d48ee61b2f49e8d2f0fe58e29db8c6d8cb499",
        "prompts/bg-v2.md": "3c59036a1f416f6187ccec06ec939e4d888a2029441daf30f6ee06a69015c465",
        "prompts/nack-v2.md": "fa7397be6e9a7d337389a401d61464464bcbbe5725b8a2c70e01e6cb670395a8",
        "prompts/bg-v3-std-notable.md": "1a145a09713fdd694696cb16d826406711567394697f0938300c285e4cba703f",
        "prompts/bg-v3-nack.md": "13c744f06613f4051888af99bf9d1692011cb95d6f301c1898f94e13d67fef33",
        "prompts/instructions.txt": "445735bf10ff30e4cc7f1a90dbeaa0c8858f0cf0b7bfe3f9dd3a0da1f1f0ec2d",
        "prompts/instructions-notation.txt": "8565178e44a566f703fe1443f028ab2877d3d931b9ddef43547b92f9d1a7acdb",
        "prompts/question.txt": "ef76def6baccec519ff9515c66b41d4c233b8e2927acf18115ad1e2e494211dc",
        "prompts/letter-system.txt": "21059b268bae257dab3aa7f608d1545d9d6a610f6f2782fc4baa84e728a6c82e",
        "prompts/prediction.txt": "cf3b989784a3b815fe1440589e2f212acc4e106ec4fe1e784d256ab58b128725",
        "prompts/prediction-system.txt": "4d08045b72eeedc28602af09f82475a60bac768819d40a00a50601a661da332f",
        "src/league/testdata/repeat_originals.json": "1e8611f27444c8e2429cd0998475dba52e5e21bdbd67e22ee51cfd282101a994",
        "src/players/testdata/league8_request.json": "a285c55eb6e76c959801ec314305d0ee193131a2658da49926c9c73eccbee818",
    })
# check's exit status when the only failure is the repeat name missing from the late_entry_stage trigger: the one
# condition run.sh prepares (backup, trigger) before checking again; every other failure exits 1.
TRIGGER_MISSING = 3
NOT_IN_TRIGGER = "trigger missing: late_entry_stage does not name it"
# The runner every repeat uses (Zeki #4860, #4886, #4896, #4928): branch pinned-late-reax 0e66836 = origin/late-reax
# acfd89c (the originals' runner line, with the decision clients reax, baselabs, drex-max, nace, liquid and fastino) +
# 4ca4f08 cherry-picked without conflict (313e96f) + the offline admit command (e77e3a0) made read-only (d24d90a:
# database and budget ledgers opened read-only and immutable, client types outside the repeats' rosters refused before
# construction) + its admitted-settings record (0e66836: the config file's sha256, each pinned opponent's players row and
# settings sha256, compared by check and before the league starts with what v3.db holds now),
# bound by sha256 as above: the binary as built from a clean detached checkout of exactly that commit (its own tree,
# which the binary also asks for its harness commit at runtime), every compile input outside src (include_str!; no
# build.rs) and the test data inside src, Cargo.toml and Cargo.lock (all 18 at the same sha256 as 4ca4f08's). check
# refuses any other binary, commit, changed src or input. Review packages: mailbox/pinned-late-review/ (e77e3a0), its
# round2/ (d24d90a) and round3/ (0e66836).
RUNNER = dict(
    binary=str(MAIN / "target/pinned-late/release/jevgammon"),
    binary_sha256="60b3643b9ce7f58fce9217fa53c7a42990b19e56af85468ae3d6d6b8ad7818cc",
    tree="/home/cbasaran/code/jevgammon-runner-admit-bind", commit="0e66836",
    commit_full="0e668368dfd8db2da70663cda6b2ed183dd8532e", src_tree="280a60ec121341d2488336707e1ee457103f5500",
    build=dict(
        command=("cd /home/cbasaran/code/jevgammon-runner-admit-bind && CARGO_TARGET_DIR=/home/cbasaran/code/"
                 "jevgammon/target/pinned-late cargo build --release --locked"),
        toolchain="rustc 1.97.1 (8bab26f4f 2026-07-14), cargo 1.97.1 (c980f4866 2026-06-30)",
        built="2026-11-11T18:05Z",
        tree=("git worktree add /home/cbasaran/code/jevgammon-runner-admit-bind pinned-late-reax (d24d90a); commit "
              "0e66836; checkout --detach (clean; only the untracked METADATA.worktree added)")),
    inputs=dict(RUNNER_4CA4F08["inputs"]))
RUNNER_DIFFERENCE = ("Runner: " + RUNNER["commit"] + ", the originals' runner line (origin/late-reax acfd89c) with the "
                     "pinned-pairs change 4ca4f08 (the pins are its only change for these leagues), where the original "
                     "ran %s; the same prompt version, option-order seed and rules.")
# Gemini Decision 1's repeat runner (Ümit via Zeki #5359, #5385): branch pinned-late-gemini c13992f = RUNNER's 0e66836
# + the four runner commits its original ran, cherry-picked from late-gemini-decision (cb669a0): dab6da5 (decision
# clients merge the player's `request` fields, e.g. the OpenRouter provider pin), 1b234da, c0b58f3 (map-check v2 for
# google/gemini-decision-1 only) and 38024d6 (raw_entries decoder); + the run guard (c13992f, Zeki #5385: `league
# --guard`/`admit --guard`, every reply's served identity and one shared pre-send cap, used only with --guard; see
# GEMINI_GUARD). The 18 build inputs are RUNNER's, unchanged. Bound as RUNNER is. Review packages:
# mailbox/gemini-repeat/ (cb669a0) and its round2/ (c13992f).
RUNNER_GEMINI = dict(
    binary=str(MAIN / "target/pinned-gemini/release/jevgammon"),
    binary_sha256="811ef5b033ded7f14912b9e195820dc52f9bd508dd0dbb6daf91540600ef4dde",
    tree="/home/cbasaran/code/jevgammon-runner-gemini", commit="c13992f",
    commit_full="c13992f0f415d81da40a54b1b5bf9fbe60d31ea2", src_tree="f60c64c24a5d87dcb8bfd3dba9a5e1819a21a6d2",
    build=dict(
        command=("cd /home/cbasaran/code/jevgammon-runner-gemini && CARGO_TARGET_DIR=/home/cbasaran/code/jevgammon/"
                 "target/pinned-gemini cargo build --release --locked"),
        toolchain="rustc 1.97.1 (8bab26f4f 2026-07-14), cargo 1.97.1 (c980f4866 2026-06-30)",
        built="2026-11-12T13:52Z",
        tree=("git worktree add -b pinned-late-gemini /home/cbasaran/code/jevgammon-runner-gemini 0e66836; "
              "cherry-pick dab6da5 1b234da c0b58f3 38024d6 (cb669a0); commit c13992f (run guard); checkout --detach "
              "(clean; only the untracked METADATA.worktree added); the cb669a0 binary kept aside as "
              "target/pinned-gemini/jevgammon-cb669a0")),
    inputs=dict(RUNNER["inputs"]))
# The league of a recorded attempt is kept as it is and never resumed: league_id() skips it, so the repeat's next start
# creates a new league with the same config (repeat name, pins); check fails while such a league differs from its
# record (a process resumed, completed or edited it). The record is the attempt's whole historical state (Zeki #4928
# L1, #4954): its leagues row, every column, and every league_players row of the league, every column, with the joined
# players.name as player_name (the participant columns are these rows' keys besides player_name), as v3.db held them
# when the attempt stopped (read-only, 2026-11-11). The manifest lists these attempts before the current one.
REAX_ATTEMPT_1 = dict(
    league=24, runner=dict(commit=RUNNER_4CA4F08["commit"], commit_full=RUNNER_4CA4F08["commit_full"],
                           binary_sha256=RUNNER_4CA4F08["binary_sha256"]),
    record=dict(
        league=dict(
            id=24, started_at="2026-11-11T15:25:16.745Z", finished_at=None, seed=2567889193785291627, rounds=3,
            clock_seconds=None, delay_seconds=None, max_turns=300, status="running", ranking=None,
            note=("Reproducibility repeat 1 of REAX 1.3 (Ümit via Zeki, bus #4663, #4666, #4667 (protocol), #4671 "
                  "(d1-ultra), #4710; run repeat-2026-11-11-reax-1.3-r1): REAX 1.3 [repeat 1] plays REAX 1.3's "
                  "original League 1 field again, one match at a time, each pair pinned to its original match's seed "
                  "and seating (pinned_pairs), the same option-order seed, prompt, rules and settings. Hidden league; "
                  "matches stage 'late-entry' and the name held (tools/site/content/held_setups.json): in no "
                  "standings, table, Cup input or other setup's numbers. mailbox/repeats/manifest-2026-11-11.json"),
            prompt_version="bg-v2", order_seed=1190975713392774006, heartbeat_at=None, mirror_concurrent=1,
            seed_rule="pair-v1", hidden=1, only_pairs_of="REAX 1.3 [repeat 1]", start_position=None,
            pinned_pairs=(
                '{"Celeris-1 Decision":{"seed":7161064289564184736,"seat_first":true},'
                '"Clef":{"seed":14863584321610017996,"seat_first":true},'
                '"Cygnet (Gemma 4 12B)":{"seed":11364547734129190159,"seat_first":false},'
                '"Decider Flash v1.2":{"seed":10926795277747235328,"seat_first":false},'
                '"Decider v1.1 27B":{"seed":6810423341903318602,"seat_first":true},'
                '"Decider v1.2 27B":{"seed":1021836415416679067,"seat_first":true},'
                '"Fastino GLiDE":{"seed":8676420728319782702,"seat_first":false},'
                '"Fastino GLiDE v1.2 (local)":{"seed":9547641185966060099,"seat_first":true},'
                '"GNUbg weak":{"seed":7687453975057924759,"seat_first":false},'
                '"Jev 1.13.0":{"seed":1191860321266350990,"seat_first":true},'
                '"Jev 1.14.0":{"seed":12685378779393301775,"seat_first":true},'
                '"Liquid d1-ultra":{"seed":18385022176221832218,"seat_first":false},'
                '"Mercury Decide":{"seed":847988905885570598,"seat_first":true},'
                '"Open-Jev 27B v1.1":{"seed":11746268790371622157,"seat_first":false},'
                '"Random":{"seed":14048797037936432625,"seat_first":false},'
                '"Safest":{"seed":4250404258724067804,"seat_first":false},'
                '"SubQ Snap Preview":{"seed":1831931896691103214,"seat_first":false},'
                '"Winnow-12B":{"seed":4483105724799583608,"seat_first":true}}')),
        participants=[dict(id=lp, league_id=24, player_id=pid, joined_at="2026-11-11T15:25:16.745Z", left_at=None,
                           note=None, player_name=name)
                      for lp, pid, name in [(369, 65, "REAX 1.3 [repeat 1]"), (370, 39, "GNUbg weak"),
                                            (371, 42, "Random"), (372, 43, "Safest")]]),
    matches=0,
    outcome=("stopped: the entrant's client could not be built, 'unknown provider `reax`' (4ca4f08 is on origin/main's "
             "runner line); the league waited with 0 matches until stopped. Kept as the stopped attempt: not deleted, "
             "not completed, not resumed (Zeki #4886)."))


def repeat_note(rid: str, extra: str = "") -> str:
    return (f" Reproducibility repeat 1 ({rid}; tools/v3/repeats, mailbox/repeats/manifest-2026-11-11.json): the "
            "original's League 1 field again, one match at a time, each pair with its original match's seed and seats; "
            "held: in no standings, table, Cup input or other setup's numbers." + extra)


# Gemini Decision 1's entry cap (tools/v3/late-gemini-decision/start.sh on late-gemini-decision): $5 for the entrant
# plus the paid opponents, billed from match #993; its guard recorded $1.1819 when the entry ended
# (workspace/late-gemini-decision/state/guard.log, 2026-11-11T22:12:14Z). The repeat stays inside that cap.
GEMINI_CAP_USD, GEMINI_SPENT_USD = 5.0, 1.1819
# Gemini Decision 1's run guard (Zeki #5385; the runner's `league --guard`/`admit --guard`, src/guard.rs): the entrant
# and its paid opponents (BILLED among its pins) metered in one budget ledger under the remaining cap (each request
# attempt, warm-ups, retries and failures included, reserved at its worst case before it is sent and refused when it
# would pass the cap; settled at max(list price, reported usage.cost)), and every reply of the entrant (warm-ups and
# each split group included) naming exactly the original's served identity (model google/gemini-decision-1-20261111,
# provider Google AI Studio, as on all 1,704 original decisions). Either stop writes the latch file: the runner then
# sends and starts nothing, check refuses, run.sh stops; only a person removes it. Written by `configs` as
# leagues/../guards/ID.json (wanted_guard), its ledger created by the preparation (prepare_ledger).
GEMINI_STATE = MAIN / "workspace/repeats/gemini-decision-1-r1"
GEMINI_GUARD = dict(
    ledger=str(GEMINI_STATE / "guard-budget.db"), latch=str(GEMINI_STATE / "guard-latch"),
    expect_route=dict(models=["google/gemini-decision-1-20261111"], provider="Google AI Studio"))


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
        attempts=[REAX_ATTEMPT_1],
        status="queued",
        hold=None,
        server=dict(kind="logic", mib=75000, start=None, stop=None,
                    health=LOGIC_REAX["url"] + "/healthz", health_any_status=False,
                    smoke=f"python3 /home/cbasaran/code/jevgammon/workspace/reax/reax.py smoke {LOGIC_REAX['url']} reax13",
                    provenance=("logic's unit logic-dm-reax13 (~/code/benchmark/decision/servers.sh), started by logic "
                                "on bariton GPU 0 under Main's reservation r_57d739c4cd53 at 14:36 UTC 11 Nov, Logic & "
                                "Math and Reading repeats first (logic #4785, turkce #4819): the same image "
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
            ("Server: logic's container logic-dm-reax13, on the internal network reax13-offline (internal=true, no "
             "outbound route; egress test from inside: Network is unreachable), no published port, reached through a "
             "loopback forwarder on 127.0.0.1:19100; read-only root, cap-drop ALL, user 1000:1000 (logic #4785). The "
             "original ran reax13-late on the same internal network, reached on the container's address. Same image, "
             "engine, kit, weights, config and serve.py arguments; shared in turn with logic's and turkce's repeats."),
            ("no-new-privileges: off, as in the original; Can renewed his one-run exception (#2199) for this repeat "
             "server, offline only (#4745, answering #4744)."),
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
    "drex-max-1.1-r1": dict(
        original="Drex Max 1.1", original_league=15, original_stage="late-entry",
        runner=RUNNER, original_runner="e58fc6c255304c085bdb5eb8dec34b83c473573a",
        server=dict(kind="api", mib=0, start=None, stop=None, health=None, smoke=None,
                    provenance=("Nace's hosted System One endpoint (https://console.nace.ai/v1/systemone), model "
                                "drex-max-v1.1, no open weights (NACEAI_API_KEY in ~/.keys); every request booked "
                                f"first in the original's pre-send ledger {NACE_LEDGER} (its settings.budget)"),
                    measured="none (hosted)"),
        settings_change=dict(),
        rules=dict(mirror_concurrent=True),
        cost_method=("Each playable pair's billed cost in the original match: the paid opponent's recorded cost_usd "
                     "(Fastino GLiDE: input tokens x $0.04/M), plus Drex Max 1.1's own input tokens x $0.03/M (Nace's "
                     "billed launch price; its cost_usd records the $0.06 list price); local setups and programs bill "
                     "nothing."),
        server_starts="entrant: none (hosted); each local opponent 1-5 min (state logs of the original)",
        differences=[
            RUNNER_DIFFERENCE % "e58fc6c (clean)",
            ("Hosted model: Drex Max 1.1 is served by Nace; whether the model behind drex-max-v1.1 changed since "
             "2026-11-06 cannot be checked from here."),
            ("Nace pre-send cap: the settings (unchanged) book every request in the original's ledger "
             "workspace/drex/state/nace-budget.db, cap $1.25 shared with Drex 2.0, which the original started empty "
             "and which held $0.7856 settled on 2026-11-11 (Drex Max 1.1 $0.2853, Drex 2.0 $0.5003); the repeat has "
             "the $0.4644 left. Its expected own bill ($0.2751 at $0.03/M) fits; reaching the cap would refuse its "
             "requests and leave the repeat incomplete."),
        ]),
    "glide-v1.2-r1": dict(
        original="Fastino GLiDE v1.2 (local)", original_league=1, original_stage="league",
        # Its League 1 matches (matchday 24, joined late 2026-10-22; #547 on are ladder matches).
        original_matches=list(range(482, 500)),
        runner=RUNNER, original_runner="two builds: d2f1f9e (uncommitted changes) for #482-#486, ec555d6 (clean) for #487-#499",
        server=dict(kind="ours", mib=62000, start="GLIDE_GPU=$g /home/cbasaran/code/jevgammon/tools/v3/servers/glide-v12.sh start",
                    stop="/home/cbasaran/code/jevgammon/tools/v3/servers/glide-v12.sh stop",
                    health="http://127.0.0.1:18101/health", health_any_status=False,
                    smoke=("S=workspace/repeats/glide-v1.2-r1/smoke.db; rm -f $S && "
                           "/home/cbasaran/code/jevgammon/target/pinned/release/jevgammon ask --config "
                           "/home/cbasaran/code/jevgammon/leagues/smoke-glide-v12.json --positions "
                           "/home/cbasaran/code/jevgammon/positions/smoke.jsonl --setup 'Fastino GLiDE v1.2 (local)' "
                           "--out $S --time-limit 600 && n=$(sqlite3 $S \"SELECT count(*) FROM answers WHERE setup = "
                           "'Fastino GLiDE v1.2 (local)' AND error IS NULL AND COALESCE(invalid, 0) = 0 AND "
                           "probabilities IS NOT NULL\") && echo \"$n/50 answered with probabilities\" && "
                           "[ \"$n\" = 50 ]"),
                    provenance=("tools/v3/servers/glide-v12.sh and _lib.sh unchanged since ec555d6 (2026-10-22, the "
                                "original's start); fastino/GLiDE snapshot a7e45896be7c96ba3354891da790c5ec99c30b6c, "
                                "bf16, glide/server.py, GLIDE_MAX_BATCH=1; ~/code/glide/.venv torch 2.14.0+cu130, "
                                "transformers 5.17.0, flash-linear-attention 0.5.2 (checked 2026-11-11). Smoke as "
                                "its original's: jevgammon ask on the 50 smoke positions (leagues/smoke-glide-v12.json; "
                                "originally 50/50)"),
                    measured=("53.6 GiB loaded, 60.2 GB peak for a 39k-token question on bariton GPU 0 "
                              "(tools/v3/servers/README.md); glide-v12.sh start refuses under 62,000 MiB free")),
        settings_change=dict(),
        rules=dict(mirror_concurrent=False),
        server_starts=("entrant: GLiDE v1.2 loads in about 20 s, its smoke 50 positions about 1 min; each local "
                       "opponent 1-5 min (state logs of the originals). The local minutes include League 1's pause "
                       "(17:22 to about 22:23 UTC, Can) in #482, #483, #484 and #486, about 5 h each"),
        differences=[
            ("Runner: its 18 League 1 matches were played by d2f1f9e with uncommitted changes (#482-#486) and ec555d6 "
             f"(clean, #487-#499); the repeat uses the pinned-pairs build {RUNNER['commit']}. Same prompt version "
             "bg-v2, option-order seed and rules; mirror games off as in its originals."),
            ("Opponent hardware: Clef (#484) and Cygnet (#486) answered from DGX Spark (GB10) servers then, Decider "
             "v1.1 27B (#483) from spark3 until 22:41 UTC; they now run on our RTX PRO 6000 cards with the same "
             "checkpoints and arguments (their players.device records the move and its 20-request replays: same play "
             "20/20, 20/20 and 19/20)."),
            ("Server: the same script, snapshot and Python environment; the original ran on one RTX PRO 6000 card "
             "beside the opponents' servers on two others and the DGX Sparks, the repeat runs it on one card with the "
             "opponents one at a time on the same or a second card."),
        ]),
    "gemini-decision-1-r1": dict(
        original="Gemini Decision 1", original_league=26, original_stage="late-entry", prepared="2026-11-12",
        requested_by="Ümit via Zeki, bus #5359 (Ümit #5220: GPT-6 Luna and Mercury Decide not required)",
        # Its 17 required pairs (League 1 table; #993-#1013 first stage, #1053-#1063 local stage). #1016 (Mercury
        # Decide, aborted at its start, no game) is not required and not pinned; GPT-6 Luna was never scheduled.
        original_matches=[993, 994, 995, 996, 997, 998, 999, 1005, 1013, 1053, 1055, 1056, 1057, 1060, 1061, 1062,
                          1063],
        not_required={
            "GPT-6 Luna": dict(match=None, reason=(
                "not required (Ümit #5220); never scheduled: OpenAI Decisions out of credit (start.sh: deferred)")),
            "Mercury Decide": dict(match=1016, reason=(
                "not required (Ümit #5220); #1016 aborted at its start, no game: no OpenRouter endpoint for "
                "inception/mercury-decide")),
        },
        runner=RUNNER_GEMINI,
        original_runner=("two builds: dab6da5 (clean) for #993-#1013 and the aborted #1016 (every decision before "
                         "21:46:31Z), 38024d6 (clean; map-check v2) for #1053-#1063"),
        server=dict(kind="api", mib=0, start=None, stop=None, health=None,
                    smoke=("curl -fsS -m 20 https://openrouter.ai/api/v1/models/google/gemini-decision-1/endpoints | "
                           "python3 -c 'import json,sys; e=json.load(sys.stdin)[\"data\"][\"endpoints\"]; "
                           "ok=(len(e) == 1 and e[0][\"tag\"] == \"google-ai-studio\" and e[0][\"status\"] == 0 and "
                           "float(e[0][\"pricing\"][\"prompt\"]) == 1e-7 and "
                           "float(e[0][\"pricing\"][\"completion\"]) == 0); "
                           "print(\"listed as pinned: one endpoint google-ai-studio, up, $0.10/$0\" if ok else e); "
                           "sys.exit(not ok)'"),
                    provenance=("Google's Gemini Decision 1 through OpenRouter's System One route "
                                "(openrouter-decisions/google/gemini-decision-1; replies name "
                                "google/gemini-decision-1-20261111), provider pinned to google-ai-studio, fallbacks "
                                "off (players.settings request), OPENROUTER_API_KEY in ~/.keys; smoke = the "
                                "original's listed() check (one endpoint, Google AI Studio, up, $0.10/M input, $0 "
                                "output; listed so on 2026-11-12T13:00Z)"),
                    measured="none (hosted)"),
        settings_change=dict(),
        guard=GEMINI_GUARD,
        rules=dict(mirror_concurrent=True),
        cap_usd=round(GEMINI_CAP_USD - GEMINI_SPENT_USD, 4),
        cap_basis=(f"Gemini Decision 1's entry cap: ${GEMINI_CAP_USD:.2f} (entrant + paid opponents; "
                   "tools/v3/late-gemini-decision/start.sh), of which its guard recorded "
                   f"${GEMINI_SPENT_USD} at the entry's end (workspace/late-gemini-decision/state/guard.log, "
                   "2026-11-11T22:12:14Z; it billed every late-entry match from #993, other entries' paid opponents "
                   "included); the repeat's run guard (runner c13992f, `league --guard`) holds the entrant and the paid "
                   f"opponents to the remaining ${GEMINI_CAP_USD - GEMINI_SPENT_USD:.4f}: every request attempt is "
                   "reserved at its worst case in one ledger before it is sent and refused when it would pass the cap "
                   "(the runner refuses to send; run.sh's minute check of the ledger only reports and stops)."),
        cost_method=("Each playable pair's billed cost in the original match: the paid opponent's recorded cost_usd "
                     "(Fastino GLiDE: input tokens x $0.04/M), plus Gemini Decision 1's own recorded cost_usd "
                     "(OpenRouter usage.cost, $0.10/M input); local setups and programs bill nothing. Enforced in the "
                     "repeat by the run guard's ledger (spent + reserved in flight), not by stored turns."),
        server_starts="entrant: none (hosted); each local opponent 1-5 min (state logs of the originals)",
        opp_gpu=("<second card>", (
            "Gemini Decision 1 is hosted (no card of its own); its 8 local opponents run one at a time on a second "
            "card, OPP_GPU, with room for the largest (Clef, 53,144 MiB + 2,000), as in its original (bariton GPU 2, "
            "reservation r_82bfcd93782c).")),
        concurrency=("Name: '<original> [repeat 1]', a new players row; settings otherwise as the original's (the "
                     "changed fields are listed under Settings); one match at a time, as the original (start.sh, "
                     "max_matches 1)."),
        differences=[
            ("Runner: the original ran dab6da5 (clean) for its first stage (#993-#1013) and 38024d6 (clean; map-check "
             "v2 and the raw_entries decoder) for its local stage (#1053-#1063), both on origin/main's runner line "
             f"(ca112dc); the repeat runs {RUNNER_GEMINI['commit']} (branch pinned-late-gemini): the repeats' runner "
             f"{RUNNER['commit']} (late-reax line with the pinned-pairs change 4ca4f08 and admit) with those four "
             "runner commits cherry-picked (cb669a0) and the run guard (c13992f: reply identity and the shared "
             "pre-send cap, used with --guard only). late-reax adds decision clients (reax, baselabs, drex, nace) and "
             "a budget ledger, which the run guard uses; requests, sampling (provider defaults, nothing set), the "
             "prompt version, option-order seed and rules are the same."),
            ("Map check: map-check v2 (a probability map that is not exactly the shown ids, finite in [0, 1], summing "
             "to 1 within 1e-6, stores no probabilities; the returned choice is still played) applies to every "
             "repeat pair; the original's first-stage pairs (#993-#1013, dab6da5) ran without it. Plays are not "
             "affected; a first-stage pair can store probabilities in the original where the repeat stores none."),
            ("Hosted model: Gemini Decision 1 is served by Google AI Studio through OpenRouter. The repeat accepts a "
             "reply only when it names the original's served model google/gemini-decision-1-20261111 and provider "
             "Google AI Studio (as all 1,704 original decisions did); a model served under that same name but "
             "changed behind it cannot be detected from here."),
            ("Route check: the original's guard re-checked OpenRouter's listing every minute (3 failures stopped "
             "it); the repeat checks it once before the first match (smoke) and, in the runner (run guard), the served "
             "identity of every entrant reply: model google/gemini-decision-1-20261111 and provider Google AI Studio "
             "exactly, or the guard latches and the league stops for good. Fallbacks stay off."),
            ("Cap: the original's $5 entry cap with $1.1819 recorded (a minute poll of stored turns); the repeat's "
             "run guard holds the entrant and paid opponents to the remaining $3.8181 before every request attempt "
             "(see cost_basis)."),
        ]),
}
DISPLAY = {"mammoth-1-r1": "Mammoth-1", "drex-max-v1-r1": "Drex Max v1", "reax-1.3-r1": "REAX 1.3",
           "d1-ultra-r1": "Liquid d1-ultra", "drex-max-1.1-r1": "Drex Max 1.1",
           "glide-v1.2-r1": "Fastino GLiDE v1.2 (local)", "gemini-decision-1-r1": "Gemini Decision 1"}


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
        opp_billed = own_billed = None
        if opp in BILLED and theirs:
            opp_billed = (theirs["tokens"] or 0) * FASTINO_RATE / 1e6 if opp == "Fastino GLiDE" else theirs["cost"]
        if mine and r["server"]["kind"] == "api":
            own_billed = ((mine["tokens"] or 0) * ENTRANT_RATE[r["original"]] / 1e6 if r["original"] in ENTRANT_RATE
                          else mine["cost"])
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
                            original=round(own_billed, 4) if own_billed is not None else None),
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
            used=(f"Runner change on branch pinned-pairs, commit 4ca4f08 (Zeki #4710), run as {RUNNER['commit']} "
                  "(branch pinned-late-reax: the originals' runner line origin/late-reax with 4ca4f08 cherry-picked; "
                  "Zeki #4860, #4886): league config field "
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
        not_required = r.get("not_required", {})
        reasons = {x["opponent"]: x["reason"] for x in late if x["entrant"] == r["original"]}
        reasons |= {o: n["reason"] for o, n in not_required.items() if o not in reasons}
        playable = [p for p in pairs if p["status"] == "finished" and not p["blocked_today"]]
        dropped = [p["opponent"] for p in played if p["blocked_today"]]
        unpinned = [o for o in missing if o not in {p["opponent"] for p in pairs}]
        srv = r["server"]
        opps = [o for o in LOCAL if o != r["original"]]
        big = [o for o in opps if srv["mib"] + LOCAL[o][0] + MARGIN_MIB > GPU_MIB]
        rules = {k: v for k, v in pairs[0]["rules"].items()}
        for p in pairs:
            if p["rules"] != rules:
                sys.exit(f"{rid}: rules differ between its original matches (#{p['original_match']})")
        paid = [p for p in playable if p["billed_usd"]["opponent"] is not None or p["billed_usd"]["original"]]
        est_opp = sum(p["billed_usd"]["opponent"] or 0 for p in playable)
        est_own = sum(p["billed_usd"]["original"] or 0 for p in playable)
        mins = {k: round(sum(p["minutes"] or 0 for p in playable if p["kind"] == k), 1) for k in ("program", "api", "local")}
        out["repeats"].append(dict(
            id=rid, run_id=f"repeat-{r.get('prepared', '2026-11-11')}-{rid}", name=name, display=DISPLAY[rid],
            original=r["original"], original_player_id=row["id"], original_league=r["original_league"],
            original_stage=r["original_stage"], status=r.get("status", "queued"), hold=r.get("hold"),
            prepared=r.get("prepared", "2026-11-11"), started=None, finished=None,
            league_config=f"tools/v3/repeats/leagues/{rid}.json",
            status_file=f"mailbox/repeats/{rid} - status.md",
            runner=dict(r["runner"], original=r["original_runner"]),
            attempts=attempts(conn, rid),
            rules=dict(rules, mirror_concurrent=r["rules"]["mirror_concurrent"]),
            settings_original=settings, settings_repeat=rep, settings_changed=diff,
            server={k: v for k, v in srv.items() if k not in ("start", "stop", "health_any_status")}
            | dict(start=srv["start"], stop=srv["stop"]),
            coverage_original=dict(
                played=len(played), of=len(field),
                not_played=[dict(opponent=o, match=next((p["original_match"] for p in pairs if p["opponent"] == o),
                                                        not_required.get(o, {}).get("match")),
                                 reason=reasons.get(o, "no match")) for o in missing]),
            coverage_repeat_today=dict(
                playable=len(playable), of=len(field),
                blocked=[dict(opponent=p["opponent"], reason=p["blocked_today"]) for p in pairs if p["blocked_today"]
                         and p["status"] == "finished"],
                not_in_original=[dict(opponent=o, reason=reasons.get(o, "no original match"),
                                      today=BLOCKED_TODAY.get(o)) for o in missing],
                unpinned=unpinned),
            **({} if not not_required else dict(coverage_required=required_coverage(
                pairs, field, not_required, r["rules"]["mirror_concurrent"]))),
            **({} if not r.get("guard") else dict(guard=dict(
                r["guard"], file=f"tools/v3/repeats/guards/{rid}.json", cap_usd=r.get("cap_usd", 5.0),
                metered="the entrant and the paid opponents it is pinned against (BILLED); prices in the file",
                enforced=("runner `league --guard` (c13992f, src/guard.rs): every request attempt reserved before it "
                          "is sent, refused past the cap; every entrant reply's model and provider exactly the "
                          "expected ones; a stop latches (no request, no league start, check refuses)")))),
            cost_basis=dict(
                method=r.get("cost_method", (
                    "Each playable pair's billed cost in the original match: the paid opponent's recorded "
                    "cost_usd (Fastino GLiDE: input tokens x $0.04/M), plus Liquid d1-ultra's own cost_usd in its "
                    "repeat; local setups and programs bill nothing.")),
                pairs={p["opponent"]: p["billed_usd"] for p in paid},
                estimate_usd=round(est_opp + est_own, 4), opponents_usd=round(est_opp, 4), entrant_usd=round(est_own, 4),
                cap_usd=r.get("cap_usd", 5.0), **({"cap_basis": r["cap_basis"]} if "cap_basis" in r else {})),
            time=dict(
                method=("Sum of each playable pair's original match duration (start to finish; the originals ran "
                        "several matches at once, so one at a time is about this or less), plus server starts."),
                minutes_matches=mins, minutes_total_matches=round(sum(mins.values()), 1),
                server_starts=r.get("server_starts", (
                    "entrant: Mammoth-1 1-2 min, Drex Max v1 about 1 min, REAX 1.3 already up (logic), "
                    "d1-ultra none; each local opponent 1-5 min (state logs of the originals)"))),
            gpu_plan=dict(
                entrant_mib=srv["mib"], entrant_measured=srv["measured"],
                fits_beside_entrant=[o for o in opps if o not in big],
                needs_second_gpu=big,
                note=r["opp_gpu"][1] if "opp_gpu" in r else (
                    "One card: the entrant's server (none for d1-ultra) stays up for the whole repeat; the opponent "
                    "servers run one at a time beside it, smallest first. A pair needs both servers at once, so the "
                    "opponents in needs_second_gpu (entrant + opponent + 2 GB over 97,887 MiB) wait for a second "
                    "card (OPP_GPU) or stay unplayed.")),
            differences=[r.get("concurrency", (
                "Name: '<original> [repeat 1]', a new players row; settings otherwise as the original's (the "
                "changed fields are listed under Settings); one match at a time, where the original played "
                "several at once."))]
                        + r.get("differences", []) + (
                [f"Not replayable today, though played in the original: {', '.join(dropped)} (blockers today); "
                 "their seed pins are kept so they replay with the original seeds once unblocked."] if dropped else []),
            start=start_commands(rid),
            pairs=pairs))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"{MANIFEST.relative_to(REPO)}: {len(out['repeats'])} repeats")


def required_coverage(pairs: list[dict], field: list[str], not_required: dict, mirror: bool) -> dict:
    """Coverage over the required pairs (the field less not_required), each count separately: pairs the original
    played (history), pairs pinned (every pair in pairs is pinned: wanted_pins), pinned pairs playable today (not
    blocked), and matched fixtures: pinned pairs whose original finished match recorded its games' dice seeds and ran
    with the repeat's mirror rule (the other rules are one set across the originals, checked above; configs refuses a
    clock or another start), so the pin's seed and seating give the original's dice, seats and option orders."""
    required = [o for o in field if o not in not_required]
    mine = [p for p in pairs if p["opponent"] in required]
    played = [p["opponent"] for p in mine if p["status"] == "finished"]
    pinned = [p["opponent"] for p in mine]
    playable = [p["opponent"] for p in mine if p["status"] == "finished" and not p["blocked_today"]]
    matched = [p["opponent"] for p in mine if p["status"] == "finished" and p["games"]
               and all(g["dice_seed"] is not None for g in p["games"]) and p["rules"]["mirror_concurrent"] == mirror]
    return dict(
        rule="GPT-6 Luna and Mercury Decide pairs are not required (Ümit #5220)", required=len(required),
        history_played=len(played), pinned=len(pinned), playable_today=len(playable), matched_fixtures=len(matched),
        not_required=[dict(opponent=o, **n) for o, n in not_required.items()],
        missing=dict(history=[o for o in required if o not in played], pins=[o for o in required if o not in pinned],
                     today=[o for o in required if o not in playable], fixtures=[o for o in required if o not in matched]))


def start_commands(rid: str) -> list[str]:
    run = f"{HERE}/run.sh {rid}"
    unit = f"systemd-run --user --unit=repeat-{rid} --working-directory=/home/cbasaran/code/jevgammon"
    r = REPEATS[rid]
    opp = r["opp_gpu"][0] if "opp_gpu" in r else "0"
    gpu = {"ours": f"-E GPU=0 -E OPP_GPU={opp}", "logic": f"-E GPU=0 -E OPP_GPU={opp}",
           "api": f"-E OPP_GPU={opp}"}[r["server"]["kind"]]
    if r.get("status") == "held":
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
            note=(f"Reproducibility repeat 1 of {m['original']} ({REPEATS[rid].get('requested_by', WRITTEN_FOR)}, "
                  f"#4710; run {m['run_id']}): {m['name']} "
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
        guard = wanted_guard(conn, rid, m)
        if guard is not None:
            gpath = guard_path(rid)
            gpath.parent.mkdir(exist_ok=True)
            gpath.write_text(json.dumps(guard, indent=2, ensure_ascii=False) + "\n")
            print(f"{gpath.relative_to(REPO)}: run guard metering {', '.join(guard['metered'])} under "
                  f"${guard['cap_usd']}, reply identity of {', '.join(guard['expect_route'])}")


def guard_path(rid: str) -> Path | None:
    """The repeat's run guard file (`league --guard`), or None for a repeat without one."""
    return HERE / "guards" / f"{rid}.json" if REPEATS[rid].get("guard") else None


def guard_prices(name: str, settings: dict) -> dict:
    """A metered setup's list prices for the run guard: its settings' price (Fastino GLiDE records none: FASTINO_RATE,
    as every guard's estimate); cached input at the input price."""
    price = settings.get("price") or ({"input_per_mtok": FASTINO_RATE} if name == "Fastino GLiDE" else None)
    if not price:
        sys.exit(f"{name}: a paid setup without a price; the run guard cannot meter it")
    return dict(input_per_mtok=price["input_per_mtok"], cached_input_per_mtok=price["input_per_mtok"],
                output_per_mtok=price.get("output_per_mtok", 0.0))


def wanted_guard(conn, rid: str, m) -> dict | None:
    """The run guard the repeat must run under (src/guard.rs GuardConfig): its ledger, the manifest's cap and the latch
    file; metered: the entrant (its repeat settings' price) and every paid opponent it is pinned against (BILLED; prices
    from v3.db's players.settings); the entrant's expected reply identity."""
    g = REPEATS[rid].get("guard")
    if not g:
        return None
    metered = {m["name"]: guard_prices(m["name"], m["settings_repeat"])}
    for name in sorted(o for o in wanted_pins(m) if o in BILLED):
        row = conn.execute("SELECT settings FROM players WHERE name = ?", (name,)).fetchone()
        metered[name] = guard_prices(name, json.loads(row[0]))
    return dict(note=(f"Run guard of {m['name']} ({rid}; Zeki #5385; tools/v3/repeats repeats.py wanted_guard): "
                      "the entrant and its paid opponents under one pre-send cap; the entrant's reply identity "
                      "exact; a stop latches"),
                ledger=g["ledger"], cap_usd=m["cost_basis"]["cap_usd"], latch=g["latch"], metered=metered,
                expect_route={m["name"]: g["expect_route"]})


# The runner's budget ledger as Ledger::open leaves it (src/budget.rs SCHEMA; WAL; the cap row), for the preparation.
LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY CHECK (id = 1), cap_usd REAL NOT NULL);
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY, setup TEXT NOT NULL, pid INTEGER NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
    status TEXT NOT NULL, reserved_usd REAL NOT NULL, cost_usd REAL, list_cost_usd REAL, reported_cost_usd REAL,
    input_tokens INTEGER, cached_tokens INTEGER, output_tokens INTEGER, reasoning_tokens INTEGER, note TEXT);
"""
NO_LEDGER = "guard ledger missing: the preparation creates it (admission runs once it exists)"
# check's preparable failures: run.sh prepares exactly these (backup, ledger, trigger), then checks everything again.
PREPARABLE = {NOT_IN_TRIGGER, NO_LEDGER}


def prepare_ledger(guard: dict) -> None:
    """Creates the run guard's empty ledger (refused when it exists): as Ledger::open would, closed (checkpointed)."""
    path = Path(guard["ledger"])
    if path.exists():
        sys.exit(f"guard ledger {path} exists; not created again")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(LEDGER_SCHEMA)
    conn.execute("INSERT INTO budget (id, cap_usd) VALUES (1, ?)", (guard["cap_usd"],))
    conn.commit()
    conn.close()


def guard_committed(guard: dict) -> float:
    """Dollars the run guard's ledger holds against its cap: spent (settled, lost) plus reserved in flight (open)."""
    path = Path(guard["ledger"])
    if not path.exists():
        return 0.0
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
    return conn.execute("""SELECT COALESCE(SUM(CASE status WHEN 'settled' THEN cost_usd WHEN 'lost' THEN reserved_usd
                                                  WHEN 'open' THEN reserved_usd END), 0) FROM attempts""").fetchone()[0]


def shell_env(args) -> None:
    m = load()[args.id]
    s, r = REPEATS[args.id]["server"], m["runner"]
    gpath = guard_path(args.id)
    g = REPEATS[args.id].get("guard") or {}
    for k, v in dict(NAME=m["name"], RUN_ID=m["run_id"], KIND=s["kind"], BIN=r["binary"], ENTRANT_MIB=s["mib"],
                     START=s["start"] or "", STOP=s["stop"] or "", HEALTH=s["health"] or "",
                     HEALTH_ANY=int(bool(s.get("health_any_status"))), SMOKE=s["smoke"] or "",
                     STATUS=m["status_file"], CAP=m["cost_basis"]["cap_usd"], GUARD=gpath or "",
                     GUARD_LATCH=g.get("latch", "")).items():
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


def trigger_names(conn) -> list[str] | None:
    """The names the late_entry_stage trigger stages as late entries; None when v3.db has no such trigger."""
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = 'late_entry_stage'").fetchone()
    if not sql:
        return None
    return [n.replace("''", "'") for n in re.findall(r"'((?:[^']|'')*)'", TRIGGER.search(sql[0]).group(1))]


def sha256(path) -> str | None:
    try:
        with open(path, "rb") as f:
            return hashlib.file_digest(f, "sha256").hexdigest()
    except FileNotFoundError:
        return None


def runner_problems(rn) -> list[str]:
    """The runner is the reviewed build: its tree at exactly the recorded commit with src and every build input as
    committed (untracked files included), each input and the binary at their recorded sha256."""
    bad = []
    tree = Path(rn["tree"])
    git = lambda *a: subprocess.run(["git", "-C", str(tree), *a], capture_output=True, text=True)
    head = git("rev-parse", "HEAD").stdout.strip()
    if head != rn["commit_full"]:
        bad.append(f"runner tree {tree} is at {head[:7] or 'no commit'}, not {rn['commit']}")
    status = git("status", "--porcelain", "--untracked-files=all", "--", "src", *rn["inputs"])
    if status.returncode:
        bad.append(f"runner tree {tree}: git status failed ({status.stderr.strip()})")
    elif status.stdout.strip():
        bad.append(f"runner tree {tree} differs from {rn['commit']} in "
                   + ", ".join(line[3:] for line in status.stdout.splitlines()))
    for rel, want in rn["inputs"].items():
        got = sha256(tree / rel)
        if got != want:
            bad.append(f"build input {rel} " + ("missing" if got is None else f"has sha256 {got[:16]}…")
                       + f", recorded {want[:16]}…")
    got = sha256(rn["binary"])
    if got != rn["binary_sha256"]:
        bad.append(f"runner {rn['binary']} " + ("missing" if got is None else f"has sha256 {got[:16]}…")
                   + f", not the {rn['commit']} build {rn['binary_sha256'][:16]}…")
    elif not os.access(rn["binary"], os.X_OK):
        bad.append(f"runner {rn['binary']} is not executable")
    return bad


def settings_problems(conn, rid: str, m, cfg) -> list[str]:
    """The league config plays the manifest's repeat settings under the original's rules, the original's stored
    settings are the manifest's, and the repeat changes only its name, max_matches, note and its listed changes."""
    bad = []
    players = cfg.get("players") or [None]
    if players[0] != m["settings_repeat"]:
        bad.append("league config entrant settings differ from the manifest's settings_repeat")
    row = conn.execute("SELECT settings FROM players WHERE name = ?", (m["original"],)).fetchone()
    if row is None or json.loads(row[0]) != m["settings_original"]:
        bad.append(f"{m['original']}'s stored settings differ from the manifest's settings_original")
    orig, rep = m["settings_original"], m["settings_repeat"]
    allowed = {"name", "max_matches", "note"} | set(REPEATS[rid]["settings_change"])
    extra = sorted(k for k in set(orig) | set(rep) if orig.get(k) != rep.get(k) and k not in allowed)
    if extra:
        bad.append(f"repeat settings change {', '.join(extra)} beyond the listed changes")
    r = m["rules"]
    for k, v in dict(prompt_version=r["prompt_version"], order_seed=r["order_seed"], rounds=r["rounds"],
                     max_turns=r["max_turns"], mirror_concurrent=r["mirror_concurrent"], only_pairs_of=m["name"],
                     hidden=True).items():
        if cfg.get(k) != v:
            bad.append(f"league config {k} is {cfg.get(k)!r}, not {v!r}")
    if [p.get("name") for p in players[1:] if p] != PROGRAMS:
        bad.append(f"league config programs are not {', '.join(PROGRAMS)}")
    for p in players[1:]:
        row = conn.execute("SELECT settings FROM players WHERE name = ?", ((p or {}).get("name"),)).fetchone()
        if row is None or json.loads(row[0]) != p:
            bad.append(f"league config settings of {(p or {}).get('name')} differ from v3.db's")
    return bad


# The keys run.sh loads before the league (~/.keys; Celeris' key file when ~/.keys has none), so admission builds each
# client with the credentials the league will have.
KEYS = ('set -a; . ~/.keys; set +a; [[ -n ${CELERIS_API_KEY:-} ]] || '
        '{ CELERIS_API_KEY="$(cat ~/.config/celeris/key)"; export CELERIS_API_KEY; }; ')
ADMIT_TIMEOUT_S = 600
# The last line of a successful `jevgammon admit` (runner 0e66836): the settings it admitted, as JSON.
ADMITTED = "admitted-settings "


def admission_problems(rn, config: Path, guard: Path | None = None) -> tuple[list[str], dict | None]:
    """Client admission by the bound runner (Zeki #4860, #4896): `jevgammon admit --db DB --config <league config>`
    builds the client of every config player and of every opponent its pinned_pairs names (from players.settings), as
    the league builds them, but only decision services and the local engines (any other client type is refused before
    it is constructed); the database and every budget ledger are opened read-only and immutable and no request is
    sent, so admission writes nothing. A refused client, an error, no answer in ADMIT_TIMEOUT_S or no admitted-settings
    record is a problem; else the record (Zeki #4928): the config file's sha256, every client with its source and, for
    a pinned opponent, its players row and the sha256 of the settings text admitted. With a run guard (`--guard`, Zeki
    #5385) the metered clients are built with its ledger, a latched guard is refused, and the record names the guard
    file's sha256."""
    try:
        r = subprocess.run(["bash", "-c", KEYS + 'exec "$0" admit --db "$1" --config "$2" ${3:+--guard "$3"}',
                            rn["binary"], str(DB), str(config), str(guard or "")],
                           capture_output=True, text=True, timeout=ADMIT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return [f"client admission: jevgammon admit gave no answer in {ADMIT_TIMEOUT_S} s"], None
    if r.returncode == 0:
        records = [line[len(ADMITTED):] for line in r.stdout.splitlines() if line.startswith(ADMITTED)]
        try:
            (admitted,) = [json.loads(x) for x in records]
            if not (isinstance(admitted, dict) and isinstance(admitted.get("config_sha256"), str)
                    and isinstance(admitted.get("clients"), list) and all(isinstance(c, dict) for c in admitted["clients"])):
                raise ValueError("not a record of the config's sha256 and its clients")
        except ValueError as e:
            return [f"client admission: jevgammon admit gave no single admitted-settings record ({e})"], None
        return [], admitted
    why = [line.strip() for line in r.stdout.splitlines() if line.startswith("REFUSED")]
    why += [line.strip() for line in r.stderr.splitlines() if line.strip()]
    return [f"client admission refused (jevgammon admit exit {r.returncode}): " + " | ".join(why)], None


def binding_problems(conn, config: Path, admitted: dict, guard: Path | None = None) -> list[str]:
    """The settings admitted are the settings the league runs (Zeki #4928 S1). Admission reads v3.db immutably (its main
    file only: a change still in the write-ahead log, a new row or an UPDATE of an existing one, is not seen) and
    records what it admitted; conn is an ordinary read-only connection (write-ahead-log-aware: what league-add and the
    league read). The config file is the one admitted (sha256); the admitted clients are exactly the config's players
    and the other opponents its pinned_pairs names; each config player's v3.db row, once there, holds the config's
    settings (a league resumes its players from v3.db); each pinned opponent's row is the one admitted, its settings
    text of the admitted sha256 (the text league-add --entry passes and the league loads). With a run guard, the record
    names this guard file and its sha256 is the file's now (the league reads it at start). Any difference is a
    problem."""
    if guard is not None:
        g = admitted.get("guard") or {}
        now = sha256(guard)
        if g.get("path") != str(guard) or now is None or g.get("sha256") != now:
            return [f"run guard {guard} is not the one admitted (sha256 {str(now)[:16]}…, admitted "
                    f"{g.get('path')} {str(g.get('sha256'))[:16]}…)"]
    try:
        data = config.read_bytes()
    except OSError as e:
        return [f"league config {config} unreadable: {e}"]
    got = hashlib.sha256(data).hexdigest()
    if got != admitted.get("config_sha256"):
        return [f"league config {config} is not the one admitted (sha256 {got[:16]}…, admitted "
                f"{str(admitted.get('config_sha256'))[:16]}…)"]
    cfg = json.loads(data)
    players = {p["name"]: p for p in cfg.get("players") or []}
    pinned = sorted(n for n in cfg.get("pinned_pairs") or {} if n not in players)
    clients = admitted.get("clients") or []
    bad = []
    if ([c.get("name") for c in clients if c.get("source") == "league config"] != list(players)
            or sorted(c.get("name") for c in clients if c.get("source") != "league config") != pinned):
        bad.append("the admitted clients are not the league config's players and pinned opponents")
    for c in clients:
        row = conn.execute("SELECT id, settings FROM players WHERE name = ?", (c.get("name"),)).fetchone()
        if c.get("source") == "league config":
            try:
                same = row is None or json.loads(row[1]) == players.get(c.get("name"))
            except (TypeError, ValueError):
                same = False
            if not same:
                bad.append(f"{c.get('name')}: v3.db's settings (players #{row[0]}) are not the league config's, "
                           "which were admitted")
        elif row is None:
            bad.append(f"{c.get('name')}: no players row in v3.db now (admitted players #{c.get('player_id')})")
        else:
            now = hashlib.sha256(row[1].encode()).hexdigest() if isinstance(row[1], str) else "not text"
            if row[0] != c.get("player_id") or now != c.get("settings_sha256"):
                bad.append(f"{c.get('name')}: v3.db's settings now (players #{row[0]}, sha256 {now[:16]}…) are not "
                           f"the ones admitted (players #{c.get('player_id')}, sha256 "
                           f"{str(c.get('settings_sha256'))[:16]}…)")
    return bad


def problems(rid: str, admitted: dict | None = None) -> list[str]:
    """Everything check verifies, read-only; NOT_IN_TRIGGER stands for the trigger lacking the name, NO_LEDGER for a run
    guard's ledger not yet created (admission then waits for it). When everything from admission on passes, admitted
    (if given) receives the admitted-settings record."""
    m = load()[rid]
    conn = ro()
    bad = []
    if m["status"] == "held" or REPEATS[rid].get("status") == "held":
        bad.append(f"held: {m['hold'] or REPEATS[rid].get('hold')}")
    path = HERE / "leagues" / f"{rid}.json"
    cfg = json.loads(path.read_text()) if path.exists() else {}
    if not cfg:
        bad.append(f"no league config {path}")
    want = wanted_pins(m)
    if cfg.get("pinned_pairs") != want:
        bad.append("league config pins differ from the manifest's original seeds and seats")
    bad += attempt_problems(conn, rid, want)
    lid = league_id(conn, rid)
    if lid is not None:
        stored = conn.execute("SELECT pinned_pairs FROM leagues WHERE id = ?", (lid,)).fetchone()[0]
        if json.loads(stored or "{}") != want:
            bad.append(f"league #{lid} holds other pins")
    bad += settings_problems(conn, rid, m, cfg)
    held = json.loads(subprocess.run(["git", "-C", str(MAIN), "show", "HEAD:tools/site/content/held_setups.json"],
                                     capture_output=True, text=True).stdout or "{}").get("held", {})
    if m["name"] not in held:
        bad.append("not held in the main checkout's committed tools/site/content/held_setups.json")
    rb = runner_problems(m["runner"])
    bad += rb
    gpath = guard_path(rid)
    ledger_ok = True
    if gpath is not None:  # the run guard (Zeki #5385): exactly the wanted one, not latched, its ledger present
        want_guard = wanted_guard(conn, rid, m)
        got_guard = json.loads(gpath.read_text()) if gpath.exists() else None
        if got_guard != want_guard:
            bad.append(f"run guard {gpath} differs from the repeat's (or is missing)")
        latch = Path(want_guard["latch"])
        if latch.exists():
            bad.append(f"run guard latched ({latch}): {latch.read_text(errors='replace').strip()[:300]}")
        ledger_ok = Path(want_guard["ledger"]).exists()
        if not ledger_ok:
            bad.append(NO_LEDGER)
    if not rb and cfg and ledger_ok:  # only the bound binary is executed
        refused, record = admission_problems(m["runner"], path, gpath)
        bad += refused
        if record is not None:
            differ = binding_problems(conn, path, record, gpath)
            bad += differ
            if not differ and admitted is not None:
                admitted.update(record)
    names = trigger_names(conn)
    if names is None:
        bad.append("v3.db has no late_entry_stage trigger")
    elif m["name"] not in names:
        bad.append(NOT_IN_TRIGGER)
    return bad


def check(args) -> None:
    """Fail closed (read-only): a held repeat, other pins or settings, the name not held on the site, another runner
    binary, commit, src or build input, another or a latched run guard, a client the bound runner's `admit` refuses,
    admitted settings other than v3.db holds now (binding_problems) exit 1; when the only failures are preparable (the
    trigger lacking the name, a run guard's ledger not yet created), exits TRIGGER_MISSING (3), the condition run.sh
    prepares. On success the last line is the admitted-settings record (ADMITTED + JSON), which run.sh keeps for `bound`
    and `entry`."""
    admitted = {}
    bad = problems(args.id, admitted)
    if bad and set(bad) <= PREPARABLE:
        print(f"{args.id}: {'; '.join(bad)} (everything else passes)", file=sys.stderr)
        sys.exit(TRIGGER_MISSING)
    if bad:
        print(f"{args.id}: " + "; ".join(bad), file=sys.stderr)
        sys.exit(1)
    m = load()[args.id]
    rn = m["runner"]
    print(f"{args.id}: {len(wanted_pins(m))} pairs pinned in its config, settings as the manifest's, trigger and held "
          f"name in place, runner {rn['commit']} (binary sha256 {rn['binary_sha256'][:16]}…, "
          f"{len(rn['inputs'])} build inputs as recorded, tree {rn['tree']}), every client admitted (jevgammon admit), "
          f"the {len(admitted['clients'])} admitted settings those v3.db holds"
          + (f"; run guard {admitted['guard']['path']} (sha256 {admitted['guard']['sha256'][:16]}…) admitted, its "
             "ledger present, not latched" if admitted.get("guard") else ""))
    print(ADMITTED + json.dumps(admitted, ensure_ascii=False))


def read_admitted(rid: str, path: str) -> dict:
    try:
        admitted = json.loads(Path(path).read_text())
        if not (isinstance(admitted, dict) and isinstance(admitted.get("clients"), list)
                and all(isinstance(c, dict) for c in admitted["clients"])):
            raise ValueError("not an admitted-settings record")
        return admitted
    except (OSError, ValueError) as e:
        sys.exit(f"{rid}: refused: no admitted-settings record in {path} ({e})")


def bound(args) -> None:
    """Before the league starts (run_league.sh; read-only): the settings it will read are the ones check admitted
    (binding_problems against the record run.sh kept); exit 1 on any difference."""
    bad = binding_problems(ro(), HERE / "leagues" / f"{args.id}.json", read_admitted(args.id, args.admitted),
                           guard_path(args.id))
    if bad:
        sys.exit(f"{args.id}: refused, not the admitted settings: " + "; ".join(bad))
    print(f"{args.id}: the league config and v3.db's settings are the admitted ones")


def entry(args) -> None:
    """league-add --entry for a pinned opponent (read-only): its players.settings text, printed only when everything is
    as admitted (binding_problems) and the text printed is the one admitted (sha256); exit 1 otherwise."""
    admitted = read_admitted(args.id, args.admitted)
    conn = ro()
    bad = binding_problems(conn, HERE / "leagues" / f"{args.id}.json", admitted, guard_path(args.id))
    if bad:
        sys.exit(f"{args.id}: refused, not the admitted settings: " + "; ".join(bad))
    c = next((c for c in admitted["clients"] if c["name"] == args.name and c["source"] != "league config"), None)
    row = conn.execute("SELECT id, settings FROM players WHERE name = ?", (args.name,)).fetchone()
    if (c is None or row is None or row[0] != c["player_id"] or not isinstance(row[1], str)
            or hashlib.sha256(row[1].encode()).hexdigest() != c["settings_sha256"]):
        sys.exit(f"{args.id}: refused: {args.name}'s settings are not an admitted pinned opponent's")
    print(row[1])


def trigger(args) -> None:
    """The preparation (run.sh, after a verified backup): refused unless check's only failures are preparable; creates a
    run guard's empty ledger when it is missing, then adds the repeat name to the late_entry_stage trigger."""
    bad = problems(args.id)
    if bad and not set(bad) <= PREPARABLE:
        sys.exit(f"{args.id}: trigger refused, the check fails beyond the trigger: " + "; ".join(bad))
    if NO_LEDGER in bad:
        read = ro()
        guard = wanted_guard(read, args.id, load()[args.id])
        read.close()  # no reader left open: the trigger's write below is checkpointed into v3.db when it closes
        prepare_ledger(guard)
        print(f"run guard ledger {guard['ledger']} created (cap ${guard['cap_usd']}, empty)")
    name = load()[args.id]["name"]
    conn = sqlite3.connect(f"file:{DB}?mode=rw", uri=True, timeout=120)
    conn.execute("BEGIN IMMEDIATE")
    names = trigger_names(conn)
    if names is None:
        sys.exit("v3.db has no late_entry_stage trigger")
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


def league_id(conn, rid: str):
    """The repeat's current league: the newest one playing only its pairs, a recorded attempt's league never."""
    skip = [a["league"] for a in REPEATS[rid].get("attempts", [])]
    row = conn.execute(f"""SELECT id FROM leagues WHERE only_pairs_of = ? AND id NOT IN ({",".join("?" * len(skip))})
                           ORDER BY id DESC LIMIT 1""", (repeat_name(rid), *skip)).fetchone()
    return row[0] if row else None


def attempt_problems(conn, rid: str, want: dict) -> list[str]:
    """Each recorded attempt's league is exactly as recorded (Zeki #4886, #4928 L1, #4954): its leagues row, every column
    (a column added, missing or of another value or type differs); the league_players table's columns exactly the
    recorded ones, in order (any other column set, e.g. an added `name`, differs); the league's league_players rows,
    read by an explicit projection of the recorded columns plus the joined players.name as player_name (no two labels
    alike, so no column can shadow another), every field compared, in id order (a process resuming, completing or
    editing it, or any other change, differs); its repeat name and pins as the config's."""
    def shown(v):
        return repr(v) if len(repr(v)) <= 80 else repr(v)[:77] + "..."

    def differences(prefix: str, got: dict, rec: dict) -> list[str]:
        none = "(no column)"
        return [f"{prefix}{k} {shown(got.get(k, none))} (recorded {shown(rec.get(k, none))})"
                for k in [*rec, *(k for k in got if k not in rec)]
                if k not in got or k not in rec or got[k] != rec[k] or type(got[k]) is not type(rec[k])]
    bad = []
    for a in REPEATS[rid].get("attempts", []):
        row = conn.execute("SELECT * FROM leagues WHERE id = ?", (a["league"],)).fetchone()
        if row is None:
            bad.append(f"attempt league #{a['league']} is missing")
            continue
        league, rec = dict(row), a["record"]
        changed = differences("", league, rec["league"])
        columns = [k for k in rec["participants"][0] if k != "player_name"]
        table = [r[1] for r in conn.execute("SELECT * FROM pragma_table_info('league_players')")]
        if table != columns:
            changed.append(f"league_players columns {table} (recorded {columns})")
        players = []
        if set(columns) <= set(table):  # the recorded fields are still compared when a column is added
            players = [dict(r) for r in conn.execute(
                f"""SELECT {", ".join('lp."' + c.replace('"', '""') + '"' for c in columns)}, p.name AS player_name
                    FROM league_players lp LEFT JOIN players p ON p.id = lp.player_id
                    WHERE lp.league_id = ? ORDER BY lp.id""", (a["league"],))]
        for i in range(max(len(players), len(rec["participants"]))):
            got = players[i] if i < len(players) else None
            was = rec["participants"][i] if i < len(rec["participants"]) else None
            if got is None or was is None:
                changed.append(f"league_players row {shown(got)} (recorded {shown(was)})")
            else:
                changed += differences(f"league_players #{was['id']} ", got, was)
        if changed:
            bad.append(f"attempt league #{a['league']} changed: " + "; ".join(changed))
        if league.get("only_pairs_of") != repeat_name(rid):
            bad.append(f"attempt league #{a['league']} plays {league.get('only_pairs_of')!r}, not {repeat_name(rid)!r}")
        if json.loads(league.get("pinned_pairs") or "{}") != want:
            bad.append(f"attempt league #{a['league']} holds other pins")
    return bad


def attempts(conn, rid: str) -> list[dict]:
    """The repeat's recorded attempts, then the current one (its league once created, else None)."""
    rn = REPEATS[rid]["runner"]
    current = dict(league=league_id(conn, rid), runner=dict(commit=rn["commit"], commit_full=rn["commit_full"],
                                                             binary_sha256=rn["binary_sha256"]))
    return REPEATS[rid].get("attempts", []) + [current]


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
    """Dollars the repeat has billed: under a run guard its ledger's spent plus reserved in flight (every request
    attempt of the entrant and the paid opponents, Zeki #5385); otherwise the stored turns' costs."""
    guard = REPEATS[m["id"]].get("guard")
    if guard:
        return guard_committed(guard)
    total = 0.0
    for r in conn.execute(
            """SELECT p.name, SUM(COALESCE(t.cost_usd, 0)) AS cost, SUM(t.input_tokens) AS tokens FROM turns t
               JOIN games g ON g.id = t.game_id JOIN matches m ON m.id = g.match_id
               JOIN players p ON p.id = CASE t.player WHEN 1 THEN m.player1 ELSE m.player2 END
               JOIN players a ON a.id = m.player1 JOIN players b ON b.id = m.player2
               WHERE m.stage = 'late-entry' AND ? IN (a.name, b.name) GROUP BY p.name""", (m["name"],)):
        if r["name"] == "Fastino GLiDE":
            total += (r["tokens"] or 0) * FASTINO_RATE / 1e6
        elif r["name"] == m["name"] and m["original"] in ENTRANT_RATE:
            total += (r["tokens"] or 0) * ENTRANT_RATE[m["original"]] / 1e6
        elif r["name"] in BILLED or (r["name"] == m["name"] and m["server"]["kind"] == "api"):
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
        lid = league_id(conn, rid)
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
    p.set_defaults(fn=lambda a: print(league_id(ro(), a.id) or ""))
    p = sub.add_parser("pending")
    p.add_argument("id", choices=list(REPEATS))
    p.add_argument("opponents", nargs="*")
    p.set_defaults(fn=pending)
    p = sub.add_parser("bound")
    p.add_argument("id", choices=list(REPEATS))
    p.add_argument("admitted", help="check's admitted-settings record (JSON file)")
    p.set_defaults(fn=bound)
    p = sub.add_parser("entry")
    p.add_argument("id", choices=list(REPEATS))
    p.add_argument("name", help="a pinned opponent")
    p.add_argument("admitted", help="check's admitted-settings record (JSON file)")
    p.set_defaults(fn=entry)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
