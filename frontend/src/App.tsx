import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import DashboardPage from './pages/Dashboard/DashboardPage';
import BacktestPage from './pages/Backtest/BacktestPage';
import StockAnalysisPage from './pages/StockAnalysis/StockAnalysisPage';
import NewsPage from './pages/News/NewsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="backtest" element={<BacktestPage />} />
          <Route path="stock-analysis" element={<StockAnalysisPage />} />
          <Route path="news" element={<NewsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}