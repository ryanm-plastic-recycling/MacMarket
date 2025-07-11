import express from 'express';
import cors from 'cors';
import 'dotenv/config';
import { fetchMarket } from './services/marketData.js';
import { fetchPolitical } from './services/politicalData.js';
import { fetchNews } from './services/newsData.js';
import { fetchCrypto } from './services/cryptoData.js';
import { fetchMacro } from './services/macroData.js';
import { runBacktest } from './backtest/strategyEngine.js';
import { fetchDiscord } from './services/discordData.js';
import { validateMessages } from './services/validateDiscussion.js';
import { query as dbQuery } from './db/index.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());

app.get('/api/panorama', async (req, res) => {
  try {
    const [market, political, news, crypto, macro, discord] = await Promise.all([
      fetchMarket(),
      fetchPolitical(),
      fetchNews(),
      fetchCrypto(),
      fetchMacro(),
      fetchDiscord((process.env.DISCORD_CHANNEL_IDS || '').split(','))
    ]);
    const validated = await validateMessages(discord);
    res.json({ market, political, news, crypto, macro, discord, validated });
  } catch (err) {
    console.error(err);
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

app.use(express.static('frontend'));

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
