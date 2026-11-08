# Render comparison

## 1. Files
2550 files in origin/main's render, 2550 in the candidate's; only in one: none; different: ['bg.css', 'bg.js', 'index.html', 'tables.js']

## 2. Numbers
Leaderboard rows with a details box: origin/main 63, candidate 63.

Rows whose numbers (row + box) differ: 0. Home page outside the leaderboard table: text identical.

## 3. Box first line
63 of 63 rows ok (expected = origin/main's first line + its sub-line; 'Maker not recorded' left out; late tag unchanged; no sub-line).

| Box | Row | First line | Tag | OK |
|---|---|---|---|---|
| hl-1-box | ranked | GPT-6 Astra (high) · OpenAI · chat model · high | late entry | yes |
| hl-1-1-box | other setting | GPT-6 Astra (low) · OpenAI · chat model · low |  | yes |
| hl-1-2-box | other setting | GPT-6 Astra (medium) · OpenAI · chat model · medium |  | yes |
| hl-2-box | ranked | Gemini 4 Argon (high) · Google · chat model · high |  | yes |
| hl-2-1-box | other setting | Gemini 4 Argon (low) · Google · chat model · low |  | yes |
| hl-3-box | ranked | Claude Fable 5.1 (high) · Anthropic · chat model · high |  | yes |
| hl-3-1-box | other setting | Claude Fable 5.1 (low) · Anthropic · chat model · low |  | yes |
| hl-4-box | ranked | GPT-6.1 Sol (high) · OpenAI · chat model · high |  | yes |
| hl-4-1-box | other setting | GPT-6.1 Sol (low) · OpenAI · chat model · low |  | yes |
| hl-5-box | ranked | Claude Opus 5.5 (high) · Anthropic · chat model · high |  | yes |
| hl-5-1-box | other setting | Claude Opus 5.5 (low) · Anthropic · chat model · low |  | yes |
| hl-6-box | ranked | DeepSeek V4.1 Flash (low) · DeepSeek · chat model · low |  | yes |
| hl-6-1-box | other setting | DeepSeek V4.1 Flash 1017 (low) · DeepSeek · chat model · low |  | yes |
| hl-6-2-box | other setting | DeepSeek V4.1 Flash (off) · DeepSeek · chat model · off |  | yes |
| hl-6-3-box | other setting | DeepSeek V4.1 Flash 1017 (off) · DeepSeek · chat model · off |  | yes |
| hl-7-box | ranked | Grok 4.7 (high) · xAI · chat model · high |  | yes |
| hl-7-1-box | other setting | Grok 4.7 (low) · xAI · chat model · low |  | yes |
| hl-8-box | ranked | Claude Sonnet 5.5 (high) · Anthropic · chat model · high |  | yes |
| hl-8-1-box | other setting | Claude Sonnet 5.5 (low) · Anthropic · chat model · low |  | yes |
| hl-9-box | ranked | Gemini 3.8 Flash (high) · Google · chat model · high |  | yes |
| hl-9-1-box | other setting | Gemini 3.8 Flash (low) · Google · chat model · low |  | yes |
| hl-10-box | ranked | Kimi K3.1 Pro (off) · Moonshot · chat model · off |  | yes |
| hl-11-box | ranked | Gemma 4 31B (on) · Google · chat model · on |  | yes |
| hl-11-1-box | other setting | Gemma 4 31B (off) · Google · chat model · off |  | yes |
| hl-12-box | ranked | Liquid d1-ultra · Liquid AI · decision model |  | yes |
| hl-13-box | ranked | Base Labs Mammoth-1 · Base Labs · decision model | late entry | yes |
| hl-14-box | ranked | Drex Max v1 · Nace.AI · decision model | late entry · provisional | yes |
| hl-15-box | ranked | Qwen3.8-27B (low) · Alibaba (Qwen) · chat model · low |  | yes |
| hl-15-1-box | other setting | Qwen3.8-27B (off) · Alibaba (Qwen) · chat model · off |  | yes |
| hl-16-box | ranked | GLM-5.3 (low) · Z.ai · chat model · low |  | yes |
| hl-17-box | ranked | REAX 1.3 · REAX Labs · decision model | late entry · provisional | yes |
| hl-18-box | ranked | Fastino GLiDE · Fastino · decision model |  | yes |
| hl-19-box | ranked | Jev 1.13.0 · TypeSafe · decision model |  | yes |
| hl-20-box | ranked | Qwen3.8 Flash (off) · Alibaba (Qwen) · chat model · off |  | yes |
| hl-21-box | ranked | Jev 1.14.0 · TypeSafe · decision model |  | yes |
| hl-22-box | ranked | Drex Max 1.1 · Nace.AI · decision model | late entry · provisional | yes |
| hl-23-box | ranked | Fastino GLiDE v1.2 (local) · Fastino · decision model |  | yes |
| hl-24-box | ranked | Drex 2.0 · Nace.AI · decision model | late entry · provisional | yes |
| hl-24-1-box | other setting | Drex 2.0 (local) · Nace.AI · decision model | late entry · provisional | yes |
| hl-25-box | ranked | Decider v1.2 27B · Perplexity · decision model |  | yes |
| hl-26-box | ranked | Celeris-1 Decision · Celeris · decision model |  | yes |
| hl-27-box | ranked | Base Labs Elephant-1 · Base Labs · decision model | late entry | yes |
| hl-28-box | ranked | Clef · decision model |  | yes |
| hl-29-box | ranked | Cygnet (Gemma 4 12B) · Google · chat model |  | yes |
| hl-30-box | ranked | Decider v1.1 27B · Perplexity · decision model |  | yes |
| hl-31-box | ranked | SubQ Snap 1.1 · SubQ · decision model | late entry | yes |
| hl-32-box | ranked | SubQ Snap Preview · SubQ · decision model |  | yes |
| hl-33-box | ranked | GPT-6 Luna · OpenAI · decision model |  | yes |
| hl-34-box | ranked | Winnow-12B · decision model |  | yes |
| hl-35-box | ranked | Mercury Decide · Inception · decision model |  | yes |
| hl-36-box | ranked | LFM2.5-24B-A2B (on) · Liquid AI · chat model · on |  | yes |
| hl-36-1-box | other setting | LFM2.5-24B-A2B (off) · Liquid AI · chat model · off |  | yes |
| hl-37-box | ranked | Decider Flash v1.2 · Perplexity · decision model |  | yes |
| hl-38-box | ranked | Open-Jev 27B v1.1 · decision model |  | yes |
| hl-p-1-box | program | GNUbg weak · x86-64 build: its noise is shifted, so it overplays gammons |  | yes |
| hl-p-1-1-box | other setting | GNUbg weak · x86-64 build: its noise is shifted, so it overplays gammons |  | yes |
| hl-p-1-2-box | other setting | GNUbg weak · x86-64 build: its noise is shifted, so it overplays gammons |  | yes |
| hl-p-2-box | program | Safest · always plays safe |  | yes |
| hl-p-2-1-box | other setting | Safest (computed) · always plays safe |  | yes |
| hl-p-2-2-box | other setting | Safest (computed) · always plays safe |  | yes |
| hl-p-3-box | program | Random · a random legal play |  | yes |
| hl-p-3-1-box | other setting | Random (computed) · a random legal play |  | yes |
| hl-p-3-2-box | other setting | Random (computed) · a random legal play |  | yes |

**Failures: 0**
