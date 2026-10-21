---
name: robot-art
description: Draw Rennie, the meal planner's robot (the big-nosed guitar robot from the error screen), in new scenes, in the app's cream-ink halftone style, and put the picture into index.html. Use when asked for a new robot picture, illustration or empty-state art ("robot stirring a pot", "Rennie holding a cake", "art for the empty grocery list", "more of that robot"). Draws locally with code; never uses Higgsfield or other image generators.
---

# Robot art

The robot is drawn from fixed code parts in `robot_art.py`, so he looks the same in every picture. Each scene is a short Python file in `scenes/`. The render goes SVG → headless Chrome → `robot_style.py`, which turns it into cream ink (#EEE9DE) on transparent with halftone dots, exactly like `ERR_ART`.

Do not use Higgsfield, Figma image generation or any other AI image service. Everything here is drawn by code.

## The character: Rennie (keep these the same in every scene)
His name is only for us; it does not appear in the app.
- Tall rounded head with a shaded inner edge (right side and bottom). Face: a BIG cream nose (tall, round-topped) with a small dot eye on each side. Curved antenna with an outlined drop tip. `head()`
- Round-shouldered torso with a cream belly patch. `torso()`
- Thick tube arms and legs with stripe bands; every other band is halftone. `limb()`
- Cream mitten hands `hand()`, cream blob feet `foot()`.
- Soft halftone spotlight from above, a halftone floor shadow, lots of empty space.
- Look at `images/guitar.png` (the original guitar robot) before drawing. `images/` also holds a preview of every scene (the pictures in the README).

## Steps
1. Copy `scenes/eating.py` to a new file named after the scene (e.g. `stirring.py`). It is the worked example.
2. Compose back to front: spotlight, shadow, far props, far arm, legs, feet, torso, head, near props, near arm, hand, little marks (`notes()`).
3. Render: `.venv/bin/python .claude/skills/robot-art/scenes/<scene>.py`. Output goes to `scenes/out/` (ignored by git).
4. Read `scenes/out/<name>.preview.png` and compare with `images/guitar.png`. Fix and re-render until the pose reads clearly at 200px wide. Usually it takes 2–4 rounds.
5. Show the user the preview and get their OK before touching the app.
6. To put it in the app: `.venv/bin/python .claude/skills/robot-art/scenes/<scene>.py NAME_ART` prints `const NAME_ART='data:...';`. Add that line next to `const ERR_ART` in `index.html`, use it the way `errStateHtml()` uses `ERR_ART` (class `err-art`, real width/height attributes), then copy `index.html` to `compare/after/index.html`. Once the user is happy, copy `scenes/out/<name>.preview.png` into `images/` and add it to the README's robot table.

## Drawing rules
- Three tones only: `INK` (white → solid cream), `SHADE` (grey → halftone dots), `DARK` (black → transparent, used to cover what's behind a shape). `SOFT` is only for the spotlight.
- Props are raw SVG via `s.add(...)`: stroke `INK`, `stroke-width="{LW}"`, round caps and joins, fills `DARK`, `INK` or `SHADE`. Keep props chunky and simple (bowls, pots, bags, books), no fine detail. Anything thinner than 3px disappears.
- Canvas 400×380, floor around y = 350. Standard body: `torso(cx, 214)`, `head(cx + 2, 182)`, shoulders near (cx∓34, 196), hips near (cx∓20, 250), legs `width=36`, arms `width=30`.
- Expressions: `head(..., eye="open" | "wide" | "happy" | "closed" | "x")`; the nose is always there. `look=-1 | 0 | 1` turns the face toward what he is doing. Tilt the head (`tilt=±6..12`) for life. Plain dot eyes ("open") read best at small sizes.
- Marks: `notes([(x, y, "note" | "z" | "spark" | "steam" | "heart" | "question")])`.
- Sitting or lying poses: bend legs with 3 points, and move the torso/head down; nothing is tied together, so keep the joints overlapping.

## Needs
- `.venv` in the project with pillow and numpy (`python3 -m venv .venv && .venv/bin/pip install pillow numpy`).
- Google Chrome in /Applications (used headless to turn the SVG into pixels).
