#!/usr/bin/env python3
"""Builds the backgammon benchmark site (https://zekiworks.github.io/analysis/backgammon/) from the data files, then checks it.

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
import close_choices as CC  # noqa: E402
import offline as O  # noqa: E402
import pages  # noqa: E402
from common import (CONTENT, EARLIER, INTERNAL, PENDING, PROVISIONAL, PUBLISHED, ROOT, SITE, THRESHOLDS,  # noqa: E402
                    aliases, relabel, setup_slug)

BASE = "https://zekiworks.github.io/analysis/backgammon/"


def load_setups() -> dict:
    """Setup metadata keyed by (dataset, name the data uses): a renamed league setup is listed under its shown name
    (content/labels.json) and keyed by its old name, the one the databases and the computation use."""
    data = json.loads((CONTENT / "setups.json").read_text())
    out = {}
    for s in data["setups"]:
        if s["dataset"].startswith("league-") and aliases(s["name"]):
            s = dict(s, aliases=aliases(s["name"]))
            out[(s["dataset"], INTERNAL[s["name"]])] = s
        else:
            out[(s["dataset"], s["name"])] = s
    return out


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
    audit = O.load_audit()
    boots = {}
    close_records = {}
    for lg in L["leagues"]:
        names = lg["names"]
        summary = A.dataset_summary(lg["dataset"], lg["decisions"], names)
        offline = O.league(lg, {n: m for (d, n), m in setups.items() if d == lg["dataset"]}, audit)
        boots[lg["dataset"]] = offline.pop("_boot")
        # Close choices (Method spec 2026-10-24 §9): per setup, and per decision for Every decision.
        close = CC.league(lg, audit, state / "plays")
        close_records.update(close["records"])
        for n, s in summary.items():
            s["close"] = close["setups"].get(n)
        leagues.append(dict(
            id=lg["id"], dataset=lg["dataset"], version="v3", status=lg["status_label"], state=lg["state"],
            metric_status=lg["metric_status"], matches=lg["fixtures"], matches_done=lg["done"], games=lg["games"],
            started=lg["started"], finished=lg["finished"],
            decisions=len(lg["decisions"]), scored=sum(1 for d in lg["decisions"] if d["scored"]),
            matches_list=lg["matches_list"],
            standings=[dict(place=t["place"], name=t["name"], played=t["played"], won=t["won"], drawn=t["drawn"],
                            lost=t["lost"], points=t["points"], games_won=t["gw"], games_lost=t["gl"],
                            gammons_won=lg["gammons"].get(t["name"], 0), to_play=lg["left"].get(t["name"], 0))
                       for t in lg["table"]],
            setups=summary, references=A.references(lg["dataset"], lg["decisions"], names), offline=offline))
    hypothesis = O.hypothesis([(lg["dataset"], lg["offline"]) for lg in leagues], boots)
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
    # Stats strip and subtitle: model setups and models in the leagues (programs left out), from setups metadata.
    programs = {k for k, m in setups.items() if m.get("model_type") == "program"}
    model_setups = sorted({(lg["dataset"], n) for lg in leagues for n in lg["setups"]} - programs)
    counts = dict(model_setups=len(model_setups),
                  models=len({setups[k]["model"] if k in setups else k[1] for k in model_setups}),
                  leagues=len(leagues), decisions_scored=sum(lg["scored"] for lg in leagues))
    for lg in leagues:
        lg["reasoning"] = league_reasoning(lg, setups, programs)
        # League winners · match results (B4): the league's first place once it finished; never a ranking.
        lg["winner"] = lg["standings"][0]["name"] if lg["state"] == "finished" and lg["standings"] else None
    return dict(
        as_of=snapshot_time(snap), last_move=L["last_move"], leagues=leagues, setups_meta=setups,
        v1=dict(dataset="v1-set", version="v1", status=EARLIER, positions=len(v1["positions"]),
                decisions=len(v1["decisions"]), setups=v1_summary, choice_only=sorted(v1["choice_only"]),
                pairs=pairs, reasoning=reasoning_v1,
                play_order=dict(setup="Gemini 4 Argon", diff=play_order["diff"], lo=play_order["lo"],
                                hi=play_order["hi"], positions=play_order["positions"]),
                disagreements=A.disagreements(v1)),
        smoke=smoke, shared=shared, thresholds=THRESHOLDS, counts=counts, hypothesis=hypothesis,
        close_spec=dict(fixed_on=CC.CC["fixed_on"], definition=CC.DEFINITION, label=CC.LABEL), _close=close_records,
        close_b=json.loads((CONTENT / "close_choices_b_results.json").read_text()),
        status=json.loads((CONTENT / "analysis_status.json").read_text()),
        human_scale=json.loads((CONTENT / "human_scale.json").read_text()),
        _v1_raw=v1, _state=state)


def league_reasoning(lg: dict, setups: dict, programs: set) -> list[dict]:
    """One model at two reasoning settings inside one league. League games are not the same positions, so this is
    not paired and gets no verdict label (B9): 'lower/higher error rate in league play' when the two 95% intervals
    do not overlap, otherwise 'no clear difference in league play'."""
    by_model = {}
    for n, s in lg["setups"].items():
        m = setups.get((lg["dataset"], n))
        if (lg["dataset"], n) in programs or not m or not m.get("setting"):
            continue
        by_model.setdefault(m["model"], []).append((m["setting"], n, s["quality"]))
    order = {"off": 0, "low": 1, "on": 2, "medium": 2, "high": 3, "xhigh": 4, "max": 5}
    out = []
    for model, rows in sorted(by_model.items()):
        if len(rows) != 2:
            continue
        (sa, na, qa), (sb, nb, qb) = sorted(rows, key=lambda r: order.get(r[0], 9))
        if None in (qa.get("error_rate"), qb.get("error_rate")) or qa.get("too_few") or qb.get("too_few"):
            reading = None
        elif qb["error_hi"] < qa["error_lo"]:
            reading = "lower error rate in league play"
        elif qb["error_lo"] > qa["error_hi"]:
            reading = "higher error rate in league play"
        else:
            reading = "no clear difference in league play"
        # Item 4 of the reviewed brief: ability and caution, lower → higher setting (UNPAIRED: different positions).
        sdt = {}
        for m in ("main", "robust"):
            a, b = lg["setups"][na]["risk"][m]["sdt"], lg["setups"][nb]["risk"][m]["sdt"]
            sdt[m] = None if a["na"] or b["na"] else dict(
                dprime_change=b["dprime"] - a["dprime"], caution_change=b["caution"] - a["caution"])
        out.append(dict(model=model, low=na, high=nb, low_setting=sa, high_setting=sb, reading=reading,
                        extra_time_median=(qb["time_median"] - qa["time_median"])
                        if None not in (qb.get("time_median"), qa.get("time_median")) else None,
                        extra_cost=(qb["usd_per_1000"] - qa["usd_per_1000"])
                        if None not in (qb.get("usd_per_1000"), qa.get("usd_per_1000")) else None, sdt=sdt))
    return out


def write_data(S: dict, out: Path) -> None:
    """The data files: per version, league and model; small enough for a phone."""
    if (out / "data").exists():
        shutil.rmtree(out / "data")
    files = []
    def brief(s):
        """A setup in a league file: quality, confidence and every risk metric at both margins, without phases."""
        return dict(slug=s["slug"], quality=s["quality"], confidence=s.get("confidence"), close=s.get("close"),
                    risk={m: {k: v for k, v in r.items() if k != "phases"} for m, r in s["risk"].items()})

    for lg in S["leagues"]:
        head = {k: v for k, v in lg.items() if k not in ("setups", "references")}
        head["setups"] = {n: brief(s) for n, s in lg["setups"].items()}
        head["references"] = {n: dict(r, risk={m: {k: v for k, v in x.items() if k != "phases"} for m, x in r["risk"].items()})
                              for n, r in lg["references"].items()}
        write_json(out, f"data/v3/{lg['dataset']}.json", head)
        files.append(f"data/v3/{lg['dataset']}.json")
        for n, s in lg["setups"].items():
            rel = f"data/v3/{lg['dataset']}/{s['slug']}.json"
            extra = {"aliases": aliases(n)} if aliases(n) else {}
            write_json(out, rel, dict(dataset=lg["dataset"], version="v3", status=lg["metric_status"], **s, **extra))
        for n, r in lg["references"].items():
            write_json(out, f"data/v3/{lg['dataset']}/{r['slug']}.json",
                       dict(dataset=lg["dataset"], version="v3", status=lg["metric_status"], **r))
    v1 = S["v1"]
    write_json(out, "data/v1/v1-set.json", dict(
        {k: v for k, v in v1.items() if k not in ("setups", "pairs", "disagreements")},
        setups={n: brief(s) for n, s in v1["setups"].items()}))
    for n, s in v1["setups"].items():
        write_json(out, f"data/v1/v1-set/{s['slug']}.json", dict(dataset="v1-set", version="v1", status=EARLIER, **s))
    write_json(out, "data/v1/compare.json", dict(dataset="v1-set", version="v1", status=EARLIER, pairs=v1["pairs"]))
    write_json(out, "data/v1/disagreements.json", dict(dataset="v1-set", version="v1", status=EARLIER,
                                                         **v1["disagreements"]))
    write_json(out, "data/v3/shared.json", dict(version="v3", status=PENDING, **S["shared"]))
    # Reviewed brief of 24 Oct 2026, item 5A: the recorded hypothesis, tested across setups of all leagues (ranks only).
    write_json(out, "data/v3/offline-hypothesis.json", dict(version="v3", label=O.REREAD_LABEL, **S["hypothesis"]))
    # Close choices, stage B (Method spec 2026-10-24 §9.9-9.13): aggregates per complete team; pending teams by name only.
    write_json(out, "data/v3/close-choices-b.json", dict(version="v3", **S["close_b"]))
    write_json(out, "data/smoke/part-a.json", dict(dataset="smoke-part-a", status="Smoke test", rows=S["smoke"]))
    write_json(out, "data/setups.json", dict(setups=[v for v in S["setups_meta"].values()]))
    write_json(out, "data/thresholds.json", S["thresholds"])
    write_json(out, "data/analysis-status.json", S["status"])
    write_json(out, "data/human-scale.json", S["human_scale"])
    write_json(out, "data/v3/summary.json", dict(
        version="v3", note="Counts only; league numbers are never merged into one score.",
        leagues=len(S["leagues"]), league_setups=sum(len(lg["setups"]) for lg in S["leagues"]),
        league_decisions=sum(lg["decisions"] for lg in S["leagues"]),
        league_decisions_scored=sum(lg["scored"] for lg in S["leagues"]),
        model_setups=S["counts"]["model_setups"], models=S["counts"]["models"]))
    # The download linked from the hero and from Data: every league's results per setup, one league per key.
    write_json(out, "data/results.json", dict(
        version="v3", note="Results per league; leagues are never merged. Decisions: decisions/index.json.",
        leagues={lg["dataset"]: dict(id=lg["id"], status=lg["status"], metric_status=lg["metric_status"],
                                     winner=lg["winner"], reasoning=lg["reasoning"],
                                     setups={n: brief(s) for n, s in lg["setups"].items()},
                                     references={n: dict(r, risk={m: {k: v for k, v in x.items() if k != "phases"}
                                                                  for m, x in r["risk"].items()})
                                                 for n, r in lg["references"].items()})
                 for lg in S["leagues"]}))


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


def showcase(S: dict, pool: dict) -> dict | None:
    """The board on the hero and the social preview (B4): a typical Risk pays decision, from the most recent finished
    league: among the models' Risk pays decisions with a stake inside thresholds hero_stake_range, the one whose
    stake is closest to the median of that pool (ties: the lower decision id). Its callout explains that one model's
    risk call; league positions were answered only by the model that moved."""
    for lg in sorted(S["leagues"], key=lambda l: (l["metric_status"] == PUBLISHED, l["id"]), reverse=True):
        rows = pool.get(lg["dataset"])
        if rows:
            stakes = sorted(r[0] for r in rows)
            med = stakes[len(stakes) // 2]
            d = min(rows, key=lambda r: (abs(r[0] - med), r[1]))[2]
            return dict(league=lg["id"], metric_status=lg["metric_status"], pool=len(rows), median_stake=med,
                        **pages.hero_numbers(d, f"League {lg['id']}", d["setup"], setup_slug(lg["dataset"], d["setup"]),
                                             d["page"]))
    return None


def _shoot(html: str, png: Path, width: int, height: int) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "card.html"
        src.write_text(html)
        shot = Path(tmp) / "card.png"
        r = subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                            f"--window-size={width},{height}", f"--screenshot={shot}", src.as_uri()],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not shot.exists():
            print("image failed:", r.stderr[-500:], file=sys.stderr)
            return False
        shutil.copy(shot, png)
    return True


def risk_cards(S: dict, out: Path) -> dict:
    """B6.5: the risk call card of each league winner as a standalone image for X (1200 x 675), from the current
    results, in the site's dark theme."""
    import home
    folder = out / "share"
    folder.mkdir(exist_ok=True)
    css = (SITE / "assets/site.css").read_text() + (SITE / "assets/bg.css").read_text()
    made, keep = {}, set()
    for lg in S["leagues"]:
        html = home.risk_call_card(S, lg, css)
        if html is None:
            continue
        name = f"share/risk-card-{lg['dataset']}-{hashlib.sha256(html.encode()).hexdigest()[:8]}.png"
        if (out / name).exists() or _shoot(html, out / name, 1200, 675):
            made[lg["dataset"]] = name
            keep.add(Path(name).name)
    for old in folder.glob("risk-*.png"):
        if old.name not in keep:
            old.unlink()
    return made


ARCHIVE_DATE = "2026-10-23"


def archive_pre_switch(out: Path) -> None:
    """B2: the page that was live before the switch, frozen as it was (its final data, 23 Oct 02:50 UTC), under
    archive/<date>/ with a banner; Leagues and Method hold its content in the new form."""
    src, dst = SITE / "archive_page", out / "archive" / ARCHIVE_DATE
    (out / "v3-results.json").unlink(missing_ok=True)  # that page's data file, now beside it in the archive
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "v3-results.json", dst / "v3-results.json")
    page = (src / "index.html").read_text()
    page = page.replace(f'<link rel="canonical" href="{BASE}">', f'<link rel="canonical" href="{BASE}archive/{ARCHIVE_DATE}/">', 1)
    banner = (f'<p style="margin:0;padding:.6rem 1rem;background:#fff3c4;color:#222;font:14px/1.4 system-ui,sans-serif">'
              f'Archived: this is the page as it was before the new site went live ({ARCHIVE_DATE}). The current results '
              f'are on the <a href="../../">home page</a>; this content now lives in <a href="../../leagues/">Leagues</a> '
              f'and <a href="../../method/">Method</a>.</p>')
    page = page.replace("<body>", "<body>" + banner, 1)
    (dst / "index.html").write_text(page)


def preview_redirects(out: Path, target: Path) -> None:
    """The old preview path after the switch: every page redirects to the same page on the live address, keeping the
    query and the anchor (stable links posted from the preview keep working). Fixed snapshots (results/) postdate the
    preview and get none."""
    if target.exists():
        shutil.rmtree(target)
    for page in out.rglob("index.html"):
        rel = page.parent.relative_to(out).as_posix()
        if rel.split("/")[0] == "results":
            continue
        rel = "" if rel == "." else rel + "/"
        url = BASE + rel
        stub = target / rel / "index.html"
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="robots" content="noindex">
<title>Moved to {url}</title><link rel="canonical" href="{url}"><meta http-equiv="refresh" content="0; url={url}">
<script>location.replace({json.dumps(url)} + location.search + location.hash);</script></head>
<body><p>This page moved to <a href="{url}">{url}</a>.</p></body></html>
""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="~/.local/state/bg-site")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-image", action="store_true")
    ap.add_argument("--preview-redirects", metavar="DIR",
                    help="write a redirect to the live address for every page of the build into DIR (the old preview path)")
    args = ap.parse_args()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    # Shown names (content/labels.json): everything is computed under the databases' names, then relabelled.
    S = relabel(compute(args))
    S["base"] = BASE
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
        ROOT / "positions/v1.jsonl", datasets, S["_close"])
    S["decision_files"] = sum(1 for p in (out / "decisions").rglob("*") if p.is_file())
    S["showcase"] = showcase(S, decisions_export.SHOWCASE)
    write_json(out, "data/showcase.json", S["showcase"] or {})
    S["hash"] = results_hash(out)
    manifest(S, out)
    S["image"] = None if args.no_image else preview_image(S, out)
    S["risk_cards"] = {} if args.no_image else risk_cards(S, out)
    if S["image"] is None:
        old = sorted((out / "share").glob("preview-*.png")) if (out / "share").exists() else []
        S["image"] = f"share/{old[0].name}" if old else None
    for name in ("site.css", "site.js", "tables.js", "png.js", "bg.css", "bg.js", "decisions.css", "decisions.js"):
        if (SITE / "assets" / name).exists():
            shutil.copy(SITE / "assets" / name, out / name)
    pages.write_all(S, out, BASE)
    archive_pre_switch(out)
    if args.preview_redirects:
        preview_redirects(out, Path(args.preview_redirects).expanduser())
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
