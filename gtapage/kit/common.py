import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"


def _ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FFMPEG = _ffmpeg()


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def on(c):
    return (16, 14, 28) if lum(c) > 150 else (255, 255, 255)


def pf(weight, size):
    return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)


def df(name, size):
    return ImageFont.truetype(str(FONTS / "display" / name), size)


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for w in str(text).split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def fit(text, fontfn, max_w, max_h, start, min_size=24, lh=1.12):
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    size = start
    while True:
        f = fontfn(size)
        lines = wrap(d, text, f, max_w)
        if (len(lines) * size * lh <= max_h and all(d.textlength(l, font=f) <= max_w * 1.01 for l in lines)) or size <= min_size:
            return f, lines, int(size * lh), size
        size -= 2
