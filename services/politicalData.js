import axios from 'axios';

export async function fetchPolitical() {
  const key = process.env.QUIVER_API_KEY;
  const headers = key ? { Authorization: `Bearer ${key}` } : {};
  const url = 'https://api.quiverquant.com/beta/live/congresstrading';
  const res = await axios.get(url, { headers });
  const data = Array.isArray(res.data) ? res.data.slice(0, 5) : [];
  return data.map(t => ({
    timestamp: t.TransactionDate,
    symbol: t.Ticker || t.ticker,
    metrics: t
  }));
}
