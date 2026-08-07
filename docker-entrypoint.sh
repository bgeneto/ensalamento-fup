#!/bin/sh
set -eu

# These directories are deliberately below the host-mounted /app/data tree so
# database files, generated reports, logs, and file-backed settings survive a
# rebuilt/replaced container.
mkdir -p /app/data/logs /app/data/reports /app/data/runtime

if [ "${SKIP_DB_MIGRATIONS:-0}" != "1" ]; then
  echo "Ensuring database tables and SQL migrations are up to date..."
  python init_db.py --init --migrate
  export DB_BOOTSTRAPPED=1
fi

exec "$@"
