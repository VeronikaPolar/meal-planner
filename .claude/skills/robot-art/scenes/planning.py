"""Robot with a blank clipboard, pencil at his head, thinking: nothing planned this week."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from robot_art import *

NAME = "robot-planning"
s = Scene(400, 380)
s.spotlight((200, -10), 50, 370)
s.shadow(186, 352, 140, 14)

# far arm up, pencil scratching the head
s.limb([(138, 196), (108, 176), (124, 140)], width=30, bands=3)
s.add(f'<path d="M126 142 L150 106" stroke="{INK}" stroke-width="7" stroke-linecap="round"/><path d="M150 106 L155 98" stroke="{SHADE}" stroke-width="7" stroke-linecap="round"/>')
s.hand(126, 138, r=13)

s.limb([(152, 250), (148, 300), (144, 332)], width=36, bands=3)
s.limb([(192, 250), (198, 300), (204, 332)], width=36, bands=3)
s.foot(140, 350, flip=True)
s.foot(212, 350)
s.torso(172, 214)
s.head(174, 182, tilt=8, eye="open", look=1, antenna_side=1)

# blank clipboard, held out to the side
s.add(f'<g transform="rotate(-6 262 230)"><rect x="228" y="180" width="72" height="96" rx="6" fill="{SHADE}" stroke="{INK}" stroke-width="{LW}"/>'
      f'<rect x="237" y="193" width="54" height="74" fill="{INK}"/>'
      f'<rect x="250" y="172" width="28" height="14" rx="4" fill="{DARK}" stroke="{INK}" stroke-width="4"/></g>')
s.limb([(206, 198), (226, 234), (234, 252)], width=30, bands=3)
s.hand(236, 254, r=13)
s.notes([(84, 110, "question"), (326, 150, "spark")])

s.render(NAME, out_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
         js=sys.argv[1] if len(sys.argv) > 1 else None)
