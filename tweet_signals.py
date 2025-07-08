import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import tweepy

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
TWITTER_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")


def fetch_latest_buy(ticker: str) -> dict | None:
    """Fetch the latest insider buy for the ticker."""
    try:
        url = f"{API_BASE}/api/signals/congress-buys"
        resp = requests.get(url, params={"symbol": ticker}, timeout=10)
        if resp.ok:
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict):
                return data.get("data", [None])[0]
    except Exception:
        pass
    return None


def fetch_price_history(ticker: str, period: str = "1mo") -> pd.DataFrame:
    """Return dataframe of historical prices using backend API."""
    url = f"{API_BASE}/api/history"
    resp = requests.get(url, params={"symbol": ticker, "period": period}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    dates = pd.to_datetime(data.get("dates", []))
    close = data.get("close", [])
    return pd.DataFrame({"Date": dates, "Close": close})


def plot_price(df: pd.DataFrame, output: str = "chart.png") -> None:
    """Plot closing price vs time and save to PNG."""
    plt.figure(figsize=(8, 4))
    plt.plot(df["Date"], df["Close"], label="Close")
    plt.xlabel("Date")
    plt.ylabel("Price")
    plt.title("Price History")
    plt.tight_layout()
    plt.savefig(output)
    plt.close()


def tweet_update(ticker: str, pct_change: float, image_path: str) -> None:
    """Tweet message with attached image."""
    auth = tweepy.OAuth1UserHandler(
        TWITTER_KEY,
        TWITTER_SECRET,
        TWITTER_TOKEN,
        TWITTER_TOKEN_SECRET,
    )
    api = tweepy.API(auth)
    status = f"Insider buying in ${ticker} up {pct_change:.2f}% since alert 🚀"
    api.update_status_with_media(status=status, filename=image_path)


def main(ticker: str) -> None:
    buy = fetch_latest_buy(ticker)
    if not buy:
        print("No insider buy found")
        return
    alert_price = float(buy.get("price") or 0)
    df = fetch_price_history(ticker)
    if df.empty or alert_price == 0:
        print("Insufficient data")
        return
    current = df["Close"].iloc[-1]
    pct_change = (current - alert_price) / alert_price * 100
    plot_price(df)
    tweet_update(ticker, pct_change, "chart.png")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python tweet_signals.py TICKER")
        sys.exit(1)
    main(sys.argv[1].upper())
