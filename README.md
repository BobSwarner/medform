# medform

Client medication and doctor intake form (Flask + Postgres).

## Setup

    python3 -m venv .venv
    . .venv/bin/activate              # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env              # fill in SECRET_KEY and DATABASE_URL
    set -a; . ./.env; set +a
    export FLASK_APP=wsgi.py
    flask db init                     # first time only
    flask db migrate -m "initial"
    flask db upgrade

Generate a secret key with:

    python3 -c "import secrets; print(secrets.token_hex(32))"

## Run

    gunicorn -w 2 -b 127.0.0.1:8000 wsgi:app    # nginx proxies to this
    python3 -m pytest -q                        # tests use in-memory SQLite

## Not built yet

- Admin login (Flask-Login + TOTP), submission list/detail, CSV export, audit log
- Cloudflare Turnstile on the public form
