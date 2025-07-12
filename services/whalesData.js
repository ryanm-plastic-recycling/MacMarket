import axios from 'axios';

export async function fetchWhaleMoves({ limit = 5 } = {}) {
  const key = process.env.QUIVER_API_KEY;
  const headers = key ? { Authorization: `Bearer ${key}` } : {};
  try {
    const res = await axios.get('https://api.quiverquant.com/beta/live/whalemoves', { headers });
    const data = Array.isArray(res.data) ? res.data : [];
    return data.slice(0, limit);
  } catch (err) {
    console.error('fetchWhaleMoves error', err.message);
    return [];
  }
}

