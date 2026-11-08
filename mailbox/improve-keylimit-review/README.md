# Did they improve? Provider account limit → pause (Main, after turkce #3279)

Branch `improve`, commit 45f8384, Python harness only (`workspace/improve/improve.py`, `test_improve.py`, new test double `fake_ask.py`); diff in `diff-45f8384.patch`. No binary change, no model call. The OpenRouter lane stays stopped (key still blocked).

## Rule
- **Account limit** = an error text matching `403 Forbidden … Key limit exceeded` / `credit limit`, or `402 Payment Required`, or `insufficient credits` (`KEY_LIMIT`). Other 403s (e.g. an invalid key) are unchanged: a failed request, as before.
- On an account limit the model **pauses at once**: `runs/<key>/hold.json` with reason "paused: shared-balance priority (provider account limit: HTTP 403 key limit / 402 credits)", a `key_limit` log event carrying the provider's text, `paused.json` through `run()`; the page shows paused / shared-balance priority. No retry loop. While the hold exists nothing is dispatched (`held()` before any test or match); the operator lifts it (deletes `hold.json`) when the key works again.

## Where it applies
- **Tests (empty runs, T10):** `ask_watched` runs `jevgammon ask` and polls its own newly stored answers every 50 ms. At the first answer that failed on the account limit it stops the process (SIGKILL) as soon as none of its ledger reservations is open, so requests in flight settle first and nothing more is dispatched; if a reservation is still open after 5 s it is stopped anyway and that reservation keeps its worst case (the ledger's no-response rule). Failed positions stay stored; the next asking after the hold is lifted asks only positions without a valid stored answer (the runner's existing rule: failed rows are asked again, answered ones are not). Only this asking's rows count (earlier failures kept for the re-ask do not trigger).
- **Games:** an account-limit failure ends the match (the runner already stops a match on a failed request); the harness pauses instead of failing. On resume the series is replayed from game 1 with the same dice, the plan's rule for an interrupted series.
- **Lesson calls:** an account-limit failure writes the hold and ends the hook at once (no 20-try loop); the match ends and the harness pauses as above.
- **T10 asked in the hook:** the hook's asking pauses the same way (hold written); the series' T10 is re-asked from the stored context after the hold is lifted, without replaying the games.

## Limits
- Python can only stop the runner process, not tell it to stop sending: between the first refused answer and the stop, the runner may dispatch a few more requests (each refused by the provider at $0; bounded by the test: at most 4 after the first refusal).
- A reservation still open after 5 s keeps its worst case in the ledger (overstates spend, never understates).
- Already-running lanes pick this up in new processes only (after-game hooks, the next model, the next lane start).

## Tests (`python-tests.txt`, 25 OK, exit 0)
- `test_key_limit_pauses_at_once_and_resume_reasks_only_failed_positions`: test double answers 3 positions, then every request is refused 403 "Key limit exceeded": `Pause` raised in the first round (rounds=30 not used), at most 3 + 1 + 4 requests dispatched (not 200), hold reason "shared-balance priority", `key_limit` event with the provider text, failed rows kept, no ledger reservation left open, $0 booked for refusals; while held a new asking dispatches nothing; after the hold is lifted only the failed/unasked positions are asked (none of the 3 answered ones), ending at 200 answered, 0 failed.
- `test_an_ordinary_403_is_a_failed_request_as_before`: 200 invalid-key 403s → 200 failed answers, no hold, no `key_limit` event.
- `test_key_limit_texts`: 403 key limit and 402 credits match; invalid-key 403 and 429 rate limit do not.
