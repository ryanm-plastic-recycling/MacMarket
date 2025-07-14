import { marked } from 'marked';
import { writeFile } from 'fs/promises';

const README_URL = 'https://raw.githubusercontent.com/ryanmccauley/MacMarket/main/README.md';

async function fetchAndConvert() {
  try {
    const response = await fetch(README_URL);
    if (!response.ok) {
      throw new Error(`Failed to fetch README: ${response.status} ${response.statusText}`);
    }
    const markdown = await response.text();
    const html = marked.parse(markdown);
    await writeFile('latest-readme.html', html);
    console.log('README pulled and converted to HTML.');
  } catch (err) {
    console.error('Error fetching or converting README:', err);
  }
}

fetchAndConvert();
