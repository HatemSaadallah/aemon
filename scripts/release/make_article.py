"""The Hugging Face article, made from the public README (what was approved as the write-up): the title and contents
line go, the repository-only sections (layout, run, reproduce) go, and relative links and images become GitHub URLs.

    python scripts/release/make_article.py PUBLIC_README OUT      # e.g. the public repo's README.md, docs/HF_ARTICLE.md
"""
import re, sys
src, out = sys.argv[1], sys.argv[2]
GH, RAW = 'https://github.com/HatemSaadallah/aemon', 'https://raw.githubusercontent.com/HatemSaadallah/aemon/main'
s = open(src).read()
# drop the title and wordmark (the article has its own title), the contents line, and the repo-only sections
s = s.split('\n', 1)[1]
s = re.sub(r'<picture>.*?aemon-wordmark.*?</picture>\n', '', s, count=1, flags=re.S)
s = re.sub(r'\*\*Contents:\*\*.*?\n\n', '', s, count=1, flags=re.S)
def cut(text, heading, until):
    a = text.index(heading); b = text.index(until, a + 1)
    return text[:a] + text[b:]
s = cut(s, '## Repository layout', '## See an investigation without a GPU')
s = cut(s, '## Run it', '## Licence')
# <picture> figures: keep the light image
s = re.sub(r'<picture>\s*<source[^>]*>\s*<img alt="([^"]*)" src="([^"]*)"[^>]*>\s*</picture>', r'![\1](\2)', s, flags=re.S)
def link(m):
    text, url, img = m.group(2), m.group(3), m.group(1)
    if url.startswith(('http', 'mailto:')): return m.group(0)
    if url.startswith('#'): return f'{img}[{text}]({GH}{url})'
    path, _, anchor = url.partition('#')
    if img: return f'![{text}]({RAW}/{path})'
    kind = 'tree' if path.endswith('/') else 'blob'
    return f'[{text}]({GH}/{kind}/main/{path.rstrip("/")}' + (f'#{anchor}' if anchor else '') + ')'
s = re.sub(r'(!?)\[([^\]]*)\]\(([^)\s]+)\)', link, s)
intro = (f'*Code, data and every run: [github.com/HatemSaadallah/aemon]({GH}). Try it: '
         '[huggingface.co/spaces/HatemSaadallah/aemon](https://huggingface.co/spaces/HatemSaadallah/aemon).*\n\n')
open(out, 'w').write(intro + s.lstrip())
print(len(s), 'chars')
