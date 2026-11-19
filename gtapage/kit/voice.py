"""Reel voices. Order for 'auto': ElevenLabs (your own voice, if keys exist) -> Sarvam Bulbul (natural Indian voices, SARVAM_API_KEY)
-> Gemini TTS (natural, uses the same GEMINI_API_KEY) -> Edge (free, most robotic). Each provider that fails hands over to the next one."""
import asyncio
import base64
import os
import re
import sys
import time
import wave
from pathlib import Path

G_API = "https://generativelanguage.googleapis.com/v1beta"
GENDER = (os.getenv("VOICE_GENDER") or "F").upper()[:1]

STYLE = {
    "hinglish": "natural Hinglish (Hindi and English mixed) as a friendly young Indian creator talks on Instagram; warm, upbeat, conversational and a little quick, "
                "expressive intonation, stresses the key word, tiny natural pauses at commas, smiling voice, never flat, never robotic or newsreader-like",
    "hindi": "natural spoken Hindi, warm friendly and lively like a creator talking to friends; expressive, small natural pauses, never robotic",
    "english": "natural Indian English, warm, upbeat and conversational like a friendly creator; expressive, never robotic",
    "marathi": "natural spoken Marathi, warm friendly and lively; expressive, never robotic",
    "bengali": "natural spoken Bengali, warm friendly and lively; expressive, never robotic",
}
SARVAM_LANG = {"hinglish": "hi-IN", "hindi": "hi-IN", "english": "en-IN", "marathi": "mr-IN", "bengali": "bn-IN"}
EDGE = {"english": ("en-IN-NeerjaNeural", "en-IN-PrabhatNeural"), "hinglish": ("en-IN-NeerjaNeural", "en-IN-PrabhatNeural"),
        "hindi": ("hi-IN-SwaraNeural", "hi-IN-MadhurNeural"), "marathi": ("mr-IN-AarohiNeural", "mr-IN-ManoharNeural"),
        "bengali": ("bn-IN-TanishaaNeural", "bn-IN-BashkarNeural")}


def clean(text):
    t = re.sub(r"\s*(?:[—–|]| - )\s*", ", ", str(text))
    t = re.sub(r"\s+", " ", t).strip()
    return t if re.search(r"[.!?।…]$", t) else t + "."


def _find_audio(o):
    if isinstance(o, dict):
        if o.get("type") == "audio" and isinstance(o.get("data"), str):
            return o["data"]
        for k in ("inlineData", "inline_data"):
            if isinstance(o.get(k), dict) and isinstance(o[k].get("data"), str):
                return o[k]["data"]
        for v in o.values():
            r = _find_audio(v)
            if r:
                return r
    elif isinstance(o, list):
        for v in reversed(o):
            r = _find_audio(v)
            if r:
                return r
    return None


def _save_wav(b64, out):
    raw = base64.b64decode(b64)
    if raw[:4] == b"RIFF":
        Path(out).write_bytes(raw)
    else:
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(raw)


def gemini(text, lang, out):
    import requests
    hdr = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"}
    voice = os.getenv("GEMINI_TTS_VOICE_M" if GENDER == "M" else "GEMINI_TTS_VOICE_F") or ("Charon" if GENDER == "M" else "Sulafat")
    safe = "Charon" if GENDER == "M" else "Kore"
    style = os.getenv("GEMINI_TTS_STYLE") or STYLE.get(lang, STYLE["english"])
    models = [m for m in dict.fromkeys([os.getenv("GEMINI_TTS_MODEL") or "", "gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"]) if m]
    errs, deadline = [], time.time() + 120
    for model in models + ["gemini-2.5-flash-preview-tts"]:
        legacy = "2.5" in model
        for attempt in range(3):
            if time.time() > deadline:
                raise RuntimeError("Gemini TTS out of time | " + " | ".join(errs[-3:]))
            try:
                if legacy:
                    r = requests.post(f"{G_API}/models/{model}:generateContent", headers=hdr, timeout=100, json={
                        "contents": [{"parts": [{"text": f"Say in a {style} tone: {text}"}]}],
                        "generationConfig": {"responseModalities": ["AUDIO"],
                                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}})
                else:
                    r = requests.post(f"{G_API}/interactions", headers=hdr, timeout=90, json={
                        "model": model,
                        "input": [{"type": "user_input", "content": [{"type": "text", "text": text,
                                   "annotations": [{"type": "speech_metadata", "style": style}]}]}],
                        "response_format": {"type": "audio"},
                        "generation_config": {"speech_config": [{"voice": voice}]}})
            except requests.RequestException as ex:
                errs.append(f"{model}: {str(ex)[:70]}")
                break
            if r.ok:
                try:
                    data = _find_audio(r.json())
                except Exception:
                    data = None
                if data:
                    _save_wav(data, out)
                    return f"gemini-tts:{voice}"
                errs.append(f"{model}: no audio")
                break
            errs.append(f"{model}: {r.status_code} {r.text[:90]}")
            if r.status_code == 400 and re.search(r"voice", r.text, re.I) and voice != safe:
                voice = safe
                continue
            if r.status_code == 429 and not re.search(r"PerDay|per day|daily|limit: 0", r.text, re.I):
                time.sleep(15 * (attempt + 1))
                continue
            if r.status_code in (500, 502, 503, 504):
                time.sleep(6)
                continue
            break
    raise RuntimeError("Gemini TTS: " + " | ".join(errs[-3:]))


def sarvam(text, lang, out):
    import requests
    speaker = os.getenv("SARVAM_MALE" if GENDER == "M" else "SARVAM_FEMALE") or ("ashutosh" if GENDER == "M" else "ritu")
    body = {"text": text, "target_language_code": os.getenv("VOICE_LANG") or SARVAM_LANG.get(lang, "hi-IN"), "speaker": speaker,
            "model": os.getenv("SARVAM_MODEL") or "bulbul:v3", "pace": float(os.getenv("SARVAM_PACE") or 1.05), "speech_sample_rate": 24000}
    extras, use, err = {"temperature": 0.6, "enable_preprocessing": True}, True, ""
    for attempt in range(3):
        r = requests.post("https://api.sarvam.ai/text-to-speech", headers={"api-subscription-key": os.environ["SARVAM_API_KEY"], "Content-Type": "application/json"},
                          json={**body, **(extras if use else {})}, timeout=60)
        if r.ok:
            Path(out).write_bytes(base64.b64decode(r.json()["audios"][0]))
            return f"sarvam:{speaker}"
        err = f"{r.status_code}: {r.text[:200]}"
        if r.status_code in (400, 422) and use:
            use = False
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(5 * (attempt + 1))
            continue
        break
    raise RuntimeError("Sarvam " + err)


def eleven(text, lang, out):
    import requests
    vid = os.getenv("ELEVEN_VOICE_M" if GENDER == "M" else "ELEVEN_VOICE_F") or os.getenv("ELEVEN_VOICE")
    if not vid:
        raise RuntimeError("ELEVEN_VOICE missing")
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128", headers={"xi-api-key": os.environ["ELEVEN_API_KEY"]},
                      json={"text": text, "model_id": os.getenv("ELEVEN_MODEL") or "eleven_multilingual_v2",
                            "voice_settings": {"stability": float(os.getenv("ELEVEN_STABILITY") or .4), "similarity_boost": .8, "style": .35, "use_speaker_boost": True}}, timeout=90)
    r.raise_for_status()
    Path(out).write_bytes(r.content)
    return "elevenlabs"


def edge(text, lang, out):
    import edge_tts
    f, m = EDGE.get(lang, EDGE["english"])
    v = os.getenv("EDGE_VOICE") or (m if (os.getenv("VOICE_GENDER") or "F").upper()[:1] == "M" else f)
    asyncio.run(edge_tts.Communicate(text, v, rate="+10%").save(str(out)))
    return "edge:" + v


FUNCS = {"elevenlabs": eleven, "sarvam": sarvam, "gemini": gemini, "edge": edge}


def chain(first="auto"):
    if first != "auto":
        return [first] + [p for p in ("gemini", "edge") if p != first]
    c = []
    if os.getenv("ELEVEN_API_KEY") and (os.getenv("ELEVEN_VOICE") or os.getenv("ELEVEN_VOICE_F") or os.getenv("ELEVEN_VOICE_M")):
        c.append("elevenlabs")
    if os.getenv("SARVAM_API_KEY"):
        c.append("sarvam")
    if os.getenv("GEMINI_API_KEY"):
        c.append("gemini")
    return c + ["edge"]


def speak(text, lang, out, providers):
    """Try the providers in order. Returns (provider that worked, label). Raises if all fail."""
    text = clean(text)
    errs = []
    for p in providers:
        try:
            return p, FUNCS[p](text, lang, out)
        except Exception as ex:
            errs.append(f"{p}: {str(ex)[:140]}")
            print(f"voice provider {p} failed -> next. {str(ex)[:160]}", file=sys.stderr)
    raise RuntimeError(" | ".join(errs))
