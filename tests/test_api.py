from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_db_check_success(monkeypatch):
    class DummyConn:
        def close(self):
            pass

    def dummy_connect():
        return DummyConn()

    monkeypatch.setattr("backend.app.database.connect_to_db", dummy_connect)
    response = client.get("/db-check")
    assert response.status_code == 200
    assert response.json() == {"status": "connected"}


def test_history_endpoint(monkeypatch):
    class DummyTicker:
        def history(self, period="1mo", interval="1d"):
            import pandas as pd
            return pd.DataFrame({"Close": [1.0, 2.0]}, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))

    monkeypatch.setattr("app.yf.Ticker", lambda symbol: DummyTicker())
    response = client.get("/api/history?symbol=SPY&period=1mo")
    assert response.status_code == 200
    assert response.json()["symbol"] == "SPY"
    assert response.json()["close"] == [1.0, 2.0]
    assert response.json()["dates"] == ["2024-01-01", "2024-01-02"]


def test_risk_endpoint(monkeypatch):
    class DummyPos:
        quantity = 10
        price = 2

    monkeypatch.setattr("app.risk.get_positions", lambda db, uid: [DummyPos()])
    monkeypatch.setattr("app.risk.llm_suggestion", lambda summary: "test")
    response = client.get("/api/users/1/risk")
    assert response.status_code == 200
    assert response.json()["exposure"] == 20.0
    assert response.json()["suggestion"] == "test"
