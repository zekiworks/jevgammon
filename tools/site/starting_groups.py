"""Leagues page, starting groups (Ümit, 31 Oct 2026): the three original leagues' own-group standings, the moves between
leagues, and the badges that tell a Cup place from a league move. Everything comes from saved files: the standings and
the moves from content/starting_groups.json (saved from tools/original_league.py and the ladder's records), the Cup
seeds and the knockout's entrants from S (data/v3/hype-cup.json); nothing is computed here."""

import functools
import json

import pages as P
from common import CONTENT, count, esc

SUBTITLE = "Groups reflect model profiles, not tournament rankings."
COHORT_NOTE = ("These are fixed starting cohorts, not current ladder ranks or mutually exclusive universal model "
               "types.")
PROGRAM_NOTE = "program, a reference row: an official place in the match standings, not a model type"


@functools.lru_cache(maxsize=1)
def load() -> dict:
    """The saved standings and moves, with every recorded name mapped to the name the site shows."""
    data = json.loads((CONTENT / "starting_groups.json").read_text())
    renamed = {old: v["name"] for old, v in json.loads((CONTENT / "labels.json").read_text())["renamed"].items()}
    shown = lambda n: renamed.get(n, n)
    for g in data["groups"]:
        for r in g["rows"]:
            r["name"] = shown(r["name"])
        for t in g["ties"]:
            t["setups"] = [shown(n) for n in t["setups"]]
            for m in t["matches"]:
                m["a"], m["b"] = shown(m["a"]), shown(m["b"])
    for m in data["moves"]:
        m["name"] = shown(m["name"])
    return data


def is_program(S, name: str) -> bool:
    return any(m.get("model_type") == "program" for (_, n), m in S["setups_meta"].items() if n == name)


def current_league(S, name: str) -> dict | None:
    """The league whose table holds the setup now (a program is in all three: None)."""
    found = [lg for lg in S["leagues"] if name in lg["setups"]]
    return found[0] if len(found) == 1 else None


def moves_of(G: dict) -> dict[str, list[dict]]:
    out = {}
    for m in sorted(G["moves"], key=lambda m: (m["round"], m["date"])):
        out.setdefault(m["name"], []).append(m)
    return out


def groups_of(G: dict) -> dict[str, list[dict]]:
    """Each setup's starting group(s), from the saved memberships: one for a model setup; a program is in every group
    whose saved table holds it (GNUbg weak, the anchor: all three; Safest and Random: the original League 1 only)."""
    out = {}
    for g in G["groups"]:
        for r in g["rows"]:
            out.setdefault(r["name"], []).append(g)
    return out


def move_badge(moves: list[dict]) -> str:
    """The movement badge: where the setup ended up against its starting group, every recorded move in its title and
    in small type."""
    if not moves:
        return ""
    start, end = moves[0]["from_league"], moves[-1]["to_league"]
    word = "promoted" if end > start else "relegated" if end < start else "back"
    arrow = {"promoted": "\u2191", "relegated": "\u2193", "back": "\u2195"}[word]
    label = f"{arrow} now in League {end}" if word != "back" else f"{arrow} back in League {end}"
    steps = " · ".join(f'round {m["round"]}: League {m["from_league"]} \u2192 {m["to_league"]} ({m["reason"]})' for m in moves)
    return (f'<span class="badge badge-move badge-{word}" title="{esc(steps)}">{esc(label)}</span>'
            f'<span class="small">{esc(steps)}</span>')


def cup_badge(S, name: str, league: int) -> str:
    """The Cup qualification badge: the recorded Hype Cup seed (its original league must match) and, if recorded, the
    Nackgammon knockout entry."""
    seed = next((s for s in S["cup"]["seeds"] if s["name"] == name and s["league"] == league), None)
    if not seed:
        return ""
    k = S["knockout"]
    in_k = any(name in (t.get("model1"), t.get("model2")) for t in k["ties"])
    return (f'<span class="badge badge-cup">Hype Cup seed {seed["seed"]}</span>'
            + (f'<span class="badge badge-cup">{esc(k["name"])}</span>' if in_k else ""))


def tie_note(t: dict) -> str:
    who = ", ".join(t["setups"])
    ms = "; ".join(f'{m["a"]} {m["score"][0]}\u2013{m["score"][1]} {m["b"]} (<a href="../matches/#m{m["id"]}">match #{m["id"]}</a>)'
                   for m in t["matches"])
    if t["kind"] == "head-to-head":
        return f'{t["points"]} points: {esc(who)}, in that order on head-to-head: {ms}.'
    return f'{t["points"]} points: {esc(who)}, in that order on the mini-table of their matches: {ms}.'


def group_table(S, G: dict, g: dict, moves: dict, rel: str) -> str:
    rows = []
    for r in g["rows"]:
        name, prog = r["name"], is_program(S, r["name"])
        lg = current_league(S, name)
        ds = lg["dataset"] if lg else f'league-{g["league"]}'
        label = f'<a class="model-name" href="{P.model_href(rel, ds, name, S)}">{esc(name)}</a>'
        small = f'<span class="small">{esc(PROGRAM_NOTE)}</span>' if prog else ""
        badges = "" if prog else cup_badge(S, name, g["league"]) + move_badge(moves.get(name, []))
        cls = ' class="reference"' if prog else ""
        rows.append(f'<tr{cls}><td class="model">{label}{small}</td>'
                    f'<td class="num">{r["place"]}</td><td class="num">{r["pts"]}</td><td class="num">{r["p"]}</td>'
                    f'<td class="num">{r["w"]}-{r["d"]}-{r["l"]}</td><td class="num">{r["f"]}-{r["a"]}</td>'
                    f'<td class="badges">{badges}</td></tr>')
    SWIPE, table = P.SWIPE, P.table
    head = ["Model and setting", "Place", "Match points", "Played", "Won-drawn-lost", "Score for-against",
            ("Cup place · league moves", " data-nosort")]
    ties = "".join(f"<li>{tie_note(t)}</li>" for t in g["ties"])
    return (SWIPE + table(head, rows, f'{esc(g["name"])}: the original League {g["league"]}\'s own matches, '
                          f'{count(g["pairings"])} pairings; 3 points a win, 1 a draw', cls="board list")
            + (f'<p class="table-note">Level on points, ranked by the tiebreak:</p><ul class="league-notes">{ties}</ul>'
               if ties else ""))


def section(S, rel: str = "../") -> str:
    """The Starting groups card: the shared subtitle and notes, then one sub-tab per group (Decision first)."""
    G = load()
    moves = moves_of(G)
    tabs = [(f'group-{g["name"].lower()}', g["name"], f'group-{g["name"].lower()}') for g in G["groups"]]
    blocks = (P.link_tabs(tabs, "sub", "Starting groups", "modes sub-tabs")
              + "".join(P.tab_panel(pid, f"sub-tab-{key}", f'<h3 id="group-{g["league"]}">{esc(g["name"])} <span class="small '
                                    f'inline">starting group, the original League {g["league"]}</span></h3>'
                                    f'{group_table(S, G, g, moves, rel)}', "sub-panel")
                        for (key, _, pid), g in zip(tabs, G["groups"])))
    return (f'<section class="card" id="starting-groups"><div class="section-head"><h2>Starting groups</h2></div>'
            f'<p class="subtitle-line"><strong>{esc(SUBTITLE)}</strong></p>'
            f'<p class="note cohort-note">{esc(COHORT_NOTE)}</p>'
            f'<p class="note">Each setup stays in the group it started in, the original league it played in before any '
            f'league move, with that group\'s own match points: only matches between setups of the same starting group '
            f'count, wherever they were played (league season, ladder round or gap match); late entries are left out. '
            f'3 points a win, 1 a draw. Ties: points, then head-to-head (a mini-table of the matches among three or more), '
            f'then the lower error rate (rule set on 28 Oct, after the ties were known; no place here needed the error '
            f'rate). GNUbg weak, the anchor program, is in all three groups. A setup that moved between leagues keeps its '
            f'row here; where it plays now is in <a href="#after-league-moves">After league moves</a>.</p>'
            f'<p class="note">Badges: <span class="badge badge-cup">Hype Cup seed</span> a Cup place '
            f'(<a href="#cups">Cups</a>) · <span class="badge badge-move badge-promoted">\u2191 now in League N</span> '
            f'<span class="badge badge-move badge-relegated">\u2193 now in League N</span> '
            f'<span class="badge badge-move badge-back">\u2195 back in League N</span> league moves, from the ladder\'s '
            f'records. Match points are match results only; they are not the Risk, Quality or Confidence measures.</p>'
            + blocks + '</section>')


def after_moves_intro(S) -> str:
    G = load()
    rounds = sorted({m["round"] for m in G["moves"]})
    return (f'<section class="card" id="after-league-moves"><div class="section-head"><h2>After league moves</h2></div>'
            f'<p class="note">The leagues as they stand now, after {count(len(G["moves"]))} moves in ladder rounds '
            f'{rounds[0]}\u2013{rounds[-1]} (the ladder ended on 26 Oct; its final swap stands). These leagues mix starting '
            f'groups, so they keep their numbers: League 1, League 2, League 3. Each row says its starting group and, for '
            f'a setup that moved, its recorded moves. The <a href="../">leaderboard</a>\'s League keys and links such as '
            f'?league=league-3 refer to these leagues.</p></section>')


def standing_cells(S, name: str) -> str:
    """The Starting group and Moves cells of a row of the current league standings; a program's starting groups are
    the saved groups whose tables hold it."""
    G = load()
    gs = groups_of(G).get(name, [])
    if not gs:
        return '<td>not in a starting group</td><td class="badges"></td>'
    names = ", ".join(esc(g["name"]) for g in gs)
    where = ", ".join(str(g["league"]) for g in gs)
    league = f'original League{"s" if len(gs) > 1 else ""} {where}'
    if is_program(S, name):
        return f'<td>{names} <span class="small">program, {league}</span></td><td></td>'
    return f'<td>{names} <span class="small">{league}</span></td><td class="badges">{move_badge(moves_of(G).get(name, []))}</td>'


def cups_intro() -> str:
    """The Cups section's head, above the existing Hype Cup and Nackgammon knockout card."""
    return ('<section class="card" id="cups"><div class="section-head"><h2>Cups</h2></div><p class="note">Knockout events, '
            'apart from the league tables: their places and results are not league points. The Hype Cup took its 8 teams '
            'from the starting groups\' tables (its roster rule is under its bracket); the Nackgammon knockout used the same '
            '8 teams and the same draw. A Cup place is not a promotion.</p></section>')
