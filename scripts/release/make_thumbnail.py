"""The Hugging Face article thumbnail (1200 x 630): the aemon mark, the name in lower case, the tagline and one line on
what the project is. The mark is cropped from docs/figures/aemon-wordmark-dark.png.

    python scripts/release/make_thumbnail.py      # writes docs/figures/thumbnail.png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
W, H = 1200, 630
BG, INK, MUTED, ACCENT = (20, 22, 27), (243, 244, 248), (160, 166, 184), (124, 154, 245)
SERIF = '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf'
SANS = str(Path.home() / '.local/share/fonts/Inter/Inter-{}.ttf')

img = Image.new('RGB', (W, H), BG)
draw = ImageDraw.Draw(img)
mark = Image.open(REPO / 'docs/figures/aemon-wordmark-dark.png').convert('RGBA').crop((40, 40, 240, 240)).resize((190, 190), Image.LANCZOS)
plate = Image.new('RGBA', (214, 214), (0, 0, 0, 0))  # a faint ring, so the dark mark reads on the dark background
ImageDraw.Draw(plate).rounded_rectangle((0, 0, 213, 213), radius=52, outline=(58, 62, 74), width=3)
img.paste(plate, (96, 150), plate)
img.paste(mark, (108, 162), mark)
draw.text((360, 128), 'aemon', font=ImageFont.truetype(SERIF, 168), fill=INK)
draw.text((366, 318), 'weigh what is known. test what is not.', font=ImageFont.truetype(SANS.format('LightItalic') if Path(SANS.format('LightItalic')).exists() else SANS.format('Light'), 38), fill=MUTED)
draw.rectangle((96, 430, 96 + 64, 434), fill=ACCENT)
draw.text((96, 458), 'Teaching a 3B open model to investigate a strategy question', font=ImageFont.truetype(SANS.format('SemiBold'), 33), fill=INK)
draw.text((96, 512), 'Agentic fine-tuning with AgentTune and AuditKIT  ·  Lexsi AI Hackathon, Track 3', font=ImageFont.truetype(SANS.format('Regular'), 26), fill=MUTED)
out = REPO / 'docs/figures/thumbnail.png'
img.save(out, optimize=True)
print(out, out.stat().st_size)
