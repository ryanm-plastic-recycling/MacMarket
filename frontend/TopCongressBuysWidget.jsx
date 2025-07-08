import React, { useEffect, useState } from 'react';
import './TopCongressBuysWidget.css';

/**
 * TopCongressBuysWidget fetches recent congressional trades and displays
 * the top 5 buy transactions as well as the top 5 tickers by dollar volume.
 *
 * The component automatically attaches itself to `window.TopCongressBuysWidget`
 * so it can be embedded via <script> tag or imported as a module.
 */
function TopCongressBuysWidget() {
  const [topBuys, setTopBuys] = useState([]);
  const [topByUsd, setTopByUsd] = useState([]);

  useEffect(() => {
    fetch('/api/signals/congress-buys')
      .then((res) => res.json())
      .then((data) => {
        if (!Array.isArray(data)) return;
        const buys = data.filter((t) => (t.action || '').toLowerCase() === 'buy');

        // Sort by date to get the most recent buys
        const recent = [...buys].sort(
          (a, b) => new Date(b.date) - new Date(a.date)
        );
        setTopBuys(recent.slice(0, 5));

        // Aggregate dollar totals per ticker
        const totals = {};
        for (const trade of buys) {
          const ticker = trade.ticker;
          const usd = Number(trade.usd || trade.amount || 0);
          if (!ticker) continue;
          totals[ticker] = (totals[ticker] || 0) + (isNaN(usd) ? 0 : usd);
        }
        const topUsd = Object.entries(totals)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5)
          .map(([ticker, total]) => ({ ticker, total }));
        setTopByUsd(topUsd);
      })
      .catch((err) => console.error('Failed to load congress buys', err));
  }, []);

  return (
    <div className="top-congress-buys-widget">
      <h3>Top Congressional Buys</h3>
      <ul className="buy-list">
        {topBuys.map((trade, idx) => (
          <li key={idx} className="buy-card">
            <div className="buy-ticker">{trade.ticker}</div>
            <div className="buy-member">{trade.member}</div>
            <div className="buy-date">{new Date(trade.date).toLocaleDateString()}</div>
          </li>
        ))}
      </ul>
      <h3>Top Buys by USD</h3>
      <ul className="buy-list">
        {topByUsd.map((item, idx) => (
          <li key={idx} className="buy-card">
            <div className="buy-ticker">{item.ticker}</div>
            <div className="buy-usd">${item.total.toLocaleString()}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default TopCongressBuysWidget;

// Allow usage via <script> inclusion
if (typeof window !== 'undefined') {
  window.TopCongressBuysWidget = TopCongressBuysWidget;
}
