import axios from 'axios';

export async function fetchMacro() {
  const key = process.env.FRED_API_KEY;
  const url = `https://api.stlouisfed.org/fred/series/observations?series_id=PPIACO&api_key=${key}&file_type=json&sort_order=desc&limit=12`;
  const res = await axios.get(url);
  const obs = (res.data && res.data.observations) || [];
  return obs.map(o => ({
    timestamp: o.date,
    symbol: 'PPI',
    value: parseFloat(o.value)
  }));
}
