import React, { useState, useEffect } from 'react';

export default function Dashboard() {
  const [alerts, setAlerts] = useState([]);
  const [political, setPolitical] = useState([]);
  const [riskScores, setRiskScores] = useState([]);
  const [whaleMoves, setWhaleMoves] = useState([]);
  const [newsItems, setNewsItems] = useState([]);
  const [tickerData, setTickerData] = useState([]);

  useEffect(() => {
    fetch('/api/panorama?symbols=AAPL,MSFT,GOOGL,AMZN,TSLA,SPY,QQQ,GLD,BTC-USD,ETH-USD')
      .then(res => res.json())
      .then(({ market, alerts, political, risk, whales, news }) => {
        setTickerData(market || []);
        setAlerts(alerts || []);
        setPolitical(political || []);
        setRiskScores(risk || []);
        setWhaleMoves(whales || []);
        setNewsItems(news || []);
      })
      .catch(err => console.error('load panorama failed', err));
  }, []);

  return (
    <div>
      <h2>Unusual Whales</h2>
      {alerts.length ? alerts.map(a => <div key={a.id || a.transaction_id}>{a.summary || JSON.stringify(a)}</div>)
                     : <p>No whale alerts currently.</p>}

      <h2>Capitol Trades</h2>
      {political.map(tx => (
        <div key={tx.Date + tx.Ticker}>{`${tx.Date} – ${tx.Ticker} ${tx.Transaction}`}</div>
      ))}

      <h2>Quiver Risk Scores</h2>
      {riskScores.length ? riskScores.map(r => <div key={r.ticker}>{`${r.ticker}: ${r.score}`}</div>)
                         : <p>No risk scores available.</p>}

      <h2>Quiver Whale Moves</h2>
      {whaleMoves.length ? whaleMoves.map(w => <div key={w.transaction_id}>{`${w.symbol}: ${w.amount}`}</div>)
                         : <p>No whale moves right now.</p>}

      <h2>Ticker Data</h2>
      {tickerData.length ? tickerData.map(t => (
        <div key={t.symbol}>{`${t.symbol}: ${t.value}`}</div>
      )) : <p>No market data.</p>}

      <h2>News Feed</h2>
      {newsItems.length ? newsItems.map(n => (
        <div key={n.metrics.url}>{n.metrics.title}</div>
      )) : <p>No news right now.</p>}
    </div>
  );
}
