#!/usr/bin/env python3
"""Builds the backgammon benchmark site (preview) from the data files, then checks it.

    python3 tools/site/build.py --state ~/.local/state/bg-site --out OUT_DIR [--no-image]

Inputs (nothing else): STATE/snap.db (league snapshot, tools/site/snapshot.py), STATE/plays/s*.db (GNUbg
scores of every legal play, tools/site/score_plays.py), STATE/prompts.db (what each model was sent),
replay.db + positions/v1.jsonl (earlier-version v1 set), positions/*.jsonl + positions/build-log.json
(shared positions), smoke/part-a.json (smoke tests), tools/site/content/*.json (thresholds, setups
metadata, human scale, analysis status, method experiments) and the archived sections of the earlier
page (tools/site/content/archive/).

Output OUT: every page, the data files under data/ (split per version, league and model), the decision
files under decisions/ and the link preview image under share/. Every number on a page comes from the
dicts that are also written to data/; tools/site/checks.py then checks the build (numbers trace to
data files, counts add up, no mixing of leagues or versions, no banned strings, links resolve).
Exit status 0 = built and checked; 2 = a check failed (details in OUT/../site-check-failures.json).
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analysis as A  # noqa: E402
import checks  # noqa: E402
import pages  # noqa: E402
from common import CONTENT, EARLIER, PENDING, PROVISIONAL, PUBLISHED, ROOT, SITE, THRESHOLDS  # noqa: E402

BASE = "https://zekiworks.github.io/analysis/backgammon-preview/"


def load_setups() -> dict:
    data = json.loads((CONTENT / "setups.json").read_text())
    return {(s["dataset"], s["name"]): s for s in data["setups"]}


def snapshot_time(snap: Path) -> str:
    return datetime.fromtimestamp(snap.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def write_json(out: Path, rel: str, obj) -> None:
    path = out / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def results_hash(out: Path) -> str:
    """sha256 over every data file (data/ and decisions/) except the manifest, in path order: first 8 hex."""
    h = hashlib.sha256()
    for path in sorted(list((out / "data").rglob("*")) + list((out / "decisions").rglob("*"))):
        if path.is_file() and path.name != "manifest.json":
            h.update(str(path.relative_to(out)).encode())
            h.update(path.read_bytes())
    return h.hexdigest()[:8]


def compute(args) -> dict:
    """Every number of the site, from the data files."""
    state = Path(args.state).expanduser()
    snap = state / "snap.db"
    L = A.load_leagues(snap, state / "plays")
    setups = load_setups()
    leagues = []
    for lg in L["leagues"]:
        names = lg["names"]
        summary = A.dataset_summary(lg["dataset"], lg["decisions"], names)
        leagues.append(dict(
            id=lg["id"], dataset=lg["dataset"], version="v3", status=lg["status_label"], state=lg["state"],
            metric_status=lg["metric_status"], matches=lg["fixtures"], matches_done=lg["done"], games=lg["games"],
            started=lg["started"], finished=lg["finished"],
            decisions=len(lg["decisions"]), scored=sum(1 for d in lg["decisions"] if d["scored"]),
            standings=[dict(place=i, name=t["name"], played=t["played"], won=t["won"], drawn=t["drawn"],
                            lost=t["lost"], points=t["points"], games_won=t["gw"], games_lost=t["gl"],
                            gammons_won=lg["gammons"].get(t["name"], 0), to_play=lg["left"].get(t["name"], 0))
                       for i, t in enumerate(lg["table"], 1)],
            setups=summary))
    v1 = A.load_v1(ROOT / "replay.db", ROOT / "positions/v1.jsonl")
    v1_summary = A.dataset_summary("v1-set", v1["decisions"], v1["setups"])
    per = {}
    for d in v1["decisions"]:
        per.setdefault(d["setup"], []).append(d)
    pairs = {}
    for i, a in enumerate(v1["setups"]):
        for b in v1["setups"][i + 1:]:
            p = A.paired(per[a], per[b], f"v1/{a}/{b}")
            pairs[f"{a}\u2192{b}"] = dict(a=a, b=b, **p)
    low_q = v1_summary["DeepSeek V4.1 Flash"]["quality"]
    high_q = v1_summary["DeepSeek V4.1 Flash (thinking)"]["quality"]
    reasoning_v1 = [dict(model="DeepSeek V4.1 Flash", low="DeepSeek V4.1 Flash", high="DeepSeek V4.1 Flash (thinking)",
                         extra_time_median=high_q["time_median"] - low_q["time_median"], extra_cost=None,
                         **pairs["DeepSeek V4.1 Flash\u2192DeepSeek V4.1 Flash (thinking)"])]
    play_order = pairs["Gemini 4 Argon\u2192Gemini 4 Argon (shuffled)"]
    smoke = json.loads((ROOT / "smoke/part-a.json").read_text())
    shared = A.shared_sets(ROOT)
    return dict(
        as_of=snapshot_time(snap), last_move=L["last_move"], leagues=leagues, setups_meta=setups,
        v1=dict(dataset="v1-set", version="v1", status=EARLIER, positions=len(v1["positions"]),
                decisions=len(v1["decisions"]), setups=v1_summary, choice_only=sorted(v1["choice_only"]),
                pairs=pairs, reasoning=reasoning_v1,
                play_order=dict(setup="Gemini 4 Argon", diff=play_order["diff"], lo=play_order["lo"],
                                hi=play_order["hi"], positions=play_order["positions"]),
                disagreements=A.disagreements(v1)),
        smoke=smoke, shared=shared, thresholds=THRESHOLDS,
        status=json.loads((CONTENT / "analysis_status.json").read_text()),
        human_scale=json.loads((CONTENT / "human_scale.json").read_text()),
        _v1_raw=v1, _state=state)


def write_data(S: dict, out: Path) -> None:
    """The data files: per version, league and model; small enough for a phone."""
    if (out / "data").exists():
        shutil.rmtree(out / "data")
    files = []
    for lg in S["leagues"]:
        head = {k: v for k, v in lg.items() if k != "setups"}
        head["setups"] = {n: dict(slug=s["slug"], quality=s["quality"], risk={k: v for k, v in s["risk"].items()
                                                                               if k != "phases"})
                          for n, s in lg["setups"].items()}
        write_json(out, f"data/v3/{lg['dataset']}.json", head)
        files.append(f"data/v3/{lg['dataset']}.json")
        for n, s in lg["setups"].items():
            rel = f"data/v3/{lg['dataset']}/{s['slug']}.json"
            write_json(out, rel, dict(dataset=lg["dataset"], version="v3", status=lg["metric_status"], **s))
    v1 = S["v1"]
    write_json(out, "data/v1/v1-set.json", dict(
        {k: v for k, v in v1.items() if k not in ("setups", "pairs", "disagreements")},
        setups={n: dict(slug=s["slug"], quality=s["quality"], risk={k: v for k, v in s["risk"].items() if k != "phases"})
                for n, s in v1["setups"].items()}))
    for n, s in v1["setups"].items():
        write_json(out, f"data/v1/v1-set/{s['slug']}.json", dict(dataset="v1-set", version="v1", status=EARLIER, **s))
    write_json(out, "data/v1/compare.json", dict(dataset="v1-set", version="v1", status=EARLIER, pairs=v1["pairs"]))
    write_json(out, "data/v1/disagreements.json", dict(dataset="v1-set", version="v1", status=EARLIER,
                                                         **v1["disagreements"]))
    write_json(out, "data/v3/shared.json", dict(version="v3", status=PENDING, **S["shared"]))
    write_json(out, "data/smoke/part-a.json", dict(dataset="smoke-part-a", status="Smoke test", rows=S["smoke"]))
    write_json(out, "data/setups.json", dict(setups=[v for v in S["setups_meta"].values()]))
    write_json(out, "data/thresholds.json", S["thresholds"])
    write_json(out, "data/analysis-status.json", S["status"])
    write_json(out, "data/human-scale.json", S["human_scale"])
    write_json(out, "data/v3/summary.json", dict(
        version="v3", note="Counts only; league numbers are never merged into one score.",
        leagues=len(S["leagues"]), league_setups=sum(len(lg["setups"]) for lg in S["leagues"]),
        league_decisions=sum(lg["decisions"] for lg in S["leagues"]),
        league_decisions_scored=sum(lg["scored"] for lg in S["leagues"])))


def manifest(S: dict, out: Path) -> None:
    files = []
    for path in sorted((out / "data").rglob("*.json")):
        if path.name == "manifest.json":
            continue
        files.append(dict(path=str(path.relative_to(out)), bytes=path.stat().st_size,
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    write_json(out, "data/manifest.json", dict(results=S["hash"], data_as_of=S["as_of"], files=files,
                                               decisions_files=S["decision_files"]))


def preview_image(S: dict, out: Path) -> str | None:
    """The link preview (1200 x 630) drawn from the current results by headless Chrome; file name carries its hash."""
    html = pages.share_card(S)
    share = out / "share"
    share.mkdir(exist_ok=True)
    key = hashlib.sha256(html.encode()).hexdigest()[:8]
    name = f"share/preview-{key}.png"
    if (out / name).exists():
        return name
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "card.html"
        src.write_text(html)
        shot = Path(tmp) / "card.png"
        r = subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                            "--window-size=1200,630", f"--screenshot={shot}", src.as_uri()],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not shot.exists():
            print("preview image failed:", r.stderr[-500:], file=sys.stderr)
            return None
        for old in share.glob("preview-*.png"):
            old.unlink()
        shutil.copy(shot, out / name)
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="~/.local/state/bg-site")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-image", action="store_true")
    args = ap.parse_args()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    S = compute(args)
    write_data(S, out)
    import decisions_export
    datasets = [dict(id=lg["dataset"], label=f"League {lg['id']}", version="v3", league_id=lg["id"],
                     status=PUBLISHED if lg["metric_status"] == PUBLISHED else PROVISIONAL)
                for lg in S["leagues"]]
    datasets.append(dict(id="v1-set", label=f"v1 set ({S['v1']['positions']:,} positions)", version="v1",
                         status=EARLIER, note=pages.play_order_note(S)))
    if (out / "decisions").exists():
        shutil.rmtree(out / "decisions")
    S["decisions_export"] = decisions_export.export(
        out, S["_state"] / "snap.db", S["_state"] / "plays", S["_state"] / "prompts.db", ROOT / "replay.db",
        ROOT / "positions/v1.jsonl", datasets)
    S["decision_files"] = sum(1 for p in (out / "decisions").rglob("*") if p.is_file())
    S["hash"] = results_hash(out)
    manifest(S, out)
    S["image"] = None if args.no_image else preview_image(S, out)
    if S["image"] is None:
        old = sorted((out / "share").glob("preview-*.png")) if (out / "share").exists() else []
        S["image"] = f"share/{old[0].name}" if old else None
    for name in ("site.css", "site.js", "bg.css", "bg.js", "decisions.css", "decisions.js"):
        if (SITE / "assets" / name).exists():
            shutil.copy(SITE / "assets" / name, out / name)
    pages.write_all(S, out, BASE)
    failures = checks.run(S, out)
    report = S["_state"] / "site-check-failures.json"
    if failures:
        report.write_text(json.dumps(dict(as_of=S["as_of"], results=S["hash"], failures=failures), indent=1))
        print(f"CHECKS FAILED: {len(failures)}", file=sys.stderr)
        for f in failures[:40]:
            print(" -", f, file=sys.stderr)
        sys.exit(2)
    report.unlink(missing_ok=True)
    print(json.dumps(dict(results=S["hash"], data_as_of=S["as_of"], decision_files=S["decision_files"],
                          scored={lg["dataset"]: lg["scored"] for lg in S["leagues"]})))


if __name__ == "__main__":
    main()
