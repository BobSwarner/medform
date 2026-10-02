import pytest

from app import create_app
from app.extensions import db
from app.models import AdminUser, Invite, Submission, utcnow
from datetime import timedelta

from .test_routes import base_data  # noqa: F401


@pytest.fixture
def app():
    app = create_app("app.config.TestConfig")
    with app.app_context():
        db.create_all()
        user = AdminUser(username="bob")
        user.set_password("correct horse battery")
        db.session.add(user)
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, password="correct horse battery"):
    return client.post("/admin/login", data={"username": "bob", "password": password})


def test_admin_pages_require_login(client):
    for path in ("/admin/", "/admin/links", "/admin/submissions/00000000-0000-0000-0000-000000000000"):
        r = client.get(path)
        assert r.status_code == 302 and "/admin/login" in r.headers["Location"]
    assert client.post("/admin/links", data={"client_name": "X"}).status_code == 302
    assert db.session.scalar(db.select(db.func.count(Invite.id))) == 0


def test_login_and_logout(client):
    assert b"Invalid username or password" in login(client, "wrong").data
    assert login(client).status_code == 302
    assert client.get("/admin/").status_code == 200
    client.post("/admin/logout")
    assert client.get("/admin/").status_code == 302


def test_lockout_after_repeated_failures(client, app):
    for _ in range(app.config["LOGIN_MAX_FAILURES"]):
        login(client, "wrong")
    # even the right password is refused while locked
    assert b"Invalid username or password" in login(client).data
    assert client.get("/admin/").status_code == 302


def test_create_link_and_use_it(client):
    login(client)
    r = client.post("/admin/links", data={"client_name": "Mary Smith"}, follow_redirects=True)
    inv = db.session.scalars(db.select(Invite)).one()
    full = f"https://swarner.com/medform/f/{inv.token}"
    assert full.encode() in r.data
    assert inv.client_name == "Mary Smith" and inv.created_by == "bob"
    assert 29 <= (inv.expires_at.replace(tzinfo=None) - utcnow().replace(tzinfo=None)).days <= 30

    public = app_client_for_public(client)
    assert b'value="Mary Smith"' in public.get(f"/f/{inv.token}").data


def app_client_for_public(client):
    # a fresh client with no admin session
    return client.application.test_client()


def test_revoke_link(client):
    login(client)
    client.post("/admin/links", data={"client_name": "Mary Smith"})
    inv = db.session.scalars(db.select(Invite)).one()
    client.post(f"/admin/links/{inv.id}/revoke")
    assert app_client_for_public(client).get(f"/f/{inv.token}").status_code == 404


def test_list_newest_first_and_detail(client):
    login(client)
    client.post("/admin/links", data={"client_name": "Zed"})
    inv = db.session.scalars(db.select(Invite)).one()
    pub = app_client_for_public(client)
    pub.post(f"/f/{inv.token}", data=base_data(client_name="First Person"))
    pub.post(f"/f/{inv.token}", data=base_data(client_name="Second Person"))

    r = client.get("/admin/")
    assert r.data.index(b"Second Person") < r.data.index(b"First Person")

    sub = db.session.scalars(db.select(Submission).order_by(Submission.created_at.desc())).first()
    page = client.get(f"/admin/submissions/{sub.id}").data
    for text in (b"Second Person", b"Dr. Smith", b"Lisinopril", b"10 mg",
                 b"Every other day", b"CVS, Main St", b"Walgreens, Oak Ave"):
        assert text in page


def test_https_post_with_same_origin_referer_passes_csrf(app):
    # Flask-WTF requires a Referer on HTTPS posts, so the app must not send Referrer-Policy: no-referrer.
    app.config["WTF_CSRF_ENABLED"] = True
    c = app.test_client()
    page = c.get("/admin/login", base_url="https://swarner.com")
    assert page.headers["Referrer-Policy"] == "same-origin"
    import re
    token = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', page.data).group(1).decode()
    r = c.post("/admin/login", base_url="https://swarner.com",
               headers={"Referer": "https://swarner.com/admin/login"},
               data={"username": "bob", "password": "correct horse battery", "csrf_token": token})
    assert r.status_code == 302
