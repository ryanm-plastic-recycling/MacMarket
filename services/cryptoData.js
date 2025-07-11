import axios from 'axios';

export async function fetchCrypto() {
  const endpoint = process.env.COINGECKO_ENDPOINT || 'https://api.coingecko.com/api/v3';
  const url = `${endpoint}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=5&page=1&sparkline=false`;
  const res = await axios.get(url);
  const coins = Array.isArray(res.data) ? res.data : [];
  const now = Date.now();
  return coins.map(c => ({
    timestamp: now,
    symbol: c.symbol.toUpperCase(),
    value: c.current_price,
    metrics: { change_24h: c.price_change_percentage_24h }
  }));
}
