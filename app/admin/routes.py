from datetime import timedelta

from flask import (
    Blueprint, current_app, flash, redirect, render_template, session, url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..forms import InviteForm, LoginForm
from ..models import FREQUENCY_LABELS, AdminUser, Invite, Submission, utcnow

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Checked when the username doesn't exist, so response time doesn't reveal valid usernames.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.submissions"))
    form = LoginForm()
    if form.validate_on_submit():
        now = utcnow()
        user = db.session.scalar(
            db.select(AdminUser).filter_by(username=form.username.data.strip())
        )
        if user is None:
            check_password_hash(_DUMMY_HASH, form.password.data)
        elif not user.is_locked(now) and user.check_password(form.password.data):
            user.failed_logins = 0
            user.locked_until = None
            db.session.commit()
            session.clear()
            session.permanent = True
            login_user(user)
            return redirect(url_for("admin.submissions"))
        elif not user.is_locked(now):
            user.failed_logins += 1
            if user.failed_logins >= current_app.config["LOGIN_MAX_FAILURES"]:
                user.failed_logins = 0
                user.locked_until = now + timedelta(
                    minutes=current_app.config["LOGIN_LOCKOUT_MINUTES"]
                )
            db.session.commit()
        # Same message for wrong password, unknown user and locked account.
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("admin.login"))


@bp.route("/")
@login_required
def submissions():
    rows = db.session.scalars(
        db.select(Submission).order_by(Submission.created_at.desc()).limit(500)
    ).all()
    return render_template("admin/submissions.html", submissions=rows)


@bp.route("/submissions/<uuid:submission_id>")
@login_required
def submission_detail(submission_id):
    sub = db.get_or_404(Submission, submission_id)
    return render_template(
        "admin/detail.html", sub=sub, frequency_labels=FREQUENCY_LABELS,
    )


@bp.route("/links", methods=["GET", "POST"])
@login_required
def links():
    form = InviteForm()
    if form.validate_on_submit():
        invite = Invite(
            client_name=form.client_name.data.strip(),
            expires_at=utcnow() + timedelta(days=current_app.config["INVITE_DAYS"]),
            created_by=current_user.username,
        )
        db.session.add(invite)
        db.session.commit()
        flash(f"Link created for {invite.client_name}.", "ok")
        return redirect(url_for("admin.links"))
    invites = db.session.scalars(
        db.select(Invite).order_by(Invite.created_at.desc()).limit(500)
    ).all()
    return render_template("admin/links.html", form=form, invites=invites)


@bp.route("/links/<uuid:invite_id>/revoke", methods=["POST"])
@login_required
def revoke_link(invite_id):
    invite = db.get_or_404(Invite, invite_id)
    if invite.revoked_at is None:
        invite.revoked_at = utcnow()
        db.session.commit()
        flash(f"Link for {invite.client_name} revoked.", "ok")
    return redirect(url_for("admin.links"))
