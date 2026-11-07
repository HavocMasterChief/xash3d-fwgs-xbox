#!/usr/bin/env python3
"""Draw the controller layout picture for the Xbox Controller menu.

Output: uwp/package/HalfLife/gfx/shell/xbox_controller.png (1320x660, shown
at 660x330 in the menu). A generic gamepad outline with leader lines and the
default action for each control (uwp/package/HalfLife/gamepad_presets/xbox.cfg).
Re-run this if the default layout changes.
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1320, 660
ORANGE = (255, 160, 40, 255)
BODY = (40, 40, 44, 235)
EDGE = (150, 150, 155, 255)
TEXT = (235, 235, 235, 255)
LINE = (200, 200, 200, 200)

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, '..', 'package', 'HalfLife', 'gfx', 'shell', 'xbox_controller.png')
font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
font = ImageFont.truetype(font_path, 25)
small = ImageFont.truetype(font_path, 22)

img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
pad = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(pad)
S = 0.78  # controller scale, leaves room for labels

cx, cy = W // 2, 330
# body: two grips joined by a rounded centre
d.rounded_rectangle([cx - 260, cy - 120, cx + 260, cy + 60], radius=70, fill=BODY, outline=EDGE, width=4)
d.ellipse([cx - 330, cy - 90, cx - 130, cy + 190], fill=BODY, outline=EDGE, width=4)
d.ellipse([cx + 130, cy - 90, cx + 330, cy + 190], fill=BODY, outline=EDGE, width=4)
d.rounded_rectangle([cx - 250, cy - 112, cx + 250, cy + 52], radius=64, fill=BODY)
# shoulder buttons and triggers
d.rounded_rectangle([cx - 290, cy - 150, cx - 150, cy - 118], radius=14, fill=(70, 70, 76, 255), outline=EDGE, width=3)
d.rounded_rectangle([cx + 150, cy - 150, cx + 290, cy - 118], radius=14, fill=(70, 70, 76, 255), outline=EDGE, width=3)
d.rounded_rectangle([cx - 270, cy - 200, cx - 190, cy - 155], radius=16, fill=(70, 70, 76, 255), outline=EDGE, width=3)
d.rounded_rectangle([cx + 190, cy - 200, cx + 270, cy - 155], radius=16, fill=(70, 70, 76, 255), outline=EDGE, width=3)

def stick(x, y):
    d.ellipse([x - 42, y - 42, x + 42, y + 42], fill=(25, 25, 28, 255), outline=EDGE, width=4)
    d.ellipse([x - 26, y - 26, x + 26, y + 26], fill=(60, 60, 66, 255))

ls = (cx - 200, cy - 40)
rs = (cx + 90, cy + 50)
dp = (cx - 90, cy + 50)
stick(*ls)
stick(*rs)
# d-pad
d.rectangle([dp[0] - 14, dp[1] - 40, dp[0] + 14, dp[1] + 40], fill=(25, 25, 28, 255), outline=EDGE, width=3)
d.rectangle([dp[0] - 40, dp[1] - 14, dp[0] + 40, dp[1] + 14], fill=(25, 25, 28, 255), outline=EDGE, width=3)
# face buttons
fb = (cx + 200, cy - 40)
faces = {'Y': (0, -42), 'B': (42, 0), 'A': (0, 42), 'X': (-42, 0)}
for k, (ox, oy) in faces.items():
    x, y = fb[0] + ox, fb[1] + oy
    d.ellipse([x - 20, y - 20, x + 20, y + 20], fill=(25, 25, 28, 255), outline=ORANGE, width=3)
    d.text((x, y), k, font=small, fill=ORANGE, anchor='mm')
# view / menu
view = (cx - 50, cy - 50)
menu = (cx + 50, cy - 50)
for p in (view, menu):
    d.ellipse([p[0] - 14, p[1] - 14, p[0] + 14, p[1] + 14], fill=(25, 25, 28, 255), outline=EDGE, width=3)

pad = pad.resize((int(W * S), int(H * S)), Image.LANCZOS)
ox, oy = (W - pad.width) // 2, int(cy - cy * S)
img.alpha_composite(pad, (ox, oy))
d = ImageDraw.Draw(img)

def T(pt):
    return (ox + pt[0] * S, oy + pt[1] * S)

def label(anchor_pt, text_pt, text, align):
    anchor_pt = T(anchor_pt)
    d.line([anchor_pt, text_pt], fill=LINE, width=3)
    d.text((text_pt[0] + (8 if align == 'l' else -8), text_pt[1]), text, font=font, fill=TEXT,
           anchor='lm' if align == 'l' else 'rm')

# left side
label((cx - 230, cy - 178), (330, 70), 'LT  Alt fire', 'r')
label((cx - 220, cy - 134), (330, 130), 'LB  Prev weapon', 'r')
label((ls[0] - 42, ls[1]), (330, 230), 'Move', 'r')
label((dp[0] - 40, dp[1]), (330, 400), 'D-pad  (see below)', 'r')
label((view[0], view[1] - 14), (cx - 90, 30), 'View  Scores', 'r')
# right side
label((cx + 230, cy - 178), (W - 330, 70), 'RT  Fire', 'l')
label((cx + 220, cy - 134), (W - 330, 130), 'RB  Next weapon', 'l')
label((fb[0] + 20, fb[1] - 42), (W - 330, 195), 'Y  Reload', 'l')
label((fb[0] + 62, fb[1]), (W - 330, 245), 'B  Crouch', 'l')
label((fb[0] + 20, fb[1] + 42), (W - 330, 295), 'A  Jump', 'l')
label((fb[0] - 42, fb[1] + 20), (W - 330, 345), 'X  Use', 'l')
label((rs[0] + 42, rs[1] + 10), (W - 330, 420), 'Look / click: Light', 'l')
label((menu[0], menu[1] - 14), (cx + 90, 30), 'Menu  Pause', 'l')

d.text((cx, H - 40), 'D-pad: Up/Down weapons, Left quicksave, Right last weapon', font=small, fill=(190, 190, 190, 255), anchor='mm')

os.makedirs(os.path.dirname(out), exist_ok=True)
img.save(out)
print('wrote', os.path.normpath(out))
