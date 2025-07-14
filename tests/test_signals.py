import backend.app.signals as signals


def test_generate_recommendations_quiver(monkeypatch):
    monkeypatch.setattr(signals, "news_sentiment_signal", lambda s: {"score": 1})
    monkeypatch.setattr(signals, "technical_indicator_signal", lambda s: {"signal": "bullish"})
    monkeypatch.setattr(signals, "get_risk_factors", lambda syms: {"AAPL": 0.2})
    monkeypatch.setattr(signals, "_current_price", lambda s: 100.0)
    monkeypatch.setattr(
        signals,
        "_calculate_exit",
        lambda sym, price, date: (date, price + 5),
    )
    monkeypatch.setattr(signals, "get_political_moves", lambda syms: {"AAPL": 1})
    monkeypatch.setattr(signals, "get_lobby_disclosures", lambda syms: {"AAPL": 2})
    recs = signals.generate_recommendations(["AAPL"])
    assert recs[0]["symbol"] == "AAPL"
    assert "political" in recs[0]["reason"]
    assert "lobby" in recs[0]["reason"]
    assert recs[0]["probability"] > 0.5
