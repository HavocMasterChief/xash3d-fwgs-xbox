#!/usr/bin/env python3
"""Generate the blood sprites used by the Xbox gore code (hlsdk cl_dll/xb_gore_world.cpp).

Half-Life .spr v2, INDEXALPHA: each pixel's palette index is its opacity and
palette[255] is the colour. The colour is white so the game tints each mark
red or alien-yellow itself.

  xb_splat.spr  6 frames  irregular splats (where a droplet lands)
  xb_drop.spr   1 frame   soft streak (a droplet in flight)
  xb_pool.spr   3 frames  pools that spread under bodies
  xb_foot.spr   2 frames  left / right bloody footprint

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
    data += struct.pack('<iiifiiifi', 2, 2, 3, math.hypot(w, h) / 2, w, h, len(frames), 0.0, 0)
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


def footprint(w, h, left):
    img = []
    for y in range(h):
        row = []
        for x in range(w):
            u = (x + 0.5) / w * 2 - 1
            v = (y + 0.5) / h * 2 - 1      # -1 toe .. 1 heel
            if left:
                u = -u
            # sole: ball (front ellipse) + heel (back ellipse), slight curve
            ball = ((u - 0.1 * (v + 0.4)) / 0.7) ** 2 + ((v + 0.3) / 0.62) ** 2
            heel = (u / 0.55) ** 2 + ((v - 0.62) / 0.32) ** 2
            inside = min(ball, heel)
            val = max(0.0, min(1.0, (1.0 - inside) / 0.25))
            # tread lines, a little patchy
            tread = 0.75 + 0.25 * math.sin(v * 38)
            row.append(val * tread * 220)
        img.append(row)
    return img


write_spr('xb_splat.spr', [blob(64, s) for s in range(6)])
write_spr('xb_drop.spr', [streak(16, 64)])
write_spr('xb_pool.spr', [pool(128, s) for s in (11, 12, 13)])
write_spr('xb_foot.spr', [footprint(32, 64, True), footprint(32, 64, False)])
