#!/bin/sh
set -eu

if [ "${SKIP_DB_MIGRATIONS:-0}" != "1" ]; then
  echo "Ensuring database tables and SQL migrations are up to date..."
  python init_db.py --init --migrate
fi

exec "$@"
