# Ladder and Hype Cup: response

Oct 23, 2026 · reply to "backgammon-ladder-cup.md"

## Confirmed

The plan works with the runner, with the decisions below (agreed with Can today). All three leagues have finished, so the ladder can start once the storage change is deployed and round 1 is approved. No league is playing, so changing the runner is allowed now.

## Decisions taken with Can

- **Setups move, not models.** Each off/on or low/high setup is its own row in the tables and moves on its own. A Cup can therefore hold two setups of one model.
- **One match format:** both games of a round played at the same time, as in Leagues 2 and 3 (game 2's prompt shows the round-start score). League 1 played its games in sequence; its existing matches stay as played, and the page says so.
- **Budget: per round.** Before each round I write its new pairings, estimated money cost, estimated GPU time and needed GPUs to mailbox/, and Can approves the round. Nothing starts without that approval. The Cup is approved the same way.

## How results are stored by pairing

The "participants" database layout (built and tested Oct 19, not deployed yet) is deployed before round 1:

- `players`: one row per setup. `league_players`: who is in which league, with join and leave times, so a mover's old matches leave its old league's table but stay in the database.
- `matches`: every match with its two setups, its rules and a valid flag. A league's table is the valid matches between its current members.
- **Reuse:** before any ladder or Cup match is scheduled, the pairing (two setup names, order ignored) is looked up across all leagues, ladder rounds and Cups. If a valid match exists, it stands and no new match is played. The page links to where it was played.
- **Migration check:** the migration recomputes every league table the old way and the new way and must show them identical before it is kept, as tested on a copy on Oct 19.
- **Ranking:** points, then games, then the lower error rate (GNUbg-scored league decisions), as the file asks. This replaces the runner's playoffs. One effect: League 1's top two are tied on 48 points and on games; GNUbg weak has the lower error rate and ranks first, but programs never move, so Liquid d1-ultra is still League 1's mover.

## Round 1 (estimate, not started)

| Boundary | Moves up | Moves down |
| --- | --- | --- |
| League 1 ↔ 2 | Liquid d1-ultra (League 1 winner; GNUbg weak is a program) | LFM2.5-24B-A2B (off) (League 2 last) |
| League 2 ↔ 3 | GPT-6.1 Sol (low) (League 2 winner) | Claude Fable 5.1 (off) (League 3 last) |

About 56 new matches: Liquid d1-ultra about 16, LFM2.5 (off) about 17, GPT-6.1 Sol (low) about 9, Claude Fable 5.1 (off) about 14. Pairings already played, such as every mover against GNUbg weak, are reused. The exact list goes to mailbox/ with the round-1 approval request.

- **Money:** about $3–5. OpenRouter for the matches against DeepSeek V4.1 Flash, GLM-5.3 and Qwen3.8 Flash; Liquid's API for d1-ultra (about $0.14 per 1,000 decisions). The Claude, ChatGPT, Gemini and Grok matches run on subscriptions (API-equivalent cost shown separately, no money).
- **GPU time is the real cost.** Matches against the reasoning-on setups on our GPUs (Gemma 4 31B, Qwen3.8-27B, LFM2.5) take hours each, and League 1's local decision models need two or three GPUs while LFM2.5 (off) plays them. The bariton GPUs are with the compactor agent now; I'll arrange time over the agent bus.

## Hype Cup (estimate)

At most 7 new matches (4 quarter-finals, 2 semis, final), fewer if pairings were already played. Mostly frontier and workhorse setups on subscriptions: little or no money, but slow when a reasoning-on setup plays. Ties: Cup matches use the runner's decisive mode, extra rounds until someone leads, as the old playoffs did.

## Website

Ladder section, Hype Cup page, Cup champion in the champions strip, the honesty line, and the rules explanation, all generated from the database like the rest of the site, with GNUbg labelled as a program. These are new sections, so they go live after Ümit approves them (brief v12, B2).
