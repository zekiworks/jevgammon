# League 3 - GPT-6.1 Terra (low) and (high): smoke test and estimate (2026-10-28)

For Can. **No Terra league match has run; they wait for your go.** Only the two short smoke tests ran (answers in `smoke/terra-codex-smoke.db`, git-ignored; config `smoke/terra-codex/config.json`; positions: the 20 of GPT-6 Astra (high)'s smoke test, `smoke/astra-high/positions.jsonl`). v3.db was not written for Terra.

## Route: Codex on the ChatGPT subscription works for Terra, at low and high

- **Setups:** `GPT-6.1 Terra (low)` and `GPT-6.1 Terra (high)`: spec `openai/gpt-6.1-terra`, provider `chatgpt-subscription` (Codex backend, subscription login, the route of GPT-6.1 Sol and GPT-6 Astra), `parallel` 4, price for the API-equivalent $1/$5 per M tokens (OpenRouter's list for the OpenAI endpoint, 2026-10-27). They differ only in `reasoning`.
- **Checked in the stored request/response:** the requests went out with `"model":"gpt-6.1-terra"` and `"reasoning":{"effort":"low"}` / `{"effort":"high"}`; both were accepted (no error, no retry). The efforts differ in the answers: low spends 1.3 reasoning tokens per decision, high 192.

## Smoke test (20 positions each, League 3 settings: prompt bg-v2, option-order seed, harness 6693b5b)

| Setup | Answered | Invalid | Errors / retries | Input tok / dec | Output tok / dec (reasoning) | Max output | Request s, mean / max | API-eq. (not billed) | Wall |
|---|---|---|---|---|---|---|---|---|---|
| GPT-6.1 Terra (low) | 20 / 20 | 0 | 0 / 0 | 3,274 | 16.4 (1.3) | 42 | 2.42 / 4.0 | $0.067 | 13 s |
| GPT-6.1 Terra (high) | 20 / 20 | 0 | 0 / 0 | 3,274 | 208.8 (192.2) | 610 | 5.08 / 14.0 | $0.086 | 30 s |

Same play: Terra (low) and (high) 17 of 20; Terra (low) and GPT-6 Astra (high) 11 of 20; Terra (high) and Astra (high) 12 of 20. Billed: $0.

## Opponents: an assumption to confirm

Like Astra (high), each Terra setup plays every setup of the original League 3 table once: the **12** original setups (Claude Fable 5.1 (off), (on); Claude Opus 5.5 (off), (on); Gemini 4 Argon (off), (on); GPT-6 Astra (off), (on); Grok 4.7 (off), (on); Kimi K3.1 Pro (off); GNUbg weak).

**Proposal (needs your yes):** if Astra (high), Terra (low) and Terra (high) are all late entries of the same table, they also meet each other. That adds 3 matches: Terra (low) v Terra (high), Terra (low) v Astra (high), and Terra (high) v Astra (high). Each late entry then has **14** matches, and the table is a full round robin of 15 setups. Without these 3 matches, each Terra has 12 and the late entries never meet. All three extra matches are ChatGPT v ChatGPT, so each counts as one ChatGPT job, and none touches OpenRouter.

## Estimate per Terra setup

Basis: Astra (high)'s estimate (`mailbox/League 3 - GPT-6 Astra (high) estimate 2026-10-28.md`): about 1,511 decisions in 12 League 3 matches (Astra (on)'s decisions per opponent), and League 3's input of about 4,456 tokens per decision. The smoke input (3,274) is lower because those positions are shorter. Output per decision is taken from this smoke test.

| | Terra (low) | Terra (high) |
|---|---|---|
| Decisions, 12 matches (14) | ≈ 1,511 (≈ 1,760) | ≈ 1,511 (≈ 1,760) |
| API-eq. per 1,000 decisions | $4.54 (4,456 × $1/M + 16.4 × $5/M) | $5.50 (4,456 × $1/M + 209 × $5/M) |
| API-eq., 12 matches (14) | ≈ $6.9 ($8.0) | ≈ $8.3 ($9.7) |
| Billed | $0 (ChatGPT subscription) | $0 |
| Own request time per decision | ≈ 2.4 s | ≈ 5.1 s (Astra (high): ≈ 12.4 s) |
| Opponents' time | as in Astra (high)'s table: the match length is set by the opponent; Grok 4.7 (on) ≈ 3.3 h, Grok 4.7 (off) ≈ 1.6 h, Argon (on) ≈ 1.5 h, the others 10–30 min | same |
| Wall time, all 11 non-Kimi opponents in one job | ≈ 3.3 h (Grok 4.7 (on)) | ≈ 3.3 h |
| Kimi K3.1 Pro (off) match | ≈ 15 min, **≈ $0.42 OpenRouter (worst $0.61)** | same |

## Total serialized ChatGPT time (Astra (high) + Terra (high) + Terra (low))

ChatGPT runs **one job at a time**: Astra (high), Terra (high) and Terra (low) never together and never next to another ChatGPT job (Sol, Astra (on), Luna; the Hype Cup's QF1 and the Nackgammon knockout use ChatGPT too). Within one job, the runner plays a setup's matches at once. That is the same as a league matchday, and Can allowed it.

| Order | Job (ChatGPT) | Other subscriptions it uses | Est. wall time |
|---|---|---|---|
| 1 | Astra (high) league entry (go given; started 2026-10-28 15:35 UTC with its ChatGPT/GNUbg opponents; Claude, Grok and Gemini opponents join when their subscriptions are free) | Claude, xAI, Gemini, when free | ≈ 3.5 h of matches; longer in calendar time because some opponents wait for a free subscription |
| 2 | Hype Cup QF1 (GPT-6 Astra (on) v Gemma 4 31B (on)); then the Nackgammon knockout (7 matches, 3 stages) | GPU; knockout: Claude, xAI, Liquid, Fastino, GPU | ≈ 1 h; knockout ≈ 3 stages × up to 3.3 h (Grok 4.7 (on) in QF3) |
| 3 | Terra (high), 11 or 13 matches (after your go) | Claude, xAI, Gemini | ≈ 3.3 h |
| 4 | Terra (low), 11 or 13 matches (after your go) | Claude, xAI, Gemini | ≈ 3.3 h |
| 5 | The three Kimi matches, last, one at a time, credit checked before each | OpenRouter | ≈ 3 × 15 min |

**Serialized ChatGPT time for the three late entries: ≈ 3.5 + 3.3 + 3.3 + 0.75 ≈ 11 h**, plus the Cup and knockout in between.

## OpenRouter: the Kimi matches may not all fit

The only billed cost is Kimi K3.1 Pro (off), one match per late entry: ≈ $0.42 each (Kimi's 14 v3.db matches: $0.24–0.61). Three matches: **≈ $1.26, worst ≈ $1.83**. The credit was **$1.75** at 15:30 UTC today (`/api/v1/credits`), and the key is shared with the Turkish benchmark (`mailbox/OpenRouter usage 2026-10-28.md`). Astra (high)'s Kimi match fits. The two Terra Kimi matches fit only if no other spend comes first and they run at the central cost. Each is checked against the credit before it starts, and a match that would not fit is not started.

## Note for later: Terra (high) in the Nackgammon paired test stays on hold

GPT-6.1 Terra (low) is in the paired test through **OpenRouter** (OpenAI endpoint, choice only). A Terra (high) added there through **Codex** would change the route and the effort at once, so its drop would not be comparable with Terra (low)'s. Terra (high) in the paired test stays on hold.

Waiting for Can's go on the Terra matches, and on the 12-or-14 question.

## Update 2026-10-28: cancelled (Can)

Can cancelled the League 3 entries of GPT-6.1 Terra (low) and (high): no Terra league match is played. They are to join a reasoning sweep on shared positions later. GPT-6 Astra (high)'s entry continues; its Kimi K3.1 Pro (off) match is the only Kimi match, played last after a credit check.
