import React, { useState, useEffect } from 'react';

export default function TickersPage() {
  const [tickers, setTickers] = useState([]);

  useEffect(() => {
    load();
  }, []);

  const load = () => {
    fetch('/api/tickers')
      .then(r => r.json())
      .then(setTickers)
      .catch(() => setTickers([]));
  };

  const del = async (id) => {
    await fetch(`/api/tickers/${id}`, { method: 'DELETE' });
    load();
  };

  return (
    <div>
      <h1>Your Tickers</h1>
      {tickers.map(t => (
        <div key={t.id} className="ticker-row">
          <span>{t.symbol}</span>
          <button onClick={() => del(t.id)}>&times;</button>
        </div>
      ))}
    </div>
  );
}
