# Did they improve? Harness review 3 (Zeki #3184)

Branch `improve`, commit 0c9270c; diff against bbbea9d: `diff-vs-bbbea9d.patch` (src/http.rs, src/players/llm.rs, src/players/decision.rs). No model call was made. Plan unchanged: main 7e2bf78, sha256 85a970d09cf1ae40d5567a7540ec0f607133314589119391bd71584b5ef78542.

## Fix
- `http::send` and `http::send_metered` take a stop latch (`Option<&AtomicBool>`). `send_until` reads it at the top of every attempt: before the first HTTP attempt (after the caller's pacing) and before each retry (after its backoff sleep), and before any budget reservation. When set, the call ends with `ROUTE CHECK: the player is stopped; no further HTTP attempt`, with nothing reserved and nothing sent.
- `LlmClient` passes its `route_rejected` latch on every route (Codex, Anthropic, xAI, Gemini, Antigravity, OpenAI-compatible with and without a budget). Decision services pass none (unchanged).

## Regression tests
- `http::tests::a_set_latch_sends_and_reserves_nothing`: latch already set → no request reaches the mock server and nothing is reserved in the ledger; latch set while a 503 retry waits → only the first attempt reaches the server.
- `players::llm::tests::a_request_in_backoff_sends_nothing_after_another_fails_the_route_check` (concurrent, 2 worker threads): A gets 503 and waits 2 s to retry; B gets a reply naming deepseek/deepseek-v4.1-flash-1017 → rejected, latch set; A wakes and makes no HTTP attempt (mock server count stays 2).

## Outputs
- `rust-tests.txt`: cargo test --release, 79 passed, exit 0.
- `python-tests.txt`: unittest -v, 20 OK, exit 0.
