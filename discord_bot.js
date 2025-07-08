const { Client, GatewayIntentBits, ChannelType } = require('discord.js');
const fetch = require('node-fetch'); // Node 20 has fetch; we'll use node-fetch for broad compatibility

const TOKEN = process.env.TOKEN;
const ALERT_API = process.env.ALERT_API || 'http://localhost:9500/api/signals/alert';
const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://localhost:9500/index.html';

if (!TOKEN) {
  console.error('TOKEN environment variable not set');
  process.exit(1);
}

const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages] });
let lastId = null;

client.once('ready', () => {
  console.log(`Logged in as ${client.user.tag}`);
  poll();
  setInterval(poll, 30000);
});

async function poll() {
  try {
    const res = await fetch(ALERT_API);
    if (!res.ok) return;
    const data = await res.json();
    if (!data || data.id === undefined) return;
    if (lastId === data.id) return;
    lastId = data.id;
    const channel = client.channels.cache.find(c => c.name === 'alerts' && c.type === ChannelType.GuildText);
    if (!channel) {
      console.warn('Alerts channel not found');
      return;
    }
    const priceStr = data.price < 1 ? data.price.toFixed(5) : data.price.toFixed(2);
    const msg = `🚨 New Signal: $${data.ticker} – insider buy detected at ${priceStr} ${DASHBOARD_URL}`;
    channel.send(msg);
  } catch (err) {
    console.error('Error fetching alert', err);
  }
}

client.login(TOKEN);
