"""Auto-post to Instagram. Run every 20 min by GitHub Actions. Each day it picks 4 random times (IST) and 4 formats, and posts the next
slot that is due and not yet posted.   python autopost.py [--dry-run] [--diagnose] [--force fmt]"""
import argparse
import datetime as dt
import json
import random
import sys
from pathlib import Path

from kit import content, ig, news as N, posters, reel, style
from kit.common import ROOT

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
WINS = [(8, 10.5), (11.5, 14), (16, 19), (20, 23)]
FMTS = ["reel", "carousel", "poster", "poster"]
ST = ROOT / "state.json"

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--diagnose", action="store_true")
ap.add_argument("--force", choices=["reel", "carousel", "poster"], help="post this format now, ignoring the schedule")
a = ap.parse_args()
if a.diagnose:
    ig.diagnose()
    sys.exit(0)

now = dt.datetime.now(IST)
today = now.strftime("%Y-%m-%d")
state = json.loads(ST.read_text()) if ST.exists() else {}
state.setdefault("history", [])
state.setdefault("news_seen", [])
if state.get("date") != today:                                   # new day: new random plan
    r = random.Random(today)
    f = FMTS[:]
    r.shuffle(f)
    slots = []
    for (a0, a1), fm in zip(WINS, f):
        m = int(r.uniform(a0, a1) * 60)
        slots.append({"t": f"{m // 60:02d}:{m % 60:02d}", "fmt": fm, "done": False})
    state.update(date=today, slots=sorted(slots, key=lambda s: s["t"]))
    print("Today's plan:", [(s["t"], s["fmt"]) for s in state["slots"]])
hm = now.strftime("%H:%M")
if a.force:
    slot = {"t": hm, "fmt": a.force, "done": False, "forced": True}
else:
    slot = next((s for s in state["slots"] if not s["done"] and s["t"] <= hm), None)
    if not slot:
        print("Nothing due now.", hm, [(s["t"], s["fmt"], s["done"]) for s in state["slots"]])
        ST.write_text(json.dumps(state, indent=1))
        sys.exit(0)
    if (dt.datetime.strptime(hm, "%H:%M") - dt.datetime.strptime(slot["t"], "%H:%M")).seconds > 3 * 3600:   # missed by > 3 h: skip it
        slot["done"] = True
        print("Slot missed, skipping", slot)
        ST.write_text(json.dumps(state, indent=1))
        sys.exit(0)

cfg, facts = content.load_json("config.json"), content.load_json("facts.json")
seed = int(now.strftime("%y%m%d")) * 10 + len(state["slots"]) + sum(s["done"] for s in state["slots"])
rng = random.Random(seed)
pal = rng.choice(list(style.PALETTES))
todays = N.fetch(state["news_seen"])
print(f"News found: {len(todays)}", [n["title"][:50] for n in todays[:4]])
c, how = content.make_pack(cfg, facts, rng, True, state["history"], todays)
out = ROOT / "output" / f"post_{seed}"
out.mkdir(parents=True, exist_ok=True)
h = cfg["handle"]
tags = " ".join((c.get("hashtags") or cfg["hashtags_base"])[:10])
cap = c.get("captions", {})
fmt = slot["fmt"]
print(f"Making a {fmt} for slot {slot['t']} ({how})")
try:
    if fmt == "reel":
        p = out / "reel.mp4"
        reel.build(c, h, pal, p, "auto", seed, lang=cfg.get("voice_lang", "hinglish"))
        caption = f"{cap.get('reel', '')}\n\n{tags}"
        mid = None if a.dry_run else ig.reel(str(p), caption)
    elif fmt == "carousel":
        ims = posters.carousel(c["carousel"], style.Pal(pal), seed, h)
        ps = []
        for i, im in enumerate(ims, 1):
            q = out / f"c{i}.jpg"
            im.save(q, quality=93)
            ps.append(str(q))
        caption = f"{cap.get('carousel', '')}\n\n{tags}"
        mid = None if a.dry_run else ig.carousel(ps, caption)
    else:
        i = rng.randrange(len(c["posters"]))
        q = out / "poster.jpg"
        posters.poster(c["posters"][i], style.Pal(pal), seed, h, 1, 1).save(q, quality=93)
        caption = f"{cap.get('poster_%d' % (i + 1), '')}\n\n{tags}"
        mid = None if a.dry_run else ig.image(str(q), caption)
except ig.TokenError as ex:
    print("TOKEN/ACCOUNT PROBLEM:", ex, file=sys.stderr)
    sys.exit(3)
print("Posted media id:" if mid else "Dry run (not posted).", mid or "")
if not a.dry_run:
    slot["done"] = True
    state["history"] = (state["history"] + content.lines_used(c))[-120:]
    state["news_seen"] = (state["news_seen"] + [n["title"] for n in todays[:4]])[-80:]
ST.write_text(json.dumps(state, indent=1))
