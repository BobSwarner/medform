from datetime import timedelta

import pytest

from app import create_app, turnstile
from app.config import TestConfig
from app.extensions import db
from app.models import AdminUser, Invite, Submission, utcnow

from .test_routes import base_data


class TurnstileConfig(TestConfig):
    TURNSTILE_SITE_KEY = "site-key"
    TURNSTILE_SECRET_KEY = "secret-key"


@pytest.fixture
def app(monkeypatch):
    # Pretend Cloudflare accepts only the token "good".
    monkeypatch.setattr(turnstile, "verify", lambda token: token == "good")
    app = create_app(TurnstileConfig)
    with app.app_context():
        db.create_all()
        user = AdminUser(username="bob")
        user.set_password("correct horse battery")
        inv = Invite(client_name="Jane Doe", expires_at=utcnow() + timedelta(days=30))
        db.session.add_all([user, inv])
        db.session.commit()
        app.invite_token = inv.token
        yield app
        db.drop_all()


def test_widget_and_csp_on_both_pages(app):
    c = app.test_client()
    for path in (f"/f/{app.invite_token}", "/admin/login"):
        r = c.get(path)
        assert b'class="cf-turnstile" data-sitekey="site-key"' in r.data
        assert b"challenges.cloudflare.com/turnstile/v0/api.js" in r.data
        csp = r.headers["Content-Security-Policy"]
        assert "script-src 'self' https://challenges.cloudflare.com" in csp
        assert "frame-src https://challenges.cloudflare.com" in csp


def test_form_rejected_without_valid_token(app):
    c = app.test_client()
    url = f"/f/{app.invite_token}"
    for extra in ({}, {"cf-turnstile-response": "bad"}):
        r = c.post(url, data=base_data(**extra))
        assert r.status_code == 200 and b"complete the verification" in r.data
    assert db.session.scalar(db.select(db.func.count(Submission.id))) == 0

    r = c.post(url, data=base_data(**{"cf-turnstile-response": "good"}))
    assert r.status_code == 302
    assert db.session.scalar(db.select(db.func.count(Submission.id))) == 1


def test_login_needs_token_before_password_is_checked(app):
    c = app.test_client()
    creds = {"username": "bob", "password": "correct horse battery"}
    r = c.post("/admin/login", data=creds)
    assert b"complete the verification" in r.data
    assert c.get("/admin/").status_code == 302  # still signed out

    # a bot without a token can't burn failed-login attempts or lock the account
    for _ in range(10):
        c.post("/admin/login", data={**creds, "password": "wrong"})
    assert db.session.scalars(db.select(AdminUser)).one().failed_logins == 0

    r = c.post("/admin/login", data={**creds, "cf-turnstile-response": "good"})
    assert r.status_code == 302
    assert c.get("/admin/").status_code == 200


def test_disabled_without_keys():
    app = create_app("app.config.TestConfig")
    with app.app_context():
        db.create_all()
        assert b"cf-turnstile" not in app.test_client().get("/admin/login").data
        db.drop_all()
