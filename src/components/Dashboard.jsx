import React, { useState, useEffect } from 'react';

export default function Dashboard() {
  const [alerts, setAlerts] = useState([]);
  const [political, setPolitical] = useState({ quiver: [], whales: [], capitol: [] });
  const [riskScores, setRiskScores] = useState({});
  const [whaleMoves, setWhaleMoves] = useState([]);
  const [newsItems, setNewsItems] = useState({ market: [], world: [] });
  const [tickerData, setTickerData] = useState([]);

  useEffect(() => {
    let mounted = true;
    fetch('/api/panorama?symbols=AAPL,MSFT,GOOGL,AMZN,TSLA,SPY,QQQ,GLD,BTC-USD,ETH-USD')
      .then(res => res.json())
      .then(({ market, alerts, political, risk, whales, news }) => {
        if (!mounted) return;
        setTickerData(market || []);
        setAlerts(alerts || []);
        setPolitical(political || { quiver: [], whales: [], capitol: [] });
        setRiskScores(risk || {});
        setWhaleMoves(whales || []);
        setNewsItems(news || { market: [], world: [] });
      })
      .catch(err => console.error('load panorama failed', err));
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div>
      <h2>Unusual Whales</h2>
      {alerts.length ? alerts.map(a => <div key={a.id || a.transaction_id}>{a.summary || JSON.stringify(a)}</div>)
                     : <p>No whale alerts currently.</p>}

      <h2>Capitol Trades</h2>
      {[...(political.quiver || []), ...(political.whales || []), ...(political.capitol || [])].map(tx => (
        <div key={(tx.Date || tx.TransactionDate || tx.id) + (tx.Ticker || tx.ticker || tx.symbol)}>
          {`${tx.Date || tx.TransactionDate || ''} ${tx.Ticker || tx.ticker || tx.symbol || ''} ${tx.Transaction || tx.transaction || ''}`}
        </div>
      ))}

      <h2>Quiver Risk Scores</h2>
      {Object.keys(riskScores).length ?
        Object.entries(riskScores).map(([ticker, score]) => (
          <div key={ticker}>{`${ticker}: ${score}`}</div>
        )) : <p>No risk scores available.</p>}

      <h2>Quiver Whale Moves</h2>
      {whaleMoves.length ? whaleMoves.map(w => <div key={w.transaction_id}>{`${w.symbol}: ${w.amount}`}</div>)
                         : <p>No whale moves right now.</p>}

      <h2>Ticker Data</h2>
      {tickerData.length ? tickerData.map(t => (
        <div key={t.symbol}>{`${t.symbol}: ${t.value}`}</div>
      )) : <p>No market data.</p>}

      <h2>News Feed</h2>
      {[...(newsItems.market || []), ...(newsItems.world || [])].length ?
        [...(newsItems.market || []), ...(newsItems.world || [])].map(n => (
          <div key={n.url}>{n.title}</div>
        )) : <p>No news right now.</p>}
    </div>
  );
}
