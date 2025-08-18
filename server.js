import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import 'dotenv/config';
import mysql from 'mysql2/promise';
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

// MySQL pool for alerts
const pool = mysql.createPool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME,
  connectionLimit: 10
});

async function getUserId(req) {
  // TODO: replace with real auth user id
  return (req.user && req.user.id) ? req.user.id : 1;
}

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

// List tickers
app.get('/api/tickers', async (req, res) => {
  try {
    const [rows] = await dbQuery('SELECT id, symbol FROM tickers ORDER BY position');
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

// Update ticker order
app.put('/api/tickers/order', express.json(), async (req, res) => {
  try {
    const ids = req.body;
    for (let i = 0; i < ids.length; i++) {
      await dbQuery('UPDATE tickers SET position = ? WHERE id = ?', [i, ids[i]]);
    }
    res.json({ status: 'ok' });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

// Delete a ticker
app.delete('/api/tickers/:id', async (req, res) => {
  try {
    await dbQuery('DELETE FROM tickers WHERE id = ?', [req.params.id]);
    res.sendStatus(204);
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

// ALERTS ROUTES
app.get('/api/alerts/me', async (req, res) => {
  try {
    const userId = await getUserId(req);
    const [rows] = await pool.query(
      'SELECT email, sms, frequency, strategy FROM user_alert_settings WHERE user_id = ? LIMIT 1',
      [userId]
    );
    const base = rows[0] || { email: '', sms: '', frequency: '15m', strategy: 'HACO' };
    const [sym] = await pool.query(
      'SELECT symbol FROM user_alert_symbols WHERE user_id = ? ORDER BY symbol',
      [userId]
    );
    res.json({ ...base, symbols: sym.map(r => r.symbol) });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'server_error' });
  }
});

app.post('/api/alerts/me', express.json(), async (req, res) => {
  try {
    const userId = await getUserId(req);
    const { strategy = 'HACO', email = '', sms = '', frequency = '15m', symbols = [] } = req.body || {};

    await pool.query(
      `INSERT INTO user_alert_settings (user_id, email, sms, frequency, strategy)
       VALUES (?,?,?,?,?)
       ON DUPLICATE KEY UPDATE email=VALUES(email), sms=VALUES(sms), frequency=VALUES(frequency), strategy=VALUES(strategy)`,
      [userId, email, sms, frequency, strategy]
    );

    await pool.query('DELETE FROM user_alert_symbols WHERE user_id = ?', [userId]);
    if (Array.isArray(symbols) && symbols.length) {
      const vals = symbols.map(s => [userId, String(s).toUpperCase()]);
      await pool.query('INSERT INTO user_alert_symbols (user_id, symbol) VALUES ?', [vals]);
    }

    res.json({ ok: true });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'server_error' });
  }
});

app.post('/api/alerts/test', async (req, res) => {
  // no external calls; just confirm wiring
  res.json({ ok: true });
});

// OPTIONAL placeholder for future cron worker (disabled):
// import cron from 'node-cron';
// // TODO: enable in a later PR
// // cron.schedule('*/5 * * * *', () => { console.log('[alerts] tick'); });

// Serve the site from ./frontend
app.use(express.static(path.join(__dirname, 'frontend')));
// Back-compat for templates that request /static/*
app.use('/static', express.static(path.join(__dirname, 'frontend')));

app.use(express.static(path.join(__dirname, 'frontend', 'build')));
app.get('*', (req, res) => {
  res.sendFile(path.resolve(__dirname, 'frontend', 'build', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
