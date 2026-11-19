"""Copy for one content pack. With GEMINI_API_KEY the AI writes it from facts.json (confirmed facts only); without a key a good offline template is used."""
import json
import os
import random
import re
import sys
import time

from .common import ROOT

PROMPT = """You write Instagram content for an Indian gaming fan page about Grand Theft Auto VI (written as "GTA VI" or "GTA 6").
PAGE TONE: {tone}. On-image text and captions: natural Indian English. ONLY the Reel 'say' lines are Hinglish (Roman letters, never Devanagari).
TODAY: {today} (IST). {status}
CONFIRMED FACTS (the ONLY facts you may state as true):
{facts}
RULES
- Do not state any other fact about the game (no price, map, characters, story, release time) unless it is in the list. If you want to talk about the unknown, say plainly that it is unconfirmed or a question.
- No rumours presented as facts. No leaks. No official screenshots or trailer frames are used; do not describe them.
- No income promises or "earn lakhs" claims. Creator tips must be practical and honest.
- Every line short and punchy, built to be saved, shared or commented on. Hooks first. No emojis in on-image text.
TODAY'S WORLD NEWS (headlines from the last 48h; OFFICIAL = from Rockstar/Take-Two, REPORTED = media, may be unconfirmed):
{news}
NEWS RULES
- Build the pack around the 2-4 most interesting stories above. Say only what the headline supports. Never add details.
- Mark every REPORTED story clearly as "Reported" or "Unconfirmed" on the image and in speech ("reports say", "abhi confirm nahi hai"). Only OFFICIAL stories may be stated as confirmed. Name the source on the image.
- If the news list is empty, use the confirmed facts and evergreen content instead.
GROWTH SCRIPT RULES (make people FOLLOW and ENGAGE)
- Reel: scene 1 = a hook in the first 2 seconds (shock, question or bold claim, e.g. "GTA 6 ke baare mein aaj ek badi khabar aayi"). Middle scenes = one story each, short, with a tiny open loop ("aur teesri khabar sabse badi hai"). Last scene = CTA: ask them to FOLLOW so they don't miss tomorrow's update, and to comment their opinion with a specific question.
- Every caption ends with ONE specific question that is easy to answer in a word, plus "Follow @{handle} for daily GTA 6 updates".
- Carousel: cover = curiosity hook, slides = one story each, last slide = follow + save + share.
- Poll poster = a debate about the hottest story.
- Theme of this pack: {theme}. Make every headline different in style (pun, bold claim, question, POV, contrast, challenge, one-word punch).
- Avoid reusing these earlier lines: {avoid}
Return ONLY JSON in this shape:
{schema}"""

SCHEMA = """{
 "posters":[
  {"kind":"launch","tag":"2-3 words","headline":"max 5 words","highlight":"1-2 words from headline","date":"19 NOV 2026","sub":"short line","cta":"max 8 words","cta2":"max 8 words"},
  {"kind":"fact","tag":"2-3 words","headline":"max 6 words","highlight":"1-2 words","items":["max 9 words","max 9 words","max 9 words"],"source":"source name of the facts used"},
  {"kind":"poll","tag":"2 words","headline":"max 7 words question","highlight":"1-2 words","options":["max 3 words","max 3 words"],"cta":"max 9 words"},
  {"kind":"quote","tag":"1-2 words","headline":"max 6 words","highlight":"1-2 words","sub":"max 16 words"}],
 "carousel":{"cover":{"tag":"2 words","headline":"max 8 words hook","highlight":"1-2 words"},
   "slides":[{"tag":"1-2 words","title":"max 5 words","highlight":"1-2 words","body":"max 22 words"},{"tag":"","title":"","highlight":"","body":""},{"tag":"","title":"","highlight":"","body":""},{"tag":"","title":"","highlight":"","body":""}],
   "cta":{"headline":"max 4 words","highlight":"1 word","body":"max 14 words, ask to save, share and follow"}},
 "reel":{"scenes":[{"tag":"2 words","title":"max 4 words","hl":"1 word from title","sub":"max 8 words","say":"one spoken sentence, 8-14 words, natural Hinglish in Roman letters (Hindi+English mix like a young Indian creator talks, e.g. 'Yaar, pehle storage khaali kar lo')"},{"tag":"","title":"","hl":"","sub":"","say":""},{"tag":"","title":"","hl":"","sub":"","say":""},{"tag":"","title":"","hl":"","sub":"","say":""},{"tag":"","title":"","hl":"","sub":"","say":""},{"tag":"CTA","title":"","hl":"","sub":"","say":"spoken call to action in Hinglish: follow, save, share"}]},
 "captions":{"poster_1":"","poster_2":"","poster_3":"","poster_4":"","carousel":"","reel":""},
 "hashtags":["8 to 12 relevant hashtags, no #viral #fyp"]
}"""

THEMES = ["launch-night checklist (practical, funny)", "spoiler-free survival guide for the first week", "squad and co-op planning, and debates that make people comment",
          "what is confirmed vs what is still unknown (honest, no rumours)", "how to grow a gaming page during launch week (honest creator tips)"]


def _today():
    import datetime as dt
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    try:
        ld = dt.date.fromisoformat(load_json("facts.json").get("launch_date", "2026-11-19"))
    except Exception:
        ld = dt.date(2026, 11, 19)
    d = (ld - now.date()).days
    txt = now.strftime("%A %d %B %Y")
    if d > 0:
        return txt, f"GTA VI launches in {d} day(s). Use countdown energy."
    if d == 0:
        return txt, "GTA VI LAUNCHES TODAY. Talk in present tense: it is out today / tonight. Never say 'coming soon' or 'launches on'. No pre-launch checklists that assume it is not out."
    return txt, f"GTA VI has been out for {-d} day(s). Never use countdown or 'coming soon'. Talk about launch news and what media report; keep generic tips honest."


def status_code():
    return _today()[1].split()[0:3]


def load_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def _call(prompt, key):
    import requests
    models = [m for m in (os.getenv("PAGE_MODELS") or "gemini-3.6-flash,gemini-3.5-flash,gemini-3.7-flash").split(",") if m]
    last = ""
    for m in models:
        print(f"Gemini: asking {m} ...", flush=True)
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                              json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": .9, "responseMimeType": "application/json"}}, timeout=int(os.getenv("GEMINI_TIMEOUT") or 70))
            if r.ok:
                t = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(re.sub(r"^```(?:json)?|```$", "", t.strip(), flags=re.M).strip())
            last = f"{m}: {r.status_code} {r.text[:100]}"
        except Exception as ex:
            last = f"{m}: {str(ex)[:100]}"
        print("Gemini:", last, file=sys.stderr)
    raise RuntimeError(last)


ANGLES_TODAY = [
    dict(h="It's out. Today.", q="Today is the day.", poll=("Day-one plan?", ["PLAY ALL NIGHT", "TAKE IT SLOW"], "plan"),
         cover=("TODAY", "5 things to do in your first hour", "5"),
         items=["Check your download is complete and updated", "Do not read spoilers: mute keywords", "Play with headphones for the full vibe", "Take breaks: drink water, stretch", "Screenshot nothing you will regret sharing"],
         scenes=[("OUT TODAY", "GTA 6 IS OUT", "OUT", "19 Nov 2026", "Yaar, aaj GTA 6 launch ho gaya hai! Pehle ghante ki ye cheezein dekh lo."),
                 ("TIP 1", "UPDATE FIRST", "UPDATE", "Check the download", "Sabse pehle download aur update complete hai ya nahi, check kar lo."),
                 ("TIP 2", "MUTE SPOILERS", "MUTE", "Keywords off", "Spoilers se bachna hai to apne apps pe keywords mute kar do."),
                 ("TIP 3", "USE HEADPHONES", "HEADPHONES", "Full vibe", "Headphones laga ke khelo, mazaa double ho jayega."),
                 ("TIP 4", "TAKE BREAKS", "BREAKS", "Water and stretch", "Beech beech mein paani piyo, aur thoda stretch bhi kar lo."),
                 ("CTA", "FOLLOW FOR MORE", "FOLLOW", "Daily GTA 6 updates", "Roz ki GTA 6 updates ke liye follow karo, aur comment mein batao, tum kya kar rahe ho.")]),
    dict(h="Servers, snacks, squad.", q="No plans tonight.", poll=("Where are you playing?", ["PS5", "XBOX SERIES X|S"], "console"),
         cover=("LAUNCH NIGHT", "Launch night survival kit", "Survival"),
         items=["Snacks within arm's reach", "Phone on silent, notifications off", "Charge the controller before you start", "Tell family you are unavailable tonight", "Save your game often"],
         scenes=[("LAUNCH NIGHT", "SURVIVAL KIT", "KIT", "For tonight", "Aaj raat GTA 6 hai, to ye survival kit ready rakho."),
                 ("ITEM 1", "SNACKS READY", "SNACKS", "Arm's reach", "Snacks haath ke paas rakho, baar baar uthna nahi padega."),
                 ("ITEM 2", "PHONE ON SILENT", "SILENT", "Notifications off", "Phone silent pe daal do, focus mein khelo."),
                 ("ITEM 3", "CHARGE CONTROLLER", "CHARGE", "Before you start", "Controller full charge hai na? Check kar lo."),
                 ("ITEM 4", "TELL YOUR FAMILY", "FAMILY", "You are busy tonight", "Ghar pe bata do, aaj raat tum busy ho."),
                 ("CTA", "SAVE AND SHARE", "SAVE", "Follow for daily updates", "Ye save karo, dost ko bhejo, aur roz ki updates ke liye follow karo.")]),
    dict(h="Rockstar delivered.", q="Worth the wait?", poll=("Worth the wait?", ["YES, 100%", "LET ME PLAY FIRST"], "wait"),
         cover=("DEBATE", "Was it worth the long wait?", "wait"),
         items=["Years of waiting, millions of fans", "Everyone has a different first plan", "Reviews will come in the days ahead", "Your opinion matters: tell us below", "Play first, judge later"],
         scenes=[("TODAY", "WORTH THE WAIT?", "WAIT", "Tell us", "GTA 6 aa gaya! Sawaal ye hai, kya itna intezaar worth it tha?"),
                 ("THE WAIT", "YEARS OF HYPE", "HYPE", "Millions of fans", "Saalon ka hype, aur lakhon fans ka intezaar."),
                 ("THE PLAN", "EVERYONE DIFFERENT", "PLAN", "First thing you do", "Har kisi ka pehla plan alag hota hai."),
                 ("THE VERDICT", "PLAY, THEN JUDGE", "JUDGE", "Reviews coming", "Pehle khelo, phir faisla karo."),
                 ("YOUR TAKE", "COMMENT BELOW", "COMMENT", "Yes or not yet", "Comment mein batao, haan ya abhi nahi."),
                 ("CTA", "FOLLOW US", "FOLLOW", "Daily GTA 6 news", "Roz ki GTA 6 news ke liye follow karo.")]),
]


def angle_pack(cfg, A, rng, today=True):
    hl = lambda s: s.split()[0].strip(".,'?")
    return {
        "posters": [
            {"kind": "launch", "tag": "OUT TODAY" if today else "OUT NOW", "headline": A["h"], "highlight": hl(A["h"]), "date": "19 NOV 2026", "sub": "PS5  /  XBOX SERIES X|S", "cta": "Save this. Send it to your squad.", "cta2": "Follow for daily GTA 6 updates."},
            {"kind": "fact", "tag": "FIRST HOUR", "headline": A["cover"][1], "highlight": A["cover"][2], "items": A["items"][:3], "source": "Page tips (not official)"},
            {"kind": "poll", "tag": "YOUR CALL", "headline": A["poll"][0], "highlight": A["poll"][2], "options": A["poll"][1], "cta": "Comment A or B. Tag your co-op partner."},
            {"kind": "quote", "tag": "MOOD", "headline": A["q"], "highlight": hl(A["q"]), "sub": "Tag the friend who has been waiting for this."}],
        "carousel": {"cover": {"tag": A["cover"][0], "headline": A["cover"][1], "highlight": A["cover"][2]},
                     "slides": [{"tag": "TIP", "title": x[:34], "highlight": hl(x), "body": ""} for x in A["items"][:4]],
                     "cta": {"headline": "Save this.", "highlight": "Save", "body": "Send it to your squad and follow for daily GTA 6 updates."}},
        "reel": {"scenes": [{"tag": a, "title": b, "hl": c, "sub": d, "say": e} for a, b, c, d, e in A["scenes"]]},
        "captions": {"poster_1": "It's out. What are you playing first? Tell us below.", "poster_2": "Save this for later.", "poster_3": "Pick one in the comments.", "poster_4": "Tag the friend.",
                     "carousel": "Save this. Which tip do you need most?", "reel": "Which one will you do first? Comment below. Follow for daily GTA 6 updates."},
        "hashtags": cfg["hashtags_base"]}


def fallback(cfg, facts, rng):
    code = _today()[1]
    if code.startswith("GTA VI LAUNCHES TODAY") or code.startswith("GTA VI has been out"):
        return angle_pack(cfg, rng.choice(ANGLES_TODAY), rng, code.startswith("GTA VI LAUNCHES"))
    return fallback_before(cfg, facts, rng)


def fallback_before(cfg, facts, rng):
    F = facts["confirmed"]
    date = next((f["text"] for f in F if f["id"] == "date"), "Launches 19 November 2026")
    pre = next((f["text"] for f in F if f["id"] == "preload"), "Pre-load is open")
    plat = next((f["text"] for f in F if f["id"] == "platforms"), "PS5 and Xbox Series X|S")
    pre = pre.replace("Pre-load begins", "Pre-load began")
    heads = ["It's launch day.", "Tonight, we play.", "No more waiting.", "Clear your calendar."]
    quotes = ["The wait is finally over.", "Sleep is optional now.", "Six years. One night.", "Tell your boss. Or don't."]
    polls = [("Which console are you on?", ["PS5", "XBOX SERIES X|S"], "console"), ("Solo or squad on day one?", ["SOLO RUN", "WITH THE SQUAD"], "squad"), ("Story first or free roam first?", ["STORY", "FREE ROAM"], "first")]
    pl = rng.choice(polls)
    hl = lambda t: t.split()[0].strip(".,'")
    h = rng.choice(heads)
    q = rng.choice(quotes)
    items = ["Free up storage before you play", "Charge the controller. Twice.", "Mute spoiler keywords on every app", "Plan your snacks, not just your route", "Tell your squad the start time"]
    rng.shuffle(items)
    scenes = [("LAUNCH DAY", "19 NOV 2026", "19", "Launch checklist", "Yaar, launch day aa gaya! Ye checklist dekh lo, kaam aayegi."),
              ("STEP 1", "FREE UP SPACE", "SPACE", "Storage first, always", "Sabse pehle storage khaali karo. Full drive se bura kuch nahi."),
              ("STEP 2", "CHARGE EVERYTHING", "CHARGE", "Controller, headset, phone", "Dusra, controller aur headset full charge kar lo. Do baar."),
              ("STEP 3", "MUTE THE SPOILERS", "MUTE", "Keywords off on every app", "Teesra, har app pe spoiler wale keywords mute kar do."),
              ("STEP 4", "PICK YOUR SQUAD", "SQUAD", "Agree a start time", "Chautha, squad ko exact start time bata do."),
              ("CTA", "SAVE THIS", "SAVE", "Follow for daily updates", "Ye save karo, squad ko bhejo, aur daily updates ke liye follow karo.")]
    return {
        "posters": [
            {"kind": "launch", "tag": "LAUNCH DAY", "headline": h, "highlight": hl(h), "date": "19 NOV 2026", "sub": "PS5  /  XBOX SERIES X|S", "cta": "Save this. Send it to your squad.", "cta2": "Follow for daily launch-week updates."},
            {"kind": "fact", "tag": "WHAT WE KNOW", "headline": "Confirmed, no rumours", "highlight": "Confirmed", "items": [date, pre, plat], "source": "Rockstar Games newswire"},
            {"kind": "poll", "tag": "YOUR CALL", "headline": pl[0], "highlight": pl[2], "options": pl[1], "cta": "Comment A or B. Tag your co-op partner."},
            {"kind": "quote", "tag": "MOOD", "headline": q, "highlight": hl(q), "sub": "Tag the friend who has been counting down since 2013."}],
        "carousel": {"cover": {"tag": "CHECKLIST", "headline": "5 things to do before you press start", "highlight": "5"},
                     "slides": [{"tag": "PREP", "title": t.split(".")[0][:34], "highlight": hl(t), "body": ""} for t in items[:4]],
                     "cta": {"headline": "Save this.", "highlight": "Save", "body": "Send it to your squad and follow for daily launch-week updates."}},
        "reel": {"scenes": [{"tag": a, "title": b, "hl": c, "sub": d, "say": e} for a, b, c, d, e in scenes]},
        "captions": {"poster_1": "It's here. Tag your squad.", "poster_2": "Only confirmed facts on this page. Source in the image.", "poster_3": "Pick one in the comments.", "poster_4": "Tag the friend.",
                     "carousel": "Save this checklist for launch night.", "reel": "Your launch-night checklist. Save it and send it to your squad."},
        "hashtags": cfg["hashtags_base"],
    }


def make_pack(cfg, facts, rng, use_ai=True, avoid=None, news=None):
    key = os.getenv("GEMINI_API_KEY")
    err = ""
    if use_ai and key:
        fx = "\n".join(f"- {f['text']} (source: {f['source']})" for f in facts["confirmed"])
        prompt = PROMPT.format(tone=cfg["tone"], facts=fx, today=_today()[0], status=_today()[1], theme=("today's news digest" if news else rng.choice(THEMES)), news=(_news_txt(news) if news else "(none today)"), handle=cfg["handle"], avoid="; ".join((avoid or [])[-30:]) or "none", schema=SCHEMA)
        try:
            c = _call(prompt, key)
            fb = fallback(cfg, facts, rng)
            for k in ("posters", "carousel", "reel", "captions", "hashtags"):
                c.setdefault(k, fb[k])
            return c, "written by Gemini from facts.json"
        except Exception as ex:
            print("AI copy failed, using the offline template:", ex, file=sys.stderr)
            err = str(ex)[:160]
    fb = fallback(cfg, facts, rng)
    if news and _today()[1].startswith("GTA VI launches in"):
        top = news[:3]
        fb["posters"][1] = {"kind": "fact", "tag": "TODAY'S NEWS", "headline": "GTA 6 news today", "highlight": "News",
                            "items": [(("" if n["official"] else "Reported: ") + n["title"])[:90] for n in top], "source": ", ".join(sorted({n["source"] for n in top}))[:60]}
    return fb, "offline template (" + (err or "no GEMINI_API_KEY") + ")"


def _news_txt(news):
    from . import news as N
    return N.as_prompt(news)


def lines_used(c):
    out = [p.get("headline", "") for p in c.get("posters", [])] + [c.get("carousel", {}).get("cover", {}).get("headline", "")]
    return [o for o in out if o]
