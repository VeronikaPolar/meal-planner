#!/usr/bin/env python3
"""
robot_art.py — draw the meal planner robot (the guitar robot from the error screen) in new scenes.

The robot is built from fixed parts so he looks the same in every picture:
  head()   tall rounded head, one arched window eye, curly antenna with a leaf tip
  torso()  round-shouldered body
  limb()   thick tube arm/leg through any points, with stripe bands
  hand() / foot()   cream mitten / cream blob
  shadow(), spotlight(), notes()   floor shadow, halftone light cone, little marks

Draw in three tones only (the stylizer turns them into the app style):
  INK   = white  -> solid cream lines and fills
  SHADE = grey   -> halftone dots
  DARK  = black  -> transparent (use it to "erase" behind a shape)

A scene is a small Python file:

    from robot_art import *
    s = Scene(400, 380)
    s.spotlight((200, 0), 120, 330)
    s.shadow(200, 352, 120, 14)
    ... props and robot parts, back to front ...
    s.render("robot-eating")        # -> robot-eating.png (+ .preview.png, and --js const if asked)

Run:  .venv/bin/python .claude/skills/robot-art/scenes/eating.py
Needs Google Chrome (to rasterize the SVG) and pillow + numpy.
"""
import math, os, subprocess, sys, tempfile, base64, io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import robot_style  # noqa: E402

INK, SHADE, SOFT, DARK = "#ffffff", "#666666", "#2b2b2b", "#000000"
LW = 6  # standard ink line width at 1x
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def _f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _pts(points):
    return " ".join(f"{_f(x)},{_f(y)}" for x, y in points)


def _spline(points, n=48):
    """Catmull-Rom through points -> dense list of (x, y)."""
    if len(points) < 2:
        return list(points)
    p = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(tuple(points[-1]))
    return out


def _path(pts):
    return "M" + " L".join(f"{_f(x)} {_f(y)}" for x, y in pts)


class Scene:
    def __init__(self, w=400, h=380, wobble=5, seed=7):
        self.w, self.h, self.wobble, self.seed = w, h, wobble, seed
        self.parts = []

    def add(self, svg):
        """Raw SVG for props. Stick to INK / SHADE / SOFT / DARK, stroke-width LW, round caps and joins."""
        self.parts.append(svg)
        return self

    # ---------- light and ground ----------
    def spotlight(self, apex, x_left, x_right, y_bottom=None, tone=SOFT):
        y = y_bottom if y_bottom is not None else self.h - 20
        return self.add(f'<polygon points="{_pts([apex, (x_left, y), (x_right, y)])}" fill="{tone}" filter="url(#soft)"/>')

    def shadow(self, cx, cy, rx, ry, tone=SHADE):
        return self.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{tone}"/>')

    # ---------- robot parts ----------
    def limb(self, points, width=32, bands=4, shade_bands=True, behind=False):
        """Thick striped tube (arm or leg) through points. width = tube thickness."""
        pts = _spline(points)
        d = _path(pts)
        segs = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
        length = sum(segs)
        inner = DARK if not behind else SOFT
        svg = [f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{width + 2 * LW}" stroke-linecap="round" stroke-linejoin="round"/>',
               f'<path d="{d}" fill="none" stroke="{inner}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>']
        if bands > 0:
            step = length / (bands + 1)
            if shade_bands:  # every other band filled with halftone
                svg.append(f'<path d="{d}" fill="none" stroke="{SHADE}" stroke-width="{width}" '
                           f'stroke-dasharray="{_f(step)} {_f(step)}" stroke-dashoffset="{_f(-step)}"/>')
            acc, i, target = 0.0, 0, step
            for k in range(1, bands + 1):
                target = step * k
                while i < len(segs) - 1 and acc + segs[i] < target:
                    acc += segs[i]; i += 1
                (x0, y0), (x1, y1) = pts[i], pts[i + 1]
                t = (target - acc) / max(segs[i], 1e-6)
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                dx, dy = (x1 - x0), (y1 - y0)
                n = math.hypot(dx, dy) or 1
                nx, ny = -dy / n * width / 2, dx / n * width / 2
                svg.append(f'<path d="M{_f(x - nx)} {_f(y - ny)} Q{_f(x + dx / n * 3)} {_f(y + dy / n * 3)} {_f(x + nx)} {_f(y + ny)}" '
                           f'fill="none" stroke="{INK}" stroke-width="{LW - 1}" stroke-linecap="round"/>')
        return self.add("\n".join(svg))

    def torso(self, cx, cy, w=84, h=74, tilt=0, belly=True):
        """Round-shouldered body centred at cx, cy. Head sits on top edge (cy - h/2)."""
        x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        d = (f"M{_f(x0 + 18)} {_f(y0)} L{_f(x1 - 18)} {_f(y0)} Q{_f(x1 + 4)} {_f(y0)} {_f(x1 + 2)} {_f(cy)} "
             f"Q{_f(x1)} {_f(y1)} {_f(cx + w * 0.3)} {_f(y1)} L{_f(cx - w * 0.3)} {_f(y1)} "
             f"Q{_f(x0)} {_f(y1)} {_f(x0 - 2)} {_f(cy)} Q{_f(x0 - 4)} {_f(y0)} {_f(x0 + 18)} {_f(y0)} Z")
        svg = [f'<path d="{d}" fill="{DARK}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>']
        if belly:
            svg.append(f'<ellipse cx="{_f(cx)}" cy="{_f(cy + h * 0.08)}" rx="{_f(w * 0.3)}" ry="{_f(h * 0.3)}" fill="{INK}"/>')
            svg.append(f'<path d="M{_f(x0 + 6)} {_f(y1 - 14)} Q{_f(cx)} {_f(y1 - 4)} {_f(x1 - 6)} {_f(y1 - 14)}" fill="none" stroke="{INK}" stroke-width="{LW - 1}" stroke-linecap="round"/>')
        return self.add(f'<g transform="rotate({tilt} {_f(cx)} {_f(cy)})">' + "\n".join(svg) + "</g>")

    def head(self, cx, bottom, s=1.0, tilt=0, eye="open", look=0, antenna_side=1):
        """Head standing on (cx, bottom). Face = big cream nose with a dot eye on each side.
        eye: open | wide | happy | closed | x (error).  look: -1 / 0 / 1 shifts the face left / centre / right."""
        w, h, r = 44 * s, 60 * s, 10 * s
        x0, y0 = cx - w / 2, bottom - h
        g = [f'<rect x="{_f(x0)}" y="{_f(y0)}" width="{_f(w)}" height="{_f(h)}" rx="{_f(r)}" fill="{DARK}" stroke="{INK}" stroke-width="{LW}"/>',
             # inner shade along the right side and bottom, like a box seen a little from the side
             f'<path d="M{_f(x0 + w - 7 * s)} {_f(y0 + 12 * s)} L{_f(x0 + w - 7 * s)} {_f(bottom - 9 * s)} L{_f(x0 + 7 * s)} {_f(bottom - 9 * s)} '
             f'L{_f(x0 + 7 * s)} {_f(bottom - 4 * s)} L{_f(x0 + w - 4 * s)} {_f(bottom - 4 * s)} L{_f(x0 + w - 4 * s)} {_f(y0 + 12 * s)} Z" fill="{SHADE}"/>']
        # big nose: tall cream shape with a round top, a little below the middle
        fx = cx - 2 * s + look * 3 * s
        nw, nh, ny = 13 * s, 22 * s, y0 + 24 * s
        g.append(f'<path d="M{_f(fx - nw / 2)} {_f(ny + nh)} L{_f(fx - nw / 2)} {_f(ny + nw / 2)} A{_f(nw / 2)} {_f(nw / 2)} 0 0 1 {_f(fx + nw / 2)} {_f(ny + nw / 2)} '
                 f'L{_f(fx + nw / 2)} {_f(ny + nh)} Q{_f(fx)} {_f(ny + nh + 2 * s)} {_f(fx - nw / 2)} {_f(ny + nh)} Z" fill="{INK}"/>')
        # two eyes, either side of the nose
        ey, gap = ny + 9 * s, nw / 2 + 4.5 * s
        for ex in (fx - gap, fx + gap):
            a = 2.4 * s
            if eye == "happy":
                g.append(f'<path d="M{_f(ex - a)} {_f(ey + 1.5 * s)} Q{_f(ex)} {_f(ey - 3.5 * s)} {_f(ex + a)} {_f(ey + 1.5 * s)}" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round"/>')
            elif eye == "closed":
                g.append(f'<path d="M{_f(ex - a)} {_f(ey - 1 * s)} Q{_f(ex)} {_f(ey + 3 * s)} {_f(ex + a)} {_f(ey - 1 * s)}" fill="none" stroke="{INK}" stroke-width="2.6" stroke-linecap="round"/>')
            elif eye == "x":
                b = 2.6 * s
                g.append(f'<path d="M{_f(ex - b)} {_f(ey - b)} L{_f(ex + b)} {_f(ey + b)} M{_f(ex + b)} {_f(ey - b)} L{_f(ex - b)} {_f(ey + b)}" stroke="{INK}" stroke-width="2.6" stroke-linecap="round"/>')
            else:
                g.append(f'<circle cx="{_f(ex)}" cy="{_f(ey)}" r="{_f((3.6 if eye == "wide" else 2.8) * s)}" fill="{INK}"/>')
        # antenna: curved wire + outlined drop tip
        k = antenna_side
        ax, ay = cx - 6 * s * k, y0
        tx, ty = cx + 16 * s * k, y0 - 30 * s
        g.append(f'<path d="M{_f(ax)} {_f(ay)} C{_f(ax - 2 * s * k)} {_f(ay - 18 * s)} {_f(ax + 14 * s * k)} {_f(ay - 22 * s)} {_f(tx)} {_f(ty + 8 * s)}" fill="none" stroke="{INK}" stroke-width="{LW - 1}" stroke-linecap="round"/>')
        g.append(f'<path d="M{_f(tx)} {_f(ty + 8 * s)} Q{_f(tx - 8 * s * k)} {_f(ty + 1 * s)} {_f(tx + 1 * s * k)} {_f(ty - 7 * s)} Q{_f(tx + 9 * s * k)} {_f(ty + 1 * s)} {_f(tx)} {_f(ty + 8 * s)} Z" '
                 f'fill="{SHADE}" stroke="{INK}" stroke-width="3.5" stroke-linejoin="round"/>')
        return self.add(f'<g transform="rotate({tilt} {_f(cx)} {_f(bottom)})">' + "\n".join(g) + "</g>")

    def hand(self, x, y, r=13, angle=0, holding=False):
        """Cream mitten. holding=True draws a C-clamp gripping something along `angle`."""
        if holding:
            return self.add(f'<g transform="rotate({angle} {_f(x)} {_f(y)})"><path d="M{_f(x + r * 0.2)} {_f(y - r)} A{r} {r} 0 1 0 {_f(x + r * 0.2)} {_f(y + r)}" '
                            f'fill="none" stroke="{INK}" stroke-width="{r * 0.9:.1f}" stroke-linecap="round"/></g>')
        return self.add(f'<ellipse cx="{_f(x)}" cy="{_f(y)}" rx="{_f(r)}" ry="{_f(r * 0.85)}" transform="rotate({angle} {_f(x)} {_f(y)})" fill="{INK}"/>')

    def foot(self, x, y, w=46, h=18, flip=False):
        """Cream blob foot resting on y (its bottom)."""
        k = -1 if flip else 1
        d = (f"M{_f(x - w / 2 * k)} {_f(y)} Q{_f(x - w / 2 * k)} {_f(y - h)} {_f(x)} {_f(y - h)} "
             f"Q{_f(x + w / 2 * k)} {_f(y - h)} {_f(x + w / 2 * k)} {_f(y - 3)} Q{_f(x + w / 2 * k)} {_f(y)} {_f(x + w / 2 * k - 6 * k)} {_f(y)} Z")
        return self.add(f'<path d="{d}" fill="{INK}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>')

    def notes(self, items):
        """Little marks floating around: [(x, y, kind)], kind: note | z | spark | steam | heart | question."""
        out = []
        for x, y, kind in items:
            if kind == "note":
                out.append(f'<path d="M{x} {y} L{x} {y - 22} L{x + 16} {y - 26} L{x + 16} {y - 4}" fill="none" stroke="{INK}" stroke-width="{LW - 1}" stroke-linejoin="round" stroke-linecap="round"/>'
                           f'<ellipse cx="{x - 4}" cy="{y}" rx="6" ry="4.5" fill="{INK}"/><ellipse cx="{x + 12}" cy="{y - 4}" rx="6" ry="4.5" fill="{INK}"/>')
            elif kind == "z":
                out.append(f'<path d="M{x} {y - 14} L{x + 14} {y - 14} L{x} {y} L{x + 14} {y}" fill="none" stroke="{INK}" stroke-width="{LW - 1}" stroke-linejoin="round" stroke-linecap="round"/>')
            elif kind == "spark":
                out.append(f'<path d="M{x} {y - 10} L{x} {y + 10} M{x - 10} {y} L{x + 10} {y}" stroke="{INK}" stroke-width="{LW - 1}" stroke-linecap="round"/>')
            elif kind == "steam":
                out.append(f'<path d="M{x} {y} C{x - 8} {y - 10} {x + 8} {y - 18} {x} {y - 28} C{x - 8} {y - 38} {x + 6} {y - 44} {x} {y - 52}" fill="none" stroke="{INK}" stroke-width="{LW - 1}" stroke-linecap="round"/>')
            elif kind == "question":
                out.append(f'<path d="M{x - 7} {y - 16} Q{x - 7} {y - 26} {x + 1} {y - 26} Q{x + 9} {y - 26} {x + 9} {y - 17} Q{x + 9} {y - 10} {x + 1} {y - 7} L{x + 1} {y}" fill="none" stroke="{INK}" stroke-width="{LW - 1}" stroke-linecap="round" stroke-linejoin="round"/>'
                           f'<circle cx="{x + 1}" cy="{y + 9}" r="3.2" fill="{INK}"/>')
            elif kind == "heart":
                out.append(f'<path d="M{x} {y + 8} C{x - 14} {y - 2} {x - 8} {y - 14} {x} {y - 6} C{x + 8} {y - 14} {x + 14} {y - 2} {x} {y + 8} Z" fill="{INK}"/>')
        return self.add("\n".join(out))

    # ---------- output ----------
    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                f'<defs><filter id="wob" x="-5%" y="-5%" width="110%" height="110%">'
                f'<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="{self.seed}"/>'
                f'<feDisplacementMap in="SourceGraphic" scale="{self.wobble}" xChannelSelector="R" yChannelSelector="G"/></filter>'
                f'<filter id="soft"><feGaussianBlur stdDeviation="6"/></filter></defs>'
                f'<rect width="100%" height="100%" fill="#000"/><g filter="url(#wob)">' + "\n".join(self.parts) + "</g></svg>")

    def render(self, name, out_dir=None, width=None, js=None, dot=6, solid=0.55, soft=0.12):
        """SVG -> PNG via headless Chrome -> robot_style (cream ink + halftone). Returns styled PNG path."""
        out_dir = out_dir or os.getcwd()
        os.makedirs(out_dir, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="robot-")
        html = os.path.join(tmp, "s.html")
        raw = os.path.join(out_dir, name + ".raw.png")
        with open(html, "w") as f:
            f.write(f'<html><body style="margin:0;background:#000">{self.svg()}</body></html>')
        with open(os.path.join(out_dir, name + ".svg"), "w") as f:
            f.write(self.svg())
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={tmp}/prof",
                        f"--window-size={self.w},{self.h}", "--force-device-scale-factor=3", f"--screenshot={raw}", "file://" + html],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60)
        img = robot_style.stylize(raw, width or self.w, solid, soft, dot, 45, None)
        out = os.path.join(out_dir, name + ".png")
        img.save(out, optimize=True)
        prev = robot_style.Image.new("RGBA", img.size, robot_style.APP_BG + (255,))
        prev.alpha_composite(img.convert("RGBA"))
        prev.convert("RGB").save(os.path.join(out_dir, name + ".preview.png"))
        print(f"saved {out}  {img.width}x{img.height}  ({os.path.getsize(out) // 1024} KB)", file=sys.stderr)
        if js:
            buf = io.BytesIO(); img.save(buf, "PNG", optimize=True)
            print(f"const {js}='data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}';")
        return out
