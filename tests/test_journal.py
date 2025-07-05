from fastapi.testclient import TestClient
from app import app, get_db

client = TestClient(app)


def test_journal_endpoints(monkeypatch):
    # patch db dependency with in-memory SQLite
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.app import models, crud
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    models.Base.metadata.create_all(bind=engine)

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db

    # create user directly via crud
    db = next(override_db())
    user = crud.create_user(db, "u1", "pw")
    db.close()

    entry = {
        "symbol": "AAPL",
        "action": "buy",
        "quantity": 1,
        "price": 10.0,
        "rationale": "test",
    }
    resp = client.post(f"/api/users/{user.id}/journal", json=entry)
    assert resp.status_code == 200
    resp = client.get(f"/api/users/{user.id}/journal")
    assert resp.status_code == 200
    assert resp.json()[0]["symbol"] == "AAPL"


def test_signal_endpoint(monkeypatch):
    monkeypatch.setattr("backend.app.signals.news_sentiment_signal", lambda s: {"score": 1})
    monkeypatch.setattr("backend.app.signals.technical_indicator_signal", lambda s: {"signal": "bullish"})
    resp = client.get("/api/signals/TEST")
    assert resp.status_code == 200
    assert resp.json()["news"]["score"] == 1
    assert resp.json()["technical"]["signal"] == "bullish"
