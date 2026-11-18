"""Posters, carousel slides. HUD look: dark glass cards, mono-ish labels, highlight chips, over original retro scenes."""
import math
import random

from PIL import Image, ImageDraw, ImageFilter

from . import style
from .common import df, fit, lum, mix, on, pf, wrap

W, H = 1080, 1350
TITLE_FONTS = ["Anton-Regular.ttf", "BebasNeue-Regular.ttf", "ArchivoBlack-Regular.ttf", "Bangers-Regular.ttf"]


def rrect(img, box, r, fill, outline=None, ow=0):
    x0, y0, x1, y1 = [int(v) for v in box]
    k = 3
    L = Image.new("RGBA", ((x1 - x0) * k, (y1 - y0) * k), (0, 0, 0, 0))
    ImageDraw.Draw(L).rounded_rectangle((0, 0, L.width - 1, L.height - 1), r * k, fill=fill, outline=outline, width=ow * k)
    img.alpha_composite(L.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))


def glass(img, box, P, a=190):
    rrect(img, box, 22, P.dark + (a,), P.a1 + (150,), 2)


def title(img, text, hl, box, P, tf, start=150, align="left", lh=1.0, upper=True):
    """big display headline; words in `hl` use the neon accent; thick dark shadow for punch"""
    text = text.upper() if upper else text
    hlw = {w.lower().strip(".,!?") for w in (hl or "").split()}
    x0, y0, x1, y1 = box
    f, lines, lhp, size = fit(text, lambda s: df(tf, s), x1 - x0, y1 - y0, start, 40, lh)
    d = ImageDraw.Draw(img)
    y = y0
    for ln in lines:
        wd = d.textlength(ln, font=f)
        x = x0 if align == "left" else x0 + (x1 - x0 - wd) / 2
        for w in ln.split():
            col = P.a1 if w.lower().strip(".,!?") in hlw else P.ink
            d.text((x + 5, y + 6), w, font=f, fill=(0, 0, 0, 170))
            d.text((x, y), w, font=f, fill=col)
            x += d.textlength(w + " ", font=f)
        y += lhp
    return int(y)


def tag(img, text, x, y, P, size=24, fill=None):
    fill = fill or P.a2
    d = ImageDraw.Draw(img)
    f = pf("Bold", size)
    w = int(d.textlength(text.upper(), font=f)) + 36
    rrect(img, (x, y, x + w, y + size + 20), 8, fill)
    ImageDraw.Draw(img).text((x + 18, y + 10), text.upper(), font=f, fill=on(fill))
    return x + w


def hud(img, P, left, right, handle, disclaimer=True):
    d = ImageDraw.Draw(img)
    d.text((44, 38), "GTA VI", font=pf("Bold", 30), fill=P.ink)
    d.line((44, 92, img.width - 44, 92), fill=P.ink + (90,), width=2)
    d.text((img.width - 44, 44), right, font=pf("Medium", 22), fill=P.ink + (200,), anchor="ra")
    if left:
        tag(img, left, 44, 108, P, 22)
    d = ImageDraw.Draw(img)
    y = img.height - 60
    d.text((44, y), "@" + handle, font=pf("Bold", 26), fill=P.a1)
    if disclaimer:
        d.text((img.width - 44, y + 4), "Fan page. Not affiliated with Rockstar Games or Take-Two.", font=pf("Medium", 17), fill=P.ink + (150,), anchor="ra")


def dim(img, top=0, bottom=None, a=150):
    bottom = bottom or img.height
    L = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(L).rectangle((0, top, img.width, bottom), fill=(5, 4, 18, a))
    img.alpha_composite(L)


def bottom_fade(img, h=620, a=235):
    L = Image.new("RGBA", (img.width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    for y in range(h):
        d.line((0, y, img.width, y), fill=(5, 4, 18, int(a * (y / h) ** 1.4)))
    img.alpha_composite(L, (0, img.height - h))


# ---------------------------------------------------------------- posters
def p_launch(c, P, rng, tf, handle, idx=1, n=1):
    img = style.scene("skyline", P, W, H, rng.randint(0, 9999))
    bottom_fade(img, 760)
    hud(img, P, c.get("tag", "LAUNCH DAY"), f"{idx:02d} / {n:02d}", handle)
    y = title(img, c.get("headline", "IT'S HERE."), c.get("highlight", ""), (50, 420, W - 50, 760), P, tf, 190)
    d = ImageDraw.Draw(img)
    big = c.get("date", "19 NOV 2026")
    d.text((55, y + 16), big, font=df("Anton-Regular.ttf", 120), fill=(0, 0, 0))
    d.text((50, y + 10), big, font=df("Anton-Regular.ttf", 120), fill=P.sun)
    d.text((54, y + 160), c.get("sub", "PS5  /  XBOX SERIES X|S"), font=pf("Bold", 36), fill=P.ink)
    glass(img, (50, H - 290, W - 50, H - 130), P)
    ImageDraw.Draw(img).text((84, H - 262), c.get("cta", "Save this. Send it to your squad."), font=pf("Bold", 34), fill=P.ink)
    ImageDraw.Draw(img).text((84, H - 208), c.get("cta2", "Follow for daily launch-week updates."), font=pf("Medium", 26), fill=P.ink + (210,))
    return img


def p_fact(c, P, rng, tf, handle, idx=1, n=1):
    img = style.scene(rng.choice(["palms", "beach", "rooftop"]), P, W, H, rng.randint(0, 9999))
    dim(img, 420, H, 175)
    hud(img, P, c.get("tag", "WHAT WE KNOW"), f"{idx:02d} / {n:02d}", handle)
    y = title(img, c.get("headline", "ONE THING IS CONFIRMED"), c.get("highlight", ""), (50, 400, W - 50, 700), P, tf, 120)
    items = c.get("items") or []
    top = int(y + 30)
    d = ImageDraw.Draw(img)
    for i, it in enumerate(items[:3]):
        yy = top + i * 150
        glass(img, (50, yy, W - 50, yy + 128), P)
        d = ImageDraw.Draw(img)
        d.text((86, yy + 64), f"{i + 1:02d}", font=pf("Bold", 30), fill=P.a2, anchor="lm")
        f, lines, lh_, _ = fit(it, lambda s: pf("Bold", s), W - 260, 104, 36, 22, 1.15)
        yt = yy + 64 - len(lines) * lh_ / 2
        for ln in lines:
            d.text((150, yt), ln, font=f, fill=P.ink)
            yt += lh_
    if c.get("source"):
        d.text((50, H - 118), "Source: " + c["source"], font=pf("Medium", 22), fill=P.ink + (190,))
    return img


def p_poll(c, P, rng, tf, handle, idx=1, n=1):
    img = style.scene("highway", P, W, H, rng.randint(0, 9999))
    dim(img, 0, H, 70)
    hud(img, P, c.get("tag", "YOUR CALL"), f"{idx:02d} / {n:02d}", handle)
    y = title(img, c.get("headline", "WHICH ONE ARE YOU?"), c.get("highlight", ""), (50, 190, W - 50, 520), P, tf, 150)
    opts = (c.get("options") or ["PS5", "XBOX SERIES X|S"])[:2]
    top = int(y + 40)
    for i, o in enumerate(opts):
        x0 = 50 + i * 505
        glass(img, (x0, top, x0 + 475, top + 330), P, 215)
        d = ImageDraw.Draw(img)
        d.text((x0 + 30, top + 26), "ABCD"[i], font=df("Anton-Regular.ttf", 110), fill=P.a1 if i == 0 else P.a2)
        f, lines, lh_, _ = fit(o.upper(), lambda s: df("Anton-Regular.ttf", s), 415, 150, 64, 30, 1.0)
        yt = top + 180
        for ln in lines:
            d.text((x0 + 30, yt), ln, font=f, fill=P.ink)
            yt += lh_
    glass(img, (50, top + 370, W - 50, top + 450), P, 215)
    d = ImageDraw.Draw(img)
    d.text((W // 2, top + 388), c.get("cta", "Comment A or B. Tag your co-op partner."), font=pf("Bold", 32), fill=P.ink, anchor="ma")
    return img


def p_quote(c, P, rng, tf, handle, idx=1, n=1):
    img = style.scene(rng.choice(["skyline", "beach", "palms"]), P, W, H, rng.randint(0, 9999))
    bottom_fade(img, 900, 225)
    hud(img, P, c.get("tag", "MOOD"), f"{idx:02d} / {n:02d}", handle)
    y = title(img, c.get("headline", "THE WAIT IS OVER."), c.get("highlight", ""), (50, 520, W - 50, 1010), P, tf, 190)
    d = ImageDraw.Draw(img)
    if c.get("sub"):
        f, lines, lh_, _ = fit(c["sub"], lambda s: pf("Medium", s), W - 120, 150, 36, 22, 1.3)
        yy = y + 14
        for ln in lines:
            d.text((54, yy), ln, font=f, fill=P.ink + (230,))
            yy += lh_
    return img


POSTERS = {"launch": p_launch, "fact": p_fact, "poll": p_poll, "quote": p_quote}


def poster(c, P, seed, handle, idx=1, n=1):
    rng = random.Random(seed)
    tf = rng.choice(TITLE_FONTS)
    return POSTERS.get(c.get("kind"), p_quote)(c, P, rng, tf, handle, idx, n).convert("RGB")


# ---------------------------------------------------------------- carousel
def c_cover(c, P, rng, tf, handle, n):
    img = style.scene(rng.choice(style.KINDS), P, W, H, rng.randint(0, 9999))
    bottom_fade(img, 860, 235)
    hud(img, P, c.get("tag", "THREAD"), f"01 / {n:02d}", handle)
    y = title(img, c.get("headline", ""), c.get("highlight", ""), (50, 470, W - 50, 960), P, tf, 170)
    tag(img, "Swipe  >>", 50, H - 190, P, 30, P.a1)
    return img


def c_slide(c, P, rng, tf, handle, i, n):
    img = Image.new("RGBA", (W, H), P.dark + (255,))
    sc = style.scene(rng.choice(style.KINDS), P, W, 520, rng.randint(0, 9999)).convert("RGBA")
    img.alpha_composite(sc.crop((0, 0, W, 520)))
    L = Image.new("RGBA", (W, 160), (0, 0, 0, 0))
    gd = ImageDraw.Draw(L)
    for y in range(160):
        gd.line((0, y, W, y), fill=P.dark + (int(255 * (y / 160) ** 1.5),))
    img.alpha_composite(L, (0, 360))
    hud(img, P, c.get("tag", ""), f"{i:02d} / {n:02d}", handle)
    d = ImageDraw.Draw(img)
    d.text((50, 540), f"{i - 1:02d}", font=df("Anton-Regular.ttf", 110), fill=P.a2)
    y = title(img, c.get("title", ""), c.get("highlight", ""), (50, 670, W - 50, 900), P, tf, 110)
    if c.get("body"):
        f, lines, lh_, _ = fit(c["body"], lambda s: pf("Medium", s), W - 120, 340, 44, 26, 1.35)
        yy = y + 16
        d = ImageDraw.Draw(img)
        for ln in lines:
            d.text((54, yy), ln, font=f, fill=P.ink + (235,))
            yy += lh_
    return img


def c_cta(c, P, rng, tf, handle, n):
    img = style.scene("skyline", P, W, H, rng.randint(0, 9999))
    bottom_fade(img, 1000, 230)
    hud(img, P, "YOUR TURN", f"{n:02d} / {n:02d}", handle)
    y = title(img, c.get("headline", "SAVE THIS."), c.get("highlight", ""), (50, 560, W - 50, 900), P, tf, 150)
    d = ImageDraw.Draw(img)
    f, lines, lh_, _ = fit(c.get("body", "Send it to your squad. Follow for more."), lambda s: pf("Bold", s), W - 120, 200, 38, 24, 1.3)
    yy = y + 16
    for ln in lines:
        d.text((54, yy), ln, font=f, fill=P.ink)
        yy += lh_
    return img


def carousel(c, P, seed, handle):
    rng = random.Random(seed)
    tf = rng.choice(TITLE_FONTS)
    body = c["slides"][:5]
    n = len(body) + 2
    out = [c_cover(c["cover"], P, random.Random(seed + 1), tf, handle, n)]
    for i, s in enumerate(body, 2):
        out.append(c_slide(s, P, random.Random(seed + i), tf, handle, i, n))
    out.append(c_cta(c["cta"], P, random.Random(seed + 99), tf, handle, n))
    return [x.convert("RGB") for x in out]
