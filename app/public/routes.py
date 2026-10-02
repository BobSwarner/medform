from flask import Blueprint, abort, current_app, redirect, render_template, url_for

from ..extensions import db
from ..forms import DoctorForm, MedicationForm, PharmacyForm, SubmissionForm
from ..models import Doctor, Invite, Medication, Pharmacy, Submission

bp = Blueprint("public", __name__)


def _clean(value):
    value = (value or "").strip()
    return value or None


def _active_invite_or_404(token):
    """The form is only reachable through a valid private link; anything else is a plain 404."""
    invite = db.session.scalar(db.select(Invite).filter_by(token=token))
    if invite is None or not invite.is_active:
        abort(404)
    return invite


@bp.route("/f/<token>", methods=["GET", "POST"])
def form(token):
    invite = _active_invite_or_404(token)
    form = SubmissionForm(data={"client_name": invite.client_name})
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
        consent_given=True,
        invite=invite,
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
    return redirect(url_for("public.thanks", token=token))


@bp.route("/f/<token>/thanks")
def thanks(token):
    _active_invite_or_404(token)
    return render_template("thanks.html")
