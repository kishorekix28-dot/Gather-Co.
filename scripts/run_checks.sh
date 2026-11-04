#!/usr/bin/env bash
# Pre-commit verification: system checks, migrations, Django tests, deploy check, static files.
# Requires DATABASE_URL / MONGODB_URI in the environment (or .env) for full coverage.
set -euo pipefail
PY=${PYTHON:-python}
echo "== manage.py check";                 $PY manage.py check
echo "== migrations up to date";           $PY manage.py makemigrations --check --dry-run
echo "== migrate";                         $PY manage.py migrate --noinput
echo "== Django test suite";               TESTING=true $PY manage.py test tests -v 1
echo "== production deploy check";         DEBUG=False USE_HTTPS=True SECRET_KEY=${SECRET_KEY:-$($PY -c 'import secrets;print(secrets.token_urlsafe(50))')} $PY manage.py check --deploy
echo "== collectstatic";                   DEBUG=False SECRET_KEY=${SECRET_KEY:-x$($PY -c 'import secrets;print(secrets.token_urlsafe(50))')} $PY manage.py collectstatic --noinput >/dev/null && echo "static OK"
echo "== secret scan";                     $PY scripts/secret_scan.py
