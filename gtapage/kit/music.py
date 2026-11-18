"""Original background beat made by code (no licence worries): soft kick, hats, bass and a plucky pentatonic arpeggio."""
import wave

import numpy as np

SR = 44100


def _env(n, a=.005, d=.2):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)


def track(seconds, seed, path):
    rng = np.random.RandomState(seed)
    bpm = rng.choice([96, 104, 112, 120])
    beat = 60.0 / bpm
    n = int((seconds + 1) * SR)
    out = np.zeros(n)
    root = rng.choice([48, 50, 52, 53, 55])                    # MIDI root
    scale = [0, 3, 5, 7, 10, 12] if rng.rand() < .5 else [0, 2, 4, 7, 9, 12]
    f = lambda m: 440.0 * 2 ** ((m - 69) / 12)
    prog = [0, 5, 3, 7] if scale[1] == 3 else [0, 7, 9, 5]
    step = 0
    t0 = 0.0
    while t0 < seconds + 1:
        i0 = int(t0 * SR)
        beat_i = step % 4
        bar = (step // 4) % 4
        # kick on every beat
        k = int(.28 * SR)
        tt = np.arange(k) / SR
        kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
        out[i0:i0 + k] += .55 * kick[:max(0, min(k, n - i0))] if i0 < n else 0
        # hats on offbeats
        for off in (.5,):
            j = int((t0 + off * beat) * SR)
            h = int(.05 * SR)
            if j + h < n:
                out[j:j + h] += .05 * rng.randn(h) * np.exp(-np.arange(h) / SR * 70)
        # bass note on beats 1 and 3
        if beat_i % 2 == 0:
            m = root - 12 + prog[bar]
            L = int(beat * 1.9 * SR)
            if i0 + L < n:
                x = np.arange(L) / SR
                out[i0:i0 + L] += .22 * np.sin(2 * np.pi * f(m) * x) * _env(L, .01, .5)
        # arpeggio pluck on every half-beat
        for q in (0, .5):
            m = root + 12 + prog[bar] + scale[rng.randint(len(scale))]
            j = int((t0 + q * beat) * SR)
            L = int(.4 * SR)
            if j + L < n:
                x = np.arange(L) / SR
                out[j:j + L] += .1 * (np.sin(2 * np.pi * f(m) * x) + .4 * np.sin(4 * np.pi * f(m) * x)) * _env(L, .003, .12)
        t0 += beat
        step += 1
    out = out[:n]
    out = np.tanh(out * 1.4) * .8
    fade = int(.8 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    pcm = (out * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path
