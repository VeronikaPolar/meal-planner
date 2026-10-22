# Meal Planner

A small, self-hosted meal planner for a household: a shared recipe library, weekly plates (batch-cook or day by day), a grocery list that builds itself, a cooking log, and an optional AI assistant for importing and suggesting recipes.

It is two files: `index.html` (the whole app, plain JavaScript) and `server.py` (a Python standard-library server). No build step, no database.

## Run it

```bash
python3 server.py          # http://localhost:6969
python3 server.py 8080     # another port
```

Your data is written next to `server.py`: `data.json`, `profiles/`, `users.json`, `images/` and `backups/`. None of these are in git.

## Settings

Set these as environment variables, or as `KEY=value` lines in a `.env` file next to `server.py`. Everything is optional; with nothing set, the app is open to anyone who can reach it.

| Setting | What it does |
| --- | --- |
| `MEAL_PASSWORD` | Password for the main planner |
| `MEAL_GUEST_PASSWORD` | One or more guest passwords, comma-separated |
| `MEAL_OPEN_DEMO` | `1` lets visitors try a demo without signing in |
| `MEAL_PROFILES` | Extra planners for Google sign-in, e.g. `alex@example.com:Alex, sam@example.com` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_ALLOWED_EMAILS` | Sign in with Google |
| `SESSION_SECRET` | Keeps sign-ins valid across restarts |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `STANDARDCOMPUTE_API_KEY` | AI recipe import, suggestions and chat |

## Deploying

`deploy.sh` pulls from git and restarts the server only when the code changed, so a cron job like this keeps a server up to date:

```
*/5 * * * * ~/meal-planner/deploy.sh >> ~/meal-planner/deploy.log 2>&1
```

## Backups

`backup_s3.py` packs `data.json`, `users.json`, `profiles/` and `images/` into one `.tar.gz` and uploads it to an Amazon S3 bucket, but only when something changed. It needs no extra packages. Give it a bucket with versioning on and an access key that may only `s3:PutObject`, then run it from cron:

```
*/15 * * * * cd ~/meal-planner && set -a && . ~/.config/meal-planner.env && python3 backup_s3.py >> backup.log 2>&1
```

Settings: `S3_BUCKET`, `S3_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (and optionally `S3_PREFIX`, default `meal-planner`). To restore, download a backup from S3, stop the server and run `tar -xzf <file> -C ~/meal-planner`.

## The robot

Meet Rennie. He shows up on empty screens and errors, and everyone starts with his face as their profile picture.

<table>
  <tr>
    <td align="center"><img src=".claude/skills/robot-art/images/guitar.png" width="180" alt="Rennie playing guitar"><br><sub>Something went wrong</sub></td>
    <td align="center"><img src=".claude/skills/robot-art/images/planning.png" width="180" alt="Rennie with a blank clipboard"><br><sub>Nothing planned yet</sub></td>
    <td align="center"><img src=".claude/skills/robot-art/images/shopping-done.png" width="180" alt="Rennie carrying a full grocery bag"><br><sub>Shopping done</sub></td>
  </tr>
  <tr>
    <td align="center"><img src=".claude/skills/robot-art/images/no-photo.png" width="180" alt="Rennie holding an empty picture frame"><br><sub>No photo yet</sub></td>
    <td align="center"><img src=".claude/skills/robot-art/images/no-signal.png" width="180" alt="Rennie with a cut tin-can phone"><br><sub>Couldn't reach the assistant</sub></td>
    <td align="center"><img src=".claude/skills/robot-art/images/empty-pot.png" width="180" alt="An empty pot, steaming"><br><sub>No recipes match</sub></td>
  </tr>
</table>

He's drawn by code, not an image generator. Everything about him lives in [`.claude/skills/robot-art/`](.claude/skills/robot-art/): `robot_art.py` builds him from fixed parts so he looks the same in every scene, each scene is a short script in `scenes/`, `robot_style.py` turns the render into the app's cream-ink halftone style, and `SKILL.md` explains how to draw a new one.

## License

MIT, see [LICENSE](LICENSE).
