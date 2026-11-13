"""A PDF report for one investigation, laid out like a short consulting brief.

Page one is the executive summary: the question, the recommendation and how sure it is, the next step, what would change
the answer, four headline numbers and the explanations compared. Then numbered sections: why customers might buy (with
the evidence for and against each explanation as quote cards), the proposed test, follow-up questions, and an appendix
with every source and how the report was made. Every number comes from insights.metrics; all model text is escaped.

The page is HTML with inline SVG charts, printed by headless Chrome (or Chromium) through its DevTools protocol, which
adds a running footer with page numbers; without the protocol it falls back to the plain --print-to-pdf command.
"""

from __future__ import annotations

import base64
import html
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from insights import SOURCE_KIND

Json = dict[str, Any]
INK, INK2, MUTED, LINE, WASH = '#17181c', '#4a4d55', '#6b6e76', '#e4e3de', '#f4f6fb'
ACCENT, ACCENT_INK, FOR, AGAINST, NEUTRAL = '#2f5bd3', '#1f45a8', '#0f7b6c', '#c2410c', '#9aa0a8'
KIND_COLOUR = {'verified_observation': '#334155', 'company_claim': '#a16207', 'synthetic': '#7c3aed', 'web_page': '#8a8f98', 'user_document': '#0e7490'}
LEVEL_COLOUR = {'High': ('#e6f2e9', '#1f7a3a'), 'Moderate': ('#eaf0fd', '#1f45a8'), 'Low': ('#fbf1e1', '#8a5a00')}


def e(text: Any) -> str:
    return html.escape(str(text if text is not None else ''))


def cut(text: Any) -> str:
    """Model text the length limit stopped mid-sentence ends in an ellipsis, so it reads as cut, not as a typo."""
    text = str(text or '').rstrip()
    return e(text + '…' if text and text[-1].isalnum() and len(text) > 60 else text)


def _fmt(n: Any) -> str:
    try:
        return f'{float(n):,.0f}'
    except (TypeError, ValueError):
        return str(n)


def browser() -> str | None:
    for name in (os.environ.get('LEXSI_CHROME'), 'google-chrome', 'chromium', 'chromium-browser', 'google-chrome-stable'):
        if name and shutil.which(name):
            return shutil.which(name)
    for path in ('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium'):
        if os.path.exists(path):  # macOS installs the browser as an app, not on PATH
            return path
    return None


# ---------- charts ----------

def belief_chart(beliefs: list[Json], scale: list[str], names: dict[str, str]) -> str:
    w, row, left, pad = 660, 50, 190, 46
    h = 30 + row * len(beliefs)
    step = (w - left - pad) / (len(scale) - 1)
    x = lambda i: left + i * step  # noqa: E731
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="How likely each explanation was judged">',
           f'<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/></marker></defs>']
    out.append(f'<rect x="{left - 14}" y="20" width="{w - left - pad + 28}" height="{h - 22}" rx="8" fill="{WASH}"/>')
    for i, label in enumerate(scale):
        out.append(f'<line x1="{x(i)}" y1="24" x2="{x(i)}" y2="{h - 6}" stroke="{LINE}" stroke-width="1"/>')
        out.append(f'<text x="{x(i)}" y="13" font-size="10" fill="{MUTED}" text-anchor="middle">{e(label)}</text>')
    for r, b in enumerate(beliefs):
        y = 30 + r * row + row / 2 - 4
        weight = 700 if b['favoured'] else 500
        out.append(f'<text x="0" y="{y - 3}" font-size="12" font-weight="{weight}" fill="{ACCENT_INK if b["favoured"] else INK}">{e(names.get(b["id"], b["id"]))}{" ★" if b["favoured"] else ""}</text>')
        claim = b['claim'] if len(b['claim']) <= 32 else b['claim'][:31].rstrip() + '…'
        out.append(f'<text x="0" y="{y + 12}" font-size="9.5" fill="{MUTED}">{e(claim)}</text>')
        if b['before_step'] is None:
            out.append(f'<text x="{left}" y="{y + 4}" font-size="10.5" fill="{MUTED}">not stated</text>')
            continue
        x0 = x(b['before_step'])
        if b['after_step'] is not None and b['after_step'] != b['before_step']:
            x1 = x(b['after_step'])
            out.append(f'<line x1="{x0}" y1="{y}" x2="{x1 + (-9 if x1 > x0 else 9)}" y2="{y}" stroke="{ACCENT}" stroke-width="2.5" marker-end="url(#ah)"/>')
            out.append(f'<circle cx="{x0}" cy="{y}" r="6" fill="#fff" stroke="{ACCENT}" stroke-width="2"/><circle cx="{x1}" cy="{y}" r="7.5" fill="{ACCENT}" stroke="#fff" stroke-width="2"/>')
        else:
            out.append(f'<circle cx="{x0}" cy="{y}" r="7.5" fill="{ACCENT}" stroke="#fff" stroke-width="2"/>')
    out.append('</svg>')
    return ''.join(out)


def evidence_chart(rows: list[Json], names: dict[str, str]) -> str:
    """Diverging bars from a centre line: sources against to the left, for to the right; neutral as a count."""
    w, row, label_w, neutral_w = 660, 32, 130, 80
    half = (w - label_w - neutral_w) / 2
    centre = label_w + half
    most = max([max(r['supports'], r['contradicts']) for r in rows] + [1])
    h = 26 + row * len(rows)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Sources for and against each explanation">',
           f'<text x="{centre - 8}" y="12" font-size="10" font-weight="600" fill="{AGAINST}" text-anchor="end">− against</text>',
           f'<text x="{centre + 8}" y="12" font-size="10" font-weight="600" fill="{FOR}">for +</text>',
           f'<text x="{w - neutral_w / 2}" y="12" font-size="10" fill="{MUTED}" text-anchor="middle">no bearing</text>']
    for i, r in enumerate(rows):
        y = 22 + i * row
        out.append(f'<text x="0" y="{y + 14}" font-size="11.5" font-weight="600" fill="{INK}">{e(names.get(r["id"], r["id"]))}</text>')
        if r['contradicts']:
            bw = r['contradicts'] / most * (half - 24)
            out.append(f'<rect x="{centre - bw - 1}" y="{y + 2}" width="{bw}" height="18" rx="3" fill="{AGAINST}"/><text x="{centre - bw - 6}" y="{y + 15}" font-size="10.5" fill="{INK}" text-anchor="end">{r["contradicts"]}</text>')
        if r['supports']:
            bw = r['supports'] / most * (half - 24)
            out.append(f'<rect x="{centre + 1}" y="{y + 2}" width="{bw}" height="18" rx="3" fill="{FOR}"/><text x="{centre + bw + 6}" y="{y + 15}" font-size="10.5" fill="{INK}">{r["supports"]}</text>')
        if not r['supports'] and not r['contradicts']:
            out.append(f'<text x="{centre}" y="{y + 15}" font-size="10" fill="{MUTED}" text-anchor="middle">none for or against</text>')
        out.append(f'<text x="{w - neutral_w / 2}" y="{y + 15}" font-size="11" fill="{MUTED}" text-anchor="middle">{r["neutral"]}</text>')
    out.append(f'<line x1="{centre}" y1="20" x2="{centre}" y2="{h}" stroke="{INK2}" stroke-width="1.5"/></svg>')
    return ''.join(out)


def source_bar(sources: list[Json]) -> str:
    total = sum(s['count'] for s in sources)
    if not total:
        return ''
    segs = ''.join(f'<span style="flex:{s["count"]};background:{KIND_COLOUR.get(s["class"], NEUTRAL)}"></span>' for s in sources)
    legend = ''.join(f'<span><i style="background:{KIND_COLOUR.get(s["class"], NEUTRAL)}"></i>{s["count"]} {e(s["label"].lower())}</span>' for s in sources)
    return f'<div class="stack">{segs}</div><p class="legend">{legend}</p>'


def bullet(label: str, value: Any, limit: Any, unit: str) -> str:
    if value is None or not limit:
        return ''
    share = max(0.0, min(float(value) / float(limit), 1.0))
    shown = f'€{_fmt(value)}' if unit == 'EUR' else f'{_fmt(value)} {unit}'
    of = f'€{_fmt(limit)}' if unit == 'EUR' else f'{_fmt(limit)} {unit}'
    return (f'<div class="bullet"><div class="bullet-head"><span>{e(label)}</span><b>{e(shown)} <span class="muted">of {e(of)}</span></b></div>'
            f'<div class="track"><span style="width:{share * 100:.0f}%"></span></div></div>')


# ---------- page ----------

CSS = f"""
@page {{ size: A4; margin: 15mm 15mm 17mm; }}
* {{ box-sizing: border-box; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ font-family: Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: {INK}; font-size: 10pt; line-height: 1.5; margin: 0; font-feature-settings: "cv11", "ss01"; }}
p {{ margin: 0 0 6px; }}
.muted {{ color: {MUTED}; }}
.cover {{ border-radius: 14px; padding: 22px 24px 20px; color: #fff; background: linear-gradient(120deg, #1f3d99 0%, {ACCENT} 55%, #6d4fc2 100%); margin-bottom: 16px; }}
.cover .brand {{ display: flex; justify-content: space-between; align-items: center; font-size: 8.5pt; letter-spacing: .08em; text-transform: uppercase; opacity: .9; }}
.cover .brand b {{ display: inline-flex; align-items: center; gap: 8px; letter-spacing: .04em; }}
.cover .brand i {{ display: inline-grid; place-items: center; width: 20px; height: 20px; border-radius: 6px; background: rgba(255,255,255,.22); font-style: normal; font-weight: 800; }}
.cover h1 {{ font-size: 19pt; line-height: 1.22; letter-spacing: -.015em; margin: 14px 0 6px; font-weight: 750; }}
.cover .meta {{ font-size: 9pt; opacity: .85; }}
.answer {{ border: 1px solid {LINE}; border-left: 5px solid {ACCENT}; border-radius: 12px; padding: 14px 18px; margin-bottom: 12px; break-inside: avoid; }}
.answer.stopped {{ border-left-color: #c98a00; }}
.kicker {{ font-size: 8pt; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; color: {ACCENT_INK}; margin-bottom: 4px; }}
.big {{ font-size: 13.5pt; line-height: 1.38; font-weight: 650; letter-spacing: -.01em; margin-bottom: 8px; }}
.conf {{ display: flex; gap: 10px; align-items: baseline; margin: 6px 0 8px; font-size: 9.5pt; }}
.dots {{ display: inline-flex; gap: 3px; align-self: center; }} .dots i {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
.conf b {{ flex: none; border-radius: 999px; padding: 2px 10px; font-size: 8.5pt; }}
.two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.box {{ background: {WASH}; border-radius: 10px; padding: 10px 14px; break-inside: avoid; }}
.box ul {{ margin: 0; padding-left: 16px; }}
.box li {{ margin-bottom: 3px; }}
.kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 12px 0; }}
.kpi {{ border: 1px solid {LINE}; border-radius: 10px; padding: 10px 12px; }}
.kpi b {{ display: block; font-size: 17pt; line-height: 1.15; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }}
.kpi span {{ color: {MUTED}; font-size: 8.5pt; }}
h2 {{ font-size: 13pt; letter-spacing: -.01em; margin: 20px 0 10px; display: flex; align-items: baseline; gap: 10px; break-after: avoid; }}
h2 .n {{ display: inline-grid; place-items: center; min-width: 22px; height: 22px; border-radius: 6px; background: {ACCENT}; color: #fff; font-size: 9.5pt; font-weight: 750; }}
h3 {{ font-size: 10.5pt; margin: 0 0 4px; break-after: avoid; }}
.caption {{ font-size: 8.5pt; color: {MUTED}; margin-top: 2px; }}
.page-break {{ break-before: page; }}
.keep {{ break-inside: avoid; }}
.explanation {{ border: 1px solid {LINE}; border-radius: 12px; padding: 12px 16px; margin-bottom: 10px; }}
.explanation.leading {{ border-color: #b9c8f3; background: linear-gradient(0deg, #fff, {WASH}); }}
.explanation .tag {{ display: inline-block; font-size: 8pt; font-weight: 700; border-radius: 999px; padding: 1px 8px; background: #eaf0fd; color: {ACCENT_INK}; margin-left: 6px; }}
dl {{ display: grid; grid-template-columns: 150px 1fr; gap: 3px 12px; margin: 6px 0 8px; font-size: 9.5pt; }}
dt {{ color: {MUTED}; font-weight: 600; }} dd {{ margin: 0; }}
.quote {{ border-left: 3px solid {NEUTRAL}; padding: 4px 0 4px 10px; margin: 6px 0; break-inside: avoid; font-size: 9.5pt; }}
.quote.supports {{ border-left-color: {FOR}; }} .quote.contradicts {{ border-left-color: {AGAINST}; }}
.quote .verdict {{ font-size: 8pt; font-weight: 750; text-transform: uppercase; letter-spacing: .05em; color: {MUTED}; }}
.quote.supports .verdict {{ color: {FOR}; }} .quote.contradicts .verdict {{ color: {AGAINST}; }}
.quote .src {{ font-size: 8.5pt; color: {MUTED}; }}
.kind {{ display: inline-block; color: #fff; font-size: 7.5pt; font-weight: 700; border-radius: 999px; padding: 0 7px; margin-right: 4px; }}
.stack {{ display: flex; gap: 2px; height: 12px; border-radius: 6px; overflow: hidden; margin: 4px 0 6px; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 8.5pt; color: {INK2}; }}
.legend i {{ display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }}
.bullets {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 10px 0; }}
.bullet-head {{ display: flex; justify-content: space-between; font-size: 9pt; margin-bottom: 4px; }}
.track {{ height: 8px; border-radius: 999px; background: {LINE}; overflow: hidden; }}
.track span {{ display: block; height: 100%; background: {ACCENT}; border-radius: 999px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
th, td {{ text-align: left; vertical-align: top; padding: 6px 8px; border-bottom: 1px solid {LINE}; }}
th {{ color: {MUTED}; font-weight: 600; font-size: 8.5pt; }}
tr {{ break-inside: avoid; }}
.rule {{ background: #eaf0fd; border-radius: 10px; padding: 10px 14px; margin-top: 10px; break-inside: avoid; }}
.qa {{ break-inside: avoid; margin-bottom: 10px; }}
.qa .q {{ font-weight: 650; }}
.qa .a {{ background: {WASH}; border-radius: 10px; padding: 8px 12px; margin-top: 4px; }}
.sources td:first-child {{ width: 24px; color: {MUTED}; font-variant-numeric: tabular-nums; }}
.sources .excerpt {{ color: {INK2}; font-size: 8.5pt; }}
a {{ color: {ACCENT_INK}; text-decoration: none; }}
.method {{ font-size: 8.5pt; color: {INK2}; }}
.method li {{ margin-bottom: 3px; }}
"""


def build(record: Json, m: Json, company: str, asked: str, followups: list[Json], made: float | None = None) -> str:
    final = record.get('final') or {}
    theories = record.get('theories') or {}
    sources = record.get('sources') or {}
    names = {tid: f'Explanation {i + 1}' for i, tid in enumerate(theories)}
    number = {sid: i + 1 for i, sid in enumerate(sources)}
    beliefs, ev, test, sure = m['beliefs'], m['evidence'], m['test'], m.get('confidence')
    independent = sum(s['count'] for s in m['sources'] if s['class'] == 'verified_observation')
    when = time.strftime('%d %B %Y', time.localtime(made or time.time()))
    lead = next((b for b in beliefs if b['favoured']), None)
    section = iter(range(1, 20))
    p = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{e(asked)}</title>',
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">',
         f'<style>{CSS}</style></head><body>']

    # page one: executive summary
    p.append(f'<div class="cover"><div class="brand"><b><i>a</i>aemon</b><span>Strategy brief · {e(company)}</span></div>'
             f'<h1>{e(asked)}</h1><p class="meta">{e(when)} · prepared from public sources by an AI research assistant</p></div>')
    if final:
        if final.get('draft'):
            p.append(f'<div class="answer stopped"><p class="kicker" style="color:#8a5a00">Draft recommendation</p>'
                     f'<p class="caption">The investigation stopped early{(" because " + e(final.get("stopped_because"))) if final.get("stopped_because") else ""}, so this was written from what it had found.</p>'
                     f'<p class="big">{cut(final.get("recommendation"))}</p>')
        else:
            p.append(f'<div class="answer"><p class="kicker">Our recommendation</p><p class="big">{cut(final.get("recommendation"))}</p>')
        if sure:
            bg, fg = LEVEL_COLOUR[sure['level']]
            dots = ''.join(f'<i style="background:{fg if i < sure["score"] else LINE}"></i>' for i in range(sure['out_of']))
            ticks = ' · '.join(f'{"✓" if c["passed"] else "✗"} {e(c["label"])}' for c in sure['checks'])
            p.append(f'<div class="conf"><b style="background:{bg};color:{fg}">{e(sure["level"])} confidence · {sure["score"]}/{sure["out_of"]}</b><span class="dots">{dots}</span><span>{e(sure["action"])}</span></div>'
                     f'<p class="caption">{ticks}</p>')
        if final.get('next_action'):
            p.append(f'<p><b>Next step:</b> {cut(final.get("next_action"))}</p>')
        p.append('</div>')
    else:
        p.append('<div class="answer stopped"><p class="kicker" style="color:#8a5a00">No recommendation</p>'
                 '<p>The investigation stopped before it reached a recommendation. What it found up to that point follows.</p></div>')
    test_kpi = f'€{_fmt(test["cost"])}' if test and not test.get('declined') and test.get('cost') is not None else ('None' if test and test.get('declined') else '—')
    test_sub = (f'test, of €{_fmt(test["budget"])} budget' if test and not test.get('declined') and test.get('budget') else 'test judged not worth it' if test and test.get('declined') else 'no test designed')
    p.append('<div class="kpis">'
             f'<div class="kpi"><b>{len(beliefs)}</b><span>explanations compared</span></div>'
             f'<div class="kpi"><b>{len(sources)}</b><span>sources, {independent} independent</span></div>'
             f'<div class="kpi"><b>{len(record.get("assessments") or [])}</b><span>pieces of evidence weighed</span></div>'
             f'<div class="kpi"><b>{e(test_kpi)}</b><span>{e(test_sub)}</span></div></div>')
    unsure, change = final.get('uncertainty'), final.get('would_change_if') or []
    if unsure or change:
        p.append('<div class="two">')
        p.append(f'<div class="box"><p class="kicker">What we are unsure of</p><p>{cut(unsure)}</p></div>' if unsure else '<div></div>')
        p.append('<div class="box"><p class="kicker">What would change our mind</p><ul>' + ''.join(f'<li>{cut(w)}</li>' for w in change[:3]) + '</ul></div>' if change else '<div></div>')
        p.append('</div>')
    if beliefs:
        p.append('<div class="keep">')
        p.append(f'<h2><span class="n">{next(section)}</span>The explanations compared</h2>')
        if lead:
            p.append(f'<p><b>Leading: {e(names.get(lead["id"]))}.</b> {cut(lead["claim"])}</p>')
        p.append(belief_chart(beliefs, m['scale'], names))
        moved = any(b['after_step'] is not None and b['after_step'] != b['before_step'] for b in beliefs)
        p.append('<p class="caption">How likely the assistant judged each explanation, on its own five-step scale (not a measured probability).' + (' The arrow shows how new evidence moved it.' if moved else '') + '</p></div>')

    # the reasoning
    if theories:
        p.append(f'<div class="keep"><h2><span class="n">{next(section)}</span>Why customers might buy</h2>')
        if ev:
            p.append(evidence_chart(ev, names))
            p.append('<p class="caption">How many of the sources weighed support or contradict each explanation.</p>')
        p.append('</div>')
        for tid, t in theories.items():
            is_lead = bool(lead and lead['id'] == tid)
            p.append(f'<div class="explanation{" leading" if is_lead else ""}"><h3>{e(names[tid])}{"<span class=tag>★ Leading</span>" if is_lead else ""}</h3><p>{cut(t.get("claim"))}</p>')
            facts = [('Who it is for', t.get('who_benefits')), ('Why they would change', t.get('why_behaviour_changes')), ('How the company earns', t.get('how_value_is_captured'))]
            rows = ''.join(f'<dt>{e(k)}</dt><dd>{cut(v)}</dd>' for k, v in facts if v)
            if rows:
                p.append(f'<dl>{rows}</dl>')
            for a in (record.get('assessments') or []):
                if a.get('theory_id') != tid:
                    continue
                s = sources.get(a.get('evidence_id')) or {}
                kind = s.get('class') or a.get('class') or ''
                verdict = {'supports': '+ For', 'contradicts': '− Against'}.get(a.get('direction'), 'No bearing')
                p.append(f'<div class="quote {e(a.get("direction"))}"><span class="verdict">{verdict}</span> “{e(a.get("quote"))}”'
                         f'<div class="src"><span class="kind" style="background:{KIND_COLOUR.get(kind, NEUTRAL)}">{e(SOURCE_KIND.get(kind, kind))}</span>'
                         f'[{number.get(a.get("evidence_id"), "?")}] {e(s.get("title") or a.get("evidence_id"))}{(" · " + e(s.get("date"))) if s.get("date") else ""}</div>'
                         + (f'<div class="src">Does not show: {cut(a.get("does_not_show"))}</div>' if a.get('does_not_show') else '') + '</div>')
            p.append('</div>')
        p.append('<div class="keep"><h3 style="margin-top:12px">Where the evidence came from</h3>' + source_bar(m['sources']) + '</div>')

    # the test
    if test and not test.get('declined'):
        p.append(f'<div class="keep"><h2><span class="n">{next(section)}</span>The test we propose</h2>')
        p.append(f'<h3>{e(test.get("name"))}</h3><p>{cut(test.get("method"))}</p>')
        p.append('<div class="bullets">' + bullet('Cost', test.get('cost'), test.get('budget'), 'EUR') + bullet('Time', test.get('weeks'), test.get('max_weeks'), 'weeks') + '</div></div>')
        p.append('<dl>' + (f'<dt>Who takes part</dt><dd>{cut(test.get("sample"))}</dd>' if test.get('sample') else '') + (f'<dt>What is measured</dt><dd>{cut(test.get("measure"))}</dd>' if test.get('measure') else '') + '</dl>')
        if test.get('predictions'):
            p.append('<table><thead><tr><th style="width:22%">If this is right…</th><th>…the test should show</th></tr></thead><tbody>'
                     + ''.join(f'<tr><td><b>{e(names.get(k, k))}</b></td><td>{cut(v)}</td></tr>' for k, v in test['predictions'].items()) + '</tbody></table>')
        if test.get('rule'):
            p.append(f'<div class="rule"><p class="kicker">How we will decide</p><p>{cut(test.get("rule"))}</p></div>')
    elif test and test.get('declined'):
        p.append(f'<h2><span class="n">{next(section)}</span>Why a test is not worth it here</h2><p>{cut(test.get("reason"))}</p>')

    answered = [f for f in followups if f.get('answer')]
    if answered:
        p.append(f'<h2><span class="n">{next(section)}</span>Follow-up questions</h2>')
        for f in answered:
            cited = ', '.join(f'[{number.get(s, "?")}]' for s in f.get('sources') or [])
            p.append(f'<div class="qa"><p class="q">{e(f["question"])}</p><div class="a">{cut(f["answer"])}' + (f'<p class="caption">Based on sources {cited}</p>' if cited else '') + '</div></div>')

    # appendix
    if sources:
        p.append('<h2 class="page-break"><span class="n">A</span>Sources</h2><table class="sources"><thead><tr><th>#</th><th>Source</th><th style="width:21%">Kind</th><th style="width:15%">Date</th></tr></thead><tbody>')
        for sid, s in sources.items():
            title = f'<a href="{e(s["url"])}">{e(s.get("title"))}</a>' if s.get('url') else e(s.get('title'))
            excerpt = f'<div class="excerpt">“{e(s.get("excerpt"))}”</div>' if s.get('excerpt') else ''
            kind = s.get('class')
            p.append(f'<tr><td>{number[sid]}</td><td>{title}{excerpt}</td><td><span class="kind" style="background:{KIND_COLOUR.get(kind, NEUTRAL)}">{e(SOURCE_KIND.get(kind, kind))}</span></td><td>{e(s.get("date"))}</td></tr>')
        p.append('</tbody></table>')
    steps = m.get('steps') or {}
    p.append('<h2><span class="n">B</span>How this report was made</h2><ul class="method">'
             f'<li>An AI research assistant ran the investigation in {steps.get("total", 0)} steps: {steps.get("searches", 0)} searches and {steps.get("reads", 0)} sources read. '
             'Every quote was checked against its source; a step that broke a rule was not accepted and changed nothing.</li>'
             '<li>Sources are labelled: independent sources, the company\'s own claims, and simulated what-ifs, which are never treated as evidence of real demand.</li>'
             '<li>How likely each explanation is, and the confidence label, are the assistant\'s own judgement, not measured probabilities. ' + (e(sure['rule']) if sure else '') + '</li>'
             '<li>The assistant knows only the sources listed above. Check them before acting.</li></ul>')
    p.append('</body></html>')
    return ''.join(p)


FOOTER = ('<div style="width:100%;font-family:Inter,Helvetica,Arial,sans-serif;font-size:7.5pt;color:#8a8f98;padding:0 15mm;display:flex;justify-content:space-between">'
          '<span>aemon · {company}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _print_devtools(chrome: str, source: Path, folder: str, company: str) -> bytes:
    import websocket  # websocket-client, already a dependency

    port = _free_port()
    proc = subprocess.Popen([chrome, '--headless=new', '--disable-gpu', '--no-sandbox', f'--remote-debugging-port={port}', f'--user-data-dir={folder}/profile', '--no-first-run', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/json', timeout=1).read())
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError('Chrome did not start')
        ws = websocket.create_connection(next(t for t in tabs if t['type'] == 'page')['webSocketDebuggerUrl'], timeout=60)
        n = [0]

        def call(method: str, **params: Any) -> Json:
            n[0] += 1
            ws.send(json.dumps({'id': n[0], 'method': method, 'params': params}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get('id') == n[0]:
                    return msg.get('result', {})

        call('Page.enable')
        call('Page.navigate', url=source.as_uri())
        for _ in range(60):  # wait for the page and its fonts (the font falls back to the system one when offline)
            if call('Runtime.evaluate', expression="document.readyState === 'complete' && document.fonts.status === 'loaded'", returnByValue=True).get('result', {}).get('value'):
                break
            time.sleep(0.15)
        data = call('Page.printToPDF', printBackground=True, preferCSSPageSize=True, displayHeaderFooter=True,
                    headerTemplate='<div></div>', footerTemplate=FOOTER.replace('{company}', html.escape(company)))['data']
        ws.close()
        return base64.b64decode(data)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def pdf(page: str, company: str = '') -> bytes:
    chrome = browser()
    if chrome is None:
        raise RuntimeError('no Chrome or Chromium found to print the report; set LEXSI_CHROME')
    with tempfile.TemporaryDirectory(prefix='lexsi-report-') as folder:
        source, target = Path(folder) / 'report.html', Path(folder) / 'report.pdf'
        source.write_text(page, encoding='utf-8')
        try:
            return _print_devtools(chrome, source, folder, company)
        except Exception:  # noqa: BLE001  the plain command still makes the report, without page numbers
            subprocess.run([chrome, '--headless=new', '--disable-gpu', '--no-sandbox', f'--user-data-dir={folder}/profile2', '--no-pdf-header-footer',
                            f'--print-to-pdf={target}', source.as_uri()], check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return target.read_bytes()
