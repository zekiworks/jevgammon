# Did they improve? Codex route identity (for the ChatGPT lane after 2026-11-13 11:38 UTC)

Branch `improve`, commit 6e5a15e (own commit; `diff-6e5a15e.patch`). No model call. The running lanes' binaries are untouched: the Codex lane will use its own build, target/improve-bin/jevgammon-6e5a15e (CARGO_TARGET_DIR=target/codex).

## What is checked
- The Codex route streams events; the league read only the answer text and usage, so the league stored no served model for Sol or Astra.
- Now `parse_codex_sse` also reads `response.completed` → `response.model`. Before the reply is used, `route_identity` checks it against the requested id (`gpt-6.1-sol` / `gpt-6-astra`), accepting the id itself or the id followed by a dated snapshot suffix (`-` + 4 digits…).
- Fails closed (latch set, nothing used, no further HTTP attempt from that player): a wrong model, a dated snapshot of a different id, a stream without `response.completed`, a `response.completed` without `response.model`.
- Weaker than the other routes: the value is checked against our request, not against league evidence (none exists). The page note says so once Zeki agrees.

## Tests (mock Codex endpoint through `LlmClient`)
- `codex_replies_are_used_only_with_the_requested_model`: `gpt-6.1-sol` and `gpt-6.1-sol-2026-10-01` → used (1 request each); `gpt-6-astra`, `gpt-6-astra-2026-10-01`, `response.model` null, no `response.completed` → ROUTE CHECK, nothing used, a second call sends nothing (server count stays 1).
- `codex_identity_is_the_streams_served_model`: parse + identity unit cases, `allow_dated` off rejects the dated id.
- `rust-tests.txt`: 83 passed, exit 0. `python-tests.txt`: 20 OK, exit 0.
