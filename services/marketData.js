import axios from 'axios';

export async function fetchTickerData(symbols) {
  const list = symbols || process.env.MARKET_SYMBOLS || 'AAPL,MSFT,GOOGL,AMZN,TSLA';
  const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${list}`;
  const res = await axios.get(url);
  const results = (res.data && res.data.quoteResponse && res.data.quoteResponse.result) || [];
  const now = Date.now();
  return results.map(q => ({
    timestamp: now,
    symbol: q.symbol,
    value: q.regularMarketPrice,
    metrics: { change: q.regularMarketChangePercent }
  }));
}

// Backwards compatibility
export const fetchMarket = fetchTickerData;

