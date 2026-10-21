#!/usr/bin/env python3
"""
robot_style.py — turn any illustration into the meal planner's "robot" style:
cream ink (#EEE9DE) on a transparent background, solid shapes for dark/strong areas,
halftone dots for soft shading, crisp anti-aliased edges, tiny indexed PNG.

Works on light-on-dark or dark-on-light art (it finds the background from the corners).

  pip install pillow numpy
  python3 robot_style.py robot-eating.png                     -> robot-eating.styled.png
  python3 robot_style.py in.png -o out.png --width 360 --dot 7
  python3 robot_style.py in.png --js EAT_ART                  -> also prints:  const EAT_ART='data:image/png;base64,...';
  python3 robot_style.py in.png --preview                     -> also writes out.preview.png on the app's dark background

Getting source art (any image generator, or Figma "Generate image"). This prompt matches the guitar robot:
  "Hand-drawn cartoon illustration, thick wobbly ink outlines, flat solid shapes, black and white only,
   no grey fills, simple round-headed robot with a small antenna and a tall rectangular head with one
   window-like eye, striped segmented arms and legs, [ROBOT EATING A BIG BOWL OF NOODLES AT A SMALL TABLE],
   soft spotlight from above, plain black background, playful, lots of empty space"
Swap the bracketed part (stirring a pot, holding a grocery bag, asleep on a cookbook...).
Then run this script on the result.

Knobs:
  --solid 0.55   tone above this becomes solid ink (raise for fewer solid areas)
  --soft  0.12   tone below this is empty; between soft and solid becomes dots
  --dot   6      halftone cell size in output pixels (the robot uses ~6)
  --angle 45     halftone grid angle
  --invert       force "dark lines on light paper" handling if auto-detect guesses wrong
"""
import argparse, base64, io, math, sys
import numpy as np
from PIL import Image, ImageFilter

INK = (0xEE, 0xE9, 0xDE)
APP_BG = (30, 30, 30)
SS = 3  # supersampling for clean edges and round dots

def tone_map(im, invert=None):
    """0..1 'how much ink' per pixel. Background (from the corners) -> 0."""
    rgba = im.convert("RGBA")
    a = np.asarray(rgba, dtype=np.float32) / 255.0
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    alpha = a[..., 3]
    if alpha.min() < 0.99:  # already transparent art: ink = opacity * how far from background-ish
        return np.clip(alpha, 0, 1)
    h, w = lum.shape
    k = max(2, min(h, w) // 20)
    corners = np.concatenate([lum[:k, :k].ravel(), lum[:k, -k:].ravel(), lum[-k:, :k].ravel(), lum[-k:, -k:].ravel()])
    bg = float(np.median(corners))
    dark_bg = bg < 0.5 if invert is None else not invert
    t = (lum - bg) / max(1e-3, (1 - bg)) if dark_bg else (bg - lum) / max(1e-3, bg)
    return np.clip(t, 0, 1)

def halftone(tone, cell, angle):
    """Dot coverage mask (0..1) at supersampled resolution: dot radius grows with tone."""
    h, w = tone.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    th = math.radians(angle)
    u = (xx * math.cos(th) + yy * math.sin(th)) / cell
    v = (-xx * math.sin(th) + yy * math.cos(th)) / cell
    du, dv = u - np.round(u), v - np.round(v)
    d = np.sqrt(du * du + dv * dv)                 # 0 at dot centre, ~0.7 at cell corner
    r = np.sqrt(np.clip(tone, 0, 1) / math.pi)     # area-true radius in cell units
    return np.clip((r - d) * cell * 1.5 + 0.5, 0, 1)

def stylize(src, width=None, solid=0.55, soft=0.12, dot=6, angle=45, invert=None):
    im = Image.open(src)
    if width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    W, H = im.size
    big = im.convert("RGBA").resize((W * SS, H * SS), Image.LANCZOS).filter(ImageFilter.GaussianBlur(SS * 0.4))
    t = tone_map(big, invert)
    solid_mask = np.clip((t - solid) / 0.06 + 0.5, 0, 1)                   # soft step = anti-aliased edge
    mid = np.where(t > soft, (t - soft) / max(1e-3, solid - soft), 0.0)   # shading strength between soft..solid
    dots = halftone(np.clip(mid, 0, 1) * 0.55, dot * SS, angle) * (t > soft)
    ink = np.maximum(solid_mask, dots)
    out = Image.fromarray((ink * 255).astype(np.uint8), "L").resize((W, H), Image.LANCZOS)
    # few alpha levels like the original art -> very small PNG
    a = np.asarray(out, dtype=np.float32)
    a = np.round(a / 255 * 7) / 7 * 255
    a[a < 20] = 0
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = INK
    rgba[..., 3] = a.astype(np.uint8)
    res = Image.fromarray(rgba, "RGBA")
    bbox = res.getbbox()
    if bbox:  # trim empty margins, keep 4px air
        l, t_, r, b = bbox
        res = res.crop((max(0, l - 4), max(0, t_ - 4), min(W, r + 4), min(H, b + 4)))
    return res.quantize(colors=16, method=Image.FASTOCTREE)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("-o", "--out")
    ap.add_argument("--width", type=int, default=360)
    ap.add_argument("--solid", type=float, default=0.55)
    ap.add_argument("--soft", type=float, default=0.12)
    ap.add_argument("--dot", type=float, default=6)
    ap.add_argument("--angle", type=float, default=45)
    ap.add_argument("--invert", action="store_true", help="input is dark lines on light paper")
    ap.add_argument("--js", metavar="NAME", help="print a JS const with the image as a data URI")
    ap.add_argument("--preview", action="store_true", help="also save a copy on the app's dark background")
    a = ap.parse_args()
    out = a.out or a.input.rsplit(".", 1)[0] + ".styled.png"
    img = stylize(a.input, a.width, a.solid, a.soft, a.dot, a.angle, True if a.invert else None)
    img.save(out, optimize=True)
    print(f"saved {out}  {img.width}x{img.height}", file=sys.stderr)
    if a.preview:
        p = Image.new("RGBA", img.size, APP_BG + (255,)); p.alpha_composite(img.convert("RGBA"))
        pv = out.rsplit(".", 1)[0] + ".preview.png"; p.convert("RGB").save(pv); print(f"saved {pv}", file=sys.stderr)
    if a.js:
        buf = io.BytesIO(); img.save(buf, "PNG", optimize=True)
        print(f"const {a.js}='data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}';")

if __name__ == "__main__":
    main()
