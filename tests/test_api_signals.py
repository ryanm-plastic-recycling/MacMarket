from fastapi.testclient import TestClient
import app as app_module

client = TestClient(app_module.app)

def test_signals_endpoint_swing():
    r = client.get("/api/signals/SPY?mode=swing")
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "SPY"
    assert data["mode"] == "swing"
    assert "panels" in data and isinstance(data["panels"], list)
    assert "chart" in data and "candles" in data["chart"]
    # epoch seconds check
    candles = data["chart"]["candles"]
    assert candles and isinstance(candles[0]["time"], int)

def test_signals_endpoint_day():
    r = client.get("/api/signals/SPY?mode=day")
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "day"
