# Did they improve? Codex lane fixes (Zeki #3236)

Branch `improve`, commit 938c842. `diff-6e5a15e-938c842.patch` shows everything since the reviewed 6e5a15e, including two small harness-only commits: 5ac479e records the binary per step and refuses unpinned runs; 6e37bd7 makes an operator hold pause before the input checks. Codex-lane binary: `target/improve-bin/jevgammon-938c842`, sha256 0a342d9e4670f625eb06cf05f50f14d630f6c2414449c8e3e562431410b3eebd, built in its own target directory. The running lanes' binaries are untouched. No model call was made.

## 1. Dated snapshot grammar
- `is_dated_suffix`: the suffix must be exactly `-YYYY-MM-DD`: 11 ASCII bytes, dashes at the declared places, digits elsewhere, a valid calendar date per chrono, and nothing after. Positions are checked on bytes, so any non-ASCII input fails the shape test and nothing is sliced.
- Test `dated_suffix_is_a_complete_valid_date`. Accepted: -2026-10-01 and -2024-02-29. Rejected, without panic:
  - empty, `-`, 4 digits only, a missing month or day, single-digit fields;
  - trailing text (`x`, `-mini`), `-2026-other-model`;
  - invalid dates (month 13, Feb 30, Feb 29 2025), no dash, slashes;
  - full-width digits, `é` in several positions, a combining mark after a valid date.
  - Through `route_identity`: `<id>-2026-other-model`, `<id>-1234`, `<id>-2026-10-01-mini`, a Unicode suffix, `<id>é`, `<id>-` are all rejected.

## 2. Served identity persisted per exchange
- Every checked reply's identity record is stored with its exchange: `exchanges.identity` for games, `answer_exchanges.identity` for tests. Lesson calls carry it in the exchange list of their JSON. The record is `{"result": "accepted" | "accepted_dated", "fields": {"model", "provider"}}`, with the raw identity fields as served. For Codex the field is `response.completed.response.model`.
- Rejected replies are not used. They go to the rejection log with `{"result": "wrong" | "missing", "fields", "reason"}`, the raw reply and the reported cost. This includes a Codex stream without `response.completed`.
- Tests:
  - `the_served_identity_is_persisted_per_exchange`: a Codex dated reply is stored as accepted_dated with its served model. A wrong model, a null model and a missing `response.completed` are logged with result and fields. An OpenRouter reply is stored as accepted with its model and provider.
  - `db::tests::exchange_identity_is_stored`: round trip through `record_turn`.

## Other routes: is the served identity already persisted per exchange?
Yes. On every running route (Antigravity, xAI, Claude, local vLLM, OpenRouter) the exchange stores the raw JSON reply, which contains the identity fields: `response.modelVersion` for Antigravity; `model` for xAI, Claude and vLLM; `model` and `provider` for OpenRouter. Rejected replies keep their raw reply in the rejection log, in binary 1270c04 as well. Only Codex stored the answer text alone; that is what this change fixes. The running lanes need no change.

## Outputs
- `rust-tests.txt`: 86 passed, exit 0.
- `python-tests.txt`: 20 OK, exit 0.
