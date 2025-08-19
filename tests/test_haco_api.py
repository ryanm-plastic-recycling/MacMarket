from fastapi.testclient import TestClient

from app import app
import api.haco as haco


client = TestClient(app)


def test_haco_endpoint(monkeypatch):
    def fake_build(symbol, timeframe, len_up, len_dn, lookback, show_ha):
        assert symbol == "AAPL"
        assert timeframe == "Day"
        assert len_up == 3
        assert len_dn == 4
        assert lookback == 200
        assert show_ha is True
        return {
            "series": [
                {
                    "time": 1,
                    "o": 1,
                    "h": 1,
                    "l": 1,
                    "c": 1,
                    "state": True,
                    "upw": False,
                    "dnw": False,
                    "ZlHaU": None,
                    "ZlClU": None,
                    "ZlHaD": None,
                    "ZlClD": None,
                }
            ],
            "last": {"state": True, "upw": False, "dnw": False, "reasons": "HA up"},
        }

    monkeypatch.setattr(haco, "_build_series", fake_build)

    resp = client.get(
        "/api/signals/haco?symbol=AAPL&timeframe=Day&lengthUp=3&lengthDown=4&lookback=200&showHa=true"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "series" in data and "last" in data
    assert data["series"][0]["time"] == 1


def test_haco_scan(monkeypatch):
    def fake_build(symbol, timeframe, len_up, len_dn, lookback, show_ha):
        if symbol == "AAPL":
            series = [
                {"state": False, "upw": False, "dnw": False},
                {"state": True, "upw": True, "dnw": False},
            ]
            last = {"state": True, "upw": True, "dnw": False, "reasons": "HA up"}
        else:
            series = [
                {"state": True, "upw": False, "dnw": False},
                {"state": True, "upw": False, "dnw": False},
            ]
            last = {"state": True, "upw": False, "dnw": False, "reasons": "HA up"}
        return {"series": series, "last": last}

    monkeypatch.setattr(haco, "_build_series", fake_build)

    resp = client.get("/api/signals/haco/scan?symbols=AAPL,MSFT")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    aapl = next(item for item in data if item["symbol"] == "AAPL")
    msft = next(item for item in data if item["symbol"] == "MSFT")
    assert aapl["changed"] is True
    assert msft["changed"] is False
    assert aapl["upw"] is True
    assert msft["upw"] is False

