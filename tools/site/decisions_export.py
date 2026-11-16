"""The "Every decision" page: per-decision records are not published.

    export(out, snap, plays_dir, prompts_db, league_ids) -> the hashes of the rules texts written, sorted
    body(contexts) -> the inner HTML of <main> for decisions/index.html

No bench publishes its questions (Ümit via Zeki #11048, #11050): a position published with the engine's best play is a
test item that can enter training, so the site publishes no per-decision record (board, dice, plays, best, chosen, the
request text built for a position) and the earlier version's fixed position set (v1) is not published either. What is
published under out/decisions/:
    contexts/<hash>.txt     the shared rules text of the prompts of the leagues' scored model decisions (hash =
                            sha256(text)[:12], as STATE/prompts.db keys it): the method, the same for every position
"""

import sqlite3
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE))

from common import esc  # noqa: E402

# players.spec of the players that are programs: they get no prompt.
PROGRAM_SPECS = {"random", "safest", "gnubg-weak"}

# The model decisions of a league: every turn of a match in the league's view (a setup that moved leagues keeps its
# matches here, whatever league its plays row was scored under), with whether its player is a program.
TURNS = """
SELECT t.id, p.spec IN ({programs})
FROM turns t JOIN games g ON g.id = t.game_id JOIN league_match_view lm ON lm.match_id = g.match_id
JOIN players p ON p.name = CASE t.player WHEN 1 THEN lm.model1 ELSE lm.model2 END
WHERE lm.league_id = ? AND t.decided_by IN ('model', 'fallback')
"""


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def export(out: Path, snap: Path, plays_dir: Path, prompts_db: Path, league_ids: list[int]) -> list[str]:
    """Writes out/decisions/contexts/<hash>.txt for every rules text a scored model decision of the leagues was sent."""
    root = Path(out) / "decisions" / "contexts"
    root.mkdir(parents=True)
    if not Path(prompts_db).exists():
        return []
    sdb, pdb = ro(snap), ro(prompts_db)
    turns = set()
    for league in league_ids:
        turns.update(tid for tid, program in sdb.execute(
            TURNS.format(programs=",".join("?" * len(PROGRAM_SPECS))), (*sorted(PROGRAM_SPECS), league)) if not program)
    scored = set()
    for shard in Path(plays_dir).glob("s*.db"):
        scored.update(tid for (tid,) in ro(shard).execute("SELECT turn_id FROM plays") if tid in turns)
    contexts = {ctx for tid, ctx in pdb.execute("SELECT turn_id, context FROM seen WHERE context IS NOT NULL")
                if tid in scored}
    for h in sorted(contexts):
        row = pdb.execute("SELECT text FROM contexts WHERE hash = ?", (h,)).fetchone()
        if row is None:
            raise RuntimeError(f"prompts.db: context {h} is missing")
        (root / f"{h}.txt").write_text(row[0])
    return sorted(contexts)


def body(contexts: list[str]) -> str:
    """The page's note; `contexts`: the hashes of the rules texts written by export."""
    items = "".join(f'<li><a href="contexts/{esc(h)}.txt"><code>{esc(h)}</code></a></li>' for h in contexts)
    rules = (f'<p>The rules text every model decision was sent before its position (the same for every position of a '
             f'prompt format; the method page describes the rest of the prompt):</p><ul>{items}</ul>') if items else ""
    return f"""<section class="card hero page-head">
<p class="eyebrow">Every decision</p>
<h1>Per-decision records are kept private</h1>
</section>
<section class="card" id="private">
<p>No benchmark should publish its questions: a position published with the engine's best play is a test item, and
published test items can end up in a model's training data. So this site does not publish its positions, the plays
each model chose in them or the engine's best play for each. The results, the error rates, the risk calls and every
other aggregate on this site are computed from all of them and stay public, as do the match results.</p>
{rules}</section>
"""
