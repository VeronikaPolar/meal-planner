#!/bin/bash
# Pull new code from GitHub and restart the server, but only if something changed.
# Safe to run from cron every few minutes. Data files are in .gitignore, so they are never touched.
#
# New code is checked before it goes live: server.py must compile, the app's JavaScript
# must parse (when node is installed), and a throwaway copy of the server must answer.
# If the check fails, nothing changes. If the live server doesn't answer after the
# restart, the previous version is put back. A bad commit is remembered and not retried.
set -u
cd "$(dirname "$0")"
HERE="$(pwd)"
PORT="${DEPLOY_PORT:-6969}"   # the port the live server listens on
log(){ echo "$(date '+%F %T') $*"; }

git fetch --quiet origin main || { log "fetch failed"; exit 1; }
OLD=$(git rev-parse HEAD); NEW=$(git rev-parse origin/main)
[ "$OLD" = "$NEW" ] && exit 0
[ -f .deploy-bad ] && [ "$(cat .deploy-bad)" = "$NEW" ] && exit 0

# answers URL -> exit 0 when it replies with a 2xx/3xx/401 within a few seconds
answers(){ python3 - "$1" <<'PY'
import sys, urllib.request, urllib.error
try:
    urllib.request.urlopen(sys.argv[1], timeout=5); sys.exit(0)
except urllib.error.HTTPError as e:
    sys.exit(0 if e.code in (401, 403) else 1)
except Exception:
    sys.exit(1)
PY
}

check_new(){
  local dir; dir=$(mktemp -d)
  git show "$NEW:server.py" > "$dir/server.py" && git show "$NEW:index.html" > "$dir/index.html" || { rm -rf "$dir"; return 1; }
  python3 -m py_compile "$dir/server.py" || { log "check: server.py does not compile"; rm -rf "$dir"; return 1; }
  if command -v node >/dev/null 2>&1; then
    node -e 'const s=require("fs").readFileSync(process.argv[1],"utf8");for(const m of s.matchAll(/<script>([\s\S]*?)<\/script>/g))new Function(m[1])' "$dir/index.html" \
      || { log "check: index.html has a JavaScript error"; rm -rf "$dir"; return 1; }
  fi
  local tport=$((PORT + 37)) ok=1 i
  ( cd "$dir" && exec python3 server.py "$tport" > "$dir/test.log" 2>&1 ) & local pid=$!
  for i in 1 2 3 4 5 6 7 8 9 10; do sleep 1; if answers "http://127.0.0.1:$tport/" && answers "http://127.0.0.1:$tport/api/auth"; then ok=0; break; fi; done
  kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
  [ $ok -eq 0 ] || log "check: test server did not answer: $(tail -3 "$dir/test.log" | tr '\n' ' ')"
  rm -rf "$dir"; return $ok
}

restart(){
  # systemd unit if there is one, otherwise kill and relaunch in the background
  if systemctl --user cat meal-planner >/dev/null 2>&1; then
    systemctl --user restart meal-planner
  elif systemctl cat meal-planner >/dev/null 2>&1; then
    sudo -n systemctl restart meal-planner
  else
    # stop only this folder's server (matched by its full path), never other Python programs
    pkill -f "[Pp]ython[^ ]* $HERE/server\.py" 2>/dev/null; sleep 1
    if [ -f ./start.sh ]; then nohup sh ./start.sh >> server.log 2>&1 &
    else nohup python3 "$HERE/server.py" "$PORT" >> server.log 2>&1 &
    fi
  fi
}

live_ok(){ local i; for i in 1 2 3 4 5 6 7 8 9 10; do sleep 1; answers "http://127.0.0.1:$PORT/api/auth" && return 0; done; return 1; }

if ! check_new; then
  echo "$NEW" > .deploy-bad
  log "skipped $(git log -1 --format='%h %s' "$NEW"): failed the check, live site unchanged"
  exit 1
fi

git reset --hard --quiet "$NEW"
log "updated to $(git log -1 --format='%h %s')"
restart
if live_ok; then
  rm -f .deploy-bad
  log "restarted, live site answers"
else
  echo "$NEW" > .deploy-bad
  git reset --hard --quiet "$OLD"
  restart
  if live_ok; then log "live site did not answer on $(git rev-parse --short "$NEW"); rolled back to $(git rev-parse --short "$OLD")"
  else log "live site did not answer after rolling back either; check server.log"; fi
  exit 1
fi
