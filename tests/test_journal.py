from fastapi.testclient import TestClient
from app import app, get_db

client = TestClient(app)


def test_journal_endpoints(monkeypatch):
    # patch db dependency with in-memory SQLite
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.app import models, crud
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
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
    entry_id = resp.json()["id"]
    resp = client.get(f"/api/users/{user.id}/journal")
    assert resp.status_code == 200
    assert resp.json()[0]["symbol"] == "AAPL"

    update = {"price": 12.0}
    resp = client.put(
        f"/api/users/{user.id}/journal/{entry_id}", json=update
    )
    assert resp.status_code == 200
    assert resp.json()["price"] == 12.0

    resp = client.delete(f"/api/users/{user.id}/journal/{entry_id}")
    assert resp.status_code == 200


def test_signal_endpoint(monkeypatch):
    class DummyResp:
        ok = True

        def json(self):
            return {"articles": [{"title": "good"}, {"title": "good"}]}

    monkeypatch.setattr(
        "backend.app.signals.requests.get",
        lambda *a, **k: DummyResp(),
    )

    class DummyAnalyzer:
        def polarity_scores(self, text):
            return {"compound": 0.5}

    monkeypatch.setattr(
        "backend.app.signals.SentimentIntensityAnalyzer",
        DummyAnalyzer,
    )
    monkeypatch.setattr(
        "backend.app.signals.technical_indicator_signal",
        lambda s: {"signal": "bullish"},
    )
    resp = client.get("/api/signals/TEST")
    assert resp.status_code == 200
    assert resp.json()["news"]["score"] == 1.0
    assert resp.json()["technical"]["signal"] == "bullish"
