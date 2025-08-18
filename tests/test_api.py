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


def test_positions_endpoint(monkeypatch):
    class DummyPos:
        symbol = "AAPL"
        quantity = 5
        price = 10

    monkeypatch.setattr("app.risk.get_positions", lambda db, uid: [DummyPos()])
    response = client.get("/api/users/1/positions")
    assert response.status_code == 200
    data = response.json()["positions"][0]
    assert data["symbol"] == "AAPL"
    assert data["quantity"] == 5
    assert data["price"] == 10


def test_recommendations_endpoint(monkeypatch):
    monkeypatch.setattr(
        "app.crud.get_tickers", lambda db, uid: []
    )
    monkeypatch.setattr(
        "app.signals.generate_recommendations",
        lambda symbols: [
            {
                "symbol": "AAPL",
                "action": "buy",
                "entry_date": "2024-01-01",
                "entry_price": 100,
                "exit_date": "2024-01-10",
                "exit_price": 105,
                "probability": 0.6,
                "reason": "test",
            }
        ],
    )
    response = client.get("/api/users/1/recommendations")
    assert response.status_code == 200
    rec = response.json()["recommendations"][0]
    assert rec["symbol"] == "AAPL"
    assert rec["reason"] == "test"


def test_price_endpoint(monkeypatch):
    monkeypatch.setattr("app.fetch_latest_price", lambda s: 123.45)
    resp = client.get("/api/price/AAPL")
    assert resp.status_code == 200
    assert resp.json()["price"] == 123.45


def test_single_recommendation(monkeypatch):
    monkeypatch.setattr(
        "app.signals.generate_recommendations",
        lambda symbols: [
            {
                "symbol": symbols[0],
                "action": "buy",
                "entry_date": "2024-01-01",
                "entry_price": 10,
                "exit_date": "2024-01-02",
                "exit_price": 11,
                "probability": 0.5,
                "reason": "r",
            }
        ],
    )
    resp = client.get("/api/recommendation/XYZ")
    assert resp.status_code == 200
    assert resp.json()["recommendation"]["symbol"] == "XYZ"


def test_logout_endpoint():
    response = client.post("/api/logout")
    assert response.status_code == 200
    assert response.json() == {"status": "logged out"}


def test_quiver_risk(monkeypatch):
    monkeypatch.setattr("app.signals.get_risk_factors", lambda syms: {"AAPL": 0.5})
    resp = client.get("/api/quiver/risk?symbols=AAPL")
    assert resp.status_code == 200
    assert resp.json()["risk"]["AAPL"] == 0.5


def test_quiver_whales(monkeypatch):
    monkeypatch.setattr("app.signals.get_whale_moves", lambda limit: [{"ticker": "AAPL"}])
    resp = client.get("/api/quiver/whales?limit=1")
    assert resp.status_code == 200
    assert resp.json()["whales"][0]["ticker"] == "AAPL"


def test_quiver_political(monkeypatch):
    monkeypatch.setattr("app.signals.get_political_moves", lambda syms: {"AAPL": 2})
    resp = client.get("/api/quiver/political?symbols=AAPL")
    assert resp.status_code == 200
    assert resp.json()["political"]["AAPL"] == 2


def test_quiver_lobby(monkeypatch):
    monkeypatch.setattr("app.signals.get_lobby_disclosures", lambda syms: {"AAPL": 3})
    resp = client.get("/api/quiver/lobby?symbols=AAPL")
    assert resp.status_code == 200
    assert resp.json()["lobby"]["AAPL"] == 3


def test_signal_rankings_json(monkeypatch):
    monkeypatch.setattr(
        "app.signals.generate_recommendations",
        lambda syms: [
            {
                "symbol": "A",
                "probability": 0.8,
                "action": "buy",
                "entry_date": "2024-01-01",
                "entry_price": 1,
                "exit_date": "2024-01-10",
                "exit_price": 1.1,
                "reason": "r",
            },
            {
                "symbol": "B",
                "probability": 0.5,
                "action": "buy",
                "entry_date": "2024-01-01",
                "entry_price": 1,
                "exit_date": "2024-01-10",
                "exit_price": 1.1,
                "reason": "r",
            },
        ],
    )
    resp = client.get("/api/signals/rankings")
    assert resp.status_code == 200
    data = resp.json()["rankings"]
    assert data[0]["symbol"] == "A"
    assert data[1]["symbol"] == "B"


def test_signal_rankings_csv(monkeypatch):
    monkeypatch.setattr(
        "app.signals.generate_recommendations",
        lambda syms: [
            {
                "symbol": "A",
                "probability": 0.7,
                "action": "buy",
                "entry_date": "2024-01-01",
                "entry_price": 1,
                "exit_date": "2024-01-10",
                "exit_price": 1.1,
                "reason": "r",
            },
            {
                "symbol": "B",
                "probability": 0.4,
                "action": "sell",
                "entry_date": "2024-01-01",
                "entry_price": 1,
                "exit_date": "2024-01-10",
                "exit_price": 1.1,
                "reason": "r",
            },
        ],
    )
    resp = client.get("/api/signals/rankings?format=csv")
    assert resp.status_code == 200
    lines = resp.text.strip().splitlines()
    assert lines[0] == "symbol,score"
    assert "A,0.7" in lines[1]


def test_strategy_endpoints(monkeypatch, tmp_path):
    hist_file = tmp_path / "hist.json"
    monkeypatch.setattr("macmarket.strategy_tester.HISTORY_FILE", hist_file)
    monkeypatch.setattr(
        "macmarket.strategy_tester.list_strategies", lambda: ["congress_long_short"]
    )
    monkeypatch.setattr(
        "macmarket.strategy_tester.run_strategy", lambda s: {"total_return": 0.1}
    )

    resp = client.get("/strategy-test/list")
    assert resp.status_code == 200
    assert resp.json() == ["congress_long_short"]

    resp = client.post(
        "/strategy-test/run",
        json={"strategy": "congress_long_short", "user_id": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["total_return"] == 0.1

    resp = client.get("/strategy-test/history?user_id=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "congress_long_short" in data

