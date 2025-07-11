import axios from 'axios';

export async function fetchNews() {
  const key = process.env.NEWSAPI_KEY;
  const url = `https://newsapi.org/v2/top-headlines?category=business&apiKey=${key}`;
  const res = await axios.get(url);
  const articles = (res.data && res.data.articles) || [];
  return articles.map(a => ({
    timestamp: a.publishedAt,
    symbol: a.source && a.source.name,
    metrics: { title: a.title, url: a.url, sentiment: a.sentiment || 0 }
  }));
}
