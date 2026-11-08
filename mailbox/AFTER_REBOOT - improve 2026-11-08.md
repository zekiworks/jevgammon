# After the 8 Nov ~20:21 UTC reboot — "Did they improve?" (jevgammon)

State before reboot (20:19 UTC):
- Site: main 28660c7 pushed (merge of improve-status 6522002, 'waiting for a GPU' reason). Zeki GO #3303. Deploy not yet verified; then switch the exporter's GPU_WAIT_TEXT to 'waiting for a GPU' (Zeki: only after the accepting validator is live).
- OpenRouter lane (improve-openrouter): stopped, hold on qwen3.8-flash-off (key limit 403; Can must raise the key's $200 limit). GLM/Kimi/DeepSeek holds (#3215). Key-limit pause harness 4a972b4 has Zeki GO #3287.
- Local lane (improve-local): stopped, holds on gemma-4-31b-on, qwen3.8-27b-on, lfm2.5-24b-a2b-on (GPU 3 fell off the bus 20:06:06; hardware check needed; Can's call).
- Subscription lane (improve-subs): RUNNING at reboot (Gemini 3.8 Flash 2/5). Transient unit: will NOT restart by itself. The interrupted series is archived and replayed from game 1 with the same dice on resume (plan §5).
- Exporter units (improve-export.path / timer): check they come back; if transient, restart.

Resume (from ~/code/jevgammon-improve):
1. `systemctl --user list-units --all | grep improve` — see what came back.
2. Restart the subscription lane exactly as Improve started it (see history of agent Improve / run_subs.sh), binary target/improve-bin/jevgammon-1270c04.
3. Restart the exporter (path + timer) if missing.
4. Restart ~/code/jevgammon/workspace/improve-watch.sh (WATCH_UNITS="improve-subs").
5. Do NOT start the local lane until Can clears GPU 3; do NOT start OpenRouter until the key works (/credits read OK) — then delete qwen hold and restart per Improve's command.
6. Verify the site deploy of 28660c7, then switch GPU_WAIT_TEXT.
