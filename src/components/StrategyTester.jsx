import React, { useState, useEffect } from 'react';

export default function StrategyTester({ currentUser = { id: 1 } }) {
  const [strategies, setStrategies] = useState([]);
  const [selected, setSelected] = useState('');
  const [results, setResults] = useState(null);
  const [history, setHistory] = useState({});

  useEffect(() => {
    fetch('/strategy-test/list')
      .then(res => res.json())
      .then(setStrategies)
      .catch(() => setStrategies([]));
  }, []);

  useEffect(() => {
    if (!currentUser?.id) return;
    fetch(`/strategy-test/history?user_id=${currentUser.id}`)
      .then(res => res.json())
      .then(setHistory)
      .catch(() => setHistory({}));
  }, [currentUser?.id]);

  const run = () => {
    fetch('/strategy-test/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strategy: selected, user_id: currentUser.id })
    })
      .then(res => res.json())
      .then(data => {
        setResults(data);
        fetch(`/strategy-test/history?user_id=${currentUser.id}`)
          .then(res => res.json())
          .then(setHistory)
          .catch(() => {});
      });
  };

  const formatName = key => key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="strategy-tester">
      <div className="sidebar">
        {strategies.map(key => (
          <button
            key={key}
            className={selected === key ? 'selected' : ''}
            onClick={() => setSelected(key)}
          >
            {formatName(key)}
          </button>
        ))}
      </div>
      <div className="content">
        <button onClick={run} disabled={!selected}>Run Test</button>
        {results && (
          <pre>{JSON.stringify(results, null, 2)}</pre>
        )}
        <h3>History</h3>
        <table>
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Last Run</th>
              <th>Total Return</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(history).map(([k, v]) => (
              <tr key={k}>
                <td>{formatName(k)}</td>
                <td>{v.timestamp}</td>
                <td>{v.metrics?.total_return}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
