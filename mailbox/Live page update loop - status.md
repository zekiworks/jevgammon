# Live page: update loop and the four fixes

Oct 22, 2026, 13:50 UTC · reply to the relayed message 2

## Is the loop stopped?

No. `v3-page-refresh.timer` is active and runs every 15 minutes; its last run was 13:45 UTC and the next is 14:00 UTC. The log for each run ends "scored: 0 new decisions … no change".

The page's "data as of" is the time of the newest recorded move, not the time of the last check. Two things made it look stopped:

- **"21 Oct 13:49 UTC":** League 2 was paused at 13:37 that day, and 13:49 was League 3's last move before it finished. The 14:00 run published that; every run from 14:15 to 22:15 found no new moves and published nothing, so the time stayed at 13:49. When League 2 resumed at 22:02, the 22:30 run moved it on again.
- **Now, "22 Oct 06:13 UTC":** League 2 was paused again at about 06:00 today (the GPUs were handed back). The page currently reads "League 2: 132 of 136 matches, paused", which is correct.

Possible improvement, not made yet: show "last checked <time>" next to "data as of". It would need a commit every 15 minutes even with no new data, so I'd show it only on the preview site, whose loop already writes a status file. Say if you want it on the live page too.

## The four live-page fixes

All four are deployed (analysis `3eca8e4`, jevgammon `0a97729`, 21 Oct) and the loop keeps them:

1. Every number in the v3 notes is generated from the same data as the tables, or removed.
2. League 3's heading has no "(in progress)"; the header line is generated from the leagues' status.
3. Reasoning notes say "no clear difference in league play", followed by "League games are not the same positions, so these are not paired comparisons."
4. Decider v1.1, v1.2 and Flash v1.2 cost reads "list-price estimate; runs on our GPUs".

Checked on the live page just now: "League 2: 132 of 136 matches, paused" and the "list-price estimate" label (4 occurrences) are there.

## Next

- Licence check of github.com/atlanai/decision-bench against analysis/decision-models/: in progress; reply will be "Licence check - decision-bench.md".
- Brief v6: design note first ("Backgammon site - design note.md"), then the v6 changes on the preview, then "Part B website - v6 delivery.md" with the preview URL and the B13 list. Code from decision-models is reused only after the licence check.
- Part A: Fable 5.1 and Grok 4.7 skipped as asked (their rows from 21 Oct are kept, marked "also in League 3").
- The league runner is not changed.
