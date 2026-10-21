"""Robot listening to a tin-can phone whose string is cut: couldn't reach the assistant."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from robot_art import *

NAME = "robot-no-signal"
s = Scene(400, 380)
s.spotlight((190, -10), 50, 360)
s.shadow(196, 352, 160, 14)

# far arm: palm up, shrugging
s.limb([(138, 196), (108, 214), (98, 190)], width=30, bands=3)
s.hand(98, 182, r=13)
s.limb([(152, 250), (148, 300), (144, 332)], width=36, bands=3)
s.limb([(192, 250), (198, 300), (204, 332)], width=36, bands=3)
s.foot(140, 350, flip=True)
s.foot(212, 350)
s.torso(172, 214)
s.head(172, 182, tilt=-10, eye="x", look=1)

# string from the can down to the floor, cut and frayed
s.add(f'<path d="M236 152 C262 200 236 260 280 300 C300 318 312 322 322 322" fill="none" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>'
      f'<path d="M322 322 L334 314 M322 322 L336 324 M322 322 L332 332" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>')
# tin can held to the side of the head
s.add(f'<g transform="rotate(-20 222 140)"><rect x="206" y="114" width="32" height="44" rx="5" fill="{SHADE}" stroke="{INK}" stroke-width="{LW}"/>'
      f'<path d="M207 124 L237 124 M207 148 L237 148" stroke="{INK}" stroke-width="4"/></g>')
s.limb([(206, 198), (236, 196), (226, 168)], width=30, bands=3)
s.hand(226, 168, r=13)
s.notes([(70, 130, "question"), (344, 296, "spark")])

s.render(NAME, out_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
         js=sys.argv[1] if len(sys.argv) > 1 else None)
