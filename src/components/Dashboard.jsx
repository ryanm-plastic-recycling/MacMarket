import React, { useState, useEffect } from 'react';

export default function Dashboard() {
  const [alerts, setAlerts] = useState([]);
  const [political, setPolitical] = useState([]);
  const [riskScores, setRiskScores] = useState([]);
  const [whaleMoves, setWhaleMoves] = useState([]);

  useEffect(() => {
    fetch('/api/signals/alert')
      .then(res => res.json()).then(setAlerts).catch(() => setAlerts([]));

    fetch('/api/quiver/political')
      .then(res => res.json()).then(d => setPolitical(d.political || d)).catch(() => setPolitical([]));

    fetch('/api/quiver/risk?symbols=AAPL,MSFT,GOOGL,AMZN,TSLA,SPY,QQQ,GLD,BTC-USD,ETH-USD,RVN-USD,XMR-USD')
      .then(res => res.json()).then(d => setRiskScores(d.risk || d)).catch(() => setRiskScores([]));

    fetch('/api/quiver/whales?limit=5')
      .then(res => res.json()).then(d => setWhaleMoves(d.whales || d)).catch(() => setWhaleMoves([]));
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
    </div>
  );
}
