"""Cloudflare Turnstile: server-side verification of the widget's token."""
import json
import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import current_app, request

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
FORM_FIELD = "cf-turnstile-response"  # added to the form by Cloudflare's script

log = logging.getLogger(__name__)


def enabled(app=None):
    cfg = (app or current_app).config
    return bool(cfg.get("TURNSTILE_SITE_KEY") and cfg.get("TURNSTILE_SECRET_KEY"))


def verify(token):
    """True only if Cloudflare confirms the token. Any error counts as a failure."""
    if not token:
        return False
    body = urlencode({"secret": current_app.config["TURNSTILE_SECRET_KEY"], "response": token}).encode()
    try:
        with urlopen(Request(VERIFY_URL, data=body), timeout=5) as resp:
            return bool(json.load(resp).get("success"))
    except Exception:
        log.exception("Turnstile verification request failed")
        return False


class TurnstileMixin:
    """Add to a FlaskForm (before FlaskForm) to require a passing Turnstile check.

    Runs inside validate(), so a view that checks validate_on_submit() before touching
    the database or comparing a password is protected without any other change.
    """

    turnstile_errors = ()

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        if enabled() and not verify(request.form.get(FORM_FIELD)):
            self.turnstile_errors = ["Please complete the verification and try again."]
            ok = False
        return ok
