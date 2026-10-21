"""Robot holding up an empty picture frame: no photo yet."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from robot_art import *

NAME = "robot-no-photo"
s = Scene(400, 380)
s.spotlight((200, -10), 50, 370)
s.shadow(190, 352, 150, 14)

# far arm: ta-da
s.limb([(122, 196), (100, 172), (106, 138)], width=30, bands=3)
s.hand(106, 130, r=13)
s.limb([(136, 250), (132, 300), (128, 332)], width=36, bands=3)
s.limb([(176, 250), (182, 300), (188, 332)], width=36, bands=3)
s.foot(124, 350, flip=True)
s.foot(196, 350)
s.torso(156, 214)
s.head(158, 182, tilt=-6, eye="happy", look=1)

# empty frame with a little mountain-and-sun placeholder
s.add(f'<g transform="rotate(6 268 150)"><rect x="214" y="96" width="112" height="96" rx="4" fill="{DARK}" stroke="{INK}" stroke-width="11"/>'
      f'<rect x="226" y="108" width="88" height="72" fill="none" stroke="{SHADE}" stroke-width="4" stroke-dasharray="8 7"/>'
      f'<path d="M238 170 L260 142 L274 158 L286 146 L304 170 Z" fill="{SHADE}"/><circle cx="296" cy="124" r="7" fill="{SHADE}"/></g>')
s.limb([(190, 198), (214, 214), (222, 196)], width=30, bands=3)
s.hand(222, 192, r=13)
s.notes([(342, 92, "spark"), (70, 196, "spark")])

s.render(NAME, out_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
         js=sys.argv[1] if len(sys.argv) > 1 else None)
