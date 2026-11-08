"""A PDF report for one investigation: summary first, then the reasoning, the evidence and the test, with charts.

The report is HTML with inline SVG charts, printed to PDF by headless Chrome (or Chromium). Every number comes from
insights.metrics, so the report shows what the investigation recorded and nothing else. All text from the model is
escaped.
"""

from __future__ import annotations

import html
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from insights import SOURCE_KIND

Json = dict[str, Any]
INK, MUTED, LINE, ACCENT = '#1b1f24', '#5b6470', '#e3e6ea', '#2f5bd3'
FOR, AGAINST, NEUTRAL = '#2e7d4f', '#c0392b', '#9aa3ad'


def e(text: Any) -> str:
    return html.escape(str(text if text is not None else ''))


def cut(text: Any) -> str:
    """Model text the length limit stopped mid-sentence is shown ending in an ellipsis, so it reads as cut."""
    text = str(text or '').rstrip()
    return e(text + '…' if text and text[-1].isalnum() and len(text) > 60 else text)


def browser() -> str | None:
    for name in (os.environ.get('LEXSI_CHROME'), 'google-chrome', 'chromium', 'chromium-browser', 'google-chrome-stable'):
        if name and shutil.which(name):
            return shutil.which(name)
    return None


def belief_chart(beliefs: list[Json], scale: list[str]) -> str:
    """One row per explanation on the five-step scale; an arrow when new evidence moved it."""
    w, row, left = 640, 46, 210
    h = 34 + row * len(beliefs)
    step = (w - left - 44) / (len(scale) - 1)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="How likely the agent judged each explanation">']
    for i, label in enumerate(scale):
        x = left + i * step
        out.append(f'<line x1="{x}" y1="22" x2="{x}" y2="{h - 6}" stroke="{LINE}"/>')
        out.append(f'<text x="{x}" y="14" font-size="10" fill="{MUTED}" text-anchor="middle">{e(label)}</text>')
    for r, b in enumerate(beliefs):
        y = 34 + r * row + 10
        name = f"{b['id']}{' (favoured)' if b['favoured'] else ''}"
        out.append(f'<text x="0" y="{y + 4}" font-size="11.5" fill="{INK}" font-weight="{600 if b["favoured"] else 400}">{e(name)}</text>')
        if b['before_step'] is not None:
            x0 = left + b['before_step'] * step
            if b['after_step'] is not None and b['after_step'] != b['before_step']:
                x1 = left + b['after_step'] * step
                out.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{ACCENT}" stroke-width="2" marker-end="url(#arrow)"/>')
                out.append(f'<circle cx="{x0}" cy="{y}" r="6" fill="#fff" stroke="{ACCENT}" stroke-width="2"/>')
                out.append(f'<circle cx="{x1}" cy="{y}" r="7" fill="{ACCENT}"/>')
            else:
                out.append(f'<circle cx="{x0}" cy="{y}" r="7" fill="{ACCENT}"/>')
        else:
            out.append(f'<text x="{left}" y="{y + 4}" font-size="11" fill="{MUTED}">not stated</text>')
    out.insert(1, f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{ACCENT}"/></marker></defs>')
    out.append('</svg>')
    return ''.join(out)


def evidence_chart(rows: list[Json]) -> str:
    """Stacked bars: sources supporting, neutral and contradicting each explanation."""
    w, row, left = 640, 34, 60
    most = max([r['supports'] + r['contradicts'] + r['neutral'] for r in rows] + [1])
    unit = (w - left - 60) / most
    h = 12 + row * len(rows)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="Evidence for and against each explanation">']
    for i, r in enumerate(rows):
        y, x = 6 + i * row, left
        out.append(f'<text x="0" y="{y + 15}" font-size="11.5" fill="{INK}">{e(r["id"])}</text>')
        for key, colour in (('supports', FOR), ('neutral', NEUTRAL), ('contradicts', AGAINST)):
            n = r[key]
            if n:
                out.append(f'<rect x="{x}" y="{y}" width="{max(n * unit - 2, 2)}" height="20" rx="4" fill="{colour}"/>')
                out.append(f'<text x="{x + n * unit / 2 - 1}" y="{y + 14}" font-size="10.5" fill="#fff" text-anchor="middle">{n}</text>')
                x += n * unit
        total = r['supports'] + r['contradicts'] + r['neutral']
        if not total:
            out.append(f'<text x="{left}" y="{y + 15}" font-size="11" fill="{MUTED}">no evidence assessed</text>')
    out.append('</svg>')
    return ''.join(out)


def meter(value: float | None, limit: float | None, unit: str) -> str:
    if value is None or not limit:
        return ''
    share = max(0.0, min(float(value) / float(limit), 1.0))
    return (
        f'<div class="meter"><div class="bar"><span style="width:{share * 100:.0f}%"></span></div>'
        f'<p>{e(_fmt(value))} {e(unit)} of {e(_fmt(limit))} available ({share * 100:.0f}%)</p></div>'
    )


def _fmt(n: Any) -> str:
    try:
        f = float(n)
    except (TypeError, ValueError):
        return str(n)
    return f'{f:,.0f}'


CSS = f"""
@page {{ size: A4; margin: 16mm 15mm 18mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: {INK}; font-size: 10.5pt; line-height: 1.5; margin: 0; }}
h1 {{ font-size: 19pt; line-height: 1.25; margin: 4px 0 6px; letter-spacing: -.01em; }}
h2 {{ font-size: 13pt; margin: 22px 0 8px; padding-bottom: 4px; border-bottom: 1px solid {LINE}; }}
h3 {{ font-size: 11pt; margin: 14px 0 4px; }}
p {{ margin: 0 0 8px; }}
.eyebrow {{ color: {ACCENT}; font-weight: 700; font-size: 8.5pt; letter-spacing: .08em; text-transform: uppercase; }}
.meta {{ color: {MUTED}; font-size: 9pt; }}
.answer {{ background: #f3f6fd; border-left: 4px solid {ACCENT}; border-radius: 6px; padding: 12px 14px; margin: 14px 0; }}
.answer p.big {{ font-size: 12pt; font-weight: 600; }}
.stopped {{ background: #fff6e5; border-left-color: #c98a00; }}
.kpis {{ display: flex; gap: 10px; margin: 12px 0; }}
.kpi {{ flex: 1; border: 1px solid {LINE}; border-radius: 8px; padding: 8px 10px; }}
.kpi b {{ display: block; font-size: 16pt; line-height: 1.2; }}
.kpi span {{ color: {MUTED}; font-size: 8.5pt; }}
.note {{ color: {MUTED}; font-size: 8.5pt; }}
.legend span {{ display: inline-flex; align-items: center; gap: 4px; margin-right: 12px; font-size: 8.5pt; color: {MUTED}; }}
.legend i {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
.meter .bar {{ height: 8px; background: {LINE}; border-radius: 4px; overflow: hidden; margin: 4px 0; }}
.meter .bar span {{ display: block; height: 100%; background: {ACCENT}; }}
.meter p {{ font-size: 9pt; color: {MUTED}; }}
table {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
th, td {{ text-align: left; vertical-align: top; padding: 6px 6px; border-bottom: 1px solid {LINE}; }}
th {{ color: {MUTED}; font-weight: 600; }}
.tag {{ display: inline-block; border-radius: 10px; padding: 0 7px; font-size: 8pt; font-weight: 600; }}
.supports {{ background: #e3f3e9; color: {FOR}; }} .contradicts {{ background: #fbe7e4; color: {AGAINST}; }} .neutral {{ background: #eef0f2; color: {MUTED}; }}
ul {{ margin: 0 0 8px; padding-left: 18px; }}
.qa {{ break-inside: avoid; margin-bottom: 10px; }}
.qa b {{ display: block; }}
.page-break {{ break-before: page; }}
footer {{ margin-top: 24px; color: {MUTED}; font-size: 8pt; border-top: 1px solid {LINE}; padding-top: 6px; }}
"""


def build(record: Json, m: Json, company: str, asked: str, followups: list[Json], made: float | None = None) -> str:
    final = record.get('final') or {}
    theories = record.get('theories') or {}
    sources = record.get('sources') or {}
    beliefs, ev, test = m['beliefs'], m['evidence'], m['test']
    independent = sum(s['count'] for s in m['sources'] if s['class'] == 'verified_observation')
    total_sources = sum(s['count'] for s in m['sources'])
    when = time.strftime('%d %B %Y', time.localtime(made or time.time()))
    parts = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{e(asked)}</title><style>{CSS}</style></head><body>']
    parts.append(f'<p class="eyebrow">Strategy investigation · {e(company)}</p><h1>{e(asked)}</h1><p class="meta">Report generated {e(when)} by Strategy Lab</p>')
    if final:
        parts.append(f'<div class="answer"><p class="eyebrow">Recommendation</p><p class="big">{cut(final.get("recommendation"))}</p>')
        if final.get('next_action'):
            parts.append(f'<p><b>Next step:</b> {cut(final.get("next_action"))}</p>')
        parts.append('</div>')
    else:
        parts.append('<div class="answer stopped"><p class="eyebrow">No recommendation</p><p>The investigation stopped before it reached a recommendation. What it found up to that point is below.</p></div>')
    test_kpi = f'€{_fmt(test["cost"])}' if test and not test.get('declined') and test.get('cost') is not None else ('declined' if test and test.get('declined') else '—')
    parts.append(
        '<div class="kpis">'
        f'<div class="kpi"><b>{total_sources}</b><span>sources used</span></div>'
        f'<div class="kpi"><b>{independent}</b><span>independent sources (not the company\'s own claims)</span></div>'
        f'<div class="kpi"><b>{len(record.get("assessments") or [])}</b><span>pieces of evidence weighed</span></div>'
        f'<div class="kpi"><b>{e(test_kpi)}</b><span>proposed test</span></div>'
        '</div>'
    )
    if final.get('uncertainty') or final.get('would_change_if'):
        parts.append('<h2>What we are unsure of, and what would change the answer</h2>')
        if final.get('uncertainty'):
            parts.append(f'<p>{cut(final.get("uncertainty"))}</p>')
        if final.get('would_change_if'):
            parts.append('<ul>' + ''.join(f'<li>{cut(w)}</li>' for w in final['would_change_if']) + '</ul>')
    if beliefs:
        parts.append('<h2>How likely each explanation looked</h2>')
        parts.append(belief_chart(beliefs, m['scale']))
        moved = any(b['after_step'] is not None and b['after_step'] != b['before_step'] for b in beliefs)
        parts.append('<p class="note">The agent\'s own judgement on a five-step scale, not a measured probability.' + (' An arrow shows how new evidence moved it.' if moved else '') + '</p>')
    if theories:
        parts.append('<h2>The explanations considered</h2>')
        for tid, t in theories.items():
            parts.append(f'<h3>{e(tid)}: {e(t.get("claim"))}</h3>')
            facts = [('Who benefits', t.get('who_benefits')), ('Why behaviour would change', t.get('why_behaviour_changes')), ('How the company earns from it', t.get('how_value_is_captured'))]
            parts.append('<ul>' + ''.join(f'<li><b>{e(k)}:</b> {e(v)}</li>' for k, v in facts if v) + '</ul>')
    if ev:
        parts.append('<h2>Evidence for and against each explanation</h2>')
        parts.append(f'<p class="legend"><span><i style="background:{FOR}"></i>supports</span><span><i style="background:{NEUTRAL}"></i>neutral</span><span><i style="background:{AGAINST}"></i>contradicts</span></p>')
        parts.append(evidence_chart(ev))
    if record.get('assessments'):
        parts.append('<table><thead><tr><th style="width:9%">For</th><th style="width:13%">Verdict</th><th>What the source says</th><th style="width:24%">Source</th></tr></thead><tbody>')
        for a in record['assessments']:
            s = sources.get(a.get('evidence_id')) or {}
            kind = SOURCE_KIND.get(s.get('class') or a.get('class'), s.get('class') or '')
            parts.append(
                f'<tr><td>{e(a.get("theory_id"))}</td><td><span class="tag {e(a.get("direction"))}">{e(a.get("direction"))}</span></td>'
                f'<td>“{e(a.get("quote"))}”' + (f'<br><span class="note">Does not show: {e(a.get("does_not_show"))}</span>' if a.get('does_not_show') else '') + '</td>'
                f'<td>{e(s.get("title") or a.get("evidence_id"))}<br><span class="note">{e(kind)} · {e(s.get("date"))}</span></td></tr>'
            )
        parts.append('</tbody></table>')
    if test and not test.get('declined'):
        parts.append('<h2 class="page-break">The proposed test</h2>')
        parts.append(f'<h3>{e(test.get("name"))}</h3><p>{e(test.get("method"))}</p>')
        parts.append(f'<p><b>Who takes part:</b> {e(test.get("sample"))}</p><p><b>What is measured:</b> {e(test.get("measure"))}</p>')
        parts.append(meter(test.get('cost'), test.get('budget'), 'EUR') + meter(test.get('weeks'), test.get('max_weeks'), 'weeks'))
        if test.get('predictions'):
            parts.append('<table><thead><tr><th style="width:12%">If true</th><th>The test should show</th></tr></thead><tbody>' + ''.join(f'<tr><td>{e(k)}</td><td>{e(v)}</td></tr>' for k, v in test['predictions'].items()) + '</tbody></table>')
        if test.get('rule'):
            parts.append(f'<p style="margin-top:8px"><b>What to do with the result:</b> {e(test.get("rule"))}</p>')
    elif test and test.get('declined'):
        parts.append(f'<h2>Why no test was proposed</h2><p>{e(test.get("reason"))}</p>')
    answered = [f for f in followups if f.get('answer')]
    if answered:
        parts.append('<h2>Follow-up questions</h2>')
        for f in answered:
            cited = ', '.join(e((sources.get(s) or {}).get('title') or s) for s in f.get('sources') or [])
            parts.append(f'<div class="qa"><b>{e(f["question"])}</b><p>{cut(f["answer"])}</p>' + (f'<p class="note">Sources: {cited}</p>' if cited else '') + '</div>')
    if sources:
        parts.append('<h2>Sources</h2><table><thead><tr><th>Source</th><th style="width:22%">Kind</th><th style="width:16%">Date</th></tr></thead><tbody>')
        for s in sources.values():
            title = f'<a href="{e(s["url"])}">{e(s.get("title"))}</a>' if s.get('url') else e(s.get('title'))
            parts.append(f'<tr><td>{title}</td><td>{e(SOURCE_KIND.get(s.get("class"), s.get("class")))}</td><td>{e(s.get("date"))}</td></tr>')
        parts.append('</tbody></table>')
    parts.append('<footer>Prepared by an AI research agent from public sources and the evidence listed above. Simulated what-if results are labelled and are never treated as evidence of real demand. Check the sources before acting.</footer></body></html>')
    return ''.join(parts)


def pdf(page: str) -> bytes:
    chrome = browser()
    if chrome is None:
        raise RuntimeError('no Chrome or Chromium found to print the report; set LEXSI_CHROME')
    with tempfile.TemporaryDirectory(prefix='lexsi-report-') as folder:
        source, target = Path(folder) / 'report.html', Path(folder) / 'report.pdf'
        source.write_text(page, encoding='utf-8')
        subprocess.run(
            [chrome, '--headless=new', '--disable-gpu', '--no-sandbox', f'--user-data-dir={folder}/profile', '--no-pdf-header-footer',
             f'--print-to-pdf={target}', source.as_uri()],
            check=True, timeout=90, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return target.read_bytes()
