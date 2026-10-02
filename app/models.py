import secrets
import uuid
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


def aware(dt):
    """SQLite returns naive datetimes; everything is stored as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


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


class AdminUser(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    failed_logins = db.Column(db.SmallInteger, default=0, nullable=False)
    locked_until = db.Column(db.DateTime(timezone=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_locked(self, now=None):
        return self.locked_until is not None and aware(self.locked_until) > (now or utcnow())


class Invite(db.Model):
    """A private link for one client. The unguessable token in the URL is the only way in."""
    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    token = db.Column(
        db.String(64), unique=True, nullable=False, index=True,
        default=lambda: secrets.token_urlsafe(24),
    )
    client_name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True))
    created_by = db.Column(db.String(80))

    submissions = db.relationship("Submission", back_populates="invite")

    @property
    def status(self):
        if self.revoked_at is not None:
            return "revoked"
        if aware(self.expires_at) <= utcnow():
            return "expired"
        return "active"

    @property
    def is_active(self):
        return self.status == "active"


class Submission(db.Model):
    # db.Uuid maps to native UUID on Postgres (and works on SQLite for tests)
    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    client_name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(200))  # no longer collected; kept for older submissions
    consent_given = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    status = db.Column(db.String(20), default="new", nullable=False)  # new / reviewed / archived
    invite_id = db.Column(
        db.Uuid, db.ForeignKey("invite.id", ondelete="SET NULL"), index=True,
    )

    invite = db.relationship("Invite", back_populates="submissions")

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
