import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import BacktestPage from './components/BacktestPage.jsx';
import Dashboard from './components/Dashboard.jsx';
import TickerBar from './components/TickerBar.jsx';
import TickersPage from './pages/TickersPage.jsx';
import StrategyTester from './components/StrategyTester.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <TickerBar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/backtest" element={<BacktestPage />} />
        <Route path="/tickers" element={<TickersPage />} />
        <Route path="/strategy-tester" element={<StrategyTester />} />
      </Routes>
    </BrowserRouter>
  );
}
