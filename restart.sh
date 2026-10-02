#!/usr/bin/env bash
# Restart the medform Gunicorn server (start it if it isn't running).
#   ./restart.sh            restart
#   ./restart.sh stop       stop only
# Override the address with BIND=host:port (default below). Logs: gunicorn.log
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
BIND="${BIND:-192.168.0.11:8002}"
PIDFILE="$PWD/gunicorn.pid"
LOG="$PWD/gunicorn.log"

running_pid() {
    if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        cat "$PIDFILE"
    else
        # Started by hand rather than by this script: find it by its bind address.
        pgrep -o -f "[g]unicorn.* -b $BIND" || true
    fi
}

stop() {
    local pid; pid="$(running_pid)"
    if [[ -z "$pid" ]]; then echo "Not running."; return; fi
    echo "Stopping gunicorn (pid $pid)..."
    kill -TERM "$pid"
    for _ in $(seq 1 20); do
        kill -0 "$pid" 2>/dev/null || { rm -f "$PIDFILE"; echo "Stopped."; return; }
        sleep 0.5
    done
    echo "Did not stop within 10s; sending KILL."
    kill -KILL "$pid"; rm -f "$PIDFILE"
}

if [[ "${1:-}" == "stop" ]]; then stop; exit 0; fi

stop

[[ -f .env ]] || { echo ".env not found in $PWD" >&2; exit 1; }
set -a; . ./.env; set +a

echo "Starting gunicorn on $BIND..."
.venv/bin/gunicorn -w 2 -b "$BIND" --daemon --pid "$PIDFILE" \
    --access-logfile "$LOG" --error-logfile "$LOG" wsgi:app

# Confirm it answers before reporting success.
for _ in $(seq 1 20); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "http://$BIND/admin/login" || true)"
    if [[ "$code" == "200" ]]; then echo "Up: http://$BIND/ (pid $(cat "$PIDFILE"))"; exit 0; fi
    sleep 0.5
done
echo "Server did not come up. Last log lines:" >&2
tail -n 15 "$LOG" >&2
exit 1
