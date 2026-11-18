"""Original retro 'vice sunset' poster art, drawn by code: sky + striped sun, art-deco skyline, palms, neon road, grain. No Rockstar art, logos or characters."""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .common import hexrgb, mix, lum

# sky top, sky mid, horizon, sun, building light, building shade, accent1 (neon), accent2, ink
PALETTES = {
    "sunset":    ("#1B1042", "#E8457A", "#FFB347", "#FFE066", "#FFE9D6", "#C95B8B", "#2EE6D6", "#FF3D81", "#FFFFFF"),
    "teal dusk": ("#0B1D3A", "#1F7A8C", "#F6A96B", "#FFE8A3", "#E6FFF7", "#3D9CA8", "#FF4D8D", "#FFD166", "#FFFFFF"),
    "purple hr": ("#190B3B", "#7B2CBF", "#FF6B9A", "#FFD6A5", "#FFE5F1", "#9D4EDD", "#00F5D4", "#FEE440", "#FFFFFF"),
    "hot red":   ("#2A0A12", "#C1121F", "#FF8C42", "#FFD23F", "#FFF1E0", "#B5424C", "#00D1FF", "#FFD23F", "#FFFFFF"),
    "lime neon": ("#071A2F", "#0B6E6E", "#C6F432", "#F4FFB5", "#E8FFE0", "#2D9C7A", "#FF2E93", "#C6F432", "#FFFFFF"),
    "ocean":     ("#0A1633", "#2563EB", "#FF9F6E", "#FFE29A", "#EAF4FF", "#4C7BD9", "#FF5D8F", "#2EE6D6", "#FFFFFF"),
}
KINDS = ["skyline", "highway", "rooftop", "beach", "palms"]


class Pal:
    def __init__(self, name):
        self.name = name
        (self.top, self.mid, self.hor, self.sun, self.bl, self.bs, self.a1, self.a2, self.ink) = [hexrgb(x) for x in PALETTES[name]]
        self.dark = mix(self.top, (0, 0, 0), .55)


def _grad(w, h, stops):
    ys = np.linspace(0, 1, h)[:, None]
    out = np.zeros((h, 1, 3))
    xs = [s[0] for s in stops]
    for c in range(3):
        out[:, 0, c] = np.interp(ys[:, 0], xs, [s[1][c] for s in stops])
    return Image.fromarray(np.repeat(out, w, axis=1).astype("uint8")).convert("RGBA")


def sky(w, h, P, horizon=.62):
    return _grad(w, h, [(0, P.top), (horizon * .55, P.mid), (horizon, P.hor), (horizon + .001, P.dark), (1, P.dark)])


def sun(img, P, cx, cy, r, stripes=True):
    k = 3
    S = 2 * r * k
    m = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(m)
    md.ellipse((0, 0, S - 1, S - 1), fill=255)
    if stripes:
        y, gap = S * .52, S * .035
        while y < S:
            md.rectangle((0, y, S, y + gap), fill=0)
            y += gap * 2.3
            gap *= 1.22
    L = Image.new("RGBA", (S, S), P.sun + (255,))
    top = mix(P.sun, (255, 255, 255), .25)
    bot = mix(P.sun, P.hor, .75)
    gr = np.linspace(0, 1, S)[:, None, None]
    arr = (np.array(top) * (1 - gr) + np.array(bot) * gr) * np.ones((1, S, 1))
    L = Image.fromarray(arr.astype("uint8")).convert("RGBA")
    L.putalpha(m)
    L = L.resize((2 * r, 2 * r), Image.LANCZOS)
    G = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(G).ellipse((cx - r * 1.5, cy - r * 1.5, cx + r * 1.5, cy + r * 1.5), fill=P.sun + (80,))
    img.alpha_composite(G.filter(ImageFilter.GaussianBlur(r * .4)))
    img.alpha_composite(L, (int(cx - r), int(cy - r)))


def stars(img, rng, n, ymax):
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x, y = rng.randint(0, img.width), rng.randint(0, int(ymax))
        s = rng.choice([1, 1, 2, 3])
        d.ellipse((x, y, x + s, y + s), fill=(255, 255, 255, rng.randint(110, 230)))


def building(d, x, y_base, w, h, P, rng, shade=0.0, lit=True):
    body = mix(P.bl, P.dark, shade)
    side = mix(P.bs, P.dark, shade)
    top = y_base - h
    d.rectangle((x, top, x + w, y_base), fill=body)
    d.rectangle((x + w * .72, top, x + w, y_base), fill=side)                           # shaded side
    if rng.random() < .6:                                                              # stepped deco crown
        d.rectangle((x + w * .2, top - h * .08, x + w * .8, top), fill=body)
        d.rectangle((x + w * .38, top - h * .16, x + w * .62, top - h * .08), fill=body)
    if rng.random() < .5:                                                              # rounded deco corner
        d.pieslice((x - w * .25, top, x + w * .25, top + w * .5), 180, 270, fill=body)
    stripe = P.a1 if rng.random() < .5 else P.a2
    for i in range(rng.randint(1, 3)):                                                 # neon eyebrow lines
        yy = top + h * (.15 + .22 * i + rng.random() * .05)
        d.rectangle((x, yy, x + w, yy + max(3, h * .018)), fill=mix(stripe, body, shade * .6))
    if lit:
        cols = max(2, int(w // 22))
        rows = max(3, int(h // 30))
        for r_ in range(rows):
            for c in range(cols):
                if rng.random() < .55:
                    wx, wy = x + 8 + c * (w - 16) / cols, top + 14 + r_ * (h - 28) / rows
                    d.rectangle((wx, wy, wx + 8, wy + 12), fill=mix(P.sun, P.hor, .3) + (200,))


def skyline(img, P, rng, y_base, scale=1.0, layers=2, gap_x=None):
    d = ImageDraw.Draw(img)
    for layer in range(layers):
        shade = .62 - layer * .45
        x = -rng.randint(0, 80)
        while x < img.width:
            w = int(rng.randint(70, 150) * scale * (1 + (layer * .25)))
            h = int(rng.randint(160, 520) * scale * (1.0 if layer else .62))
            if gap_x and abs((x + w / 2) - gap_x) < img.width * .24:
                h = int(h * .38)
            building(d, x, y_base - (0 if layer else 20), w, h, P, rng, shade=max(0, shade), lit=layer > 0)
            x += w + rng.randint(-10, 26)


def leaf(d, base, ang, L, droop, W, col):
    pts_l, pts_r = [], []
    for i in range(19):
        t = i / 18
        x = base[0] + math.cos(ang) * L * t
        y = base[1] + math.sin(ang) * L * t + droop * L * t * t
        w = W * math.sin(math.pi * min(1, t * 1.04)) ** .8
        nx, ny = -math.sin(ang), math.cos(ang)
        pts_l.append((x + nx * w, y + ny * w))
        pts_r.append((x - nx * w, y - ny * w))
    d.polygon(pts_l + pts_r[::-1], fill=col)


def palm(img, x0, y0, x1, y1, col, size=1.0, rng=None, lean=.25):
    rng = rng or random.Random(1)
    k = 2
    L = Image.new("RGBA", (img.width * k, img.height * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    cx, cy = (x0 + x1) / 2 + (x1 - x0) * lean, (y0 + y1) / 2 - 20
    pts = []
    for i in range(41):
        t = i / 40
        px = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
        py = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
        pts.append((px, py, 34 * size * (1 - t * .5)))
    left = [(p[0] * k - p[2] * k / 2, p[1] * k) for p in pts]
    right = [(p[0] * k + p[2] * k / 2, p[1] * k) for p in pts]
    d.polygon(left + right[::-1], fill=col)
    top = (x1 * k, y1 * k)
    for a in [-165, -140, -115, -90, -65, -40, -15, 10, 170, 195]:
        ang = math.radians(a + rng.randint(-8, 8))
        leaf(d, top, ang, rng.randint(210, 300) * size * k, .55 + rng.random() * .5, 26 * size * k, col)
    img.alpha_composite(L.resize(img.size, Image.LANCZOS))


def road(img, P, y_h, vx):
    d = ImageDraw.Draw(img)
    W, H = img.size
    d.polygon([(vx - 14, y_h), (vx + 14, y_h), (W * 1.5, H), (-W * .5, H)], fill=mix(P.dark, (0, 0, 0), .35))
    for s in (-1, 1):                                                                   # neon edge lines
        d.line([(vx + s * 12, y_h), (vx + s * W * 1.25, H)], fill=P.a1, width=5)
    for i in range(7):                                                                  # dashed centre line
        t1, t2 = (i / 7) ** 2.2, ((i + .5) / 7) ** 2.2
        y1, y2 = y_h + (H - y_h) * t1, y_h + (H - y_h) * t2
        d.polygon([(vx - 2 - 14 * t1, y1), (vx + 2 + 14 * t1, y1), (vx + 2 + 14 * t2, y2), (vx - 2 - 14 * t2, y2)], fill=P.sun)


def car(img, x, y, w, col, P):
    k = 3
    h = int(w * .42)
    L = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    s = lambda *v: tuple(int(a * w * k) if i % 2 == 0 else int(a * w * k) for i, a in enumerate(v))
    d.rounded_rectangle(s(.02, .20, .98, .34), int(.04 * w * k), fill=col)
    d.polygon(s(.22, .20, .34, .05, .66, .05, .80, .20), fill=col)
    d.polygon(s(.30, .19, .38, .09, .50, .09, .50, .19), fill=mix(P.dark, P.a1, .25))
    d.polygon(s(.53, .19, .53, .09, .63, .09, .73, .19), fill=mix(P.dark, P.a1, .25))
    for cx in (.24, .76):
        d.ellipse(s(cx - .09, .26, cx + .09, .44), fill=(16, 14, 24, 255))
        d.ellipse(s(cx - .045, .31, cx + .045, .39), fill=(150, 150, 160, 255))
    d.rectangle(s(.04, .26, .98, .28), fill=P.a2)
    L = L.resize((w, h), Image.LANCZOS)
    img.alpha_composite(L, (int(x - w / 2), int(y - h)))


def grain(img, rng, amt=14):
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    n = np.random.RandomState(rng.randint(0, 9999)).normal(0, amt, a.shape[:2])[..., None]
    out = np.clip(a + n, 0, 255).astype("uint8")
    return Image.fromarray(out).convert("RGBA")


def vignette(img, strength=.55):
    W, H = img.size
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    a = np.clip((d - .55) / .9, 0, 1) ** 1.6 * 255 * strength
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    L.putalpha(Image.fromarray(a.astype("uint8")))
    img.alpha_composite(L)


def scene(kind, pal, w, h, seed=0, night=None):
    rng = random.Random(seed)
    P = pal if isinstance(pal, Pal) else Pal(pal)
    hz = {"skyline": .66, "highway": .5, "rooftop": .72, "beach": .6, "palms": .7}[kind]
    img = sky(w, h, P, hz)
    yh = int(h * hz)
    stars(img, rng, 90, yh * .5)
    sx = w * rng.choice([.4, .5, .6])
    sun(img, P, sx, yh - w * .1, int(w * (.27 if kind != "beach" else .22)))
    if kind in ("skyline", "rooftop", "palms"):
        skyline(img, P, rng, yh + 10, scale=1.0 if kind == "skyline" else .8, layers=2, gap_x=sx)
        d = ImageDraw.Draw(img)
        d.rectangle((0, yh + 8, w, h), fill=P.dark)
        gl = Image.new("RGBA", (w, h - yh), (0, 0, 0, 0))
        ImageDraw.Draw(gl).rectangle((0, 0, w, 30), fill=P.a1 + (120,))
        img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(18)), (0, yh))
        for i in range(1, 9):                                                              # neon perspective grid
            yy = yh + (h - yh) * (i / 9) ** 2
            d.line((0, yy, w, yy), fill=P.a1 + (90,), width=2)
        for i in range(-9, 10):
            d.line((w / 2 + i * 8, yh, w / 2 + i * w * .16, h), fill=P.a1 + (70,), width=2)
    elif kind == "highway":
        skyline(img, P, rng, yh + 10, scale=.7, layers=2, gap_x=sx)
        road(img, P, yh, w * rng.choice([.45, .55]))
        car(img, w * .5, h * .86, int(w * .6), (255, 205, 40, 255) if rng.random() < .6 else P.a2, P)
    elif kind == "beach":
        d = ImageDraw.Draw(img)
        d.rectangle((0, yh, w, h), fill=mix(P.mid, P.dark, .35))
        for i in range(9):
            yy = yh + (h - yh) * (i / 9) ** 1.6
            pts = [(x, yy + math.sin(x / 70 + i) * (4 + i * 2)) for x in range(0, w + 20, 20)]
            d.line(pts, fill=mix(P.hor, P.sun, .4) + (150,), width=3 + i)
        skyline(img, P, rng, yh + 4, scale=.45, layers=1, gap_x=sx)
    dark = mix(P.dark, (0, 0, 0), .55)
    if kind in ("palms", "skyline", "beach", "highway", "rooftop"):
        palm(img, -40, h * .96, w * .10, h * .30, dark, 1.25 if kind == "palms" else 1.0, rng, lean=.5)
        palm(img, w * 1.03, h * .98, w * .90, h * .26, dark, 1.35 if kind == "palms" else 1.05, rng, lean=-.5)
    img = grain(img, rng)
    vignette(img)
    return img
