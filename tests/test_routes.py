import pytest

from app import create_app
from app.extensions import db
from app.models import Medication, Submission


@pytest.fixture
def client():
    app = create_app("app.config.TestConfig")
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def base_data(**extra):
    data = {
        "client_name": "Jane Doe",
        "contact": "555-0100",
        "consent": "y",
        "doctors-0-name": "Dr. Smith",
        "doctors-0-specialty": "Primary care",
        "doctors-1-name": "Dr. Lee",
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


def test_form_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b'name="medications-0-name"' in r.data
    assert b"medications-__i__-name" in r.data  # template row for form.js
    assert "no-store" in r.headers["Cache-Control"]


def test_valid_submission_saves_everything(client):
    r = client.post("/", data=base_data())
    assert r.status_code == 302 and r.headers["Location"].endswith("/thanks")

    sub = db.session.scalars(db.select(Submission)).one()
    assert [d.name for d in sub.doctors] == ["Dr. Smith", "Dr. Lee"]
    meds = sub.medications
    assert [m.name for m in meds] == ["Lisinopril", "Metformin"]
    assert meds[0].frequency_other is None
    assert meds[1].frequency_other == "Every other day"


def test_other_frequency_requires_explanation(client):
    r = client.post("/", data=base_data(**{"medications-1-frequency_other": ""}))
    assert r.status_code == 200
    assert b"Please describe how often" in r.data
    assert db.session.scalar(db.select(db.func.count(Medication.id))) == 0


def test_consent_required(client):
    data = base_data()
    data.pop("consent")
    r = client.post("/", data=data)
    assert r.status_code == 200
    assert db.session.scalar(db.select(db.func.count(Submission.id))) == 0


def test_too_many_medications_rejected(client):
    data = base_data()
    for i in range(2, 30):
        data.update({f"medications-{i}-name": "X", f"medications-{i}-dosage": "1",
                     f"medications-{i}-frequency": "weekly"})
    r = client.post("/", data=data)
    assert r.status_code == 200
    assert b"Too many medications" in r.data
