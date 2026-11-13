"""The aemon wordmark (1120 x 280, light and dark), name in lower case: the mark cropped from the earlier wordmark,
the name in a bold serif and the tagline in Inter.

    python scripts/release/make_wordmark.py      # writes docs/figures/aemon-wordmark.png and aemon-wordmark-dark.png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
SERIF = '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'
SANS = str(Path.home() / '.local/share/fonts/Inter/Inter-{}.ttf')
mark = Image.open(REPO / 'docs/figures/aemon-wordmark-dark.png').convert('RGBA').crop((40, 40, 240, 240))
for name, ink, muted in (('aemon-wordmark.png', (20, 22, 27), (90, 96, 112)), ('aemon-wordmark-dark.png', (243, 244, 248), (160, 166, 184))):
    img = Image.new('RGBA', (1120, 280), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    img.paste(mark, (40, 40), mark)
    draw.text((282, 28), 'aemon', font=ImageFont.truetype(SERIF, 150), fill=ink)
    draw.text((288, 196), 'weigh what is known. test what is not.', font=ImageFont.truetype(SANS.format('MediumItalic') if Path(SANS.format('MediumItalic')).exists() else SANS.format('Medium'), 34), fill=muted)
    img.save(REPO / 'docs/figures' / name, optimize=True)
    print(name)
