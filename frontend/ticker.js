// Simple ticker bar loader used on all pages
let tickerSymbols = ['AAPL','MSFT','GOOGL','AMZN','TSLA','SPY','QQQ','GLD','BTC-USD','ETH-USD'];
let tickerPaused = false;

async function loadUserTickers(){
  const userId = localStorage.getItem('userId');
  if(!userId) return;
  try {
    const resp = await fetch(`/api/users/${userId}/tickers`);
    if(resp.ok){
      const data = await resp.json();
      if(data.tickers && data.tickers.length){
        tickerSymbols = data.tickers;
      }
    }
  } catch(e) {}
}

async function updateTickerBar(){
  await loadUserTickers();
  const track = document.getElementById('ticker-track');
  if(!track) return;
  const res = await fetch('/api/ticker?symbols=' + tickerSymbols.join(','));
  const data = await res.json();
  track.innerHTML = '';
  data.data.forEach(item => {
    const span = document.createElement('span');
    const cls = item.change_percent >= 0 ? 'up' : 'down';
    span.className = 'ticker-item ' + cls;
    if(item.price === null){
      span.textContent = `${item.symbol} N/A`;
    } else {
      const priceStr = item.price < 1 ? item.price.toFixed(5) : item.price.toFixed(2);
      span.textContent = `${item.symbol} ${priceStr} (${item.change_percent.toFixed(2)}%)`;
    }
    track.appendChild(span);
  });
  track.innerHTML += track.innerHTML;
}

function toggleTicker(){
  const track = document.getElementById('ticker-track');
  if(!track) return;
  tickerPaused = !tickerPaused;
  track.style.animationPlayState = tickerPaused ? 'paused' : 'running';
  document.getElementById('ticker-toggle').textContent = tickerPaused ? 'Play' : 'Pause';
}

function initTickerBar(){
  if(document.getElementById('ticker-bar')) return; // already added
  const main = document.querySelector('main');
  if(!main) return;
  const bar = document.createElement('div');
  bar.id = 'ticker-bar';
  bar.innerHTML = '<button id="ticker-toggle">Pause</button><div id="ticker-track"></div>';
  main.prepend(bar);
  document.getElementById('ticker-toggle').addEventListener('click', toggleTicker);
  updateTickerBar();
  setInterval(updateTickerBar, 60000);
}

// expose for manual use if needed
window.initTickerBar = initTickerBar;
