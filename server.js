import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import 'dotenv/config';
import { fetchTickerData } from './services/marketData.js';
import { fetchAlerts } from './services/alertData.js';
import { fetchPolitical } from './services/politicalData.js';
import { fetchRiskScores } from './services/riskData.js';
import { fetchWhaleMoves } from './services/whalesData.js';
import { fetchNews } from './services/newsData.js';
import { runBacktest } from './backtest/strategyEngine.js';
import { query as dbQuery } from './db/index.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());

app.get('/api/panorama', async (req, res) => {
  try {
    const [market, alerts, political, risk, whales, news] = await Promise.all([
      fetchTickerData(req.query.symbols),
      fetchAlerts(),
      fetchPolitical(),
      fetchRiskScores(req.query.symbols),
      fetchWhaleMoves({ limit: 5 }),
      fetchNews()
    ]);
    res.json({ market, alerts, political, risk, whales, news });
  } catch (err) {
    console.error('panorama error', err);
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/backtest', express.json(), async (req, res) => {
  try {
    const result = await runBacktest(req.body.panorama, req.body.params);
    res.json(result);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

// List saved scenarios
app.get('/api/scenarios', async (req, res) => {
  try {
    const [rows] = await dbQuery(
      'SELECT id, name, strategy_key, params, created_at FROM scenarios ORDER BY created_at DESC'
    );
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

// Create a new scenario
app.post('/api/scenarios', express.json(), async (req, res) => {
  try {
    const { name, strategy_key, params } = req.body;
    const [result] = await dbQuery(
      'INSERT INTO scenarios (name, strategy_key, params) VALUES (?, ?, ?)',
      [name, strategy_key, JSON.stringify(params)]
    );
    res.json({ id: result.insertId, name, strategy_key, params });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

app.use(express.static(path.join(__dirname, 'frontend', 'build')));
app.get('*', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'frontend', 'build', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
