import React, { useState, useEffect } from 'react';
import { Select, Input, Button, Table, Card, Modal } from 'your-ui-lib';
import Chart from 'chart.js';

export default function BacktestPage() {
  const [strategies, setStrategies] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [results, setResults] = useState(null);
  const [scenarioName, setScenarioName] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setStrategies([
      { key: 'insider_ppi', label: 'Insider + PPI Trend' },
      { key: 'momentum_rsi', label: 'Momentum RSI' },
      { key: 'volatility_breakout', label: 'Volatility Breakout' }
    ]);
    fetch('/api/scenarios')
      .then(r => r.json())
      .then(setScenarios);
  }, []);

  const runBacktest = async (strategyKey, params) => {
    setLoading(true);
    const panorama = await fetch('/api/panorama').then(r => r.json());
    const res = await fetch('/api/backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ panorama, params: { strategy: strategyKey, ...params } })
    });
    const json = await res.json();
    setResults(json);
    setLoading(false);
  };

  const handleRun = () => {
    if (selectedScenario) {
      runBacktest(selectedScenario.strategy_key, JSON.parse(selectedScenario.params));
    } else {
      runBacktest(selectedStrategy, {});
    }
  };

  const handleSave = async () => {
    const payload = {
      name: scenarioName,
      strategy_key: selectedStrategy,
      params: {}
    };
    const res = await fetch('/api/scenarios', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    setScenarios([json, ...scenarios]);
    setScenarioName('');
  };

  return (
    <div>
      <Card title="Backtest">
        <Select
          placeholder="Select strategy"
          options={strategies.map(s => ({ value: s.key, label: s.label }))}
          value={selectedStrategy}
          onChange={e => { setSelectedStrategy(e.target.value); setSelectedScenario(null); }}
        />
        <Select
          placeholder="Or pick saved scenario"
          options={scenarios.map(s => ({ value: s.id, label: s.name }))}
          value={selectedScenario?.id || ''}
          onChange={e => {
            const sc = scenarios.find(s => s.id === +e.target.value);
            setSelectedScenario(sc);
            if (sc) setSelectedStrategy(sc.strategy_key);
          }}
        />
        <Button onClick={handleRun} disabled={loading || !(selectedStrategy || selectedScenario)}>
          {loading ? 'Running…' : 'Run Backtest'}
        </Button>
        <Input
          placeholder="Save current as scenario name"
          value={scenarioName}
          onChange={e => setScenarioName(e.target.value)}
        />
        <Button onClick={handleSave} disabled={!selectedStrategy || !scenarioName}>
          Save Scenario
        </Button>
      </Card>

      {results && (
        <>
          <Card title="Summary">
            <p>Win rate: {results.stats.winRate}%</p>
            <p>Avg return: {results.stats.avgReturn}%</p>
          </Card>
          <Card title="Trades">
            <Table
              columns={[
                { title: 'Entry', dataIndex: 'entryDate' },
                { title: 'Exit', dataIndex: 'exitDate' },
                { title: 'P&L', dataIndex: 'pnl' }
              ]}
              dataSource={results.trades}
              rowKey="id"
            />
          </Card>
          <Card title="Equity Curve">
            <canvas id="equityChart" />
          </Card>
        </>
      )}
    </div>
  );
}
