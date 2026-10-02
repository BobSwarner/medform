import click

from .extensions import db
from .models import AdminUser


def register_cli(app):
    @app.cli.command("create-admin")
    @click.argument("username")
    @click.password_option(prompt="Password", confirmation_prompt=True)
    def create_admin(username, password):
        """Create an admin user, or reset the password of an existing one."""
        if len(password) < 12:
            raise click.ClickException("Password must be at least 12 characters.")
        user = db.session.scalar(db.select(AdminUser).filter_by(username=username))
        if user is None:
            user = AdminUser(username=username)
            db.session.add(user)
        user.set_password(password)
        user.failed_logins = 0
        user.locked_until = None
        db.session.commit()
        click.echo(f"Admin '{username}' saved.")
