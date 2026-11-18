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
CONFIRMED FACTS (the ONLY facts you may state as true):
{facts}
RULES
- Do not state any other fact about the game (no price, map, characters, story, release time) unless it is in the list. If you want to talk about the unknown, say plainly that it is unconfirmed or a question.
- No rumours presented as facts. No leaks. No official screenshots or trailer frames are used; do not describe them.
- No income promises or "earn lakhs" claims. Creator tips must be practical and honest.
- Every line short and punchy, built to be saved, shared or commented on. Hooks first. No emojis in on-image text.
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


def fallback(cfg, facts, rng):
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


def make_pack(cfg, facts, rng, use_ai=True, avoid=None):
    key = os.getenv("GEMINI_API_KEY")
    if use_ai and key:
        fx = "\n".join(f"- {f['text']} (source: {f['source']})" for f in facts["confirmed"])
        prompt = PROMPT.format(tone=cfg["tone"], facts=fx, theme=rng.choice(THEMES), avoid="; ".join((avoid or [])[-30:]) or "none", schema=SCHEMA)
        try:
            c = _call(prompt, key)
            fb = fallback(cfg, facts, rng)
            for k in ("posters", "carousel", "reel", "captions", "hashtags"):
                c.setdefault(k, fb[k])
            return c, "written by Gemini from facts.json"
        except Exception as ex:
            print("AI copy failed, using the offline template:", ex, file=sys.stderr)
    return fallback(cfg, facts, rng), "offline template (no GEMINI_API_KEY or AI failed)"


def lines_used(c):
    out = [p.get("headline", "") for p in c.get("posters", [])] + [c.get("carousel", {}).get("cover", {}).get("headline", "")]
    return [o for o in out if o]
