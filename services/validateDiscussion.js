import OpenAI from 'openai';

const apiKey = process.env.OPENAI_API_KEY;
const openai = apiKey ? new OpenAI({ apiKey }) : null;

export async function validateMessages(messages = []) {
  if (!openai || !messages.length) return {};

  const results = {};
  const batchSize = 10;
  for (let i = 0; i < messages.length; i += batchSize) {
    const batch = messages.slice(i, i + batchSize);
    const prompt =
      'Here are chat excerpts:\n\n' +
      batch.map(m => m.content).join('\n') +
      '\n\nPlease rate each on a 1–5 trust scale and flag any trade advice that seems low-quality or spam.';
    try {
      const resp = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [{ role: 'user', content: prompt }]
      });
      const text = resp.choices?.[0]?.message?.content || '';
      const lines = text.split(/\n+/);
      lines.forEach((line, idx) => {
        const match = line.match(/(\d)[^0-9]*([1-5])/);
        if (!match) return;
        const msg = batch[idx];
        if (msg) {
          results[msg.id] = { trustScore: parseInt(match[2]), notes: line.replace(match[0], '').trim() };
        }
      });
    } catch (err) {
      console.error('OpenAI validation error', err.message);
    }
  }
  return results;
}
