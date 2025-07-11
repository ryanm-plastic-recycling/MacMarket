import React from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import BacktestPage from './components/BacktestPage.jsx';

function Home() {
  return <div>Home</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <nav>
        <NavLink to="/">Home</NavLink> |{' '}
        <NavLink to="/backtest">Backtest</NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/backtest" element={<BacktestPage />} />
      </Routes>
    </BrowserRouter>
  );
}
