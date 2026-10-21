#!/usr/bin/env python3
"""Tiny meal planner server. No dependencies. Usage: python3 server.py [port]"""
import base64, hashlib, hmac, html, json, mimetypes, os, re, secrets, ssl, sys, tempfile, threading, time
import urllib.request, urllib.error, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data.json")

def _load_dotenv(path):
    """KEY=value lines from a .env next to server.py. Variables already set in the
    environment (systemd, shell) win, so this only fills in what's missing."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[7:].strip()
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                    val = val[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError:
        pass

_load_dotenv(os.path.join(HERE, ".env"))
IMAGES = os.path.join(HERE, "images")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 6969
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMG_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
MAX_IMAGE_BYTES = 2_500_000
COOKIE = "meal_session"
SESSION_TTL = 30 * 24 * 3600
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
_FALLBACK_SECRET = secrets.token_bytes(32)

# ---- installable: manifest + icons (public, so the home-screen installer can fetch them) ----
_ICONS = {
    "apple-touch-icon.png": "iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAYAAAA9zQYyAAAB5UlEQVR42u3dsQnCQBiAUSOpbG1vhjRpbCKIo9jZ2QhOINjYOYcLiGDlMs4QBxAsTkjMn/f6Q+78ciSQcEVKqZ1AEFNLgKBB0CBoEDSCBkGDoEHQIGgEDYIGQYOgQdAIGgQNggZBg6ARNAgaBA2CBkEjaBA0CBoEDYJG0CBoEDQIGgRNNGUXP/LcznuZ3OLy8g/boePo60JC0KJG0KJmtA+FovZQGDLq2eYaak5V3ai466CjRYRbDhA0CBpBg6BB0CBoEDSCBkGDoEHQIGgEDcNVWoJhO+x3WeOOp7MdGgQNggZBg6ARNAgaBA2CRtAgaBA0CBoEjaBh6LwPPVLr1TJ77O3+sEODoEHQCBoEDYIGQYOgETQIGgQNggZBI2gQNAgaBA2CRtAgaOhVJx/JVnWTNS73QBzs0CBoEDQIGgSNoEHQIGgQNAgaQYOgQdAgaBA0o1CklNqIE/vlUBy+c2gQCBoEjaBB0CBoEDQIGkGDoEHQIGgQNIIGQcOfCPs+NHZoEDQIGgQNgkbQIGgQNAgaBI2gQdAgaBA0CBpBg6BB0CBoEDSCBkGDoEHQIGgEDYIGQYOgEbQlQNAgaBA0CBpBg6BB0CBoEDSCBkGDoEHQIGgEDYIGQYOgQdAIGgQNggZBw4c38WMcmtdSY+4AAAAASUVORK5CYII=",
    "icon-192.png": "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAYAAABS3GwHAAACCElEQVR42u3dsQ2CQBiAUTBUtrQ3Aw2NDSbGUezobEycwMTGzjlcwJhYsYwz6AQ2nAI53usv5k6+/DZ4eQjhncFMLRwBAgABgABAACAAEAAIAAQAAgABgABAACAAEAAIAAQAAgABgABAACAAEAAIAAQAAgABgABAACAAEAAIAAQAAgABgABAAPArxVAf1LXl6JtdXV++ceY7AaYQIQIQAQIAAZgCCEAEjKeY8+a7tsyWu1vSe6zqxlM+hQBSf9DwEwgEAAIAAYAAQAAgABAACAAEAAIAAYAAQAAgABhQ4QjSdjzse689nS8mAAgABAACAAGAAEAAIAAQAAgABAACAAGAAEAAIACYHC/E8NV2s+699v54mgAgABAACAAEAAIAAYAAQAAgABAACAAEAAIAAYAAQAAgABAACAAEADEG+1eIqm6i1sdc9wkmAAgABAACAAEgAEeAAEAAIAAQAAgABAACAAGAAEAAIABIQh5CeKe+yZj7bunHPcEgABAACAAEAAIAAYAAQAAgABAACAAEAAIAAYAA4F9m8UIMmAAgABAACAAEgAAcAQIAAYAAQAAgABAACAAEAAIAAYAAQAAgABAACAAEAAIAAYAAQAAgABAACAAEAAIAAYAAQAAgABAACAAEAAIAAYAAQAAgABAACAAEAAIAAYAAQAAgABAACAAEAAIAAUCWfQDEERyyk4JETQAAAABJRU5ErkJggg==",
    "icon-512.png": "iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6AAAHZUlEQVR42u3doQ3CYBSFUUqqsNg3A6YGAwnpKDhcTRMmIMHgmIMFCAmKZZihLEDBlOYvPWeC5lbw5VWQRUQzAQBGZWoCABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAACwAQAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAQAADAN7kJ2j12cyN0bHl+GgHABQBRBYAAQAQAIAAQAQAIAEQAAAIAEQCAAEAEACAAEAEACAAAQADgCgAgAEAEAAgAEAEAAgBEAIAAABEAIABABAAMkL8DZhARMNteDEFnFsXKCAgAE7TzowPAv/IJAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAQAABA/3ITAGOzr6vkn/FwPHlRuAAAAAIAABAAAIAAAAAEAAAgAAAAAQAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAABAAAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAACAAAQAAAAAIAABAAAMDQ5SYASE+5WSf/jNfb3YtyAQAABAAAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAADoT26Cdotilfwz7uvKiwLABQAAEAAAgAAAAAQAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAFKURURjBn6p3KyNAH/oersbwQUAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAgAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAD4JIuIxgwA4AIAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAQAAAAAIAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAQAACAAAAABAAAIAAAAAEAAAgAAEAAAAACAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAgAAAAAQAACAAAQAAAAAIAABAAAIAAAAAEAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAAABAAAIAABAAAAAAgAAEAAAgAAAAAQAACAAAID3XnB6Kp84wWW1AAAAAElFTkSuQmCC",
}
_MANIFEST = json.dumps({
    "name": "Meal Planner", "short_name": "Meals", "start_url": "/", "scope": "/",
    "display": "standalone", "background_color": "#1C1C1C", "theme_color": "#1C1C1C",
    "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
              {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
}).encode()
_PUBLIC_STATIC = set(_ICONS) | {"manifest.webmanifest"}

def _password():
    return os.environ.get("MEAL_PASSWORD") or ""

def _google_client_id():
    return os.environ.get("GOOGLE_CLIENT_ID", "")

def _google_client_secret():
    return os.environ.get("GOOGLE_CLIENT_SECRET", "")

def _google_ready():
    return bool(_google_client_id() and _google_client_secret())

def _allowed_emails():
    raw = os.environ.get("GOOGLE_ALLOWED_EMAILS") or ""
    allowed = {e.strip().lower() for e in raw.split(",") if e.strip()}
    # Anyone with their own profile may sign in too.
    return (allowed | set(_profiles())) if allowed else allowed

# ---- profiles: people who share the recipe library but keep their own plans ----
# MEAL_PROFILES="alex@gmail.com:Alex, sam@x.com"  (name after ":" is optional)
# Everyone else who signs in (and the password login) uses the main planner in data.json.
PROFILES_DIR = os.path.join(HERE, "profiles")
_STATE_LOCK = threading.Lock()

def _profiles():
    out = {}
    for part in (os.environ.get("MEAL_PROFILES") or "").split(","):
        part = part.strip()
        if not part:
            continue
        email, _, name = part.partition(":")
        email = email.strip().lower()
        if "@" in email:
            out[email] = name.strip() or email.split("@")[0]
    return out

def _profile_slug(email):
    return re.sub(r"[^a-z0-9]+", "-", email.lower()).strip("-")[:80]

# ---- name + password logins (made by the admin in Settings), stored hashed in users.json ----
USERS_FILE = os.path.join(HERE, "users.json")
_PW_ITER = 200_000

def _users():
    data = _read_json_file(USERS_FILE)
    return [u for u in (data.get("users") or []) if isinstance(u, dict) and u.get("login")]

def _save_users(users):
    _write_json_file(USERS_FILE, {"users": users})

def _login_key(name):
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").strip().lower()).strip("-")[:40]

def _pw_hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), _PW_ITER).hex()

def _user_check(name, pw):
    key = _login_key(name)
    for u in _users():
        if u.get("login") == key:
            want = u.get("hash") or ""
            got = _pw_hash(pw, u.get("salt") or "00")
            return u if hmac.compare_digest(want, got) else None
    # spend the same time on unknown names so they can't be told apart
    _pw_hash(pw, "00" * 16)
    return None

def _planners():
    """Every planner besides the main one: slug -> display name (Google profiles + password users)."""
    out = {_profile_slug(e): n for e, n in _profiles().items()}
    for u in _users():
        slug = u.get("profile") or ("u-" + u["login"])
        out.setdefault(slug, u.get("name") or u["login"])
    return out

def _shared_reviews(skip):
    """Ratings and notes from every other planner, by recipe id. Recipes are shared, so their reviews are too."""
    out = {}
    sources = [(None, _owner_name())] + sorted(_planners().items())
    for slug, name in sources:
        if slug == skip or (skip is None and slug is None):
            continue
        path = DATA if slug is None else os.path.join(PROFILES_DIR, slug + ".json")
        if not os.path.exists(path):
            continue
        for x in _read_json_file(path).get("log") or []:
            if not isinstance(x, dict) or not x.get("rid"):
                continue
            rating = x.get("rating") if isinstance(x.get("rating"), (int, float)) else 0
            note = str(x.get("note") or "").strip()[:600]
            if note.lower().startswith("backfilled"):
                note = ""  # the app's own placeholder, not a review
            if not rating and not note:
                continue
            out.setdefault(str(x["rid"]), []).append({"who": name, "date": str(x.get("date") or "")[:10],
                                                     "rating": rating, "note": note, "plate": bool(x.get("plateNote"))})
    for v in out.values():
        v.sort(key=lambda e: e["date"], reverse=True)
    return out

_LOGIN_TRIES = {}
def _login_throttled(ip):
    now = time.time()
    tries = [t for t in _LOGIN_TRIES.get(ip, []) if now - t < 300]
    _LOGIN_TRIES[ip] = tries
    return len(tries) >= 10

def _login_failed(ip):
    _LOGIN_TRIES.setdefault(ip, []).append(time.time())

def _read_json_file(path):
    try:
        with open(path, "rb") as f:
            data = json.loads(f.read() or b"{}")
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def _write_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(data, separators=(",", ":")).encode("utf-8"))
    os.replace(tmp, path)  # atomic write

def _profile_state(slug):
    """Shared recipes (+ recipe deletions) from data.json, everything else from the profile file."""
    shared = _read_json_file(DATA)
    own = _read_json_file(os.path.join(PROFILES_DIR, slug + ".json"))
    own.pop("recipes", None)
    own.pop("cuisines", None)
    if isinstance(shared.get("cuisines"), dict):
        own["cuisines"] = shared["cuisines"]
    tomb = own.get("tomb") if isinstance(own.get("tomb"), dict) else {}
    shared_tomb = shared.get("tomb") if isinstance(shared.get("tomb"), dict) else {}
    tomb = {k: v for k, v in tomb.items() if k != "r"}
    tomb["r"] = shared_tomb.get("r") or {}
    own["tomb"] = tomb
    own["recipes"] = shared.get("recipes") or []
    return own

_PERSONAL_EMPTY = {"weeks": [], "log": [], "meals": [], "plan": {}}

def _personal(slug):
    """Everything that belongs to one planner (not the shared recipes)."""
    if slug:
        own = _read_json_file(os.path.join(PROFILES_DIR, slug + ".json"))
    else:
        own = _read_json_file(DATA)
    own = {k: v for k, v in own.items() if k not in ("recipes", "cuisines")}
    tomb = own.get("tomb") if isinstance(own.get("tomb"), dict) else {}
    own["tomb"] = {k: v for k, v in tomb.items() if k != "r"}
    return own

def _store_personal(slug, own):
    if slug:
        _write_json_file(os.path.join(PROFILES_DIR, slug + ".json"),
                         {k: v for k, v in own.items() if k not in ("recipes", "cuisines")})
        return
    data = _read_json_file(DATA)
    keep = {"recipes": data.get("recipes") or []}
    if isinstance(data.get("cuisines"), dict):
        keep["cuisines"] = data["cuisines"]
    tomb = data.get("tomb") if isinstance(data.get("tomb"), dict) else {}
    out = {k: v for k, v in own.items() if k not in ("recipes", "cuisines")}
    out_tomb = out.get("tomb") if isinstance(out.get("tomb"), dict) else {}
    out_tomb["r"] = tomb.get("r") or {}
    out["tomb"] = out_tomb
    out.update(keep)
    _write_json_file(DATA, out)

def _backup_states():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(HERE, "backups")
    os.makedirs(bdir, exist_ok=True)
    if os.path.exists(DATA):
        with open(DATA, "rb") as f, open(os.path.join(bdir, "data-" + stamp + ".json"), "wb") as g:
            g.write(f.read())
    if os.path.isdir(PROFILES_DIR):
        for name in os.listdir(PROFILES_DIR):
            if name.endswith(".json"):
                with open(os.path.join(PROFILES_DIR, name), "rb") as f, \
                        open(os.path.join(bdir, name[:-5] + "-" + stamp + ".json"), "wb") as g:
                    g.write(f.read())

def _move_plans(src, dst):
    """Move weeks, cook log, saved builds and plan from one planner to another (admin)."""
    a, b = _personal(src), _personal(dst)
    moved = len(a.get("weeks") or []) + len(a.get("log") or []) + len(a.get("meals") or [])
    if not moved:
        return 0
    weeks = {w.get("weekOf"): w for w in (b.get("weeks") or []) if isinstance(w, dict)}
    for w in a.get("weeks") or []:
        if not isinstance(w, dict):
            continue
        cur = weeks.get(w.get("weekOf"))
        if not cur:
            weeks[w.get("weekOf")] = w
            continue
        for slot in [k for k in w if k in ("breakfast", "lunch", "dinner", "shop") or re.match(r"^d[0-6]-(breakfast|lunch|dinner)$", str(k))]:
            add = ((w.get(slot) or {}).get("items")) or []
            if add:
                cur.setdefault(slot, {}).setdefault("items", []).extend(add)
    b["weeks"] = sorted(weeks.values(), key=lambda w: str(w.get("weekOf")))
    for key in ("log", "meals"):
        have = {x.get("id") for x in (b.get(key) or []) if isinstance(x, dict)}
        b[key] = (b.get(key) or []) + [x for x in (a.get(key) or []) if isinstance(x, dict) and x.get("id") not in have]
    b["plan"] = {}  # retired field; never carry it across
    epoch = secrets.token_hex(6)
    a.update(_PERSONAL_EMPTY)
    a["tomb"] = {}
    a["epoch"] = epoch
    b["epoch"] = epoch
    _store_personal(src, a)
    _store_personal(dst, b)
    return moved

def _save_profile_state(slug, body):
    shared = _read_json_file(DATA)
    shared["recipes"] = body.get("recipes") or []
    if isinstance(body.get("cuisines"), dict):
        shared["cuisines"] = body["cuisines"]
    shared_tomb = shared.get("tomb") if isinstance(shared.get("tomb"), dict) else {}
    body_tomb = body.get("tomb") if isinstance(body.get("tomb"), dict) else {}
    shared_tomb["r"] = body_tomb.get("r") or {}
    shared["tomb"] = shared_tomb
    _write_json_file(DATA, shared)
    own = {k: v for k, v in body.items() if k not in ("recipes", "cuisines")}
    own["tomb"] = {k: v for k, v in body_tomb.items() if k != "r"}
    _write_json_file(os.path.join(PROFILES_DIR, slug + ".json"), own)

def _guest_passwords():
    """MEAL_GUEST_PASSWORD may hold several guest passwords, separated by commas."""
    return [p.strip() for p in (os.environ.get("MEAL_GUEST_PASSWORD") or "").split(",") if p.strip()]

def _guest_password():
    return ",".join(_guest_passwords())

def _open_demo():
    """MEAL_OPEN_DEMO=1: visitors without a session get the demo instead of the login page."""
    return (os.environ.get("MEAL_OPEN_DEMO") or "").strip().lower() in ("1", "true", "yes", "on")

def _owner_name():
    return os.environ.get("MEAL_OWNER_NAME") or "the owner"

def _auth_on():
    return bool(_password()) or bool(_guest_password()) or _google_ready() or bool(_users())

def _session_secret():
    # Prefer an explicit secret; otherwise derive one from the password so
    # signed cookies keep working across server restarts. Changing the
    # password invalidates existing sessions, which is the right behavior.
    secret = os.environ.get("SESSION_SECRET")
    if secret:
        return secret.encode("utf-8")
    if _password():
        return hashlib.sha256(b"meal-planner-session:" + _password().encode("utf-8")).digest()
    return _FALLBACK_SECRET  # per-process random: sessions reset on restart

def _b64e(data):
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")

def _b64d(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))

def _sign_token(payload):
    """payload: bytes -> 'base64url.hmac' token string."""
    p = _b64e(payload)
    sig = hmac.new(_session_secret(), p.encode("ascii"), hashlib.sha256).hexdigest()
    return p + "." + sig

def _verify_token(token, typ="session"):
    """Return the payload dict when the signature, expiry and token type check out."""
    if not token or "." not in token:
        return None
    payload_b64, sig = token.rsplit(".", 1)
    want = hmac.new(_session_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(want, sig):
        return None
    try:
        data = json.loads(_b64d(payload_b64))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    exp = data.get("exp")
    if not isinstance(exp, (int, float)) or time.time() > exp:
        return None
    if data.get("typ") != typ:
        return None
    return data

def _session_token(sub=""):
    payload = json.dumps({"typ": "session", "exp": int(time.time()) + SESSION_TTL, "sub": sub}, separators=(",", ":")).encode("utf-8")
    return _sign_token(payload)

def _password_ok(given, want=None):
    # Hash both sides so compare_digest stays constant-time for unequal lengths.
    want = _password() if want is None else want
    if not want:
        return False
    a = hashlib.sha256(want.encode("utf-8")).digest()
    b = hashlib.sha256(given.encode("utf-8")).digest()
    return hmac.compare_digest(a, b)

# ---- guest (portfolio demo): full app, real recipes, a sample week; nothing is ever saved ----
_GUEST_AI = {"window": 0, "count": 0}
GUEST_AI_PER_HOUR = int(os.environ.get("MEAL_GUEST_AI_PER_HOUR", "30") or 30)

def _guest_ai_ok():
    now = int(time.time() // 3600)
    if _GUEST_AI["window"] != now:
        _GUEST_AI["window"], _GUEST_AI["count"] = now, 0
    if _GUEST_AI["count"] >= GUEST_AI_PER_HOUR:
        return False
    _GUEST_AI["count"] += 1
    return True

def _guest_state():
    shared = _read_json_file(DATA)
    recipes = [r for r in (shared.get("recipes") or []) if isinstance(r, dict)]
    def tags(r):
        return {str(t).lower() for t in (r.get("tags") or [])}
    proteins = {"chicken", "turkey", "pork", "beef", "lamb", "sausage", "seafood", "fish"}
    mains = [r for r in recipes if tags(r) & proteins and "add-on" not in tags(r)]
    sides = [r for r in recipes if "add-on" in tags(r)]
    import datetime
    today = datetime.date.today()
    sun = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
    weeks = []
    for wi, off in enumerate((0, 7)):
        day = sun + datetime.timedelta(days=off)
        pick = lambda pool, i: pool[(i + wi * 3) % len(pool)]["id"] if pool else None
        lunch = [x for x in [pick(mains, 0)] if x]
        dinner = [x for x in [pick(mains, 1), pick(mains, 2), pick(sides, 0)] if x]
        weeks.append({"id": "demo-" + day.isoformat(), "weekOf": day.isoformat(),
                      "lunch": {"items": [{"rid": x} for x in lunch]},
                      "dinner": {"items": [{"rid": x} for x in dict.fromkeys(dinner)]}})
    tomb = shared.get("tomb") if isinstance(shared.get("tomb"), dict) else {}
    out = {"recipes": recipes, "weeks": weeks, "log": [], "meals": [], "plan": {},
           "tomb": {"r": tomb.get("r") or {}}}
    if isinstance(shared.get("cuisines"), dict):
        out["cuisines"] = shared["cuisines"]
    return out

_SHELL_CACHE = {"mtime": None, "css": "", "h1": "<h1>Meal Planner</h1>"}

def _app_shell():
    """The app's own stylesheet and title, read from index.html, so the login and
    sign-in pages always look like the app (and follow any future restyle)."""
    path = os.path.join(HERE, "index.html")
    try:
        mtime = os.path.getmtime(path)
        if _SHELL_CACHE["mtime"] != mtime:
            src = open(path, encoding="utf-8").read()
            m = re.search(r"<style>(.*?)</style>", src, re.S)
            h = re.search(r"<h1>.*?</h1>", src, re.S)
            _SHELL_CACHE.update(mtime=mtime, css=m.group(1) if m else "", h1=h.group(0) if h else _SHELL_CACHE["h1"])
    except OSError:
        pass
    return _SHELL_CACHE["css"], _SHELL_CACHE["h1"]

AUTH_CSS = """
[hidden]{display:none!important}
/* Header, stamp and form share one centred column. */
.auth-shell{max-width:520px;margin:clamp(16px,8vh,96px) auto 0}
.auth-shell .app-head{border-bottom:1px solid var(--line);margin:0}
.auth-shell .hud-stamp{margin:10px 0 16px}
.auth-wrap{margin:0}
.auth-card{margin:0}
.auth-card label{display:block;margin:0 0 10px}
.auth-card input{width:100%;margin:0}
.auth-card .field-err{min-height:0;margin:8px 0 0}
.auth-card .field-err:empty{display:none}
.auth-card .row{margin-top:16px}
.auth-divider{display:flex;align-items:center;gap:10px;margin:16px 0;color:var(--mute);font:700 10px/1 var(--mono);letter-spacing:.2em;text-transform:uppercase}
.auth-divider::before,.auth-divider::after{content:"";flex:1;height:1px;background:var(--hair)}
.gbtn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;text-decoration:none}
.auth-msg h3{margin:0 0 6px}
.auth-msg p{margin:0}
"""

def _auth_page(inner, script="", refresh=""):
    css, h1 = _app_shell()
    meta = "<meta http-equiv='refresh' content='%s'>" % refresh if refresh else ""
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1, viewport-fit=cover'>" + meta +
            "<title>Meal Planner</title><style>" + css + AUTH_CSS + "</style></head><body>"
            "<div class='bg-blobs' aria-hidden='true'></div><div class='auth-shell'>"
            "<header class='app-head'>" + h1 + "</header>"
            "<p class='hud-stamp' aria-hidden='true'>[ARCHIVE_LOG] · SYS/MEAL · <span class='acc'>LOCK</span></p>"
            "<main class='auth-wrap'>" + inner + "</main></div>" + script + "</body></html>").encode("utf-8")

GOOGLE_ICON = """<svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.1H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.6-.4-3.9z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.1H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.1 5.7l6.2 5.2C36 40.6 44 34 44 24c0-1.3-.1-2.6-.4-3.9z"/></svg>"""

LOGIN_INNER = """<form id="f" class="card auth-card" autocomplete="off">
<label class="day" for="nm">Name</label>
<input id="nm" name="meal-name" autocomplete="username" autocapitalize="words" placeholder="e.g. Alex">
<p class="mute" style="margin:6px 0 14px;font-size:12px">Leave empty if you use the main password.</p>
<label class="day" for="pw">Password</label>
<!-- readonly until you tap or type, so browsers don't silently pre-fill a saved password -->
<input id="pw" name="meal-pass" type="password" autocomplete="off" readonly>
<p id="err" class="field-err" role="alert"></p>
<div class="row"><button class="btn" id="go" type="submit">Enter</button></div>
</form>
<div id="divider" class="auth-divider" hidden><span>or</span></div>
<a id="gbtn" class="btn ghost gbtn" href="/auth/google/login" hidden>""" + GOOGLE_ICON + """ Sign in with Google</a>"""

LOGIN_SCRIPT = """<script>
const f=document.getElementById('f'),pw=document.getElementById('pw'),err=document.getElementById('err');
const go=document.getElementById('go'),gbtn=document.getElementById('gbtn'),divider=document.getElementById('divider');
const unlock=()=>pw.removeAttribute('readonly');
['pointerdown','keydown','touchstart'].forEach(t=>pw.addEventListener(t,unlock));
pw.value='';pw.focus();
fetch('/api/auth').then(r=>r.json()).then(j=>{
  if(j&&j.openDemo){const a=document.createElement('a');a.href='/';a.className='btn ghost gbtn';a.style.marginTop='12px';a.textContent='Back to the demo';document.querySelector('.auth-wrap').appendChild(a);}
  if(j&&j.google){gbtn.hidden=false;if(j.password)divider.hidden=false;}
  if(j&&!j.password){f.hidden=true;divider.hidden=true;}
  if(j&&!j.logins){const n=document.getElementById('nm');if(n){n.closest('form').querySelectorAll('[for=nm],#nm,#nm+p').forEach(e=>e.hidden=true)}}
}).catch(()=>{});
f.addEventListener('submit',async(e)=>{
  e.preventDefault();unlock();err.textContent='';go.disabled=true;
  try{
    const nm=document.getElementById('nm');
    const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:nm?nm.value:'',password:pw.value})});
    if(r.ok){location.replace('/');return}
    let msg='Wrong password.';try{const j=await r.json();if(j&&j.error)msg=j.error}catch(x){}
    err.textContent=msg;pw.select();
  }catch(ex){err.textContent='Could not reach the server.'}
  go.disabled=false;
});
</script>"""

def _login_page():
    return _auth_page(LOGIN_INNER, LOGIN_SCRIPT)
# The only tags the app keeps (one or more per group; protein is optional for add-ons).
DEFAULT_CUISINES = [("italian", "Italian"), ("italian-american", "Italian-American"), ("american", "American"),
                    ("tex-mex", "Tex-Mex"), ("mexican", "Mexican"), ("asian", "Asian"),
                    ("mediterranean", "Mediterranean"), ("european", "European")]

def _cuisine_pairs(cuisines):
    """The planner's own cuisine list from the request, or the defaults."""
    out = []
    for c in cuisines if isinstance(cuisines, list) else []:
        if isinstance(c, dict):
            cid = re.sub(r"[^a-z0-9-]", "", str(c.get("id") or "").lower())[:40]
            name = str(c.get("name") or "").strip()[:40]
            if cid and name:
                out.append((cid, name))
    return out[:40] or DEFAULT_CUISINES

def tag_list(cuisines=None):
    cz = ", ".join(cid if cid == name.lower() else "%s (%s)" % (cid, name) for cid, name in _cuisine_pairs(cuisines))
    return ("protein (exactly one; the main one): chicken, turkey, pork (also sausage, bacon, ham), beef, lamb, "
            "fish (any fish or seafood), vegetarian (no meat or fish); "
            "cuisine (exactly one, always pick the closest; a mix like Italian-American is its own entry, "
            "e.g. most US pasta bakes and red-sauce dishes are italian-american): " + cz + "; "
            "flavor (one or two that best describe how it tastes): creamy, tomatoey, bright (lemon, vinegar, herbs, tangy), "
            "umami (savory: soy, mushroom, parmesan, braised), smoky, sweet (sweet and sticky, glazed), fresh (fresh and light); "
            "carb (optional, only if cooked in the dish): pasta, potato, grain (rice and other grains), veg; "
            "mode (optional): slop (a saucy or hearty main eaten from a bowl: stews, braises, skillets, stir-fries, ragus, saucy meat over a starch), byo (build-your-own tacos, bowls, sandwiches), add-on (a side, sauce or salad, not a main)")

TAG_LIST = tag_list()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
STANDARDCOMPUTE_BASE_URL = os.environ.get("STANDARDCOMPUTE_BASE_URL", "https://api.stdcmpt.com/v1").rstrip("/")
MODELS = {
    "groq": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
    "gemini": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    "standardcompute": os.environ.get("STANDARDCOMPUTE_MODEL", "standardcompute"),
}
SYSTEM = """You are a friendly meal-planning assistant inside the user's recipe app. Use their data below: favour recipes and tags they rate highly, avoid repeating meals cooked recently, and suggest variety. Be concise and practical; for meal prep, group tasks into one cook session and note storage times.
When you propose a complete new recipe, end that reply with one fenced block exactly like:
```recipe
{"name": "...", "tags": ["chicken", "asian", "grain"], "ingredients": ["200g chicken", "1 tbsp olive oil"]}
```
so the app can save it. Put method steps in your normal text before the block. Use only these tags: """ + TAG_LIST

IMPORT_SYSTEM = """You turn pasted recipe text (any messy source: web page, video description, notes) into JSON. If the text holds no actual recipe (for example it is only a link or a title), reply exactly {"error": "no recipe in text"} and never make one up. Reply with ONLY one JSON object, no prose, no code fences:
{"name": str, "servings": number|null, "tags": [tags chosen ONLY from the allowed list below],
 "steps": [str, ...],
 "items": [{"qty": number|null, "unit": str, "item": str, "meat": bool}, ...],
 "sections": optional list of [{"label": str, "items": [{"qty": number|null, "unit": str, "item": str, "meat": bool}, ...]}] where each label is an uppercase cooking-stage heading exactly as it appears in the text (omit if the source has no stage headings),
 "meatLbs": number|null, "meatNote": str,
 "spice": heat from 0 to 5 (0 not spicy, 1 a little warm, 2 mild, 3 medium hot, 4 hot, 5 very hot), judged from chiles, hot sauce, cayenne and how much}
Rules: qty is a plain number (decimal for fractions; use the midpoint of ranges); qty null for "to taste"/"pinch". Skip nutrition lines (calories, fat, carbs, protein). If a line has a kitchen amount and a bracketed metric conversion such as (907g) or (408g Total), keep the kitchen amount and drop the conversion. A size like (16oz) is part of the ingredient, not a conversion. Write units only as lb, oz, cup, tbsp, tsp, qt, g, kg, ml, l, clove, slice, can, block, packet. Use lb, never lbs or pounds. meat is true only for animal flesh (chicken, beef, pork, lamb, turkey, fish, shellfish, sausage, bacon), false for eggs, dairy, stock, plant protein. meatLbs is the TOTAL original weight of all meat in pounds, converting from g/kg/oz. If meat is given by count, estimate typical weight and say so in meatNote (one short sentence on how you got meatLbs). meatLbs null if there is no meat. Do not invent ingredients or steps that are not in the text. Tag a carb only when it is cooked as part of the dish (pasta, potatoes, rice or another grain in the recipe itself); tortillas, buns, bread or rice merely served alongside are not a carb tag (use mode byo for build-your-own tacos, bowls and sandwiches). Always give exactly one protein tag and exactly one cuisine tag. Allowed tags: """

# ---- web recipe import: fetch the page, prefer schema.org JSON-LD, else readable page text ----
_URL_RE = re.compile(r"^\s*(https?://[^\s<>\"']+)\s*$", re.I)
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

def _fetch_page(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("That doesn't look like a web address.")
    host = parsed.hostname.lower()
    if host in ("localhost",) or host.endswith(".local") or re.match(r"^(127\.|10\.|192\.168\.|169\.254\.|0\.)", host):
        raise ValueError("Local addresses can't be imported.")
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml",
                                               "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as r:
        raw = r.read(4_000_000)
        charset = r.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, "replace")

def _ld_nodes(obj):
    if isinstance(obj, list):
        for x in obj:
            yield from _ld_nodes(x)
    elif isinstance(obj, dict):
        yield obj
        for k in ("@graph", "mainEntity", "itemListElement"):
            if k in obj:
                yield from _ld_nodes(obj[k])

def _is_recipe(node):
    t = node.get("@type")
    t = t if isinstance(t, list) else [t]
    return any(str(x).lower() == "recipe" for x in t)

def _ld_text(v):
    if isinstance(v, str):
        return html.unescape(re.sub(r"<[^>]+>", " ", v)).strip()
    if isinstance(v, dict):
        return _ld_text(v.get("text") or v.get("name") or "")
    return ""

def _ld_steps(v, out, depth=0):
    if depth > 4:
        return
    if isinstance(v, str):
        for line in re.split(r"\n+", v):
            line = _ld_text(line)
            if line:
                out.append(line)
    elif isinstance(v, list):
        for x in v:
            _ld_steps(x, out, depth + 1)
    elif isinstance(v, dict):
        if "itemListElement" in v:
            name = _ld_text(v.get("name") or "")
            if name:
                out.append(name.upper() + ":")
            _ld_steps(v["itemListElement"], out, depth + 1)
        else:
            t = _ld_text(v)
            if t:
                out.append(t)

def _recipe_from_jsonld(page):
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            data = json.loads(m.group(1).strip())
        except ValueError:
            continue
        for node in _ld_nodes(data):
            if not _is_recipe(node):
                continue
            ings = [_ld_text(x) for x in (node.get("recipeIngredient") or node.get("ingredients") or [])]
            ings = [x for x in ings if x]
            if not ings:
                continue
            steps = []
            _ld_steps(node.get("recipeInstructions"), steps)
            img = node.get("image")
            if isinstance(img, list):
                img = img[0] if img else ""
            if isinstance(img, dict):
                img = img.get("url") or ""
            yld = node.get("recipeYield")
            if isinstance(yld, list):
                yld = yld[0] if yld else ""
            text = "\n".join([_ld_text(node.get("name") or "Recipe"),
                              ("Serves: " + _ld_text(str(yld))) if yld else "",
                              "", "Ingredients:"] + ings + ["", "Method:"] + steps)
            return {"text": text, "name": _ld_text(node.get("name") or ""),
                    "image": img if isinstance(img, str) and img.startswith("http") else ""}
    return None

def _page_text(page):
    """Readable text of a page, keeping list items and headings on their own lines."""
    p = re.sub(r"(?is)<(script|style|noscript|svg|iframe|nav|footer|header|form)[^>]*>.*?</\1>", " ", page)
    p = re.sub(r"(?is)<!--.*?-->", " ", p)
    p = re.sub(r"(?i)<li[^>]*>", "\n• ", p)
    p = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6]|/tr|/section|/article)[^>]*>", "\n", p)
    p = re.sub(r"(?i)<h[1-6][^>]*>", "\n\n", p)
    p = re.sub(r"<[^>]+>", " ", p)
    p = html.unescape(p)
    p = re.sub(r"[ \t ]+", " ", p)
    lines = [ln.strip() for ln in p.split("\n")]
    out, blank = [], 0
    for ln in lines:
        if not ln:
            blank += 1
            if blank == 1:
                out.append("")
            continue
        blank = 0
        out.append(ln)
    text = "\n".join(out).strip()
    # Keep the part that holds the recipe: from the first "ingredient" heading, with some lead-in for the title
    low = text.lower()
    i = low.find("ingredient")
    if i > 0:
        text = text[max(0, i - 1500):]
    return text[:15000]

def _og_image(page):
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', page, re.I)
    return html.unescape(m.group(1)) if m and m.group(1).startswith("http") else ""

def _og_title(page):
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', page, re.I) or \
        re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
    return html.unescape(m.group(1)).strip() if m else ""

def recipe_source_from_url(url):
    """-> {"text", "image", "via"} ready for the import model, or raises ValueError with a friendly message."""
    try:
        page = _fetch_page(url)
    except urllib.error.HTTPError as e:
        raise ValueError("The site refused the request (HTTP %s)." % e.code)
    except (urllib.error.URLError, OSError, ValueError) as e:
        msg = str(e) if isinstance(e, ValueError) else "Couldn't reach that site."
        raise ValueError(msg)
    found = _recipe_from_jsonld(page)
    if found:
        return {"text": found["text"], "image": found["image"] or _og_image(page), "via": "structured"}
    text = _page_text(page)
    if "ingredient" not in text.lower():
        raise ValueError("That page doesn't seem to have an ingredient list.")
    title = _og_title(page)
    return {"text": ("Title: " + title + "\n\n" if title else "") + text, "image": _og_image(page), "via": "page"}

FUN_NAME_SYSTEM = """You are the naming desk for a black-and-amber engineering meal planner. Return ONLY one JSON object: {\"funName\": str}. Create a short, funny, memorable codename under 42 characters. The style combines cosmic engineering, industrial bureaucracy, science-lab absurdity, deadpan internet humor, and recognizable meme culture. You may use meme formats, slang, reaction-language, and phrases inspired by common Know Your Meme and Urban Dictionary usage, but make the result original rather than copying a long quote or attributing a meme.

Use dramatic technical language for ordinary food: protocols, reactors, launch systems, field operations, tactical units, planetary missions, manufacturing plants, classified projects, and containment failures. Make the joke specific to the recipe's ingredients or cooking method. Mildly edgy food puns are allowed when they are clearly harmless and recipe-related.

Strong examples:
- chicken cashew stir fry -> \"Deez Nuts Asian Slop Fry\"
- a very fatty recipe -> \"Jet Fuel 2000\"
- roast potatoes -> \"Crispy Spud Manufacturing Plant\"
- a large pasta batch -> \"Carb Loading Protocol\"
- tzatziki -> \"Cold Garlic Yogurt Operations\"
- beef kabobs without skewers -> \"Beef Surface-Mount Operations\"
- a sauce -> \"Flavor Deployment System\"

Avoid bland literal names, generic labels like \"Funny Chicken\", excessive random word salad, stale meme clichés, and repeating the real recipe name. Do not use slurs, hateful language, protected-class jokes, harassment, or sexual content. Do not mention ingredients or equipment that are not present. Do not alter the real recipe name."""

CLASSIFY_SYSTEM = """You sort recipes for a home cookbook. For each recipe in the user's JSON list, choose its tags.
Reply with ONLY one JSON object mapping each recipe id to a list of tags, like {"r1": ["pork", "italian-american"]}.
Give every recipe exactly one protein and exactly one cuisine (the closest fit, never leave it out), plus a carb or mode tag only when clearly right.
Also add one heat tag "spice:N" with N from 0 to 5 (0 not spicy, 3 medium hot, 5 very hot), judged from chiles, hot sauce and cayenne. Allowed tags: """

def classify_recipes(body):
    recipes = [r for r in (body.get("recipes") or []) if isinstance(r, dict) and r.get("id")][:20]
    if not recipes:
        return {"tags": {}}
    items = [{"id": str(r["id"])[:60], "name": str(r.get("name") or "")[:160],
              "ingredients": str(r.get("ingredients") or "")[:700]} for r in recipes]
    first = str(body.get("provider", "groq") or "groq").lower()
    keys = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "standardcompute": "STANDARDCOMPUTE_API_KEY"}
    order = [first] + [p for p in ("groq", "gemini", "standardcompute") if p != first and os.environ.get(keys[p])]
    last = "The AI didn't answer"
    for provider in order[:2]:
        out = ask_model([{"role": "user", "content": json.dumps(items)}], {}, system=CLASSIFY_SYSTEM + tag_list(body.get("cuisines")),
                        provider=provider, json_mode=True, max_chars=20000, max_tokens=3000)
        if "error" in out:
            last = out["error"]
            continue
        try:
            got = H._loose_json(out["reply"])
        except ValueError:
            last = "The AI's reply wasn't readable"
            continue
        if isinstance(got, dict):
            return {"tags": {str(k): [str(t)[:40] for t in v][:7] for k, v in got.items() if isinstance(v, list)}}
    return {"error": last}

def ask_fun_name(recipe, provider="groq"):
    r=recipe if isinstance(recipe,dict) else {}
    context={"realName":str(r.get("name") or ""),"tags":r.get("tags") or [],"ingredients":str(r.get("ingredients") or "")[:3000],"notes":str(r.get("notes") or "")[:1000]}
    out=ask_model([{"role":"user","content":json.dumps(context)}],{},system=FUN_NAME_SYSTEM,provider=provider)
    if "error" in out:return out
    raw=str(out.get("reply") or "")
    try:
        start=raw.index("{");end=raw.rindex("}")+1
        obj=json.loads(raw[start:end]); name=str(obj.get("funName") or "").strip()
    except Exception:return {"error":"The provider returned an invalid funny name."}
    return {"funName":name[:60]} if name else {"error":"The provider returned an empty funny name."}

def ask_model(messages, context, system=None, provider="groq", json_mode=False, max_chars=6000, max_tokens=None):
    provider = str(provider or "groq").lower()
    if provider not in MODELS:
        provider = "groq"
    key_names = {"groq":"GROQ_API_KEY", "gemini":"GEMINI_API_KEY", "standardcompute":"STANDARDCOMPUTE_API_KEY"}
    key = os.environ.get(key_names[provider])
    if not key:
        return {"error": "The selected chat provider is not configured on the server."}
    system = system or (SYSTEM + "\n\nUser data:\n" + json.dumps(context)[:8000])
    if not isinstance(messages, list):
        messages = []
    msgs = [{"role": m["role"], "content": str(m.get("content", ""))[:max_chars]} for m in messages
            if isinstance(m, dict) and m.get("role") in ("user", "assistant")][-20:]
    payload = {"model": MODELS[provider], "messages": [{"role": "system", "content": system}] + msgs}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if max_tokens:
        payload["max_tokens"] = int(max_tokens)
    if provider == "groq" and "gpt-oss" in str(MODELS[provider]):
        # Reasoning models can spend the whole budget thinking and return an empty reply.
        payload["reasoning_effort"] = "low"
    if provider == "gemini":
        url = GEMINI_URL
    elif provider == "standardcompute":
        url = STANDARDCOMPUTE_BASE_URL + "/chat/completions"
    else:
        url = GROQ_URL
    def send(p):
        req = urllib.request.Request(url, json.dumps(p).encode(), {
            "Content-Type": "application/json", "Authorization": "Bearer " + key, "User-Agent": "mealplanner/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    try:
        try:
            data = send(payload)
        except urllib.error.HTTPError as e:
            # Some providers/models reject the optional knobs; drop them and ask once more.
            if e.code == 400 and any(k in payload for k in ("response_format", "reasoning_effort", "max_tokens")):
                for k in ("response_format", "reasoning_effort", "max_tokens"):
                    payload.pop(k, None)
                data = send(payload)
            else:
                raise
    except urllib.error.HTTPError as e:
        return {"error": f"API {e.code}: " + e.read()[:300].decode("utf-8", "replace")}
    except Exception as e:
        return {"error": str(e)}
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return {"error": "The provider returned an unexpected response."}
    return {"reply": str(text or "")}


def _ensure_images():
    os.makedirs(IMAGES, exist_ok=True)

def _safe_image_name(name):
    name = os.path.basename(str(name or ""))
    root, ext = os.path.splitext(name)
    ext = ext.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    if ext not in IMG_EXTS or not IMG_ID_RE.match(root):
        return None
    return root + ext

def _image_paths_for_id(rid):
    if not IMG_ID_RE.match(str(rid or "")):
        return []
    return [os.path.join(IMAGES, str(rid) + ext) for ext in (".jpg", ".png", ".webp", ".gif")]

def _remove_images_for_id(rid):
    removed = False
    for path in _image_paths_for_id(rid):
        if os.path.isfile(path):
            try:
                os.remove(path)
                removed = True
            except OSError:
                pass
    return removed

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or []):
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _path(self):
        return self.path.split("?", 1)[0]

    def _https(self):
        if isinstance(getattr(self, "connection", None), ssl.SSLSocket):
            return True
        proto = (self.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
        return proto == "https"

    def _cookie(self, token):
        parts = [COOKIE + "=" + token, "HttpOnly", "SameSite=Lax", "Path=/"]
        if self._https():
            parts.append("Secure")
        return "; ".join(parts)

    def _clear_cookie(self):
        parts = [COOKIE + "=", "HttpOnly", "SameSite=Lax", "Path=/", "Max-Age=0"]
        if self._https():
            parts.append("Secure")
        return "; ".join(parts)

    def _token(self):
        raw = self.headers.get("Cookie") or ""
        for part in raw.split(";"):
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            if k.strip() == COOKIE:
                return v.strip().strip('"')
        return ""

    def _session_ok(self):
        data = _verify_token(self._token())
        if data is None:
            return False
        sub = str(data.get("sub") or "")
        if sub.startswith("user:") and not any(u.get("login") == sub[5:] for u in _users()):
            return False  # that login was removed
        return True

    def _anon_demo(self):
        return _open_demo() and _auth_on() and not self._session_ok()

    def _is_guest(self):
        data = _verify_token(self._token()) or {}
        return data.get("sub") == "guest" or self._anon_demo()

    def _is_admin(self):
        """The main-planner user (not a profile) is the admin. With login off, everyone is."""
        if _auth_on() and not self._session_ok():
            return False
        if self._is_guest():
            return False
        return self._who()[2] is None

    def _query(self, key):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        v = q.get(key)
        return v[0] if v else ""

    def _state_slug(self):
        """Whose planner this request reads/writes. Admin may pass ?as=<profile>."""
        own = self._who()[2]
        want = self._query("as")
        if want and own is None and self._is_admin():
            valid = set(_planners())
            if want in valid:
                return want
        return own

    def _who(self):
        """(email, display name, profile slug or None). Profile is None for the main planner."""
        data = _verify_token(self._token()) or {}
        sub = str(data.get("sub") or "")
        if sub == "guest":
            return "", "Guest", None
        if sub.startswith("user:"):
            key = sub[len("user:"):]
            u = next((x for x in _users() if x.get("login") == key), None)
            if not u:
                return "", "", "u-missing"   # deleted login: an empty planner, never the admin's
            return "", u.get("name") or key, u.get("profile") or ("u-" + key)
        if sub.startswith("google:"):
            email = sub[len("google:"):].lower()
            profs = _profiles()
            if email in profs:
                return email, profs[email], _profile_slug(email)
            return email, email.split("@")[0], None
        return "", "", None

    def parse_request(self):
        if not super().parse_request():
            return False
        # Public: login form, POST /api/login, GET /api/auth, Google OAuth.
        # Everything else needs a session only when a login method is on.
        path = self._path()
        if path == "/api/auth" and self.command == "GET":
            return True
        if path == "/api/login" and self.command == "POST":
            return True
        if path == "/login" and self.command == "GET":
            return True
        if path.startswith("/auth/google/"):
            return True
        if self.command == "GET" and path.lstrip("/") in _PUBLIC_STATIC:
            return True
        if not _auth_on() or self._session_ok() or _open_demo():
            return True
        if path.startswith("/api/"):
            self._send(401, b'{"error":"unauthorized"}')
        else:
            self._send(200, _login_page(), "text/html; charset=utf-8")
        return False

    def _read_json(self, limit):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n > limit:
            self._send(413, b"too large", "text/plain")
            return None
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            self._send(400, b"bad json", "text/plain")
            return None

    def _login(self):
        if not _auth_on():
            return self._send(404, b"not found", "text/plain")
        body = self._read_json(4096)
        if body is None:
            return
        given = body.get("password", "") if isinstance(body, dict) else ""
        name = str(body.get("name", "") or "").strip() if isinstance(body, dict) else ""
        if not isinstance(given, str) or not given:
            return self._send(401, b'{"error":"Wrong password."}')
        ip = (self.headers.get("X-Forwarded-For") or self.client_address[0] or "").split(",")[0].strip()
        if _login_throttled(ip):
            return self._send(429, b'{"error":"Too many tries. Wait a few minutes."}')
        if name:
            u = _user_check(name, given)
            if not u:
                _login_failed(ip)
                return self._send(401, b'{"error":"Wrong name or password."}')
            tok = _session_token("user:" + u["login"])
            return self._send(200, b'{"ok":true}', extra=[("Set-Cookie", self._cookie(tok))])
        if _password_ok(given):
            tok = _session_token("password")
        elif any(_password_ok(given, g) for g in _guest_passwords()):
            tok = _session_token("guest")
        else:
            _login_failed(ip)
            return self._send(401, b'{"error":"Wrong password."}')
        self._send(200, b'{"ok":true}', extra=[("Set-Cookie", self._cookie(tok))])

    def _logout(self):
        self._send(200, b'{"ok":true}', extra=[("Set-Cookie", self._clear_cookie())])

    def _public_origin(self):
        # Base for absolute redirect URLs. Behind tailscale serve / any proxy,
        # trust X-Forwarded-Proto and Host; direct LAN access falls back to the
        # Host header with http.
        host = (self.headers.get("Host") or "").strip()
        if not host:
            return ""
        proto = "https" if self._https() else "http"
        return proto + "://" + host

    def _redirect_uri(self):
        base = os.environ.get("GOOGLE_REDIRECT_URI")
        if base:
            return base.rstrip("/")
        return self._public_origin() + "/auth/google/callback"

    def _oauth_state(self):
        payload = json.dumps({"typ": "oauth_state", "t": int(time.time()), "exp": int(time.time()) + 600},
                             separators=(",", ":")).encode("ascii")
        return _sign_token(payload)

    def _oauth_state_ok(self, state):
        data = _verify_token(state or "", typ="oauth_state")
        return data is not None

    def _google_login_redirect(self):
        if not _google_ready():
            return self._send(404, b"not found", "text/plain")
        params = urllib.parse.urlencode({
            "client_id": _google_client_id(),
            "redirect_uri": self._redirect_uri(),
            "response_type": "code",
            "scope": "openid email profile",
            "state": self._oauth_state(),
            "prompt": "select_account",
        })
        self._send(302, b"", "text/plain", extra=[("Location", GOOGLE_AUTH_URL + "?" + params)])

    def _google_exchange(self, code):
        data = urllib.parse.urlencode({
            "code": code,
            "client_id": _google_client_id(),
            "client_secret": _google_client_secret(),
            "redirect_uri": self._redirect_uri(),
            "grant_type": "authorization_code",
        }).encode("ascii")
        req = urllib.request.Request(GOOGLE_TOKEN_URL, data, {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "mealplanner/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            return {"error": "token_endpoint_%d" % e.code}
        except Exception:
            return {"error": "network"}

    def _google_userinfo(self, access_token):
        req = urllib.request.Request(GOOGLE_USERINFO_URL, None, {
            "Authorization": "Bearer " + access_token,
            "User-Agent": "mealplanner/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            return {"error": "userinfo_%d" % e.code}
        except Exception:
            return {"error": "network"}

    def _google_callback(self):
        if not _google_ready():
            return self._send(404, b"not found", "text/plain")
        # Only a GET query string is expected here; parse_request already
        # split it off self.path, so re-derive it.
        qs = urllib.parse.parse_qs((self.path.split("?", 1)[1] if "?" in self.path else ""))
        error = (qs.get("error") or [""])[0]
        if error:
            return self._html_message("Sign-in cancelled.", "Google returned: " + error)
        code = (qs.get("code") or [""])[0]
        state = (qs.get("state") or [""])[0]
        if not code or not self._oauth_state_ok(state):
            return self._html_message("Sign-in failed.", "Invalid state. Try signing in again.")
        tok = self._google_exchange(code)
        if not isinstance(tok, dict) or not tok.get("access_token"):
            return self._html_message("Sign-in failed.", "Could not verify with Google. Try again.")
        info = self._google_userinfo(tok["access_token"])
        email = str((info or {}).get("email") or "").strip().lower()
        if not email or not (info or {}).get("email_verified", False):
            return self._html_message("Sign-in failed.", "Google did not share a verified email.")
        allowed = _allowed_emails()
        if allowed and email not in allowed:
            return self._html_message("Invite-only for now",
                                      email + " isn't on the list yet. Ask " + _owner_name() +
                                      " for access; until then you can keep exploring the demo.",
                                      back=("/", "Back to the demo") if _open_demo() else None)
        cookie = self._cookie(_session_token("google:" + email))
        page = _auth_page("<div class='card auth-msg'><h3>Signed in</h3><p class='mute'>" + html.escape(email) +
                          " · opening the app…</p></div>", refresh="1;url=/")
        return self._send(200, page, "text/html; charset=utf-8",
                          extra=[("Set-Cookie", cookie)])

    def _html_message(self, title, detail, back=None):
        href, label = back or ("/login", "Back to sign in")
        body = _auth_page("<div class='card auth-msg'><h3>" + html.escape(title) + "</h3><p class='mute'>" +
                          html.escape(detail) + "</p><div class='row' style='margin-top:16px'>"
                          "<a class='btn ghost' href='" + href + "'>" + html.escape(label) + "</a></div></div>")
        self._send(200, body, "text/html; charset=utf-8")

    def do_GET(self):
        path = self._path()
        if path == "/api/auth":
            email, name, slug = self._who() if self._session_ok() else ("", "", None)
            return self._send(200, json.dumps({
                "required": _auth_on(),
                "password": bool(_password() or _guest_password() or _users()),
                "logins": bool(_users()),
                "guest": bool(self._is_guest()),
                "openDemo": _open_demo(),
                "google": _google_ready(),
                "user": name,
                "profile": slug or "",
                "admin": bool(self._is_admin()),
                "profiles": ([{"slug": k, "name": n} for k, n in _planners().items()]
                             if self._is_admin() else []),
            }).encode())
        if path == "/auth/google/login":
            return self._google_login_redirect()
        if path == "/auth/google/callback":
            return self._google_callback()
        if path == "/login":
            if not _auth_on():
                return self._send(404, b"not found", "text/plain")
            return self._send(200, _login_page(), "text/html; charset=utf-8")
        if path == "/api/reviews":
            if self._is_guest():
                return self._send(200, b'{"reviews":{}}')
            with _STATE_LOCK:
                got = _shared_reviews(self._who()[2])
            return self._send(200, json.dumps({"reviews": got}).encode())
        if path == "/api/users":
            if not self._is_admin():
                return self._send(403, b'{"error":"admin only"}')
            return self._send(200, json.dumps({"users": [{"login": u["login"], "name": u.get("name") or u["login"],
                "profile": u.get("profile") or ("u-" + u["login"])} for u in _users()]}).encode())
        if path == "/api/state" and self._is_guest():
            with _STATE_LOCK:
                return self._send(200, json.dumps(_guest_state(), separators=(",", ":")).encode("utf-8"))
        if path == "/api/state":
            slug = self._state_slug()
            with _STATE_LOCK:
                if slug:
                    return self._send(200, json.dumps(_profile_state(slug), separators=(",", ":")).encode("utf-8"))
                body = open(DATA, "rb").read() if os.path.exists(DATA) else b"{}"
            return self._send(200, body)
        if path.startswith("/images/"):
            name = _safe_image_name(path[len("/images/"):])
            if not name:
                return self._send(404, b"not found", "text/plain")
            fpath = os.path.join(IMAGES, name)
            if not os.path.isfile(fpath):
                return self._send(404, b"not found", "text/plain")
            ctype = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
            body = open(fpath, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "private, max-age=86400")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/manifest.webmanifest":
            return self._send(200, _MANIFEST, "application/manifest+json",
                              extra=[("Cache-Control", "public, max-age=86400")])
        if path.lstrip("/") in _ICONS:
            return self._send(200, base64.b64decode(_ICONS[path.lstrip("/")]), "image/png",
                              extra=[("Cache-Control", "public, max-age=604800")])
        if path in ("/", "/index.html"):
            page = open(os.path.join(HERE, "index.html"), "rb").read()
            email, name, slug = self._who()
            js = lambda v: json.dumps(v or "").replace("</", "<\\/")
            if self._is_guest():
                slug = "guest"
            boot = ("<script>window.MP_PROFILE=" + js(slug) + ";window.MP_USER=" + js(name) +
                    ";window.MP_GUEST=" + ("true" if self._is_guest() else "false") + ";</script>").encode("utf-8")
            page = page.replace(b"<head>", b"<head>" + boot, 1)
            return self._send(200, page, "text/html; charset=utf-8")
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if self._path() == "/api/login":
            return self._login()
        if self._path() == "/api/logout":
            return self._logout()
        if self._is_guest():
            if self._path() in ("/api/image", "/api/move-plans"):
                n = int(self.headers.get("Content-Length", 0) or 0)
                self.rfile.read(min(n, 10_000_000))
                return self._send(403, b'{"error":"Not available in the demo."}')
            if self._path() == "/api/classify":
                n = int(self.headers.get("Content-Length", 0) or 0)
                self.rfile.read(min(n, 1_000_000))
                return self._send(403, b'{"error":"Not available in the demo."}')
            if self._path() in ("/api/chat", "/api/import", "/api/fun-name") and not _guest_ai_ok():
                n = int(self.headers.get("Content-Length", 0) or 0)
                self.rfile.read(min(n, 1_000_000))
                return self._send(200, b'{"error":"The demo has used its AI calls for this hour. Try again later."}')
        if self._path() == "/api/image":
            return self._save_image()
        if self._path() == "/api/users":
            if not self._is_admin():
                return self._send(403, b'{"error":"admin only"}')
            body = self._read_json(10_000)
            if body is None:
                return
            act = str(body.get("action") or "")
            name = str(body.get("name") or "").strip()[:40]
            key = _login_key(body.get("login") or name)
            pw = str(body.get("password") or "")
            with _STATE_LOCK:
                users = _users()
                cur = next((u for u in users if u["login"] == key), None)
                if act in ("create", "password"):
                    if len(pw) < 6:
                        return self._send(400, b'{"error":"Use at least 6 characters."}')
                    if act == "create":
                        if not key or not name:
                            return self._send(400, b'{"error":"Add a name."}')
                        if cur:
                            return self._send(400, b'{"error":"That name is taken."}')
                        prof = str(body.get("profile") or "")
                        if prof and prof not in _planners():
                            return self._send(400, b'{"error":"Unknown planner."}')
                        cur = {"login": key, "name": name, "profile": prof or ("u-" + key)}
                        users.append(cur)
                    elif not cur:
                        return self._send(404, b'{"error":"No such login."}')
                    salt = secrets.token_hex(16)
                    cur["salt"], cur["hash"] = salt, _pw_hash(pw, salt)
                elif act == "delete":
                    users = [u for u in users if u["login"] != key]
                else:
                    return self._send(400, b'{"error":"bad action"}')
                _save_users(users)
            return self._send(200, b'{"ok":true}')
        if self._path() == "/api/move-plans":
            if not self._is_admin():
                return self._send(403, b'{"error":"admin only"}')
            body = self._read_json(10_000)
            if body is None:
                return
            valid = set(_planners())
            src, dst = str(body.get("from") or ""), str(body.get("to") or "")
            if src == dst or any(x and x not in valid for x in (src, dst)):
                return self._send(400, b'{"error":"bad planner"}')
            with _STATE_LOCK:
                _backup_states()
                moved = _move_plans(src or None, dst or None)
            return self._send(200, json.dumps({"ok": True, "moved": moved}).encode())
        if self._path() == "/api/classify":
            body = self._read_json(300_000)
            if body is None:
                return
            return self._send(200, json.dumps(classify_recipes(body)).encode())
        if self._path() == "/api/fun-name":
            n=int(self.headers.get("Content-Length",0) or 0)
            if n>100_000:return self._send(413,b'{"error":"too large"}')
            try:body=json.loads(self.rfile.read(n) or b"{}")
            except ValueError:return self._send(400,b'{"error":"bad json"}')
            if not isinstance(body,dict):return self._send(400,b'{"error":"bad json"}')
            return self._send(200,json.dumps(ask_fun_name(body.get("recipe"),body.get("provider","groq"))).encode())
        if self._path() not in ("/api/chat", "/api/import"):
            return self._send(404, b"not found", "text/plain")
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n > 1_000_000:
            return self._send(413, b"too large", "text/plain")
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, b"bad json", "text/plain")
        if not isinstance(body, dict):
            return self._send(400, b"bad json", "text/plain")
        if self._path() == "/api/import":
            out = self.do_POST_import(body)
        else:
            out = ask_model(body.get("messages", []), body.get("context", {}), provider=body.get("provider", "groq"))
        self._send(200, json.dumps(out).encode())

    def do_DELETE(self):
        if self._path() != "/api/image":
            return self._send(404, b"not found", "text/plain")
        if self._is_guest():
            return self._send(403, b'{"error":"Not available in the demo."}')
        # ?id=recipeId
        q = ""
        if "?" in self.path:
            q = self.path.split("?", 1)[1]
        rid = ""
        for part in q.split("&"):
            if part.startswith("id="):
                rid = part[3:]
                break
        if not IMG_ID_RE.match(rid):
            return self._send(400, b'{"error":"bad id"}')
        _ensure_images()
        _remove_images_for_id(rid)
        self._send(200, b'{"ok":true}')

    def _save_image(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        # base64 JSON can be ~4/3 of binary; allow a bit over MAX_IMAGE_BYTES
        if n > MAX_IMAGE_BYTES * 2:
            return self._send(413, b'{"error":"too large"}')
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._send(400, b'{"error":"bad json"}')
        if not isinstance(body, dict):
            return self._send(400, b'{"error":"bad json"}')
        rid = str(body.get("id") or "")
        if not IMG_ID_RE.match(rid):
            return self._send(400, b'{"error":"bad id"}')
        if body.get("clear"):
            _ensure_images()
            _remove_images_for_id(rid)
            return self._send(200, b'{"ok":true,"url":""}')
        data = body.get("data") or ""
        if not isinstance(data, str) or not data:
            return self._send(400, b'{"error":"missing data"}')
        mime = "image/jpeg"
        b64 = data
        if data.startswith("data:") and ";base64," in data:
            header, b64 = data.split(";base64,", 1)
            mime = header[5:] or mime
        mime = str(mime).split(";")[0].strip().lower()
        ext = { "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
                "image/webp": ".webp", "image/gif": ".gif" }.get(mime)
        if not ext:
            return self._send(400, b'{"error":"unsupported type"}')
        try:
            raw = base64.b64decode(b64, validate=False)
        except Exception:
            return self._send(400, b'{"error":"bad base64"}')
        if not raw or len(raw) > MAX_IMAGE_BYTES:
            return self._send(413, b'{"error":"too large"}')
        _ensure_images()
        _remove_images_for_id(rid)  # one image per recipe
        fpath = os.path.join(IMAGES, rid + ext)
        fd, tmp = tempfile.mkstemp(dir=IMAGES, suffix=ext)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        os.replace(tmp, fpath)
        url = "/images/" + rid + ext
        self._send(200, json.dumps({"ok": True, "url": url}).encode())

    @staticmethod
    def _loose_json(raw):
        """Read the model's JSON even with code fences, smart quotes or trailing commas around it."""
        t = str(raw or "").strip()
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I)
        if "{" not in t or "}" not in t:
            raise ValueError("no object")
        t = t[t.index("{"):t.rindex("}") + 1]
        for cand in (t, re.sub(r",\s*([}\]])", r"\1", t),
                     re.sub(r",\s*([}\]])", r"\1", t.replace("\u201c", '"').replace("\u201d", '"'))):
            try:
                return json.loads(cand, strict=False)
            except ValueError:
                continue
        raise ValueError("unreadable")

    def do_POST_import(self, body):
        text = str(body.get("text", ""))[:20000]
        if not text.strip():
            return {"error": "Nothing to parse."}
        meta = {}
        m = _URL_RE.match(text)
        if m:
            # A bare link: read the page ourselves; never let the model guess from the address.
            try:
                got = recipe_source_from_url(m.group(1))
            except ValueError as e:
                return {"error": str(e) + " Paste the recipe text instead."}
            text = got["text"][:20000]
            meta = {"source": m.group(1), "via": got["via"]}
        first = str(body.get("provider", "groq") or "groq").lower()
        keys = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY", "standardcompute": "STANDARDCOMPUTE_API_KEY"}
        order = [first] + [p for p in ("groq", "gemini", "standardcompute") if p != first and os.environ.get(keys[p])]
        recipe, last_err = None, None
        for provider in order[:2]:
            convo = [{"role": "user", "content": text}]
            for attempt in range(2):
                out = ask_model(convo, {}, system=IMPORT_SYSTEM + tag_list(body.get("cuisines")), provider=provider,
                                json_mode=True, max_chars=20000, max_tokens=8000)
                if "error" in out:
                    last_err = out["error"]
                    break
                try:
                    recipe = self._loose_json(out["reply"])
                    break
                except ValueError:
                    last_err = "The AI's reply wasn't a readable recipe"
                    # Show it what came back and ask for the JSON alone.
                    convo = convo + [{"role": "assistant", "content": (out["reply"] or "(empty reply)")[:6000]},
                                     {"role": "user", "content": "That was not one valid JSON object. Reply again with ONLY the JSON object described, nothing else."}]
            if recipe is not None:
                break
        if recipe is None:
            return {"error": last_err or "The AI's reply wasn't a readable recipe"}
        if not isinstance(recipe, dict) or recipe.get("error"):
            return {"error": "No recipe found in that text."}
        return {"recipe": recipe, **meta}

    def do_PUT(self):
        if self._path() != "/api/state":
            return self._send(404, b"not found", "text/plain")
        if self._is_guest():
            n = int(self.headers.get("Content-Length", 0) or 0)
            self.rfile.read(min(n, 5_000_000))
            return self._send(200, b'{"ok":true,"demo":true}')
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n > 5_000_000:
            return self._send(413, b"too large", "text/plain")
        raw = self.rfile.read(n)
        try:
            body = json.loads(raw)
        except ValueError:
            return self._send(400, b"bad json", "text/plain")
        if not isinstance(body, dict):
            return self._send(400, b"bad json", "text/plain")
        slug = self._state_slug()
        with _STATE_LOCK:
            if slug:
                _save_profile_state(slug, body)
            else:
                fd, tmp = tempfile.mkstemp(dir=HERE)
                with os.fdopen(fd, "wb") as f:
                    f.write(raw)
                os.replace(tmp, DATA)  # atomic write
        self._send(200, b'{"ok":true}')

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    _ensure_images()
    print(f"Meal planner on http://0.0.0.0:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
