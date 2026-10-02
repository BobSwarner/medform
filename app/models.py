import uuid
from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


# (stored value, label shown to the client)
FREQUENCY_CHOICES = [
    ("once_daily", "Once daily"),
    ("twice_daily", "Twice daily"),
    ("three_daily", "Three times daily"),
    ("four_daily", "Four times daily"),
    ("weekly", "Weekly"),
    ("as_needed", "As needed"),
    ("other", "Other"),
]
FREQUENCY_LABELS = dict(FREQUENCY_CHOICES)


class Submission(db.Model):
    # db.Uuid maps to native UUID on Postgres (and works on SQLite for tests)
    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    client_name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(200), nullable=False)
    consent_given = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    status = db.Column(db.String(20), default="new", nullable=False)  # new / reviewed / archived

    doctors = db.relationship(
        "Doctor", back_populates="submission",
        cascade="all, delete-orphan", order_by="Doctor.position",
    )
    medications = db.relationship(
        "Medication", back_populates="submission",
        cascade="all, delete-orphan", order_by="Medication.position",
    )
    pharmacies = db.relationship(
        "Pharmacy", back_populates="submission",
        cascade="all, delete-orphan", order_by="Pharmacy.position",
    )


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Uuid, db.ForeignKey("submission.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    position = db.Column(db.SmallInteger, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    specialty = db.Column(db.String(100))
    phone = db.Column(db.String(30))

    submission = db.relationship("Submission", back_populates="doctors")


class Pharmacy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Uuid, db.ForeignKey("submission.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    position = db.Column(db.SmallInteger, nullable=False)
    name = db.Column(db.String(200), nullable=False)  # name and location, as the client wrote it

    submission = db.relationship("Submission", back_populates="pharmacies")


class Medication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(
        db.Uuid, db.ForeignKey("submission.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    position = db.Column(db.SmallInteger, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(
        db.Enum(*FREQUENCY_LABELS.keys(), name="med_frequency"), nullable=False
    )
    frequency_other = db.Column(db.String(200))

    submission = db.relationship("Submission", back_populates="medications")
