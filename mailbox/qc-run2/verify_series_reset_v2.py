"""QC 2026-11-12, Zeki #5362 item 1: series reset, checked canonically on the stored message arrays (read-only).

Replaces the substring check of verify_series_reset.py. For every stored request of one learning-lane arm:
  - the message array is normalised (OpenAI `messages`; Antigravity `systemInstruction` + `contents`) to
    (role, text) pairs; the role sequence and the message count are tallied;
  - play requests (games, T10, E runs): the system message must EQUAL the runner's composition
    (llm::play_system, runner 8b6f9a1 src/players/llm.rs:289-301): the base system prompt S0, or
    S0 + "\\n\\n" + note.trim_end() when the note is non-empty. The expected note is the series' OWN stored
    context file: game N <- contexts/after-g(N-1).txt (game 1: none, so system == S0), T10 <- contexts/after-g10.txt,
    E runs: none. The user message must not contain the notes marker;
  - lesson calls: exactly two messages, system == the series' lesson-system.txt and user == that game's
    lessons-gNN.user.txt (byte-exact, compared by sha256).
Outputs counts and sha256 only (no prompt, lesson or answer text).
Usage: python3 verify_series_reset_v2.py MODEL-KEY"""
import collections, hashlib, json, sqlite3, sys
from pathlib import Path

key = sys.argv[1]
RUNS = Path("/home/cbasaran/code/jevgammon/workspace/improve/runs") / key
DB = Path("/home/cbasaran/code/jevgammon/smoke/improve") / f"{key}.db"
MARK = "=== NOTES FROM YOUR EARLIER GAMES IN THIS SERIES ==="
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def messages(raw):
    v = json.loads(raw)
    if "messages" in v:
        out = []
        for m in v["messages"]:
            c = m.get("content")
            out.append((m["role"], c if isinstance(c, str) else "".join(p.get("text", "") for p in c or [])))
        return out
    out = []
    if v.get("systemInstruction"):
        out.append(("system", "".join(p.get("text", "") for p in v["systemInstruction"].get("parts", []))))
    for c in v.get("contents", []):
        out.append((c.get("role"), "".join(p.get("text", "") for p in c.get("parts", []))))
    return out


def composed(s0, note):
    return f"{s0}\n\n{note.rstrip()}" if note.strip() else s0


# S0: the base system prompt, from an E1 request (E runs carry no note by construction; checked below)
e1 = db.execute("SELECT x.request FROM answer_exchanges x JOIN answers a ON a.id = x.answer_id WHERE a.setup LIKE ? "
                "ORDER BY x.id LIMIT 1", ("% | improve | E1",)).fetchone()[0]
S0 = messages(e1)[0][1]
out = dict(model=key, base_system_sha256=sha(S0), composition="runner 8b6f9a1 src/players/llm.rs:289-301 play_system",
           series={}, empty_runs={})


def check_play(reqs, expected_note):
    """reqs: raw request strings; expected_note: the own context text ('' = none)."""
    want = composed(S0, expected_note)
    r = collections.Counter()
    for raw in reqs:
        m = messages(raw)
        r["requests"] += 1
        r["roles " + ",".join(x[0] for x in m)] += 1
        r[f"message_count {len(m)}"] += 1
        r["system_equal_to_S0_plus_own_note" if m and m[0][0] == "system" and m[0][1] == want else "system_mismatch"] += 1
        r["notes_marker_in_non_system_message"] += any(MARK in t for role, t in m[1:])
    return dict(r, expected_note_sha256=sha(expected_note) if expected_note.strip() else None,
                expected_note_empty=not expected_note.strip())


for s in range(1, 6):
    d = RUNS / f"S{s}"
    agg = json.loads((d / "aggregate.json").read_text())
    match_id = int((d / "match.done").read_text())
    games = {}
    for g in range(1, 11):
        rows = [r[0] for r in db.execute(
            "SELECT x.request FROM exchanges x JOIN turns t ON t.id = x.turn_id JOIN games g ON g.id = t.game_id "
            "WHERE g.match_id = ? AND 2 * (g.round_no - 1) + g.leg = ? AND t.player = 1 ORDER BY x.id", (match_id, g))]
        note = "" if g == 1 else (d / "contexts" / f"after-g{g - 1:02d}.txt").read_text()
        games[f"g{g:02d}"] = check_play(rows, note)
    name = json.loads((d / f"test-S{s}.json").read_text())["players"][0]["name"]
    t10 = check_play([r[0] for r in db.execute(
        "SELECT x.request FROM answer_exchanges x JOIN answers a ON a.id = x.answer_id WHERE a.setup = ? ORDER BY x.id",
        (name,))], (d / "contexts" / "after-g10.txt").read_text())
    lessons = collections.Counter()
    for g in range(1, 11):
        call = json.loads((d / f"lessons-g{g:02d}.call.json").read_text())
        sys_file, user_file = (d / "lesson-system.txt").read_text(), (d / f"lessons-g{g:02d}.user.txt").read_text()
        for x in call["exchanges"]:
            m = messages(x["request"])
            lessons["requests"] += 1
            lessons["roles " + ",".join(r[0] for r in m)] += 1
            lessons[f"message_count {len(m)}"] += 1
            ok = len(m) == 2 and m[0] == ("system", sys_file) and m[1][0] == "user" and m[1][1] == user_file
            lessons["exactly_system_file_and_user_file" if ok else "lesson_request_mismatch"] += 1
            lessons["notes_marker_present"] += any(MARK in t for _, t in m)
    out["series"][f"S{s}"] = dict(match=match_id, attempt=agg["attempt"], t10_setup_sha256=sha(name),
                                  games=games, t10=t10, lesson_calls=dict(lessons),
                                  games_with_requests=sum(1 for v in games.values() if v["requests"]))
for e in ("E1", "E2", "E3"):
    out["empty_runs"][e] = check_play([r[0] for r in db.execute(
        "SELECT x.request FROM answer_exchanges x JOIN answers a ON a.id = x.answer_id WHERE a.setup LIKE ? "
        "ORDER BY x.id", (f"% | improve | {e}",))], "")
tot = collections.Counter()
for s in out["series"].values():
    for v in list(s["games"].values()) + [s["t10"]]:
        for k in ("requests", "system_equal_to_S0_plus_own_note", "system_mismatch", "notes_marker_in_non_system_message"):
            tot[k] += v.get(k, 0)
    for k in ("requests", "exactly_system_file_and_user_file", "lesson_request_mismatch"):
        tot["lesson " + k] += s["lesson_calls"].get(k, 0)
for v in out["empty_runs"].values():
    for k in ("requests", "system_equal_to_S0_plus_own_note", "system_mismatch"):
        tot["E " + k] += v.get(k, 0)
out["totals"] = dict(tot)
print(json.dumps(out, indent=1))
