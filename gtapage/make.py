"""Make one content pack:  python make.py            (posters + carousel + Reel + captions)
   python make.py --no-reel --offline --voice none --palette teal   etc."""
import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path

from kit import content, news as N, posters, reel, style
from kit.common import ROOT

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=None)
ap.add_argument("--no-reel", action="store_true")
ap.add_argument("--offline", action="store_true", help="skip Gemini, use the built-in template copy")
ap.add_argument("--voice", default="auto", choices=["auto", "none", "edge", "gemini", "sarvam", "elevenlabs"])
ap.add_argument("--palette", default="", help="force one palette name; default rotates")
a = ap.parse_args()

cfg, facts = content.load_json("config.json"), content.load_json("facts.json")
seed = a.seed if a.seed is not None else int(time.time()) % 100000
rng = random.Random(seed)
pal = a.palette or rng.choice(list(style.PALETTES))
if pal not in style.PALETTES:
    sys.exit("palette must be one of: " + ", ".join(style.PALETTES))
hist_f = ROOT / "history.json"
hist = json.loads(hist_f.read_text()) if hist_f.exists() else []
todays = N.fetch()
c, how = content.make_pack(cfg, facts, rng, not a.offline, hist, todays)
out = ROOT / "output" / f"pack_{seed}"
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)
h = cfg["handle"]
pp = c["posters"][:4]
for i, p in enumerate(pp, 1):
    posters.poster(p, style.Pal(pal), seed + i, h, i, len(pp)).save(out / f"poster_{i}_{p.get('kind', 'x')}.jpg", quality=93)
for i, im in enumerate(posters.carousel(c["carousel"], style.Pal(pal), seed + 50, h), 1):
    im.save(out / f"carousel_{i:02d}.jpg", quality=93)
info = "skipped"
if not a.no_reel:
    try:
        info = reel.build(c, h, pal, out / "reel.mp4", a.voice, seed, lang=cfg.get("voice_lang", "hinglish"))
    except Exception as ex:
        info = f"FAILED: {ex}"
        print("Reel failed:", ex, file=sys.stderr)
cap = c.get("captions", {})
tags = " ".join(c.get("hashtags") or cfg["hashtags_base"])
txt = [f"PACK {seed}  |  palette: {pal}  |  copy: {how}  |  reel: {info}", ""]
for k, v in cap.items():
    txt += [f"--- {k.upper()} CAPTION ---", v, ""]
txt += ["--- HASHTAGS (paste in first comment or caption, max 5-8 work best) ---", tags, "",
        "BEFORE POSTING: check every fact against facts.json sources. Keep the fan-page disclaimer. Do not add official trailer clips, screenshots, logos or music."]
sched = []
wins = [(8, 10.5), (11.5, 14), (16, 19), (20, 23)]       # IST windows; one post in each, random minute, so times differ daily
fmts = ["Reel (reel.mp4)", "Carousel (carousel_01..06)", "Poster 1 or 3", "Poster 2 or 4"]
rng.shuffle(fmts)
for (a0, a1), fm in zip(wins, fmts):
    m = int(rng.uniform(a0, a1) * 60)
    sched.append(f"{m // 60:02d}:{m % 60:02d} IST  ->  {fm}")
sched.sort()
(out / "POST_SCHEDULE_TODAY.txt").write_text("Today's 4 posts (random times, different every day). Set a phone alarm for each.\n\n" + "\n".join(sched) + "\n\nTip: use Instagram's 'Schedule' option (Professional account, Create > Advanced settings) to schedule them in advance.\n", encoding="utf-8")
(out / "captions_and_hashtags.txt").write_text("\n".join(txt), encoding="utf-8")
hist_f.write_text(json.dumps((hist + content.lines_used(c))[-120:]))
print(f"Done -> {out}\n{how}\nReel: {info}")
