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
    assert resp.json()["user_id"] == uid

