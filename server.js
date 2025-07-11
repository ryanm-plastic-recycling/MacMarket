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

app.use(express.static('frontend'));

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
