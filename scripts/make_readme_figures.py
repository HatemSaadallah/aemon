"""README figures from the committed final-test reports, in a light and a dark version each (GitHub picks one).

Colours: categorical slots 1 and 2 of the reference palette, validated for both surfaces. Fine-tuned is slot 1,
base is slot 2, in every figure. Usage: python scripts/make_readme_figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/figures'
FINAL = ROOT / 'reports/judge/final'
MODES = {
    'light': {'surface': '#fcfcfb', 'text': '#0b0b0b', 'muted': '#52514e', 'grid': '#e4e3df', 'tuned': '#2a78d6', 'base': '#eb6834'},
    'dark': {'surface': '#1a1a19', 'text': '#f0efec', 'muted': '#c3c2b7', 'grid': '#3a3a37', 'tuned': '#3987e5', 'base': '#d95926'},
}
DIMS = {
    'problem_framing': 'Problem framing',
    'causal_mechanism': 'Causal mechanism',
    'distinct_theories': 'Distinct theories',
    'assumptions_predictions': 'Assumptions & predictions',
    'evidence_judgement': 'Evidence judgement',
    'seeking_challenge': 'Seeking challenge',
    'experiment_design': 'Experiment design',
    'revision': 'Revision',
    'recommendation': 'Recommendation',
}


def fmt(value: float) -> str:
    """Half-up to two decimals, so 1.765 reads 1.77 as in the text (Python's float formatting would give 1.76)."""
    from decimal import ROUND_HALF_UP, Decimal

    return str(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def style(ax, c):
    ax.set_facecolor(c['surface'])
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_color(c['grid'])
    ax.tick_params(colors=c['muted'], labelsize=10)
    ax.xaxis.label.set_color(c['muted'])
    ax.yaxis.label.set_color(c['muted'])


def figure(c, w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=160)
    fig.patch.set_facecolor(c['surface'])
    style(ax, c)
    return fig, ax


def save(fig, name, mode):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f'{name}-{mode}.png', facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close(fig)


def quality(report, c, mode):
    groups = [('Judge 1\n(Claude)', report['judges']['claude']['by_arm']), ('Judge 2\n(Codex)', report['judges']['codex']['by_arm'])]
    mean = report['mean_of_judges']['by_arm']
    groups.append(('Mean of\nthe two', {k: {'mean': v} for k, v in mean.items()}))
    fig, ax = figure(c, 7, 3.6)
    width = 0.34
    for i, (label, arm) in enumerate(groups):
        for offset, key, colour in ((-width / 2 - 0.01, 'base', c['base']), (width / 2 + 0.01, 'trained', c['tuned'])):
            value = arm[key]['mean']
            ax.bar(i + offset, value, width, color=colour, edgecolor=c['surface'], linewidth=2)
            ax.text(i + offset, value + 0.04, fmt(value), ha='center', va='bottom', color=c['text'], fontsize=10)
    ax.set_xticks(range(len(groups)), [g[0] for g in groups], color=c['text'])
    ax.set_ylim(0, 3)
    ax.set_ylabel('Blind quality score (0–3)')
    ax.yaxis.grid(True, color=c['grid'], linewidth=0.8)
    ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c['base']), plt.Rectangle((0, 0), 1, 1, color=c['tuned'])]
    legend = ax.legend(handles, ['Base model, best prompt', 'Fine-tuned'], frameon=False, loc='upper left', fontsize=10)
    for t in legend.get_texts():
        t.set_color(c['text'])
    ax.set_title('Final test: four companies never seen in training (96 runs)', color=c['text'], fontsize=12, loc='left')
    save(fig, 'quality', mode)


def differences(report, kinds, c, mode):
    rows = [('All 16 cases', report['mean_of_judges']['difference']['mean_and_95_interval'])]
    names = {'base': 'No new evidence', 'irrelevant': 'Irrelevant evidence', 'supports': 'Supporting what-if', 'undermines': 'Undermining what-if'}
    rows += [(names[k], kinds[k]['mean_and_95_interval']) for k in ('base', 'irrelevant', 'supports', 'undermines')]
    fig, ax = figure(c, 7, 3.2)
    for i, (label, (m, lo, hi)) in enumerate(reversed(rows)):
        ax.plot([lo, hi], [i, i], color=c['tuned'], linewidth=2, solid_capstyle='round')
        ax.plot([m], [i], 'o', color=c['tuned'], markersize=9, markeredgecolor=c['surface'], markeredgewidth=2)
        ax.text(hi + 0.04, i, f'+{fmt(m)}  [{fmt(lo)}, {fmt(hi)}]', va='center', color=c['text'], fontsize=10)
    ax.axvline(0, color=c['muted'], linewidth=1)
    ax.set_yticks(range(len(rows)), [r[0] for r in reversed(rows)], color=c['text'])
    ax.set_xlim(-0.1, 1.95)
    ax.set_xlabel('Fine-tuned minus base, mean of judges, with 95% interval')
    ax.xaxis.grid(True, color=c['grid'], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title('The gain holds for every kind of new evidence', color=c['text'], fontsize=12, loc='left')
    save(fig, 'difference', mode)


def dimensions(report, c, mode):
    def mean(arm, d):
        return sum(report['judges'][j]['by_arm_dimension'][arm][d] for j in ('claude', 'codex')) / 2

    rows = sorted(DIMS, key=lambda d: mean('trained', d) - mean('base', d))
    fig, ax = figure(c, 7, 4.2)
    for i, d in enumerate(rows):
        b, t = mean('base', d), mean('trained', d)
        ax.plot([b, t], [i, i], color=c['grid'], linewidth=3, solid_capstyle='round', zorder=1)
        ax.plot([b], [i], 'o', color=c['base'], markersize=9, markeredgecolor=c['surface'], markeredgewidth=2, zorder=2)
        ax.plot([t], [i], 'o', color=c['tuned'], markersize=9, markeredgecolor=c['surface'], markeredgewidth=2, zorder=3)
    ax.set_yticks(range(len(rows)), [DIMS[d] for d in rows], color=c['text'])
    ax.set_xlim(0, 3)
    ax.set_xlabel('Score per dimension, mean of the two judges (0–3)')
    ax.xaxis.grid(True, color=c['grid'], linewidth=0.8)
    ax.set_axisbelow(True)
    handles = [plt.Line2D([], [], marker='o', linestyle='', color=c['base'], markersize=8), plt.Line2D([], [], marker='o', linestyle='', color=c['tuned'], markersize=8)]
    legend = ax.legend(handles, ['Base model', 'Fine-tuned'], frameon=False, loc='lower right', fontsize=10)
    for t in legend.get_texts():
        t.set_color(c['text'])
    ax.set_title('Where the fine-tuned agent improved, and where it is still weak', color=c['text'], fontsize=12, loc='left')
    save(fig, 'dimensions', mode)


def main():
    report = json.loads((FINAL / 'report_trained_vs_base.json').read_text())
    kinds = json.loads((FINAL / 'report_by_evidence.json').read_text())['mean']
    for mode, c in MODES.items():
        quality(report, c, mode)
        differences(report, kinds, c, mode)
        dimensions(report, c, mode)
    print(sorted(p.name for p in OUT.glob('*.png')))


if __name__ == '__main__':
    main()
