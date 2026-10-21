"""An empty pot, steaming: no recipes match. No robot here, just the pot."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from robot_art import *

NAME = "pot-no-match"
s = Scene(320, 300)
s.spotlight((160, -10), 30, 290, y_bottom=280)
s.shadow(160, 272, 120, 12)

# big pot, seen a little from above so the empty inside shows
s.add(f'<path d="M70 168 L76 250 Q160 272 244 250 L250 168 Z" fill="{DARK}" stroke="{INK}" stroke-width="{LW}" stroke-linejoin="round"/>'
      f'<path d="M74 214 L246 214 L245 246 Q160 266 75 246 Z" fill="{SHADE}"/>'
      f'<path d="M74 196 L246 196" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
      # handles
      f'<path d="M70 184 Q44 182 46 200 Q48 214 72 210 M250 184 Q276 182 274 200 Q272 214 248 210" fill="none" stroke="{INK}" stroke-width="{LW + 1}" stroke-linecap="round"/>'
      # rim, seen from above: lit back wall, dark empty bottom
      f'<ellipse cx="160" cy="168" rx="94" ry="30" fill="{INK}"/>'
      f'<ellipse cx="160" cy="170" rx="82" ry="22" fill="{DARK}"/>'
      f'<path d="M80 168 Q82 150 160 149 Q238 150 240 168 Q200 160 160 160 Q120 160 80 168 Z" fill="{SHADE}"/>'
      f'<ellipse cx="160" cy="178" rx="50" ry="9" fill="none" stroke="{SOFT}" stroke-width="4"/>')
s.notes([(130, 160, "steam"), (160, 152, "steam"), (190, 160, "steam")])

s.render(NAME, out_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"),
         js=sys.argv[1] if len(sys.argv) > 1 else None)
