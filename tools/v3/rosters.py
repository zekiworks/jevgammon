"""Writes the v3 rosters leagues/league1.json, league2.json and league3.json (design, Leagues and
players), with every setup's provider pin, quantization, reasoning effort and list price.

    python3 tools/v3/rosters.py

Open models' "on" setups use the lowest effort their API offers (OpenRouter reasoning_effort
"low"; local Gemma and Qwen have no effort knob and think at the chat template's default);
closed models keep low and high. OpenRouter endpoints are pinned (provider.order, no
fallbacks, require_parameters) and read letter probabilities from the answer token
(letter_readout "answer"). Prices: OpenRouter endpoint pricing (14 Oct 2026; OpenRouter's
reported cost is logged when present) and the API list prices of the Turkish benchmark's price
table; local models have no price.
"""

import json

ORDER_SEED = json.load(open("seeds.json"))["option_order_seed"]
OR = "https://openrouter.ai/api/v1"


def common(seed, note):
    return {"note": note, "prompt_version": "bg-v2", "seed": seed, "order_seed": ORDER_SEED,
            "rounds": 3, "clock": 300, "delay": 30, "max_turns": 300}


def price(i, o):
    return {"input_per_mtok": i, "output_per_mtok": o}


def openrouter(name, slug, tag, quant, effort, p, top=20, note=None, readout="answer", schema=True, parallel=8):
    pin = {"order": [tag], "allow_fallbacks": False, "require_parameters": True}
    request = {"provider": pin, "usage": {"include": True}}
    if effort is None:
        request["reasoning"] = {"enabled": False}
    if not schema:
        # The endpoint takes no JSON schema: the letter is unconstrained.
        request["response_format"] = None
    d = {"name": name, "spec": f"openai-compatible/{slug}", "base_url": OR,
         "api_key_env": "OPENROUTER_API_KEY", "provider": f"openrouter:{tag}", "quantization": quant,
         "request": request, "letter_readout": readout, "price": p, "parallel": parallel,
         "rpm": 18}
    if effort:
        d["reasoning"] = effort
    if top != 20:
        d["top_logprobs"] = top
    if note:
        d["note"] = note
    return d


def local(name, model, url, quant, thinking_on, kwargs_on, kwargs_off, note, parallel=8):
    d = {"name": name, "spec": f"local/{model}", "base_url": url, "provider": "local-vllm",
         "quantization": quant, "parallel": parallel, "note": note}
    if thinking_on:
        # No effort knob: thinking on with the chat template's default depth; the
        # reasoning_effort field is not sent.
        d["reasoning"] = "template default"
        d["max_tokens"] = 24000  # the servers' context is 32,768 tokens with the ~4k prompt
        d["request"] = {"chat_template_kwargs": kwargs_on, "reasoning_effort": None}
    else:
        d["request"] = {"chat_template_kwargs": kwargs_off}
    return d


def gemini(name, model, level, p, note=None):
    d = {"name": name, "spec": f"gemini/{model}", "provider": "gemini-api", "reasoning": level,
         "price": p, "parallel": 4}
    if note:
        d["note"] = note
    return d


def sub(name, spec, provider, level, p):
    return {"name": name, "spec": spec, "provider": provider, "reasoning": level, "price": p,
            "parallel": 4, "note": "subscription login; cost is API-list-price equivalent"}


GNUBG = {"name": "GNUbg weak", "spec": "gnubg-weak", "provider": "local",
         "note": "gnubg 1.08 Beginner level (0-ply, deterministic noise 0.060)", "parallel": 1}

# Our servers (tools/v3/servers/README.md): served model, URL, quantization, thinking switch.
L = json.loads("""{"decider": {"quant": "bf16"}, "clef": {"quant": "bf16"}, "openjev": {"quant": "bf16"}, "cygnet": {"quant": "bf16"},
 "gemma": {"model": "gemma-4-31B-it", "url": "http://127.0.0.1:8894/v1", "quant": "fp8 (bf16 checkpoint quantized by vLLM at load; fp8 KV cache)", "on": {"enable_thinking": true}, "off": {"enable_thinking": false}},
 "qwen": {"model": "qwen3.8-flash-next", "url": "http://127.0.0.1:8896/v1", "quant": "fp8 (checkpoint, 128x128 block scales)", "on": {"enable_thinking": true}, "off": {"enable_thinking": false}}}""")

league1 = common(2567889193785291627, "v3 League 1: decision models and models on our own hardware")
league1["players"] = [
    {"name": "Jev 1.13.0", "spec": "jev/jev-1.13.0", "provider": "typesafe", "price": price(0.042, 0)},
    {"name": "GPT-6 Luna", "spec": "openai-decisions/gpt-6-luna", "provider": "openai-decisions",
     "price": price(0.1, 0)},
    {"name": "Decider v1.1 27B", "spec": "pplx-local", "provider": "local (pplx-decider server.py)",
     "quantization": L["decider"]["quant"], "price": price(0.02, 0), "parallel": 1,
     "note": "runs on our GPUs (Perplexity hosting of v1.1 unverified); price = Perplexity list price"},
    {"name": "SubQ Snap Preview", "spec": "subq/subq-snap-preview", "provider": "subq",
     "price": price(0.05, 0)},
    {"name": "Fastino GLiDE", "spec": "fastino", "provider": "fastino", "price": price(0.15, 0)},
    {"name": "Celeris-1 Decision", "spec": "celeris/celeris-1-decision", "provider": "celeris",
     "price": price(0.04, 0)},
    {"name": "Clef", "spec": "clef", "provider": "local", "quantization": L["clef"]["quant"], "parallel": 1},
    {"name": "Open-Jev 27B v1.1", "spec": "open-jev", "provider": "local",
     "quantization": L["openjev"]["quant"], "parallel": 1},
    {"name": "Cygnet (Gemma 4 12B)", "spec": "cygnet", "provider": "local",
     "quantization": L["cygnet"]["quant"], "parallel": 4},
    local("Gemma 4 31B (off)", L["gemma"]["model"], L["gemma"]["url"], L["gemma"]["quant"], False,
          L["gemma"]["on"], L["gemma"]["off"], "thinking off; vLLM on our GPUs", parallel=4),
    local("Gemma 4 31B (on)", L["gemma"]["model"], L["gemma"]["url"], L["gemma"]["quant"], True,
          L["gemma"]["on"], L["gemma"]["off"], "thinking on (enable_thinking); no effort knob, template default", parallel=4),
    openrouter("Qwen3.8-27B (off)", "qwen/qwen3.8-27b", "cerebras/fp16", "fp16", None, price(0.99, 1.49),
               schema=False, parallel=2, note="Cerebras takes no response_format: unconstrained letter"),
    openrouter("Qwen3.8-27B (on)", "qwen/qwen3.8-27b", "cerebras/fp16", "fp16", "low", price(0.99, 1.49),
               schema=False, parallel=2, note="reasoning effort low; Cerebras takes no response_format: unconstrained letter"),
    {"name": "Random", "spec": "random", "provider": "local"},
    {"name": "Safest", "spec": "safest", "provider": "local"},
    GNUBG,
]

league2 = common(8637860750269043463, "v3 League 2: workhorses, closed and open")
league2["players"] = [
    gemini("Gemini 3.8 Flash (low)", "gemini-3.8-flash", "low", price(0.75, 3.75)),
    gemini("Gemini 3.8 Flash (high)", "gemini-3.8-flash", "high", price(0.75, 3.75)),
    sub("Claude Sonnet 5.5 (low)", "anthropic/claude-sonnet-5-5", "claude-subscription", "low", price(2, 10)),
    sub("Claude Sonnet 5.5 (high)", "anthropic/claude-sonnet-5-5", "claude-subscription", "high", price(2, 10)),
    sub("GPT-6.1 Sol (low)", "openai/gpt-6.1-sol", "chatgpt-subscription", "low", price(2, 10)),
    sub("GPT-6.1 Sol (high)", "openai/gpt-6.1-sol", "chatgpt-subscription", "high", price(2, 10)),
    openrouter("DeepSeek V4.1 Flash (off)", "deepseek/deepseek-v4.1-flash", "fireworks", None, None,
               price(0.3, 1.2), top=5, note="Fireworks via OpenRouter; quantization not published; top_logprobs max 5"),
    openrouter("DeepSeek V4.1 Flash (on)", "deepseek/deepseek-v4.1-flash", "fireworks", None, "low",
               price(0.3, 1.2), top=5, note="reasoning effort low; letter logprobs read from the answer after reasoning"),
    local("Qwen3.8 Flash Next (off)", L["qwen"]["model"], L["qwen"]["url"], L["qwen"]["quant"], False,
          L["qwen"]["on"], L["qwen"]["off"], "not on OpenRouter: our GPUs, same build as v1; thinking off"),
    local("Qwen3.8 Flash Next (on)", L["qwen"]["model"], L["qwen"]["url"], L["qwen"]["quant"], True,
          L["qwen"]["on"], L["qwen"]["off"], "thinking on (enable_thinking); no effort knob, template default"),
    openrouter("GLM-5.3 (on)", "z-ai/glm-5.3", "fireworks", None, "low", price(1.4, 4.4), top=5,
               note="reasoning is mandatory on this endpoint, so no off setup; effort low"),
    GNUBG,
]

league3 = common(3685413082999515901, "v3 League 3: frontier, closed and open")
league3["players"] = [
    sub("GPT-6 Astra (low)", "openai/gpt-6-astra", "chatgpt-subscription", "low", price(10, 50)),
    sub("GPT-6 Astra (high)", "openai/gpt-6-astra", "chatgpt-subscription", "high", price(10, 50)),
    sub("Claude Opus 5.5 (low)", "anthropic/claude-opus-5-5", "claude-subscription", "low", price(4, 20)),
    sub("Claude Opus 5.5 (high)", "anthropic/claude-opus-5-5", "claude-subscription", "high", price(4, 20)),
    gemini("Gemini 4 Argon (low)", "gemini-4-argon", "low", price(2, 10),
           note="thinking level low spends no reasoning tokens: effectively off"),
    gemini("Gemini 4 Argon (high)", "gemini-4-argon", "high", price(2, 10), note="effectively on"),
    openrouter("DeepSeek V4 Pro (off)", "deepseek/deepseek-v4-pro", "novita/fp8", "fp8", None, price(1.6, 3.2),
               schema=False, note="Novita takes no JSON schema: unconstrained letter"),
    openrouter("DeepSeek V4 Pro (on)", "deepseek/deepseek-v4-pro", "novita/fp8", "fp8", "low", price(1.6, 3.2),
               schema=False, note="reasoning effort low; Novita takes no JSON schema: unconstrained letter"),
    openrouter("Qwen3.8-Max (on)", "qwen/qwen3.8-2.4t-a95b", "together", None, "low", price(2, 6),
               note="joins only if its open weights are confirmed (listed as open on OpenRouter); "
                    "reasoning mandatory, so no off setup; effort low"),
    GNUBG,
]

for i, league in enumerate([league1, league2, league3], 1):
    with open(f"leagues/league{i}.json", "w") as f:
        json.dump(league, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(i, len(league["players"]))
