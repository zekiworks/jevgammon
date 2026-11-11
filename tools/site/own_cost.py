"""Cost of the setups that ran on our own machines, and of hosted setups priced from our token counts (Ümit #4399
JOB 7; content/own_cost.json holds the rule, the machines' rates and each setup's machine timeline).

Own machines: per setup and dataset, its answers from our machines in time order; each step between two consecutive
answers of at most gap_minutes counts as wall-clock time on the machine the later answer came from (the setup's spans,
else one RTX PRO 6000), times that machine's hourly rate and the GPUs the setup's server used; longer steps are left
out and listed. One setup's simultaneous matches count once (the union of its own answer times); other setups' servers
on the same machine are not separated, so each setup is charged the whole device ('GPU time, at most'). A mixed-route
setup's hosted answers keep their recorded cost. A machine with an input left null: its hours, no dollar figure.
"""

import json
from datetime import datetime, timezone

from common import CONTENT

C = json.loads((CONTENT / "own_cost.json").read_text())
LABEL = C["label"]
GAP_S = C["gap_minutes"] * 60
MACHINES = C["machines"]
SETUPS = C["setups"]
TOKEN_PRICED = C["token_priced"]


def _t(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def spark_parts() -> tuple | None:
    """(purchase CHF/h, electricity CHF/h, total CHF/h, USD/h) of the DGX Spark, or None while an input is null."""
    m = MACHINES["dgx_spark"]
    keys = ("purchase_chf", "years", "hours_per_year", "kwh_chf", "watts", "chf_usd")
    if any(m.get(k) is None for k in keys):
        return None
    buy = m["purchase_chf"] / (m["years"] * m["hours_per_year"])
    power = m["kwh_chf"] * m["watts"] / 1000
    return buy, power, buy + power, (buy + power) * m["chf_usd"]


def rate(machine: str) -> float | None:
    """USD per GPU-hour of a machine; None while its inputs are not all known."""
    if machine == "rtx_pro_6000":
        return MACHINES[machine]["usd_per_gpu_hour"]
    parts = spark_parts()
    return parts[3] if parts else None


def _where(spans: list, at: float) -> tuple[str, int]:
    for s in spans:
        if _t(s["from"]) <= at < _t(s["to"]):
            return s["machine"], s.get("gpus", 1)
    return "rtx_pro_6000", 1


def _local(d: dict) -> bool:
    return (d.get("provider") or "").startswith("local")


def cost(name: str, decs: list[dict]) -> dict | None:
    """The setup's cost record, or None for a setup this file does not list. usd: the total, None while a machine's
    rate is pending; usd_per_1000 over every decision of the setup in the dataset."""
    if name in TOKEN_PRICED:
        p = TOKEN_PRICED[name]
        tin, tout = sum(d["tin"] or 0 for d in decs), sum(d["tout"] or 0 for d in decs)
        usd = (tin * p["input_per_mtok"] + tout * p["output_per_mtok"]) / 1e6
        return dict(kind="tokens", decisions=len(decs), tokens_in=tin, tokens_out=tout,
                    input_per_mtok=p["input_per_mtok"], output_per_mtok=p["output_per_mtok"], source=p["source"],
                    usd=usd, usd_per_1000=1000 * usd / len(decs) if decs else None)
    if name not in SETUPS:
        return None
    spans = SETUPS[name]
    local = sorted(_t(d["at"]) for d in decs if _local(d))
    hosted = [d for d in decs if not _local(d)]
    api_usd = sum(d["cost"] for d in hosted if d["cost"] is not None)
    hours, gaps = {}, []
    for a, b in zip(local, local[1:]):
        if b - a > GAP_S:
            gaps.append([datetime.fromtimestamp(a, timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                         datetime.fromtimestamp(b, timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), round((b - a) / 60)])
            continue
        machine, gpus = _where(spans, b)
        key = f"{machine}/{gpus}"
        hours[key] = hours.get(key, 0) + (b - a) / 3600
    parts = []
    gpu_usd = 0.0
    for key, h in sorted(hours.items()):
        machine, gpus = key.split("/")
        r = rate(machine)
        usd = h * int(gpus) * r if r is not None else None
        parts.append(dict(machine=machine, gpus=int(gpus), hours=h, usd_per_gpu_hour=r, usd=usd))
        gpu_usd = None if usd is None or gpu_usd is None else gpu_usd + usd
    usd = gpu_usd + api_usd if gpu_usd is not None else None
    sp = spark_parts() if any(p["machine"] == "dgx_spark" for p in parts) else None
    return dict(kind="gpu", estimate=True, provenance="content/own_cost.json: wall clock on our machines \u00d7 hourly rate",
                spark_rate=dict(purchase_chf_per_h=sp[0], electricity_chf_per_h=sp[1], chf_per_h=sp[2],
                                usd_per_h=sp[3]) if sp else None,
                decisions=len(decs), gpu_decisions=len(local), hosted_decisions=len(hosted),
                excluded_hours=sum(g[2] for g in gaps) / 60,
                hosted_usd=api_usd, hosted_unpriced=sum(1 for d in hosted if d["cost"] is None), parts=parts,
                hours=sum(hours.values()), gaps=gaps, gpu_usd=gpu_usd, usd=usd,
                usd_per_1000=1000 * usd / len(decs) if usd is not None and decs else None)


def apply(name: str, decs: list[dict], quality: dict, phases: dict) -> None:
    """Replaces the setup's recorded cost with its own-machine (or token-priced) cost: usd_per_1000 and
    cost_coverage on the whole and on each phase (the same rate per decision), the record under own_cost."""
    c = cost(name, decs)
    if c is None:
        return
    for q in (quality, *phases.values()):
        q["own_cost"] = c
        q.pop("usd_per_1000", None)
        if c["usd_per_1000"] is not None and q.get("decisions"):
            q["usd_per_1000"] = c["usd_per_1000"]
            q["cost_coverage"] = 1.0


def _h(x: float) -> str:
    return f"{x:,.1f}" if x >= 0.1 else f"{x:.2f}"


def spark_formula() -> str | None:
    """The DGX Spark rate, purchase part and electricity part (logic #4416, Ümit #4421; Zeki #4430: the electricity
    part uses the GB10 chip's measured draw at the ewz.natur high rate)."""
    p = spark_parts()
    if p is None:
        return None
    m = MACHINES["dgx_spark"]
    return (f'NVIDIA DGX Spark (GB10): CHF {m["purchase_chf"]:,.0f} \u00f7 ({m["years"]} years \u00d7 '
            f'{m["hours_per_year"]:,} h) = CHF {p[0]:.3f}/h purchase + CHF {m["kwh_chf"]}/kWh (ewz.natur high rate) '
            f'\u00d7 {m["watts"] / 1000:.4f} kW (the chip\'s measured draw, not the whole box) = CHF {p[1]:.3f}/h '
            f'electricity; CHF {p[2]:.3f}/h \u2248 ${p[3]:.3f}/h (CHF 1 = ${m["chf_usd"]}, ECB {m["chf_usd_date"]})')


def basis(c: dict) -> str | None:
    """Where a setup on our machines ran, for the cost cell's second line (Ümit #4665 item 4, as logic #4685): the
    machine it used most, 'RTX PRO 6000 Blackwell' or 'DGX Spark', and ' + API' where some of its answers came from the
    hosted API (each machine's part and the hosted part are in the tooltip). None for a token-priced setup (its dollar
    figure is a recorded price, not an estimate)."""
    if c["kind"] == "tokens":
        return None
    parts = sorted(c["parts"], key=lambda p: -p["hours"] * p["gpus"])  # the machine it used most first
    machine = MACHINES[parts[0]["machine"]]["short"] if parts else "our machines"
    return machine + (" + API" if c["hosted_decisions"] else "")


def tooltip(c: dict, every_gap: bool = True) -> str:
    """The cost cell's tooltip: the formula with this setup's figures (plain text, for a title attribute); every_gap
    False (the details box): the count and total length of the left-out gaps instead of each one."""
    if c["kind"] == "tokens":
        return (f'List price \u00d7 our recorded tokens: {c["tokens_in"]:,} input tokens \u00d7 ${c["input_per_mtok"]:g} '
                f'per 1M (output ${c["output_per_mtok"]:g}) = ${c["usd"]:.2f} \u00f7 {c["decisions"]:,} decisions '
                f'({c["source"]})')
    terms = []
    for p in c["parts"]:
        m = MACHINES[p["machine"]]
        count = f'{p["gpus"]} \u00d7 ' if p["gpus"] > 1 else ""
        price = (f' \u00d7 ${p["usd_per_gpu_hour"]:.3g}/h' + (f' \u00d7 {p["gpus"]}' if p["gpus"] > 1 else "")
                 + f' = ${p["usd"]:.2f}' if p["usd"] is not None else " (rate pending)")
        terms.append(f'{_h(p["hours"])} h on {count}{m["name"]}{price}')
    hosted = (f'; plus {c["hosted_decisions"]:,} answers from the hosted API at their recorded cost, '
              f'${c["hosted_usd"]:.2f}' if c["hosted_decisions"] else "")
    total = (f'; total ${c["usd"]:.2f} \u00f7 {c["decisions"]:,} decisions' if c["usd"] is not None
             else f'; no dollar figure until the rate is known; {c["decisions"]:,} decisions')
    if not c["gaps"]:
        gaps = "; no gap over 10 min"
    elif every_gap:
        gaps = ("; left out, gaps over 10 min between consecutive answers: "
                + ", ".join(f'{a} to {b} ({m:,} min)' for a, b, m in c["gaps"]))
    else:
        gaps = (f'; left out: {len(c["gaps"]):,} gaps over 10 min between consecutive answers, '
                f'{_h(c["excluded_hours"])} h in all (each one listed in the data file)')
    spark = spark_formula() if any(p["machine"] == "dgx_spark" for p in c["parts"]) else None
    rtx = MACHINES["rtx_pro_6000"]
    rtx_line = (f'{rtx["name"]}: ${rtx["usd_per_gpu_hour"]}/h per GPU'
                if any(p["machine"] == "rtx_pro_6000" for p in c["parts"]) else None)
    head = (f'Estimate: ${c["usd_per_1000"]:.3f} per 1,000 decisions ({LABEL}). ' if c["usd_per_1000"] is not None
            else f'{LABEL}: {_h(c["hours"])} h, no dollar estimate until the rate is known. ')
    return (head + 'Counted as the wall clock from the first to the last answer, pauses over 10 min left out, '
            '\u00d7 the hourly rate \u00f7 decisions. '
            + " + ".join(terms) + hosted + total + gaps + ". "
            + " ".join(f"{x}." for x in (rtx_line, spark) if x)
            + " Other setups' servers may have run on the same machine at the same time; each setup is charged the "
              "whole device, so this is an upper bound.")
