"""Graphics-only Reel (1080x1920): moving retro scenes, kinetic headline + highlight chip, HUD progress, natural Indian-English voice-over, generated beat."""
import random
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import music, style, voice
from .common import FFMPEG, ROOT, df, pf
from .posters import glass, rrect, tag, title, TITLE_FONTS

RW, RH = 1080, 1920
FPS = 30
PAD = 1.25   # extra scene length so the picture can breathe after the sentence


def _wav_len(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def _to_wav(src, dst):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src), "-ar", "44100", "-ac", "1", str(dst)], check=True)


def _voice(scenes, tmp, mode, lang="hinglish"):
    """returns list of wav paths (or None per scene) and the label of the voice used"""
    if mode == "none":
        return [None] * len(scenes), "no voice"
    prov = voice.chain("auto" if mode == "auto" else mode)
    out, label = [], ""
    for i, s in enumerate(scenes):
        raw = tmp / f"v{i}.raw"
        try:
            p, label = voice.speak(s.get("say") or s.get("title", ""), lang, raw, prov)
            f = next((x for x in tmp.glob(f"v{i}.*") if x.suffix != ".wav"), raw)
            wv = tmp / f"v{i}.wav"
            _to_wav(f, wv)
            out.append(wv)
            prov = [p] + [x for x in prov if x != p]
        except Exception as ex:
            print("voice failed for scene", i, str(ex)[:150], file=sys.stderr)
            out.append(None)
    return out, label


def _frame_static(s, P, tf, handle, i, n):
    """overlay with text, built once per scene"""
    L = Image.new("RGBA", (RW, RH), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    d.text((48, 70), "GTA VI", font=pf("Bold", 34), fill=P.ink)
    d.text((RW - 48, 76), f"{i + 1:02d} / {n:02d}", font=pf("Medium", 26), fill=P.ink + (210,), anchor="ra")
    if s.get("tag"):
        tag(L, s["tag"], 48, 140, P, 26)
    d = ImageDraw.Draw(L)
    d.text((48, RH - 200), "@" + handle, font=pf("Bold", 30), fill=P.a1)
    d.text((48, RH - 150), "Fan page. Not affiliated with Rockstar Games or Take-Two.", font=pf("Medium", 18), fill=P.ink + (150,))
    return L


def _title_layer(s, P, tf):
    L = Image.new("RGBA", (RW, 760), (0, 0, 0, 0))
    glass(L, (36, 20, RW - 36, 730), P, 150)
    y = title(L, s.get("title", ""), s.get("hl", ""), (80, 70, RW - 80, 470), P, tf, 220, "left", .98)
    if s.get("sub"):
        d = ImageDraw.Draw(L)
        f = pf("Bold", 40)
        d.text((84, min(y + 24, 560)), s["sub"], font=f, fill=P.ink)
    return L


def _ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def build(copy, handle, palette, out_path, voice_mode="auto", seed=7, tmp=None, lang="hinglish"):
    """returns info string"""
    scenes = copy["reel"]["scenes"]
    n = len(scenes)
    tmp = Path(tmp or out_path.parent / "_reel_tmp")
    tmp.mkdir(parents=True, exist_ok=True)
    P = style.Pal(palette)
    rng = random.Random(seed)
    tf = rng.choice(TITLE_FONTS[:2])
    wavs, vlabel = _voice(scenes, tmp, voice_mode, lang)
    durs = [(_wav_len(w) + PAD) if w else 3.4 for w in wavs]
    kinds = list(style.KINDS)
    rng.shuffle(kinds)
    pal_cycle = [palette] * n
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{RW}x{RH}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-an", str(tmp / "video.mp4")]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i, s in enumerate(scenes):
        bg = style.scene(kinds[i % len(kinds)], P, RW + 160, RH + 160, seed + i * 13).convert("RGB")
        stat = _frame_static(s, P, tf, handle, i, n)
        tl = _title_layer(s, P, tf)
        dark = Image.new("RGBA", (RW, RH), (4, 3, 16, 0))
        dr = ImageDraw.Draw(dark)
        for y in range(RH):                              # soft dark gradient so text stays readable
            a = int(150 * max(0, (y - RH * .35) / (RH * .65)) ** 1.2)
            dr.line((0, y, RW, y), fill=(4, 3, 16, a))
        frames = int(durs[i] * FPS)
        dirx = rng.choice([-1, 1])
        for f in range(frames):
            t = f / max(1, frames - 1)
            ox = int(80 + dirx * (t - .5) * 150)
            oy = int(80 - t * 70)
            fr = bg.crop((ox, oy, ox + RW, oy + RH)).convert("RGBA")
            fr.alpha_composite(dark)
            fr.alpha_composite(stat)
            e = _ease(f / (FPS * .45))                   # headline slides up and fades in
            lay = tl.copy()
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * e)))
            fr.alpha_composite(lay, (0, int(RH - 1000 + (1 - e) * 120)))
            d = ImageDraw.Draw(fr)
            d.rectangle((0, RH - 14, RW, RH), fill=(255, 255, 255, 40))                        # progress bar over the whole reel
            tot = sum(durs)
            done = (sum(durs[:i]) + f / FPS) / tot
            d.rectangle((0, RH - 14, int(RW * done), RH), fill=P.a1 + (255,))
            pr.stdin.write(fr.convert("RGB").tobytes())
    pr.stdin.close()
    pr.wait()
    if pr.returncode:
        raise RuntimeError("ffmpeg video encode failed")
    # audio: voice clips placed at scene starts, beat underneath
    total = sum(durs)
    mlabel = music.pick(total + 1, seed, tmp / "beat.wav", ROOT / "music", FFMPEG)
    ins = ["-i", str(tmp / "video.mp4"), "-i", str(tmp / "beat.wav")]
    filt, mix_in, k, t0 = [], ["[1:a]volume=0.30[b]"], 2, 0.0
    labels = ["[b]"]
    for i, w in enumerate(wavs):
        if w:
            ins += ["-i", str(w)]
            ms = int((t0 + .25) * 1000)
            mix_in.append(f"[{k}:a]adelay={ms}|{ms},volume=1.6[v{i}]")
            labels.append(f"[v{i}]")
            k += 1
        t0 += durs[i]
    fc = ";".join(mix_in) + ";" + "".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.95[a]"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", str(out_path)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return f"{total:.0f}s Reel, voice: {vlabel}, music: {mlabel}"
