#!/bin/bash
# Pull new code from GitHub and restart the server, but only if something changed.
# Safe to run from cron every few minutes. Data files are in .gitignore, so they are never touched.
set -u
cd "$(dirname "$0")"

git fetch --quiet origin main || { echo "$(date '+%F %T') fetch failed"; exit 1; }
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] && exit 0

git reset --hard --quiet origin/main
echo "$(date '+%F %T') updated to $(git log -1 --format='%h %s')"

# Restart: systemd unit if there is one, otherwise kill and relaunch in the background
if systemctl --user cat meal-planner >/dev/null 2>&1; then
  systemctl --user restart meal-planner
elif systemctl cat meal-planner >/dev/null 2>&1; then
  sudo -n systemctl restart meal-planner
else
  pkill -f "python3? .*server\.py" ; sleep 1
  if [ -x ./start.sh ]; then nohup ./start.sh >> server.log 2>&1 &
  else nohup python3 server.py >> server.log 2>&1 &
  fi
fi
echo "$(date '+%F %T') restarted"
