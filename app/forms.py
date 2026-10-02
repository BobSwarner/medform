from flask import current_app
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, FieldList, Form, FormField, PasswordField, SelectField, StringField,
)
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from .models import FREQUENCY_CHOICES


class MedicationForm(Form):
    """One medication row. Plain Form (not FlaskForm) so the row has no CSRF field of its own."""

    name = StringField(
        "Medication name",
        validators=[DataRequired(), Length(max=200)],
        description="Enter the name exactly as it appears on the bottle or pharmacy label.",
    )
    dosage = StringField(
        "Dosage / strength",
        validators=[DataRequired(), Length(max=100)],
        description="Example: 10 mg, 500 mg, 2 puffs.",
    )
    frequency = SelectField(
        "How often do you take it?",
        choices=[("", "Select...")] + FREQUENCY_CHOICES,
        validators=[DataRequired()],
    )
    frequency_other = StringField(
        "If “Other,” please explain", validators=[Optional(), Length(max=200)]
    )
    def validate(self, extra_validators=None):
        # Checked here rather than as validate_frequency_other: the Optional() validator
        # stops the field's chain when it's blank, so an inline validator would never run.
        ok = super().validate(extra_validators)
        if self.frequency.data == "other" and not (self.frequency_other.data or "").strip():
            self.frequency_other.errors = [*self.frequency_other.errors,
                                           "Please describe how often you take it."]
            ok = False
        return ok


class DoctorForm(Form):
    name = StringField("Doctor’s name", validators=[DataRequired(), Length(max=200)])
    specialty = StringField(
        "Specialty",
        validators=[Optional(), Length(max=100)],
        description="Example: primary care, cardiology, endocrinology.",
    )
    phone = StringField("Doctor’s phone number", validators=[Optional(), Length(max=30)])


class PharmacyForm(Form):
    name = StringField(
        "Pharmacy name and location",
        validators=[Optional(), Length(max=200)],
        description="Example: CVS, Main Street, Springfield.",
    )


class SubmissionForm(FlaskForm):
    client_name = StringField("Full name", validators=[DataRequired(), Length(max=200)])
    consent = BooleanField(
        "I understand this information will be used to review my coverage options.",
        validators=[DataRequired(message="Please confirm to continue.")],
    )
    medications = FieldList(FormField(MedicationForm), min_entries=1)
    doctors = FieldList(FormField(DoctorForm), min_entries=1)
    pharmacies = FieldList(FormField(PharmacyForm), min_entries=1)

    def validate_medications(self, field):
        if len(field.entries) > current_app.config["MAX_MEDICATIONS"]:
            raise ValidationError("Too many medications in one form.")

    def validate_doctors(self, field):
        if len(field.entries) > current_app.config["MAX_DOCTORS"]:
            raise ValidationError("Too many doctors in one form.")

    def validate_pharmacies(self, field):
        if len(field.entries) > current_app.config["MAX_PHARMACIES"]:
            raise ValidationError("Too many pharmacies in one form.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=200)])


class InviteForm(FlaskForm):
    client_name = StringField("Client’s full name", validators=[DataRequired(), Length(max=200)])
