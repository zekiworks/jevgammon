# Did they improve? Harness review 2 (Zeki #3179)

- Branch `improve`, commit bbbea9d; diff against the reviewed 2864b9e: `diff-vs-2864b9e.patch` (also contains 3ed2d80, the plan-hash binding).
- Final plan: `mailbox/Did they improve - plan 2026-11-08.md` at main 7e2bf78, sha256 85a970d09cf1ae40d5567a7540ec0f607133314589119391bd71584b5ef78542 (harness constant PLAN_SHA256; page commit 2dce5ce on improve-page computes the same hash from the plan file).
- No model call was made.

## 1. Plan identity
- `bind_plan` (improve.py): before a model's first call the current plan hash must equal PLAN_SHA256; it is then stored in `runs/<key>/plan.json` and in the model DB (`improve_identity`). Every start and resume compares the current plan file with the stored hash and refuses on mismatch.
- `summary()` exports the stored identity (`bound_plan`), never the current file's hash; models bound to different plans are refused.
- Test: `test_plan_identity_is_stored_and_resume_refuses_a_changed_plan` (plan edited after the start: resume refused, the summary keeps the stored hash, a new model cannot start).

## 2. Route identity
- Runner (`src/players/llm.rs`): player config `expect_route {models, provider, reject_log}`; in `LlmClient::call`, after the response arrives (cost already booked in the ledger) and before the reply is used, `route_identity` checks the response's `model` and `provider`. Missing, unreadable or wrong identity fails closed: the reply is not used, the raw response + request + reported cost go to the reject log, the player sends no further request, and replies of requests already in flight are not used either.
- Harness: billed models carry `expect_route`; any ROUTE CHECK in a test answer, the match or a lesson call stops the model; a test with a ROUTE CHECK error is never re-asked; a non-empty reject log stops the model before any step; an empty identity record after a step fails closed.
- Tests: Rust `route_identity_fails_closed`, `a_wrong_route_stops_before_the_reply_is_used_and_nothing_more_is_sent` (mock server: wrong first reply → error, nothing used, logged with raw response and cost, request count stays 1; anonymous reply → error; right reply → used). Python: `test_route_check` (empty evidence fails), `test_billed_players_carry_the_route_guard`, `test_a_rejected_route_stops_before_any_step`.

## Outputs
- `rust-tests.txt`: cargo test --release, 77 passed, exit 0.
- `python-tests.txt`: unittest -v, 20 tests OK, exit 0.
- `dry-run-E2.txt`: Safest in the model seat resumed to E2 (plan bound on resume), exit 0.
