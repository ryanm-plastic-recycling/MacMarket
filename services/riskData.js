import axios from 'axios';

export async function fetchRiskScores(symbols) {
  const tickers = symbols || process.env.MARKET_SYMBOLS || 'AAPL,MSFT,GOOGL,AMZN,TSLA';
  const key = process.env.QUIVER_API_KEY;
  const headers = key ? { Authorization: `Bearer ${key}` } : {};
  try {
    const res = await axios.get('https://api.quiverquant.com/beta/live/riskfactors', {
      headers,
      params: { tickers }
    });
    const data = Array.isArray(res.data) ? res.data : [];
    return data.map(item => ({
      ticker: item.Ticker || item.ticker,
      score: parseFloat(item.RiskScore || item.Score)
    }));
  } catch (err) {
    console.error('fetchRiskScores error', err.message);
    return [];
  }
}

