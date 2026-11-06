"""YouTube Shorts thumbnail (1080x1920 PNG) in the video's look, from content.json "thumbnail".

  python3 tools/thumbnail.py

Writes output/thumbnail.png. Upload it in YouTube Studio on a computer (Content > Shorts > Thumbnail).
"""
import io
import json

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

from build import ACCENT, COLORS, EDITOR_TOP, H, PROGRESS_H, ROOT, W, parse_line

FONTS = ROOT / "assets/fonts"
BOX_W, BOX_MAX_H, PAD = 1000, 1100, 64   # navy box as wide as the video's code box, kept in the middle
TITLE_MAX, TITLE_WARN, TITLE_LH = 190, 140, 1.22
SUB_FS, SUB_GAP = 50, 36


def pretendard_bold():
    # Pillow can't read woff2: unpack it to TrueType once (fontTools + brotli)
    f = TTFont(FONTS / "Pretendard-Bold.woff2")
    f.flavor = None
    buf = io.BytesIO()
    f.save(buf)
    data = buf.getvalue()
    return lambda size: ImageFont.truetype(io.BytesIO(data), size)


def width(src, font):
    return sum(font.getlength(text) for _, text in parse_line(src))


def draw_line(d, x, y, src, font, default):
    for tag, text in parse_line(src):
        d.text((x, y), text, font=font, fill=default if tag == "w" else COLORS[tag], anchor="lm")
        x += font.getlength(text)
    return x


def main():
    thumb = json.loads((ROOT / "content.json").read_text())["thumbnail"]
    title, sub = thumb["title"], thumb.get("sub")
    bold = pretendard_bold()
    code = lambda size: ImageFont.truetype(str(FONTS / "D2Coding-Regular.ttf"), size)

    img = Image.new("RGB", (W, H), "#0d1117")
    d = ImageDraw.Draw(img)

    # top: progress bar + terminal title, as in the video
    d.rectangle((0, 0, W, PROGRESS_H - 1), fill=ACCENT)
    d.rectangle((0, PROGRESS_H, W, EDITOR_TOP - 1), fill="#161b22")
    d.rectangle((0, EDITOR_TOP - 2, W, EDITOR_TOP - 1), fill="#21262d")
    f = thumb["file"]
    tab = f"<b>❯</b> {f}" if "." not in f else f"<b>❯</b> <i>cat</i> {f}"
    x, y, tab_font = 44, (PROGRESS_H + EDITOR_TOP) / 2, code(30)
    for tag, text in parse_line(tab):
        d.text((x, y), text, font=tab_font, fill={"b": ACCENT, "i": "#7d8590"}.get(tag, "#e6edf3"), anchor="lm")
        x += tab_font.getlength(text)

    # title fits the box width; the sub line (a code comment) sits above it
    inner = BOX_W - 2 * PAD
    sub_fs = min(SUB_FS, SUB_FS * inner / width(sub, code(SUB_FS))) if sub else 0
    sub_h = sub_fs * 1.3 + SUB_GAP if sub else 0
    w100 = max(width(line, bold(100)) for line in title)
    fs = min(TITLE_MAX, 100 * inner / w100, (BOX_MAX_H - 2 * PAD - sub_h) / (len(title) * TITLE_LH))
    box_h = 2 * PAD + sub_h + fs * TITLE_LH * len(title)
    top, left = (H - box_h) / 2, (W - BOX_W) / 2
    d.rectangle((left, top, left + BOX_W, top + box_h), fill="#172033")

    y = top + PAD
    if sub:
        draw_line(d, left + PAD, y + sub_fs * 0.65, sub, code(round(sub_fs)), COLORS["c"])
        y += sub_h
    font = bold(round(fs))
    for line in title:
        end = draw_line(d, left + PAD, y + fs * TITLE_LH / 2, line, font, COLORS["w"])
        y += fs * TITLE_LH
    # the mint cursor after the last line
    cy = y - fs * TITLE_LH / 2
    d.rectangle((end + fs * 0.08, cy - fs * 0.5, end + fs * 0.08 + fs * 0.22, cy + fs * 0.5), fill=ACCENT)

    out = ROOT / "output/thumbnail.png"
    out.parent.mkdir(exist_ok=True)
    img.save(out, optimize=True)
    print(f"{out.relative_to(ROOT)}  title {fs:.0f}px")
    if fs < TITLE_WARN:
        print(f"title font down to {fs:.0f}px: shorten the longest title line")


if __name__ == "__main__":
    main()
