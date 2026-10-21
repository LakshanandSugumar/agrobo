"""Procedural photographic-style leaf textures (RGBA albedo with alpha cut-out + height map for veins).
Run once: python textures.py  -> writes ../tex/*.png"""
import os, math
import numpy as np
from PIL import Image, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tex')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def fbm(h, w, octaves=6, base=4, seed=0):
    r = np.random.default_rng(seed); acc = np.zeros((h, w)); amp = 1.0; tot = 0
    for o in range(octaves):
        n = base * 2 ** o
        g = r.random((n + 1, int(n * w / h) + 2))
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        acc += amp * np.asarray(im, float) / 255; tot += amp; amp *= .5
    return acc / tot


def leaflet(W=1024, H=512, seed=1, lobes=True):
    """Tomato leaflet: u (x) along the blade 0..1 base->tip, v (y) across. Ovate, pointed, irregularly serrated/lobed."""
    r = np.random.default_rng(seed)
    x = np.linspace(0, 1, W)[None, :].repeat(H, 0); y = np.linspace(-1, 1, H)[:, None].repeat(W, 1)
    half = .92 * np.sin(np.pi * np.clip(x, 0, 1) ** .95) ** 1.1 * (1 - .22 * x)
    half *= np.where(x < .1, (x / .1) ** 1.2, 1)  # tapered base into the petiolule
    # serration (sawtooth) + irregular lobes, different on each side
    side = np.sign(y)
    ph = np.where(side > 0, r.random() * 6, r.random() * 6)
    saw = ((x * 22 + ph) % 1.0)
    tooth = np.minimum(saw / .8, (1 - saw) / .2)  # asymmetric teeth leaning to the tip
    serr = .055 * (1 - tooth) * np.clip((x - .12) * 4, 0, 1) * (1 + .5 * np.sin(x * 37 + ph))
    lobe = (.10 * np.sin(x * np.pi * 3.2 + ph) ** 2 * np.clip(1 - x, 0, 1)) if lobes else 0
    edge = half * (1 - serr - lobe)
    alpha = np.clip((edge - np.abs(y)) * H * .5, 0, 1)
    # veins: midrib + curved secondaries + fine reticulation
    ay = np.abs(y) / np.maximum(half, 1e-3)
    mid = np.exp(-(y / (.018 + .02 * (1 - x))) ** 2)
    sec = np.zeros_like(x)
    for xi in np.arange(.1, .92, .085):
        d = x - (xi + .30 * ay ** 1.2 * (1 - .2 * xi))
        sec = np.maximum(sec, np.exp(-(d / (.007 + .006 * (1 - ay))) ** 2) * (ay < .92) * (1 - .7 * ay))
    reti = fbm(H, W, 5, 24, seed + 3); reti = np.clip(1 - np.abs(reti - .5) * 22, 0, 1) * .18
    veins = np.clip(mid + .7 * sec + reti * (1 - mid), 0, 1)
    # colour: deep green blade, lighter veins, mottling, darker margins, slightly yellow at the tip sometimes
    m = fbm(H, W, 6, 3, seed + 9)
    base = np.stack([.035 + .025 * m, .085 + .045 * m, .018 + .012 * m], -1)  # linear; ~sRGB (50,85,25)
    vein_c = np.array([.12, .19, .05])
    col = base * (1 - .45 * veins[..., None]) + vein_c * .45 * veins[..., None]
    col *= (1 - .25 * np.clip(ay - .75, 0, 1)[..., None] * 4)
    yel = np.clip((fbm(H, W, 4, 2, seed + 21) - .62) * 4, 0, 1) * .5
    col = col * (1 - yel[..., None]) + np.array([.16, .17, .03]) * yel[..., None]
    rgba = np.dstack([np.clip(col, 0, 1) ** (1 / 2.2), alpha])
    height = np.clip(.5 + .35 * (1 - veins) * .8 + .15 * fbm(H, W, 6, 16, seed + 5), 0, 1)
    return rgba, height


def twig_card(S=512, seed=1, n=46, col=(.16, .24, .09)):
    """Card with a leafy clump (sub-twigs carrying small elliptic leaves) for distant trees and hedges."""
    r = np.random.default_rng(seed)
    img = np.zeros((S, S, 4))
    yy, xx = np.mgrid[0:S, 0:S] / S
    for t in range(5):  # sub-twigs radiating from the bottom centre
        a0 = -np.pi / 2 + (t - 2) * .28
        twig = np.abs((xx - .5) * np.sin(a0) - (yy - .95) * np.cos(a0)) < .004
        along = (xx - .5) * np.cos(a0) + (yy - .95) * np.sin(a0)
        twig &= (along > 0) & (along < .5)
        img[twig, :3] = [.03, .025, .02]; img[twig, 3] = 1
    for k in range(n):
        rad = .42 * np.sqrt(r.random()); th = r.random() * 2 * np.pi
        ex, ey = .5 + rad * np.cos(th), .48 + rad * np.sin(th) * .9
        ang = r.random() * np.pi; L = .09 + .05 * r.random(); Wd = L * .5
        dx, dy = xx - ex, yy - ey
        u = dx * np.cos(ang) + dy * np.sin(ang); v = -dx * np.sin(ang) + dy * np.cos(ang)
        a = (u / L * 2) ** 2 + (v / Wd * 2) ** 2 < 1
        shade = .6 + .7 * r.random()
        c = np.array(col) ** 2.2 * shade * np.array([1 + .2 * (r.random() - .5), 1, 1 + .2 * (r.random() - .5)])
        vein = np.exp(-(v / .003) ** 2) * .25
        img[a, :3] = (c * (1 + vein[..., None]))[a]; img[a, 3] = 1
    img[..., :3] = np.clip(img[..., :3], 0, 1) ** (1 / 2.2)
    return img


def save_rgba(a, name):
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGBA').save(f'{OUT}/{name}')


def save_gray(a, name):
    Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(.6)).save(f'{OUT}/{name}')


if __name__ == '__main__':
    for s in range(3):
        rgba, h = leaflet(seed=s + 1); save_rgba(rgba, f'leaflet{s}.png'); save_gray(h, f'leaflet{s}_h.png')
    for s, c in enumerate([(.16, .24, .09), (.19, .27, .1), (.24, .27, .11), (.13, .2, .08)]):
        save_rgba(twig_card(seed=s + 10, col=c), f'twig{s}.png')
    print('textures ->', OUT, sorted(os.listdir(OUT)))
