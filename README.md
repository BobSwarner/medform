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

    gunicorn -w 2 -b 127.0.0.1:8002 wsgi:app    # nginx proxies to this
    python3 -m pytest -q                        # tests use in-memory SQLite

## Running as a service

`deploy/medform.service` is a systemd unit (starts on boot, restarts on failure). Install with
`sudo cp deploy/medform.service /etc/systemd/system/ && sudo systemctl daemon-reload &&
sudo systemctl enable --now medform`. After that, `./restart.sh` just runs
`sudo systemctl restart medform`; logs are in `journalctl -u medform`.

## Admin console

Create (or reset) an admin user, then sign in at `/admin/`:

    flask create-admin <username>      # prompts for a password (12+ chars)

- **Submissions** lists every submission, newest first; click one for the full details.
- **Client links** creates a private link for a client's name:
  `<PUBLIC_BASE_URL>/f/<token>`, shown as a ready-to-send email with a Copy button. The form opens only through a valid link (everything else,
  including `/`, is a 404), and the client's name is pre-filled. Links are multi-use,
  expire after `INVITE_DAYS` (30) and can be revoked.
- Set `PUBLIC_BASE_URL` in `.env` if the public address isn't `https://medform.swarner.com`.
  `SENDER_NAME` (default `Dana`) signs the invitation email shown for each link.
- Five failed sign-ins lock that account for 15 minutes.

## Cloudflare Turnstile

The client form and the admin login both require a Turnstile check when `TURNSTILE_SITE_KEY` and
`TURNSTILE_SECRET_KEY` are set in `.env` (the app logs a warning at startup if they aren't).
Create a widget for `medform.swarner.com` in the Cloudflare dashboard. For testing, Cloudflare's
dummy keys always pass: site `1x00000000000000000000AA`, secret `1x0000000000000000000000000000000AA`.
If Cloudflare can't be reached, verification fails and the form can't be submitted.

## Not built yet

- TOTP for admin login, CSV export, audit log
