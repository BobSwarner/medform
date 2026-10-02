from zoneinfo import ZoneInfo

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import csrf, db, login_manager, migrate


def create_app(config_object="app.config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)
    for key in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI"):
        if not app.config.get(key):
            raise RuntimeError(f"{key} is not set (see .env.example)")

    # Behind Caddy, which strips /medform and sends X-Forwarded-Prefix/Proto/Host
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    from . import models
    from .public.routes import bp as public_bp
    from .admin.routes import bp as admin_bp
    from .cli import register_cli
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    register_cli(app)

    @login_manager.user_loader
    def load_admin(user_id):
        return db.session.get(models.AdminUser, int(user_id))

    @app.template_filter("localtime")
    def localtime(dt, fmt="%b %d, %Y %I:%M %p %Z"):
        if dt is None:
            return ""
        return models.aware(dt).astimezone(ZoneInfo(app.config["DISPLAY_TZ"])).strftime(fmt)

    @app.after_request
    def security_headers(resp):
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"  # CSRF over HTTPS needs a Referer on our own POSTs; nothing is sent cross-site
        resp.headers["Cache-Control"] = "no-store"  # don't cache pages holding health data
        return resp

    return app
