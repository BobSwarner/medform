import pytest

from app import create_app
from app.extensions import db
from datetime import timedelta

from app.models import Invite, Medication, Submission, utcnow


@pytest.fixture
def app():
    app = create_app("app.config.TestConfig")
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def invite(app):
    inv = Invite(client_name="Jane Doe", expires_at=utcnow() + timedelta(days=30))
    db.session.add(inv)
    db.session.commit()
    return inv


@pytest.fixture
def url(invite):
    return f"/f/{invite.token}"


@pytest.fixture
def client(app, invite):
    return app.test_client()


def base_data(**extra):
    data = {
        "client_name": "Jane Doe",
        "consent": "y",
        "doctors-0-name": "Dr. Smith",
        "doctors-0-specialty": "Primary care",
        "doctors-1-name": "Dr. Lee",
        "pharmacies-0-name": "CVS, Main St",
        "pharmacies-1-name": "Walgreens, Oak Ave",
        "pharmacies-2-name": "",
        "medications-0-name": "Lisinopril",
        "medications-0-dosage": "10 mg",
        "medications-0-frequency": "once_daily",
        "medications-1-name": "Metformin",
        "medications-1-dosage": "500 mg",
        "medications-1-frequency": "other",
        "medications-1-frequency_other": "Every other day",
    }
    data.update(extra)
    return data


def test_form_renders(client, url):
    r = client.get(url)
    assert r.status_code == 200
    assert b'name="medications-0-name"' in r.data
    assert b"medications-__i__-name" in r.data  # template row for form.js
    assert b"pharmacies-__i__-name" in r.data
    assert "no-store" in r.headers["Cache-Control"]


def test_valid_submission_saves_everything(client, url):
    r = client.post(url, data=base_data())
    assert r.status_code == 302 and r.headers["Location"] == url + "/thanks"

    sub = db.session.scalars(db.select(Submission)).one()
    assert [d.name for d in sub.doctors] == ["Dr. Smith", "Dr. Lee"]
    assert [p.name for p in sub.pharmacies] == ["CVS, Main St", "Walgreens, Oak Ave"]  # blank row dropped
    meds = sub.medications
    assert [m.name for m in meds] == ["Lisinopril", "Metformin"]
    assert meds[0].frequency_other is None
    assert meds[1].frequency_other == "Every other day"


def test_other_frequency_requires_explanation(client, url):
    r = client.post(url, data=base_data(**{"medications-1-frequency_other": ""}))
    assert r.status_code == 200
    assert b"Please describe how often" in r.data
    assert db.session.scalar(db.select(db.func.count(Medication.id))) == 0


def test_consent_required(client, url):
    data = base_data()
    data.pop("consent")
    r = client.post(url, data=data)
    assert r.status_code == 200
    assert db.session.scalar(db.select(db.func.count(Submission.id))) == 0


def test_too_many_medications_rejected(client, url):
    data = base_data()
    for i in range(2, 30):
        data.update({f"medications-{i}-name": "X", f"medications-{i}-dosage": "1",
                     f"medications-{i}-frequency": "weekly"})
    r = client.post(url, data=data)
    assert r.status_code == 200
    assert b"Too many medications" in r.data


def test_pharmacies_optional(client, url):
    data = {k: v for k, v in base_data().items() if not k.startswith("pharmacies-")}
    r = client.post(url, data=data)
    assert r.status_code == 302
    assert db.session.scalars(db.select(Submission)).one().pharmacies == []


def test_too_many_pharmacies_rejected(client, url):
    data = base_data(**{f"pharmacies-{i}-name": "X" for i in range(2, 8)})
    r = client.post(url, data=data)
    assert r.status_code == 200
    assert b"Too many pharmacies" in r.data


def test_root_and_unknown_tokens_rejected(client):
    assert client.get("/").status_code == 404
    assert client.post("/", data=base_data()).status_code == 404
    assert client.get("/f/not-a-real-token").status_code == 404
    assert client.post("/f/not-a-real-token", data=base_data()).status_code == 404
    assert client.get("/thanks").status_code == 404
    assert db.session.scalar(db.select(db.func.count(Submission.id))) == 0


def test_expired_and_revoked_links_rejected(client, url, invite):
    invite.expires_at = utcnow() - timedelta(seconds=1)
    db.session.commit()
    assert client.get(url).status_code == 404
    assert client.post(url, data=base_data()).status_code == 404

    invite.expires_at = utcnow() + timedelta(days=1)
    invite.revoked_at = utcnow()
    db.session.commit()
    assert client.get(url).status_code == 404


def test_name_prefilled_and_submission_linked_to_invite(client, url, invite):
    assert b'value="Jane Doe"' in client.get(url).data
    client.post(url, data=base_data())
    sub = db.session.scalars(db.select(Submission)).one()
    assert sub.invite_id == invite.id
    # multi-use: the same link still works afterwards
    assert client.get(url).status_code == 200
def test_no_contact_field(client, url):
    assert b"contact" not in client.get(url).data.replace(b"contact you", b"")
