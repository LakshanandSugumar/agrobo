"""Synthesised score for the Agrobo film (no samples, no external assets). Writes out/score.wav."""
import numpy as np, wave, pathlib
SR, DUR = 48000, 86.0
N = int(SR * DUR)
L = np.zeros(N); R = np.zeros(N); SUB = np.zeros(N)
rng = np.random.default_rng(7)
mf = lambda m: 440 * 2 ** ((m - 69) / 12)

def add(buf, t0, sig, gain=1.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if j > i: buf[i:j] += sig[: j - i] * gain

def pad_note(m, dur, bright, att=1.6, rel=2.2):
    n = int((dur + rel) * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for cents in (-7, 0, 7):
        f = mf(m) * 2 ** (cents / 1200); ph = rng.uniform(0, 6.28)
        for h in range(1, 14):
            if f * h > 9000: break
            out += np.sin(2 * np.pi * f * h * t + ph * h) / h ** bright
    env = np.minimum(1, t / att) * np.where(t < dur, 1, np.exp(-(t - dur) / (rel / 3)))
    env *= 1 + 0.08 * np.sin(2 * np.pi * 0.15 * t)
    return out * env / 3

CHORDS = [  # start, end, midi notes, brightness exponent (higher = darker), gain
    (0, 7.4, [38, 45, 53, 60, 64], 2.2, .9), (7, 15.4, [34, 46, 53, 57, 62], 2.0, .8),
    (15, 20.2, [38, 45, 53, 57, 62], 1.8, .8), (20, 25.4, [34, 46, 53, 58, 62], 1.8, .8),
    (25, 29.7, [41, 48, 53, 57, 60], 1.7, .8), (29.5, 34.4, [36, 43, 52, 55, 60], 1.7, .8),
    (34, 37.2, [38, 45, 53, 57, 62], 1.6, .8), (37, 40.2, [34, 46, 53, 58, 62], 1.6, .8),
    (40, 43.2, [41, 48, 53, 57, 60], 1.6, .8), (43, 46.4, [36, 43, 52, 55, 60], 1.6, .8),
    (46, 56.4, [38, 45, 57, 64], 2.4, .7),
    (56, 58.7, [34, 46, 53, 58, 62], 1.5, .85), (58.5, 61.2, [36, 48, 52, 55, 60], 1.5, .85),
    (61, 63.7, [38, 50, 53, 57, 62], 1.4, .9), (63.5, 66.4, [34, 46, 53, 58, 65], 1.4, .9),
    (66, 71.2, [41, 48, 57, 60, 65], 2.0, .85), (71, 76.4, [34, 46, 57, 62, 65], 2.0, .85),
    (76, 86, [29, 41, 48, 53, 57, 60, 65, 69], 1.8, 1.0),
]
for a, b, notes, br, g in CHORDS:
    for m in notes:
        sig = pad_note(m, b - a, br, rel=4.5 if a == 76 else 2.2)
        pan = 0.5 + 0.35 * np.tanh((m - 52) / 12) * (1 if m % 2 else -1)
        add(L, a, sig, g * .11 * (1 - pan) * 2); add(R, a, sig, g * .11 * pan * 2)

def kick(gain=1.0, f0=95, f1=38, dec=.45):
    t = np.arange(int(SR * 1.0)) / SR; f = f1 + (f0 - f1) * np.exp(-t / .05)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec) * gain
beat = 60 / 96
t = 15.0
while t < 66:
    if t < 25: g = .35 if (round((t - 15) / beat) % 2 == 0) else 0
    elif t < 46: g = .45 + .25 * (t - 25) / 21
    elif t < 56: g = .5 if (round((t - 46) / beat) % 2 == 0) else .3   # heartbeat
    else: g = .7 + .25 * (t - 56) / 10
    if g: add(SUB, t, kick(g))
    t += beat
add(SUB, 23.2, kick(1.2, 120, 32, .9)); add(SUB, 76.0, kick(1.4, 110, 28, 1.6)); add(SUB, 15.0, kick(.8, 110, 30, .9))

def click(f=4200, dec=.018, g=1.0):
    n = int(SR * .12); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / dec) + rng.normal(0, .5, n) * np.exp(-t / .003)) * g
t = 46.4
while t < 55.6:   # watch-movement ticks during the harvest
    s = click(3600 if round((t - 46.4) / (beat / 2)) % 2 else 4400, g=.10); add(L, t, s, .9); add(R, t, s, 1.0); t += beat / 2
for k in range(46):  # data blips while parcels are scored
    tt = 15.4 + k * .083; s = click(rng.choice([1800, 2400, 3000, 3600]), .035, .05); add(L if k % 2 else R, tt, s)

def whoosh(cut, pre=1.0, post=.5, g=.35, lo=300, hi=6000):
    n = int(SR * (pre + post)); x = rng.normal(0, 1, n); X = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1 / SR)
    X *= np.exp(-((np.log(fr + 1) - np.log(np.sqrt(lo * hi))) ** 2) / 1.2); x = np.fft.irfft(X, n); x /= np.abs(x).max()
    t = np.arange(n) / SR; env = np.where(t < pre, (t / pre) ** 2.5, np.exp(-(t - pre) / .12))
    s = x * env * g; add(L, cut - pre, s); add(R, cut - pre, np.roll(s, 200))
for c in (7, 15, 25, 34, 46, 56, 66, 76): whoosh(c, g=.28 if c != 76 else .4)

def bell(m, dur=3.5, g=.2):
    n = int(SR * dur); t = np.arange(n) / SR; f = mf(m)
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (d)) for r, a, d in [(1, 1, 1.2), (2.01, .5, .6), (3.0, .25, .35), (4.2, .12, .2)]) * g
add(L, 11.25, click(2600, .01, .25)); add(R, 11.25, click(2600, .01, .25))      # tap
for tt, m in [(66.8, 76), (66.95, 83)]: s = bell(m, g=.16); add(L, tt, s); add(R, tt, s)  # notification chime
s = bell(81, 2, .22); add(L, 23.2, s, .7); add(R, 23.2, s, .9)                    # stamp shimmer

def piano(m, dur=4, g=.18):
    n = int(SR * dur); t = np.arange(n) / SR; f = mf(m)
    return sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (1.4 + h * .9)) for h, a in [(1, 1), (2, .45), (3, .2), (4, .1)]) * np.minimum(1, t / .004) * g
MOTIF = [(0, 69), (.55, 72), (1.1, 74), (1.9, 76)]
for t0, sc in [(1.2, .8), (67.6, 1.0), (77.0, 1.1)]:
    for dt, m in MOTIF: s = piano(m, g=.16 * sc); add(L, t0 + dt, s, .9); add(R, t0 + dt, s, 1.0)
for dt, m in [(0, 77), (.45, 76), (.9, 74), (1.6, 72)]:  # answer phrase before the payout
    s = piano(m, g=.12); add(L, 62.4 + dt, s); add(R, 62.4 + dt, s)

# reverb (stereo exponential-noise IR) via FFT convolution
irn = int(SR * 3.2); ti = np.arange(irn) / SR
def rev(x, seed):
    ir = np.random.default_rng(seed).normal(0, 1, irn) * np.exp(-ti / .75); ir[:int(SR * .02)] *= np.linspace(0, 1, int(SR * .02))
    m = 1 << int(np.ceil(np.log2(len(x) + irn))); y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)]
    return y / np.abs(ir).sum() * 18
wl, wr = rev(L, 1), rev(R, 2)
outL = L + .55 * wl + SUB; outR = R + .55 * wr + SUB
mix = np.stack([outL, outR], 1)
mix /= np.abs(mix).max(); mix = np.tanh(mix * 1.6) / np.tanh(1.6)
tt = np.arange(N) / SR; mix *= np.minimum(1, tt / 1.0)[:, None] * np.minimum(1, (DUR - tt) / 2.5)[:, None]
mix *= 10 ** (-1 / 20) / np.abs(mix).max()
out = pathlib.Path(__file__).resolve().parents[1] / 'out' / 'score.wav'
with wave.open(str(out), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote', out)
