#!/usr/bin/env python3
"""Generate the blood sprites used by the Xbox gore code (hlsdk cl_dll/xb_gore_world.cpp).

Half-Life .spr v2, INDEXALPHA: each pixel's palette index is its opacity and
palette[255] is the colour. The colour is white so the game tints each mark
red or alien-yellow itself.

  xb_splat.spr  6 frames  irregular splats (where a droplet lands)
  xb_drop.spr   1 frame   soft streak (a droplet in flight)
  xb_pool.spr   3 frames  pools that spread under bodies
  xb_foot.spr   8 frames  left / right: full, toe only, heel only, smudged

Output: uwp/package/HalfLife/sprites/
"""
import math
import os
import random
import struct

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'package', 'HalfLife', 'sprites')


def write_spr(name, frames):
    w, h = len(frames[0][0]), len(frames[0])
    data = bytearray()
    data += b'IDSP'
    data += struct.pack('<iiifiiifi', 2, 2, 2,  # type VP_PARALLEL_ORIENTED, texFormat SPR_INDEXALPHA (3 would be alpha-test)
                         math.hypot(w, h) / 2, w, h, len(frames), 0.0, 0)
    data += struct.pack('<h', 256)
    for i in range(256):
        data += bytes((255, 255, 255)) if i == 255 else bytes((i, i, i))
    for f in frames:
        data += struct.pack('<i', 0)                       # SPR_SINGLE
        data += struct.pack('<iiii', -w // 2, h // 2, w, h)
        for row in f:
            data += bytes(max(0, min(255, int(v))) for v in row)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), 'wb') as fp:
        fp.write(data)
    print('wrote', name, w, 'x', h, len(frames), 'frames')


def blob(size, seed, lobes=7, rough=0.22, droplets=6, soft=0.12, core=1.0):
    """Irregular round splat with a ragged edge and satellite drops."""
    rnd = random.Random(seed)
    phases = [(rnd.uniform(0, 6.28), rnd.uniform(0.3, 1.0)) for _ in range(lobes)]
    sats = []
    for _ in range(droplets):
        a = rnd.uniform(0, 6.28)
        d = rnd.uniform(0.55, 0.9)
        sats.append((math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.04, 0.1)))
    img = []
    for y in range(size):
        row = []
        for x in range(size):
            u = (x + 0.5) / size * 2 - 1
            v = (y + 0.5) / size * 2 - 1
            r = math.hypot(u, v)
            a = math.atan2(v, u)
            edge = 0.55 + sum(amp * rough * math.sin(a * (i + 2) + ph) / (i + 1) for i, (ph, amp) in enumerate(phases))
            t = (edge - r) / soft
            val = max(0.0, min(1.0, t))
            for sx, sy, sr in sats:
                dd = math.hypot(u - sx, v - sy)
                val = max(val, max(0.0, min(1.0, (sr - dd) / (sr * 0.5))))
            # darker, thicker middle
            val *= 0.85 + 0.15 * core * max(0.0, 1 - r)
            row.append(val * 250)
        img.append(row)
    return img


def streak(w, h):
    img = []
    for y in range(h):
        row = []
        for x in range(w):
            u = (x + 0.5) / w * 2 - 1
            v = (y + 0.5) / h            # 0 head .. 1 tail
            width = 1.0 - 0.75 * v
            val = max(0.0, 1 - abs(u) / max(width, 0.05)) * (1.0 - 0.8 * v)
            row.append(val * 240)
        img.append(row)
    return img


def pool(size, seed):
    rnd = random.Random(seed)
    phases = [(rnd.uniform(0, 6.28), rnd.uniform(0.4, 1.0)) for _ in range(5)]
    img = []
    for y in range(size):
        row = []
        for x in range(size):
            u = (x + 0.5) / size * 2 - 1
            v = (y + 0.5) / size * 2 - 1
            r = math.hypot(u, v)
            a = math.atan2(v, u)
            edge = 0.8 + sum(amp * 0.035 * math.sin(a * (i + 2) + ph) for i, (ph, amp) in enumerate(phases))
            t = (edge - r) / 0.08
            val = max(0.0, min(1.0, t))
            # thin glossy rim, solid body
            val *= 0.92 + 0.08 * max(0.0, 1 - abs(r - edge) * 12)
            row.append(val * 235)
        img.append(row)
    return img


def value_noise(w, h, cell, seed):
    """smooth random field 0..1"""
    rnd = random.Random(seed)
    gw, gh = w // cell + 2, h // cell + 2
    g = [[rnd.random() for _ in range(gw)] for _ in range(gh)]
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            fx, fy = x / cell, y / cell
            ix, iy = int(fx), int(fy)
            tx, ty = fx - ix, fy - iy
            tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
            a = g[iy][ix] * (1 - tx) + g[iy][ix + 1] * tx
            b = g[iy + 1][ix] * (1 - tx) + g[iy + 1][ix + 1] * tx
            row.append(a * (1 - ty) + b * ty)
        out.append(row)
    return out


def footprint(w, h, left, mode='full', seed=0):
    """Boot sole: rounded toe, wide ball, narrow arch on the outer side, heel block, lug tread.
    mode: full (fresh, wet), toe / heel (only part of the sole still carries blood),
    smudge (nearly dry, broken up)."""
    rnd = random.Random(seed * 2 + (7 if left else 8))
    noise = value_noise(w, h, 6, seed * 31 + (1 if left else 2))

    def smooth(a, b, x):
        x = max(0.0, min(1.0, (x - a) / (b - a)))
        return x * x * (3 - 2 * x)

    def profile(t):
        """half width and centre across the sole, t = 0 toe .. 1 heel"""
        if t < 0.3:
            hw = 0.92 * math.sqrt(max(0.0, 1 - ((0.3 - t) / 0.3) ** 2))   # round toe to the ball
        elif t < 0.62:
            hw = 0.92 - 0.38 * smooth(0.36, 0.56, t)                      # ball narrowing to the arch
        else:
            hw = 0.54 + 0.2 * smooth(0.62, 0.72, t)                       # heel
            hw *= math.sqrt(max(0.0, 1 - ((t - 0.8) / 0.2) ** 2)) if t > 0.8 else 1.0
        c = 0.08 * (1 - smooth(0.1, 0.4, t)) - 0.2 * smooth(0.36, 0.56, t) * (1 - smooth(0.62, 0.72, t))
        return hw, c

    img = []
    for y in range(h):
        row = []
        t = (y + 0.5) / h
        hw, c = profile(t)
        for x in range(w):
            u = (x + 0.5) / w * 2 - 1
            if left:
                u = -u
            d = (hw - abs(u - c)) / 0.12
            val = max(0.0, min(1.0, d))
            if 0.6 < t < 0.65:
                val *= 0.25
            # tread
            lug = math.sin((t * 2 + abs(u - c) * 0.3) * 30) if t < 0.6 else math.sin(t * 2 * 34)
            n = noise[y][x]
            if mode == 'full':
                # wet: tread half filled in, edges a little blotchy
                tread = 0.65 if lug > 0.55 else 1.0
                val *= 0.8 + 0.2 * n
            elif mode == 'toe':
                tread = 0.3 if lug > 0.55 else 1.0
                val *= 1.0 - smooth(0.42, 0.62, t)            # heel no longer prints
                val *= smooth(0.25, 0.55, n + 0.15)
            elif mode == 'heel':
                tread = 0.3 if lug > 0.55 else 1.0
                val *= smooth(0.55, 0.68, t)                  # only the heel
                val *= smooth(0.25, 0.55, n + 0.15)
            else:
                tread = 0.3 if lug > 0.4 else 1.0
                val *= smooth(0.45, 0.7, n)                   # broken, mostly gone
            tread *= 0.8 + 0.2 * rnd.random()
            row.append(val * tread * 225)
        img.append(row)
    return img


write_spr('xb_splat.spr', [blob(64, s) for s in range(6)])
write_spr('xb_drop.spr', [streak(16, 64)])
write_spr('xb_pool.spr', [pool(128, s) for s in (11, 12, 13)])
# left/right pairs: 0-1 full, 2-3 toe only, 4-5 heel only, 6-7 smudged
write_spr('xb_foot.spr', [footprint(32, 80, left, mode, i)
                          for i, mode in enumerate(('full', 'toe', 'heel', 'smudge'))
                          for left in (True, False)])
