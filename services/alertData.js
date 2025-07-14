import axios from 'axios';

export async function fetchAlerts(limit = 5) {
  const key = process.env.WHALES_API_KEY;
  const headers = key ? { Authorization: `Bearer ${key}` } : {};
  try {
    const res = await axios.get('https://api.unusualwhales.com/alerts', { headers });
    const data = res.data?.results || res.data;
    return Array.isArray(data) ? data.slice(0, limit) : [];
  } catch (err) {
    console.error('fetchAlerts error', err.message);
    return [];
  }
}

