from flask import Blueprint, current_app, redirect, render_template, url_for

from ..extensions import db
from ..forms import DoctorForm, MedicationForm, PharmacyForm, SubmissionForm
from ..models import Doctor, Medication, Pharmacy, Submission

bp = Blueprint("public", __name__)


def _clean(value):
    value = (value or "").strip()
    return value or None


@bp.route("/", methods=["GET", "POST"])
def form():
    form = SubmissionForm()
    if not form.validate_on_submit():
        return render_template(
            "form.html", form=form,
            max_meds=current_app.config["MAX_MEDICATIONS"],
            max_doctors=current_app.config["MAX_DOCTORS"],
            max_pharmacies=current_app.config["MAX_PHARMACIES"],
            # Unbound rows for the <template> elements that form.js clones
            blank_med=MedicationForm(prefix="medications-__i__-"),
            blank_doc=DoctorForm(prefix="doctors-__i__-"),
            blank_pharm=PharmacyForm(prefix="pharmacies-__i__-"),
        )

    submission = Submission(
        client_name=form.client_name.data.strip(),
        contact=form.contact.data.strip(),
        consent_given=True,
    )

    # Pharmacies are optional: blank rows are dropped rather than rejected.
    names = [n for n in (_clean(e.form.name.data) for e in form.pharmacies.entries) if n]
    for pos, name in enumerate(names):
        submission.pharmacies.append(Pharmacy(position=pos, name=name))

    for pos, entry in enumerate(form.doctors.entries):
        submission.doctors.append(Doctor(
            position=pos,
            name=entry.form.name.data.strip(),
            specialty=_clean(entry.form.specialty.data),
            phone=_clean(entry.form.phone.data),
        ))

    for pos, entry in enumerate(form.medications.entries):
        f = entry.form
        submission.medications.append(Medication(
            position=pos,
            name=f.name.data.strip(),
            dosage=f.dosage.data.strip(),
            frequency=f.frequency.data,
            frequency_other=_clean(f.frequency_other.data) if f.frequency.data == "other" else None,
        ))

    # One transaction: the submission and all its rows are saved together or not at all.
    db.session.add(submission)
    db.session.commit()

    # Redirect so a browser refresh can't resubmit, and don't echo any data back.
    return redirect(url_for("public.thanks"))


@bp.route("/thanks")
def thanks():
    return render_template("thanks.html")
