"""Robot eating a bowl of noodles at a small table."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from robot_art import *

s = Scene(400, 380)
s.spotlight((215, -10), 70, 380)
s.shadow(205, 352, 165, 14)

# table legs (behind everything)
s.add(f'<path d="M248 262 L244 348 M342 262 L348 348" stroke="{INK}" stroke-width="{LW}" stroke-linecap="round"/>')

# far arm, resting on the knee
s.limb([(138, 196), (116, 232), (128, 262)], width=30, bands=3)
s.hand(134, 266, r=12)

# legs, standing at the table
s.limb([(152, 250), (148, 300), (144, 332)], width=36, bands=3)
s.limb([(192, 250), (198, 300), (204, 332)], width=36, bands=3)
s.foot(140, 350, flip=True)
s.foot(212, 350)

s.torso(172, 214)
s.head(174, 182, tilt=-6, eye="open", look=1)

# table top + bowl of noodles
s.add(f'<path d="M226 258 L366 258" stroke="{INK}" stroke-width="{LW + 3}" stroke-linecap="round"/>')
s.add(f'<path d="M256 222 Q259 256 296 256 Q333 256 336 222 Z" fill="{DARK}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
      f'<path d="M266 240 Q296 248 326 240" fill="none" stroke="{SHADE}" stroke-width="7" stroke-linecap="round"/>'
      f'<ellipse cx="296" cy="222" rx="40" ry="8" fill="{INK}"/>')
s.notes([(300, 206, "steam"), (322, 200, "steam")])

# near arm lifting noodles with chopsticks
s.limb([(206, 196), (238, 222), (258, 196)], width=30, bands=3)
s.add(f'<path d="M256 186 L300 150 M262 192 L306 160" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
      f'<path d="M298 154 C292 176 302 196 290 218 M302 156 C300 180 312 200 302 218 M305 160 C310 182 318 198 312 218" '
      f'fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>')
s.hand(258, 190, r=12)
s.notes([(92, 150, "heart")])

s.render("robot-eating", out_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
         js=sys.argv[1] if len(sys.argv) > 1 else None)
