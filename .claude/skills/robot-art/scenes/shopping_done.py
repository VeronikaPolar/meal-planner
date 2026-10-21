"""Robot happily carrying a full grocery bag: every item on the list is checked off."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from robot_art import *

s = Scene(420, 380)
s.spotlight((215, -10), 60, 390)
s.shadow(212, 352, 160, 14)

# far arm waving
s.limb([(160, 196), (132, 172), (124, 134)], width=30, bands=3)
s.hand(124, 126, r=13)

# legs
s.limb([(174, 250), (168, 300), (162, 332)], width=36, bands=3)
s.limb([(210, 250), (216, 300), (222, 332)], width=36, bands=3)
s.foot(156, 350, flip=True)
s.foot(228, 350)

s.torso(192, 214)
s.head(194, 182, tilt=-8, eye="happy")

# what sticks out of the bag: leek, baguette, apple
s.add(f'<path d="M264 214 L252 150" stroke="{INK}" stroke-width="15" stroke-linecap="round"/>'
      f'<path d="M248 156 Q226 134 222 108 Q238 124 256 150 Z M250 154 Q246 120 258 96 Q264 124 258 154 Z M256 156 Q268 128 288 116 Q278 140 262 160 Z" '
      f'fill="{INK}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
      f'<path d="M294 218 L328 150" stroke="{INK}" stroke-width="20" stroke-linecap="round"/>'
      f'<path d="M308 186 L318 192 M316 170 L326 176 M322 156 L330 160" stroke="{DARK}" stroke-width="3" stroke-linecap="round"/>'
      f'<circle cx="282" cy="206" r="13" fill="{SHADE}" stroke="{INK}" stroke-width="{LW}"/>'
      f'<path d="M282 193 Q284 186 290 184" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>')

# paper bag
s.add(f'<path d="M250 210 L322 210 L328 292 L244 292 Z" fill="{DARK}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
      f'<path d="M252 226 L320 226" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
      f'<path d="M249 258 L325 258 L327 288 L247 288 Z" fill="{SHADE}"/>')

# near arm hugging the bag
s.limb([(222, 198), (262, 232), (270, 254)], width=30, bands=3)
s.hand(272, 256, r=13)

s.notes([(92, 104, "spark"), (352, 96, "spark"), (90, 200, "heart")])

s.render("robot-shopping-done", out_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
         js=sys.argv[1] if len(sys.argv) > 1 else None)
