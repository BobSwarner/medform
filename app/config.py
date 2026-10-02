import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")  # postgresql+psycopg://user:pass@host/db
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    MAX_CONTENT_LENGTH = 64 * 1024  # a full form is a few KB; reject anything large
    MAX_MEDICATIONS = 25
    MAX_DOCTORS = 10
    MAX_PHARMACIES = 5

    # Cookies are only ever sent over HTTPS (Cloudflare terminates TLS in front of nginx)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 2  # give slow form-fillers two hours


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-only"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
