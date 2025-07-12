import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import BacktestPage from './components/BacktestPage.jsx';
import Dashboard from './components/Dashboard.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/backtest" element={<BacktestPage />} />
      </Routes>
    </BrowserRouter>
  );
}
