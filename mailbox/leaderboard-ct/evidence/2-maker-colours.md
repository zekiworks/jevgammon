# 2. Maker colours (Ümit #2745 item 7; Main #2749)

One file: `tools/site/content/maker_colors.json` holds the makers, their colours and every setup's maker. Every chart of the home page (Risk judgement, Error rate, Cost, Time, the two finding charts, Too safe) and the leaderboard take a setup's colour from it; `families.json` keeps only the icons (its colours are removed). Switching the other makers from grey to the Decision models site's family colours is an edit of that file (each grey maker records its sibling colour beside it).

| Maker | Colour | Setups |
|---|---|---|
| OpenAI | `#199e70` | GPT-6 Luna, GPT-6.1 Sol (low), GPT-6.1 Sol (high), GPT-6 Astra (low), GPT-6 Astra (medium), GPT-6 Astra (high) |
| Google | `#2a78d6` | Cygnet (Gemma 4 12B), Gemini 3.8 Flash (low), Gemini 3.8 Flash (high), Gemma 4 31B (on), Gemma 4 31B (off), Gemini 4 Argon (low), Gemini 4 Argon (high) |
| Anthropic | `#d9653b` | Claude Sonnet 5.5 (low), Claude Sonnet 5.5 (high), Claude Opus 5.5 (low), Claude Opus 5.5 (high), Claude Fable 5.1 (low), Claude Fable 5.1 (high) |
| xAI | `#6250d6` | Grok 4.7 (low), Grok 4.7 (high) |
| DeepSeek | `#a61e4d` | DeepSeek V4.1 Flash (off), DeepSeek V4.1 Flash (low), DeepSeek V4.1 Flash 1017 (off), DeepSeek V4.1 Flash 1017 (low) |
| Moonshot | `#d55181` | Kimi K3.1 Pro (off) |
| Liquid AI | `#c98500` | Liquid d1-ultra, LFM2.5-24B-A2B (off), LFM2.5-24B-A2B (on) |
| Perplexity (grey for now) | `#8f9399` (sibling: `#9256b3` Perplexity) | Decider v1.1 27B, Decider Flash v1.2, Decider v1.2 27B |
| SubQ (grey for now) | `#8f9399` (sibling: `#fd9cba` SubQ) | SubQ Snap Preview, SubQ Snap 1.1 |
| TypeSafe (grey for now) | `#8f9399` (sibling: `#466fcb` Jev) | Jev 1.14.0, Jev 1.13.0 |
| Celeris (grey for now) | `#8f9399` (sibling: `#9dbdff` Celeris) | Celeris-1 Decision |
| Inception (grey for now) | `#8f9399` (sibling: `#d071bb` Inception) | Mercury Decide |
| Fastino (grey for now) | `#8f9399` (sibling: `#b85207` Fastino) | Fastino GLiDE, Fastino GLiDE v1.2 (local) |
| Z.ai (grey for now) | `#8f9399` (sibling: `#7dd67d` GLM) | GLM-5.3 (low) |
| Alibaba (Qwen) (grey for now) | `#8f9399` (sibling: `#00829a` Qwen) | Qwen3.8 Flash (off), Qwen3.8-27B (off), Qwen3.8-27B (low) |
| Base Labs (grey for now) | `#8f9399` (sibling: `#1aa2eb` Elephant) | Base Labs Elephant-1, Base Labs Mammoth-1 |
| Nace.AI (grey for now) | `#8f9399` (sibling: `#6b7f09` Drex) | Drex Max 1.1, Drex 2.0, Drex Max v1, Drex 2.0 (local) |
| REAX Labs (grey for now) | `#8f9399` | REAX 1.3 |
| Maker not recorded (grey for now) | `#8f9399` | Clef, Open-Jev 27B v1.1, Winnow-12B |

## Existing charts: family colour before → maker colour now

| Family | Before | Maker | Now |
|---|---|---|---|
| Gemini | `#3d7ff0` | Google | `#2a78d6` |
| Gemma | `#dca2ff` | Google | `#2a78d6` |
| GPT | `#18a37a` | OpenAI | `#199e70` |
| Claude | `#f08a3c` | Anthropic | `#d9653b` |
| Grok | `#8da523` | xAI | `#6250d6` |
| Qwen | `#00829a` | Alibaba (Qwen) | `#8f9399` |
| DeepSeek | `#b74771` | DeepSeek | `#a61e4d` |
| GLM | `#7dd67d` | Z.ai | `#8f9399` |
| Kimi | `#14d3f7` | Moonshot | `#d55181` |
| Liquid | `#f2c12e` | Liquid AI | `#c98500` |
| Fastino | `#b85207` | Fastino | `#8f9399` |
| Mammoth | `#ce8703` | Base Labs | `#8f9399` |
| Elephant | `#1aa2eb` | Base Labs | `#8f9399` |
| Drex | `#6b7f09` | Nace.AI | `#8f9399` |
| SubQ | `#fd9cba` | SubQ | `#8f9399` |
| Perplexity | `#9256b3` | Perplexity | `#8f9399` |
| Jev | `#466fcb` | Maker not recorded, TypeSafe | `#8f9399`, `#8f9399` |
| Celeris | `#9dbdff` | Celeris | `#8f9399` |
| Clef | `#9f6700` | Maker not recorded | `#8f9399` |
| Cygnet | `#ffa475` | Google | `#2a78d6` |
| Winnow | `#57b058` | Maker not recorded | `#8f9399` |
| Inception | `#d071bb` | Inception | `#8f9399` |

Setups with no family (no icon) now take their maker's colour as well: Liquid d1-ultra (Liquid AI) was the neutral grey before.

For Ümit: the other makers and their grey: Perplexity, SubQ, TypeSafe, Celeris, Inception, Fastino, Z.ai, Alibaba (Qwen), Base Labs, Nace.AI, REAX Labs, Maker not recorded. Judgement calls recorded in the file: Cygnet is Google's gemma-4-12B-it unchanged behind our letter-reading server, so Google; Winnow-12B (a Gemma fine-tune by its author), Clef and Open-Jev 27B v1.1 have no maker on record; Jev's maker is taken from its API (TypeSafe); the other names come from setups.json's provider, model id or notes (the `source` field per maker).
