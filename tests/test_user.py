from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import app, get_db
from backend.app import models
import os


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models.Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_module(module):
    os.environ["RECAPTCHA_SECRET"] = "test"

def test_login_and_tickers(monkeypatch):
    monkeypatch.setattr("backend.app.security.verify_recaptcha", lambda token: True)
    class DummyTOTP:
        def verify(self, otp):
            return True

    monkeypatch.setattr("pyotp.TOTP", lambda secret: DummyTOTP())
    client.post(
        "/api/register",
        json={"username": "demo", "password": "pass", "captcha_token": "x"},
    )
    resp = client.post(
        "/api/login",
        json={"username": "demo", "password": "pass", "captcha_token": "x", "otp": "123456"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is False
    user_id = resp.json()["user_id"]

    resp = client.put(f"/api/users/{user_id}/tickers", json={"tickers": ["AAPL", "MSFT"]})
    assert resp.status_code == 200

    resp = client.get(f"/api/users/{user_id}/tickers")
    assert resp.status_code == 200
    assert resp.json()["tickers"] == ["AAPL", "MSFT"]


def test_update_password(monkeypatch):
    monkeypatch.setattr("backend.app.security.verify_recaptcha", lambda token: True)
    class DummyTOTP:
        def verify(self, otp):
            return True

    monkeypatch.setattr("pyotp.TOTP", lambda secret: DummyTOTP())
    client.post(
        "/api/register",
        json={"username": "demo2", "password": "old", "captcha_token": "x"},
    )
    resp = client.post(
        "/api/login",
        json={"username": "demo2", "password": "old", "captcha_token": "x", "otp": "123"},
    )
    assert resp.status_code == 200
    uid = resp.json()["user_id"]
    resp = client.put(f"/api/admin/users/{uid}/password", json={"password": "new"})
    assert resp.status_code == 200
    resp = client.post(
        "/api/login",
        json={"username": "demo2", "password": "new", "captcha_token": "x", "otp": "123"},
    )
    assert resp.status_code == 200

def test_update_email(monkeypatch):
    monkeypatch.setattr("backend.app.security.verify_recaptcha", lambda token: True)
    class DummyTOTP:
        def verify(self, otp):
            return True

    monkeypatch.setattr("pyotp.TOTP", lambda secret: DummyTOTP())
    client.post(
        "/api/register",
        json={"username": "demo3", "password": "pass", "captcha_token": "x"},
    )
    resp = client.post(
        "/api/login",
        json={"username": "demo3", "password": "pass", "captcha_token": "x", "otp": "000"},
    )
    assert resp.status_code == 200
    uid = resp.json()["user_id"]
    resp = client.put(f"/api/users/{uid}/email", json={"email": "user@example.com"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@example.com"


def test_enable_otp_and_username_change(monkeypatch):
    monkeypatch.setattr("backend.app.security.verify_recaptcha", lambda token: True)

    class DummyTOTP:
        def verify(self, otp):
            return otp == "000000"

    monkeypatch.setattr("pyotp.TOTP", lambda secret: DummyTOTP())

    client.post(
        "/api/register",
        json={"username": "demo5", "password": "pass", "captcha_token": "x"},
    )
    resp = client.post(
        "/api/login",
        json={"username": "demo5", "password": "pass", "captcha_token": "x"},
    )
    uid = resp.json()["user_id"]

    resp = client.put(f"/api/users/{uid}/otp", json={"otp_enabled": True})
    assert resp.status_code == 200

    resp = client.post(
        "/api/login",
        json={"username": "demo5", "password": "pass", "captcha_token": "x", "otp": "000000"},
    )
    assert resp.status_code == 200

    resp = client.put(f"/api/users/{uid}/username", json={"username": "demo6"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "demo6"


def test_login_security_disabled(monkeypatch):
    os.environ["DISABLE_CAPTCHA"] = "1"
    os.environ["DISABLE_OTP"] = "1"

    monkeypatch.setattr("backend.app.security.verify_recaptcha", lambda token: True)
    client.post(
        "/api/register",
        json={"username": "demo4", "password": "pass", "captcha_token": "x"},
    )

    def recaptcha_unused(token):
        raise AssertionError("recaptcha should not be checked")

    def otp_unused(secret):
        raise AssertionError("otp should not be checked")

    monkeypatch.setattr("backend.app.security.verify_recaptcha", recaptcha_unused)
    monkeypatch.setattr("pyotp.TOTP", otp_unused)

    resp = client.post(
        "/api/login",
        json={"username": "demo4", "password": "pass"},
    )
    assert resp.status_code == 200


def test_login_db_failure(monkeypatch):
    """Ensure database errors during login return 503."""
    from sqlalchemy.exc import SQLAlchemyError

    monkeypatch.setattr("backend.app.security.verify_recaptcha", lambda token: True)

    def failing_auth(db, username, password):
        raise SQLAlchemyError("db down")

    monkeypatch.setattr("app.crud.authenticate_user", failing_auth)

    resp = client.post(
        "/api/login",
        json={"username": "x", "password": "y", "captcha_token": "t"},
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Database unavailable"


def test_admin_manage_user_fields(monkeypatch):
    monkeypatch.setattr("backend.app.security.verify_recaptcha", lambda token: True)

    class DummyTOTP:
        def verify(self, otp):
            return True

    monkeypatch.setattr("pyotp.TOTP", lambda secret: DummyTOTP())

    client.post(
        "/api/register",
        json={"username": "admintest", "password": "pass", "captcha_token": "x"},
    )
    resp = client.post(
        "/api/login",
        json={"username": "admintest", "password": "pass", "captcha_token": "x", "otp": "000"},
    )
    uid = resp.json()["user_id"]
    # admin modify fields
    resp = client.put(f"/api/admin/users/{uid}/username", json={"username": "changed"})
    assert resp.status_code == 200
    resp = client.put(f"/api/admin/users/{uid}/email", json={"email": "u@e.com"})
    assert resp.status_code == 200
    resp = client.put(f"/api/admin/users/{uid}/otp", json={"otp_enabled": True})
    assert resp.status_code == 200
    users = client.get("/api/admin/users").json()["users"]
    user = [u for u in users if u["id"] == uid][0]
    assert user["username"] == "changed"
    assert user["email"] == "u@e.com"
    assert user["otp_enabled"] is True
    assert user["last_logged_in"] is not None

