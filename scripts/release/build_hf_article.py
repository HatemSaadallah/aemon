"""Write docs/HF_ARTICLE.md from docs/PUBLIC_README.md: the same write-up with absolute links and images, so it renders
as a Hugging Face article (or an organization card).

Usage: python scripts/release/build_hf_article.py
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = 'https://raw.githubusercontent.com/HatemSaadallah/aemon/main/'
BLOB = 'https://github.com/HatemSaadallah/aemon/blob/main/'
TITLE = '# aemon: teaching a 3B model to investigate a strategy question, with AgentTune and AuditKIT\n'


def article(readme: str) -> str:
    s = re.sub(r'<picture>\s*<source[^>]*>\s*<img alt="([^"]*)" src="([^"]*)"[^>]*>\s*</picture>', lambda m: f'![{m.group(1)}]({m.group(2)})', readme)
    s = re.sub(r'!\[([^\]]*)\]\((?!http)([^)]+)\)', lambda m: f'![{m.group(1)}]({RAW}{m.group(2)})', s)
    s = re.sub(r'(?<!!)\[([^\]]*)\]\((?!http|#)([^)]+)\)', lambda m: f'[{m.group(1)}]({BLOB}{m.group(2)})', s)
    s = s.replace('# aemon\n', TITLE, 1)
    s = re.sub(r'\*\*Contents:\*\*.*?\n\n', '', s, flags=re.S)  # in-page anchors do not work in an article
    s = s.replace('**Teaching a 3B model to investigate a strategy question, with AgentTune and AuditKIT.**\n', '')
    return s.replace('| **Live demo** |', '| Code and full repository | [github.com/HatemSaadallah/aemon](https://github.com/HatemSaadallah/aemon) |\n| **Live demo** |', 1)


if __name__ == '__main__':
    out = article((REPO / 'docs/PUBLIC_README.md').read_text())
    (REPO / 'docs/HF_ARTICLE.md').write_text(out)
    print(len(out.splitlines()), 'lines')
