"""The Clear risk page (preliminary): the clear-risk scan, its checks, the rollout check and Part 2, rendered from
S["clear_risk"] (content/clear_risk_results.json, written by clear_risk_publish.py from saved reports). Every number on
the page is in that data file; nothing here holds a result number."""

from common import esc

import pages as P


def body(S) -> str:
    C = S["clear_risk"]
    toc = "".join(f'<li><a href="#{s["id"]}">{esc(s["title"])}</a></li>' for s in C["sections"])
    out = [P.page_head(S, C["status"], "Clear risk: when one play is clearly better",
                       esc(C["label"]) + ' Data: <a href="../data/v3/clear-risk.json">clear-risk.json</a> · '
                       '<a href="../method/#clear-risk">Method</a>'),
           f'<nav class="toc card" aria-label="On this page"><ul>{toc}</ul></nav>']
    pend = "".join(f"<li>{esc(p['what'])}: pending. {esc(p['blocker'])}.</li>" for p in C["pending"])
    omit = "".join(f"<li>{esc(o['what'])}: not published ({esc(o['why'])}).</li>" for o in C["omitted"])
    asof = f'<p class="note">{esc(C["scan_as_of"])}</p>' if C.get("scan_as_of") else ""
    out.append(f'<section class="card" id="clear-risk-status"><h2>Status</h2><p class="note">{esc(C["status"])}</p>'
               f"{asof}<ul>{pend}{omit}</ul></section>")
    for s in C["sections"]:
        notes = "".join(f"<li>{esc(n)}</li>" for n in s["notes"])
        tabs = "".join(P.SWIPE + P.table([esc(h) for h in t["head"]],
                                         ["<tr>" + "".join(f'<td{"" if i == 0 else " class=num"}>{esc(c)}</td>'
                                                           for i, c in enumerate(r)) + "</tr>" for r in t["rows"]],
                                         esc(t["caption"]))
                       for t in s["tables"])
        out.append(f'<section class="card" id="{s["id"]}"><h2>{esc(s["title"])}</h2>'
                   f'<p class="note">{esc(C["status"])}</p><ul class="notes">{notes}</ul>{tabs}</section>')
    return "\n".join(out)
