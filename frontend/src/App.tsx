import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import DashboardPage from './pages/Dashboard/DashboardPage';
import BacktestPage from './pages/Backtest/BacktestPage';
import StockAnalysisPage from './pages/StockAnalysis/StockAnalysisPage';
import NewsPage from './pages/News/NewsPage';

const basename = import.meta.env.VITE_BASE_PATH || '';

export default function App() {
  return (
    <BrowserRouter basename={basename}>
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