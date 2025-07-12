from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_panorama(monkeypatch):
    monkeypatch.setattr('app.ticker_data', lambda symbols: {"data": [
        {"symbol": "AAPL", "price": 1, "change_percent": 0.1}
    ]})

    async def dummy_fetch(limit=5):
        return [{"id": 1}]
    async def dummy_political():
        return {"quiver": [], "whales": [], "capitol": []}
    async def dummy_quiver_risk(symbols):
        return {"risk": {"AAPL": 0.2}}
    async def dummy_quiver_whales(limit=5):
        return {"whales": [{"ticker": "AAPL"}]}
    monkeypatch.setattr('app.fetch_unusual_whales', dummy_fetch)
    monkeypatch.setattr('app.political', dummy_political)
    monkeypatch.setattr('app.quiver_risk', dummy_quiver_risk)
    monkeypatch.setattr('app.quiver_whales', dummy_quiver_whales)
    monkeypatch.setattr('app.news', lambda age='week': {"market": [], "world": []})

    resp = client.get('/api/panorama')
    assert resp.status_code == 200
    data = resp.json()
    assert 'market' in data
    assert 'alerts' in data
    assert 'political' in data
    assert 'risk' in data
    assert 'whales' in data
    assert 'news' in data
