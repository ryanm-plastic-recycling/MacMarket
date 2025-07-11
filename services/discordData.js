import { Client, GatewayIntentBits } from 'discord.js';

export async function fetchDiscord(channels = []) {
  const token = process.env.DISCORD_BOT_TOKEN;
  const ids = (channels.length ? channels : (process.env.DISCORD_CHANNEL_IDS || '').split(','))
    .map(id => id.trim())
    .filter(Boolean);

  if (!token || !ids.length) return [];

  const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages] });
  await client.login(token);

  const all = [];
  for (const id of ids) {
    try {
      const channel = await client.channels.fetch(id);
      const messages = await channel.messages.fetch({ limit: 100 });
      messages.forEach(m => {
        all.push({
          id: m.id,
          timestamp: m.createdTimestamp,
          author: m.author.username,
          content: m.content
        });
      });
    } catch (err) {
      console.error('Discord fetch error for channel', id, err.message);
    }
  }

  await client.destroy();
  return all;
}
