#!/bin/sh
# Create missing tables (waiting for Postgres to accept connections), then run the command.
set -e
i=0
until flask init-db; do
    i=$((i + 1))
    [ "$i" -ge 30 ] && { echo "Database not reachable; giving up." >&2; exit 1; }
    echo "Waiting for database..." >&2
    sleep 2
done
exec "$@"
