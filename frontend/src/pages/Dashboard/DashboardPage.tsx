import { useState, useEffect } from 'react';
import { marketApi } from '../../api';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  RefreshCw,
  Shield,
  Zap,
  Info,
  ChevronDown,
  ChevronUp,
  Target,
  Download,
  CheckCircle,
  XCircle,
  TrendingUp,
  Minus,
  ArrowUp,
  ArrowDown,
  Clock,
  FileText,
} from 'lucide-react';

// ========== 类型定义 ==========

interface CFTCItem {
  instrument: string;
  section: string;
  trader_type: string;
  net: number;
  net_z: number;
  net_ww: number;
  net_ww_z: number;
  long: number;
  long_z: number;
  long_ww: number;
  long_ww_z: number;
  short: number;
  short_z: number;
  short_ww: number;
  short_ww_z: number;
  flow_state: string;
  price_chg: number | null;
  crowding: { level: string; label: string; direction: string };
}

interface CFTCAnalysisSummary {
  total_instruments: number;
  net_bull: number;
  net_bear: number;
  extreme_count: number;
  crowded_count: number;
}

interface CFTCAnalysis {
  report_date: string;
  summary: CFTCAnalysisSummary;
  section_summary: Record<string, { net_bull: number; net_bear: number; items: string[] }>;
  findings: Array<{ type: string; title: string; detail: string }>;
  generated_at: string;
}

interface CFTCReport {
  report_date: string;
  tff_items: CFTCItem[];
  disagg_items: CFTCItem[];
  analysis: CFTCAnalysis;
  price_data: Record<string, unknown>;
  source: string;
  updated_at: string;
}

interface PutCallData {
  date: string;
  equity_put_call_ratio: number;
  index_put_call_ratio: number;
  total_put_call_ratio: number;
}

interface PutCallReportSection {
  title: string;
  content: string;
}

interface PutCallReport {
  sections: PutCallReportSection[];
  equity_vs_index: string;
  generated_at: string;
}

interface PutCallAnalysis {
  current_ratio: number;
  current_equity_ratio: number;
  current_index_ratio: number;
  avg_5d: number;
  avg_10d: number;
  avg_20d: number;
  avg_30d: number;
  volatility_20d: number;
  percentile: number;
  sentiment: string;
  signal: string;
  risk_level: string;
  trend: string;
  trend_strength: string;
  trend_detail: string;
  extremes: Array<{ type: string; message: string }>;
  report: PutCallReport;
  data: PutCallData[];
  source: string;
  analysis_time: string;
}

// ---------- SSE 期权类型 ----------

interface SSEOptionRecord {
  underlying_code: string;
  underlying_name: string;
  contract_count: number;
  turnover: number;
  total_volume: number;
  call_volume: number;
  put_volume: number;
  pc_ratio_volume: number;
  total_oi: number;
  call_oi: number;
  put_oi: number;
  pc_ratio_oi: number;
  trade_date: string;
}

interface SSESummary {
  total_call_volume: number;
  total_put_volume: number;
  pc_ratio_volume: number;
  total_call_oi: number;
  total_put_oi: number;
  pc_ratio_oi: number;
  total_turnover: number;
  underlying_count: number;
}

interface SSEReportSection {
  title: string;
  content: string;
}

interface SSEReport {
  sections: SSEReportSection[];
  generated_at: string;
}

interface SSEAnalysis {
  date: string;
  current_pc_ratio_volume: number;
  current_pc_ratio_oi: number;
  avg_5d_volume: number;
  avg_5d_oi: number;
  avg_10d_volume: number;
  avg_10d_oi: number;
  avg_20d_volume: number;
  avg_20d_oi: number;
  volatility_20d: number;
  percentile_volume: number;
  percentile_oi: number;
  sentiment: string;
  signal: string;
  risk_level: string;
  trend: string;
  trend_strength: string;
  summary: SSESummary;
  records: SSEOptionRecord[];
  extremes: Array<{ type: string; message: string }>;
  report: SSEReport;
  history: Array<{
    date: string;
    call_volume: number;
    put_volume: number;
    pc_ratio_volume: number;
    call_oi: number;
    put_oi: number;
    pc_ratio_oi: number;
  }>;
  source: string;
  analysis_time: string;
}

interface SSETrackingCurrent {
  pc_ratio_volume: number;
  pc_ratio_oi: number;
  sentiment: string;
  trend: string;
  risk_level: string;
  avg_5d_volume: number;
  avg_20d_volume: number;
  volatility_20d: number;
  percentile_volume: number;
  signal: string;
}

interface SSETrackingDailyChange {
  vol_change?: number;
  vol_change_pct?: number;
  oi_change?: number;
  oi_change_pct?: number;
  prev_date?: string;
}

interface SSETrackingSignal {
  type: string;
  days?: number;
  level: string;
  detail: string;
}

interface SSETrendPoint {
  date: string;
  pc_ratio_volume: number;
  pc_ratio_oi: number;
  call_volume: number;
  put_volume: number;
  sentiment: string;
}

interface SSETrackingReport {
  current: SSETrackingCurrent;
  daily_change: SSETrackingDailyChange;
  cumulative_signals: SSETrackingSignal[];
  trend_data: SSETrendPoint[];
  records: SSEOptionRecord[];
  summary: SSESummary;
  snapshot_count: number;
  interpretation: string;
  source: string;
  generated_at: string;
}

// ---------- 持续跟踪类型 ----------

interface CFTCTrackingSignal {
  type: string;
  weeks?: number;
  days?: number;
  detail: string;
}

interface CFTCInstrumentTracking {
  instrument: string;
  section: string;
  trader_type: string;
  current: {
    net: number;
    long: number;
    short: number;
    net_z: number;
    flow_state: string;
    crowding: { level: string; label: string; direction: string };
  };
  changes: {
    net_ww?: number;
    long_ww?: number;
    short_ww?: number;
    net_z_ww?: number;
    flow_prev?: string;
  };
  trend_signals: CFTCTrackingSignal[];
  interpretation: string;
}

interface CFTCTrackingReport {
  report_date: string;
  previous_report_date: string | null;
  snapshot_count: number;
  instrument_analysis: CFTCInstrumentTracking[];
  section_analysis: Record<string, { net_total: number; count: number; bull: number; bear: number; net_change?: number }>;
  aggregate_signals: CFTCTrackingSignal[];
  summary: CFTCAnalysisSummary;
  summary_interpretation: string;
  source: string;
  generated_at: string;
}

interface CBOECumulativeSignal {
  type: string;
  days?: number;
  level: string;
  detail: string;
}

interface CBOETrendPoint {
  date: string;
  ratio: number;
  equity_ratio: number;
  index_ratio: number;
  avg_5d: number;
  avg_20d: number;
  sentiment: string;
}

interface CBOETrackingReport {
  current: {
    ratio: number;
    equity_ratio: number;
    index_ratio: number;
    sentiment: string;
    trend: string;
    risk_level: string;
    avg_5d: number;
    avg_20d: number;
    avg_30d: number;
    volatility_20d: number;
    percentile: number;
    signal: string;
  };
  daily_change: {
    ratio_change?: number;
    ratio_change_pct?: number;
    sentiment_prev?: string;
    sentiment_changed?: boolean;
    trend_prev?: string;
    trend_changed?: boolean;
    risk_prev?: string;
    risk_changed?: boolean;
  };
  cumulative_signals: CBOECumulativeSignal[];
  trend_data: CBOETrendPoint[];
  snapshot_count: number;
  interpretation: string;
  source: string;
  generated_at: string;
}

// ========== 工具函数 ==========

const formatNum = (n: number) => {
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿';
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(1) + '万';
  return n.toLocaleString();
};

const zColor = (z: number) => {
  if (z >= 2.0) return 'var(--accent-red)';
  if (z >= 1.0) return 'var(--accent-yellow)';
  if (z <= -2.0) return 'var(--accent-green)';
  if (z <= -1.0) return 'var(--accent-blue)';
  return 'var(--text-secondary)';
};

const zBarWidth = (z: number) => {
  const absZ = Math.abs(z);
  return Math.min(absZ / 3 * 100, 100);
};

const flowTagStyle = (state: string): React.CSSProperties => {
  const bull = ['多头建仓', '空头回补', '多头挤压'];
  const bear = ['空头建仓', '多头平仓', '空头施压'];
  if (bull.includes(state)) return { background: 'rgba(0,200,83,0.15)', color: '#00c853' };
  if (bear.includes(state)) return { background: 'rgba(255,82,82,0.15)', color: '#ff5252' };
  return { background: 'rgba(255,193,7,0.15)', color: '#ffc107' };
};

const crowdingStyle = (level: string): React.CSSProperties => {
  if (level === 'extreme') return { background: 'rgba(255,82,82,0.2)', color: '#ff5252', fontWeight: 700 };
  if (level === 'crowded') return { background: 'rgba(255,152,0,0.15)', color: '#ff9800', fontWeight: 600 };
  return {};
};

const getSentimentColor = (sentiment: string) => {
  if (sentiment.includes('恐慌')) return 'var(--accent-red)';
  if (sentiment.includes('空')) return 'var(--accent-yellow)';
  if (sentiment.includes('乐观')) return 'var(--accent-green)';
  return 'var(--text-primary)';
};

const getRiskColor = (level: string) => {
  if (level === 'high') return 'var(--accent-red)';
  if (level === 'medium') return 'var(--accent-yellow)';
  return 'var(--accent-green)';
};

const findIcon = (type: string) => {
  if (type === 'warning') return <AlertTriangle size={14} color="var(--accent-red)" />;
  if (type === 'info') return <Info size={14} color="var(--accent-blue)" />;
  return <Info size={14} color="var(--text-secondary)" />;
};

// ========== 子组件 ==========

function ZBar({ value }: { value: number }) {
  if (value === null || isNaN(value)) return <span style={{ color: 'var(--text-muted)' }}>-</span>;
  const v = Number(value);
  const pct = zBarWidth(v);
  const isPos = v > 0;
  return (
    <div style={{ position: 'relative', minWidth: 50, textAlign: 'center', height: 20 }}>
      <div style={{
        position: 'absolute', top: 2, bottom: 2,
        [isPos ? 'left' : 'right']: '50%',
        width: `${pct / 2}%`,
        background: isPos ? 'rgba(0,200,83,0.3)' : 'rgba(255,82,82,0.3)',
      }} />
      <span style={{ position: 'relative', zIndex: 1, fontSize: 11, fontWeight: 600, color: zColor(v) }}>
        {v.toFixed(1)}
      </span>
    </div>
  );
}

function ChgTd({ chg, z }: { chg: number; z: number }) {
  if (chg == null || isNaN(chg)) return <td style={{ color: 'var(--text-muted)', textAlign: 'right' }}>-</td>;
  const cls = chg > 0 ? 'var(--accent-green)' : chg < 0 ? 'var(--accent-red)' : 'var(--text-secondary)';
  const zStr = z != null && !isNaN(z) ? ` (${z.toFixed(1)}z)` : '';
  return (
    <td style={{ color: cls, textAlign: 'right', fontSize: 11, whiteSpace: 'nowrap' }}>
      {chg > 0 ? '+' : ''}{formatNum(chg)}{zStr}
    </td>
  );
}

// ========== 主页面 ==========

export default function DashboardPage() {
  const [cftcReport, setCftcReport] = useState<CFTCReport | null>(null);
  const [putCallAnalysis, setPutCallAnalysis] = useState<PutCallAnalysis | null>(null);
  const [sseAnalysis, setSseAnalysis] = useState<SSEAnalysis | null>(null);
  const [sseTracking, setSseTracking] = useState<SSETrackingReport | null>(null);
  const [cftcTracking, setCftcTracking] = useState<CFTCTrackingReport | null>(null);
  const [cboeTracking, setCboeTracking] = useState<CBOETrackingReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'cftc' | 'putcall' | 'sse' | 'tracking'>('cftc');
  const [trackingSubTab, setTrackingSubTab] = useState<'cftc_track' | 'cboe_track' | 'sse_track'>('cftc_track');
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const [refreshingCFTC, setRefreshingCFTC] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    // CFTC 和 CBOE 分开加载，互不阻塞
    const results = await Promise.allSettled([
      marketApi.getCFTCLatest() as Promise<CFTCReport>,
      marketApi.getPutCallAnalysis() as Promise<PutCallAnalysis>,
    ]);
    if (results[0].status === 'fulfilled') {
      setCftcReport(results[0].value);
    } else {
      console.warn('CFTC加载失败:', results[0].reason);
    }
    if (results[1].status === 'fulfilled') {
      setPutCallAnalysis(results[1].value);
    } else {
      console.warn('CBOE加载失败:', results[1].reason);
    }
    // 两者都失败才报错
    if (results[0].status === 'rejected' && results[1].status === 'rejected') {
      setError('CFTC 和 CBOE 数据均加载失败，请检查网络连接');
    }
    setLoading(false);
  };

  // SSE 数据按需加载
  const fetchSSEData = async () => {
    if (sseAnalysis) return;
    try {
      const res = await marketApi.getSSEOptionsAnalysis() as SSEAnalysis;
      setSseAnalysis(res);
    } catch (e: unknown) {
      console.warn('SSE期权数据加载失败:', e);
    }
  };

  // 跟踪数据按需加载（切换到跟踪Tab时才请求）
  const fetchTrackingData = async () => {
    if (cftcTracking && cboeTracking && sseTracking) return; // 已加载
    try {
      const promises: Promise<unknown>[] = [];
      if (!cftcTracking) promises.push(marketApi.getCFTCTracking().then(r => setCftcTracking(r as CFTCTrackingReport)));
      if (!cboeTracking) promises.push(marketApi.getCBOETracking().then(r => setCboeTracking(r as CBOETrackingReport)));
      if (!sseTracking) promises.push(marketApi.getSSEOptionsTracking().then(r => setSseTracking(r as SSETrackingReport)));
      await Promise.all(promises);
    } catch (e: unknown) {
      console.warn('跟踪数据加载失败:', e);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefreshCFTC = async () => {
    setRefreshingCFTC(true);
    setRefreshMsg(null);
    try {
      const [res, trackRes] = await Promise.all([
        marketApi.refreshCFTC() as Promise<{ success: boolean; message: string; data: CFTCReport }>,
        marketApi.getCFTCTracking(true) as Promise<CFTCTrackingReport>,
      ]);
      setCftcReport(res.data);
      setCftcTracking(trackRes);
      setRefreshMsg({ type: 'success', text: res.message });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'CFTC 数据获取失败';
      setRefreshMsg({ type: 'error', text: msg });
      // CFTC 需要电脑端 VPN，手机 VPN 无效
      if (msg.includes('VPN') || msg.includes('代理') || msg.includes('503')) {
        setRefreshMsg({ type: 'error', text: 'CFTC 数据获取失败：请确保电脑端已开启 VPN/代理（手机端 VPN 无效），然后重试。' });
      }
    } finally {
      setRefreshingCFTC(false);
      setTimeout(() => setRefreshMsg(null), 5000);
    }
  };

  const toggleSection = (key: string) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div className="loading-spinner" />
        <span style={{ marginLeft: 12, color: 'var(--text-secondary)' }}>加载市场数据...</span>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* 标题 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>市场交易数据看板</h1>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            CFTC 持仓报告 & CBOE Put/Call 比率 & SSE 上交所期权跟踪
            {cftcReport && <span style={{ marginLeft: 12, color: 'var(--accent-green)' }}>数据来源: {cftcReport.source}</span>}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {activeTab === 'cftc' && (
            <button
              className="btn-primary"
              onClick={handleRefreshCFTC}
              disabled={refreshingCFTC}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: refreshingCFTC ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                color: '#fff',
                cursor: refreshingCFTC ? 'not-allowed' : 'pointer',
                opacity: refreshingCFTC ? 0.7 : 1,
              }}
            >
              <Download size={14} style={refreshingCFTC ? { animation: 'spin 0.8s linear infinite' } : undefined} />
              {refreshingCFTC ? '获取中...' : '一键获取最新 CFTC'}
            </button>
          )}
          <button className="btn-secondary" onClick={fetchData} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={14} />
            刷新数据
          </button>
        </div>
      </div>

      {refreshMsg && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 16px', marginBottom: 16, borderRadius: 6,
          fontSize: 13,
          background: refreshMsg.type === 'success' ? 'rgba(0,200,83,0.1)' : 'rgba(255,82,82,0.1)',
          border: `1px solid ${refreshMsg.type === 'success' ? 'rgba(0,200,83,0.3)' : 'rgba(255,82,82,0.3)'}`,
          color: refreshMsg.type === 'success' ? 'var(--accent-green)' : 'var(--accent-red)',
        }}>
          {refreshMsg.type === 'success' ? <CheckCircle size={14} /> : <XCircle size={14} />}
          {refreshMsg.text}
        </div>
      )}

      {error && (
        <div style={{
          background: 'rgba(239,83,80,0.1)', border: '1px solid rgba(239,83,80,0.3)',
          borderRadius: 6, padding: '12px 16px', marginBottom: 16,
          color: 'var(--accent-red)', fontSize: 13,
        }}>
          <AlertTriangle size={14} style={{ display: 'inline', marginRight: 6 }} />
          {error}
        </div>
      )}

      {/* Tab 切换 */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border-color)', flexWrap: 'wrap' }}>
        {[
          { key: 'cftc', label: 'CFTC 持仓报告', icon: BarChart3 },
          { key: 'putcall', label: 'CBOE Put/Call 比率', icon: Activity },
          { key: 'sse', label: '上交所期权 Put/Call', icon: TrendingUp },
          { key: 'tracking', label: '持续跟踪报告', icon: TrendingUp },
        ].map(tab => (
          <button
            key={tab.key}
            className="tab-btn"
            onClick={() => {
              setActiveTab(tab.key as 'cftc' | 'putcall' | 'sse' | 'tracking');
              if (tab.key === 'tracking') fetchTrackingData();
              if (tab.key === 'sse') fetchSSEData();
            }}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '10px 20px',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid var(--accent-green)' : '2px solid transparent',
              color: activeTab === tab.key ? 'var(--accent-green)' : 'var(--text-secondary)',
              fontSize: 13,
              fontWeight: activeTab === tab.key ? 600 : 400,
              cursor: 'pointer',
              transition: 'all 0.2s',
              whiteSpace: 'nowrap',
            }}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* CFTC 持仓报告 */}
      {activeTab === 'cftc' && cftcReport && (
        <div>
          {cftcReport.analysis && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 12, marginBottom: 20 }}>
              <div className="trading-card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>报告日期</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{cftcReport.report_date}</div>
              </div>
              <div className="trading-card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>跟踪品种</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>{cftcReport.analysis.summary.total_instruments}</div>
              </div>
              <div className="trading-card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>净多/净空</div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>
                  <span style={{ color: 'var(--accent-green)' }}>{cftcReport.analysis.summary.net_bull}</span>
                  <span style={{ color: 'var(--text-secondary)' }}> / </span>
                  <span style={{ color: 'var(--accent-red)' }}>{cftcReport.analysis.summary.net_bear}</span>
                </div>
              </div>
              <div className="trading-card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>极端拥挤</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: cftcReport.analysis.summary.extreme_count > 0 ? 'var(--accent-red)' : 'var(--text-primary)' }}>
                  {cftcReport.analysis.summary.extreme_count}
                </div>
              </div>
              <div className="trading-card" style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>拥挤</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: cftcReport.analysis.summary.crowded_count > 0 ? 'var(--accent-yellow)' : 'var(--text-primary)' }}>
                  {cftcReport.analysis.summary.crowded_count}
                </div>
              </div>
            </div>
          )}

          {cftcReport.analysis?.findings && cftcReport.analysis.findings.length > 0 && (
            <div className="trading-card" style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Target size={14} color="var(--accent-yellow)" />
                CFTC 持仓分析报告
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {cftcReport.analysis.findings.map((f, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'flex-start', gap: 10,
                    padding: '10px 14px',
                    background: f.type === 'warning' ? 'rgba(255,82,82,0.08)' : 'var(--bg-tertiary)',
                    borderRadius: 6,
                    border: f.type === 'warning' ? '1px solid rgba(255,82,82,0.2)' : '1px solid var(--border-color)',
                  }}>
                    {findIcon(f.type)}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                        {f.title}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                        {f.detail}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {cftcReport.tff_items && cftcReport.tff_items.length > 0 && (
            <div className="trading-card" style={{ marginBottom: 20 }}>
              <div
                onClick={() => toggleSection('tff')}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', marginBottom: expandedSections['tff'] ? 12 : 0 }}
              >
                <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Zap size={14} color="var(--accent-yellow)" />
                  杠杆基金 Leveraged Funds（TFF 报告）
                </h3>
                {expandedSections['tff'] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </div>
              {expandedSections['tff'] && <CFTCTable items={cftcReport.tff_items} />}
            </div>
          )}

          {cftcReport.disagg_items && cftcReport.disagg_items.length > 0 && (
            <div className="trading-card">
              <div
                onClick={() => toggleSection('disagg')}
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', marginBottom: expandedSections['disagg'] ? 12 : 0 }}
              >
                <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Shield size={14} color="var(--accent-blue)" />
                  管理资金 Managed Money（COT 分类报告）
                </h3>
                {expandedSections['disagg'] ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </div>
              {expandedSections['disagg'] && <CFTCTable items={cftcReport.disagg_items} />}
            </div>
          )}
        </div>
      )}

      {/* CBOE Put/Call 比率 */}
      {activeTab === 'putcall' && putCallAnalysis && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 14, marginBottom: 20 }}>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                当前 Put/Call 比率
              </div>
              <div style={{ fontSize: 36, fontWeight: 700, color: getSentimentColor(putCallAnalysis.sentiment) }}>
                {putCallAnalysis.current_ratio.toFixed(3)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                分位: {putCallAnalysis.percentile.toFixed(0)}%
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                市场情绪
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: getSentimentColor(putCallAnalysis.sentiment) }}>
                {putCallAnalysis.sentiment}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                风险: <span style={{ color: getRiskColor(putCallAnalysis.risk_level), fontWeight: 600 }}>{putCallAnalysis.risk_level === 'high' ? '高' : putCallAnalysis.risk_level === 'medium' ? '中' : '低'}</span>
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                5日均值
              </div>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>
                {putCallAnalysis.avg_5d.toFixed(3)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                趋势: {putCallAnalysis.trend}
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                20日波动率
              </div>
              <div style={{ fontSize: 28, fontWeight: 700, color: putCallAnalysis.volatility_20d > 0.1 ? 'var(--accent-yellow)' : 'var(--text-primary)' }}>
                {putCallAnalysis.volatility_20d.toFixed(3)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                20日均: {putCallAnalysis.avg_20d.toFixed(3)}
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                Equity P/C
              </div>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>
                {putCallAnalysis.current_equity_ratio.toFixed(3)}
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                Index P/C
              </div>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>
                {putCallAnalysis.current_index_ratio.toFixed(3)}
              </div>
            </div>
          </div>

          {putCallAnalysis.extremes && putCallAnalysis.extremes.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
              {putCallAnalysis.extremes.map((ext, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  padding: '10px 14px',
                  background: ext.type === 'warning' ? 'rgba(255,82,82,0.08)' : 'rgba(255,193,7,0.08)',
                  borderRadius: 6,
                  border: `1px solid ${ext.type === 'warning' ? 'rgba(255,82,82,0.2)' : 'rgba(255,193,7,0.2)'}`,
                }}>
                  {ext.type === 'warning' ? <AlertTriangle size={14} color="var(--accent-red)" /> : <Info size={14} color="var(--accent-yellow)" />}
                  <div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5 }}>{ext.message}</div>
                </div>
              ))}
            </div>
          )}

          {putCallAnalysis.report?.sections && (
            <div className="trading-card" style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Target size={14} color="var(--accent-yellow)" />
                每日跟踪分析报告
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {putCallAnalysis.report.sections.map((s, i) => (
                  <div key={i} style={{
                    padding: '12px 16px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 6,
                    border: '1px solid var(--border-color)',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-green)', marginBottom: 4 }}>
                      {s.title}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-line' }}>
                      {s.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="trading-card" style={{ marginBottom: 20 }}>
            <div style={{
              background: 'var(--bg-tertiary)',
              borderRadius: 6,
              padding: '16px 20px',
              border: '1px solid var(--border-color)',
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: getSentimentColor(putCallAnalysis.sentiment),
                  marginTop: 4, flexShrink: 0,
                }} />
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
                    {putCallAnalysis.signal}
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {putCallAnalysis.trend_detail} | 数据来源: {putCallAnalysis.source}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="trading-card">
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
              Put/Call 比率趋势 (近30日)
            </h3>
            <div style={{ overflow: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th style={{ textAlign: 'right' }}>Total P/C</th>
                    <th style={{ textAlign: 'right' }}>Equity P/C</th>
                    <th style={{ textAlign: 'right' }}>Index P/C</th>
                    <th style={{ textAlign: 'center' }}>信号</th>
                  </tr>
                </thead>
                <tbody>
                  {putCallAnalysis.data.slice().reverse().slice(0, 30).map((item, i) => {
                    const ratio = item.total_put_call_ratio;
                    let tag = '';
                    let tagStyle: React.CSSProperties = {};
                    if (ratio > 1.0) { tag = '恐慌'; tagStyle = { background: 'rgba(255,82,82,0.15)', color: '#ff5252' }; }
                    else if (ratio > 0.85) { tag = '偏空'; tagStyle = { background: 'rgba(255,152,0,0.15)', color: '#ff9800' }; }
                    else if (ratio > 0.7) { tag = '中性'; tagStyle = { background: 'rgba(33,150,243,0.15)', color: '#2196f3' }; }
                    else if (ratio > 0.55) { tag = '正常'; tagStyle = { background: 'rgba(76,175,80,0.15)', color: '#4caf50' }; }
                    else { tag = '乐观'; tagStyle = { background: 'rgba(0,200,83,0.15)', color: '#00c853' }; }
                    return (
                      <tr key={i}>
                        <td>{item.date}</td>
                        <td style={{ textAlign: 'right', fontWeight: 600, color: ratio > 0.9 ? 'var(--accent-red)' : ratio < 0.5 ? 'var(--accent-green)' : 'var(--text-primary)' }}>
                          {ratio.toFixed(3)}
                        </td>
                        <td style={{ textAlign: 'right' }}>{item.equity_put_call_ratio.toFixed(3)}</td>
                        <td style={{ textAlign: 'right' }}>{item.index_put_call_ratio.toFixed(3)}</td>
                        <td style={{ textAlign: 'center' }}>
                          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 3, fontWeight: 600, ...tagStyle }}>{tag}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SSE 上交所ETF期权 Put/Call */}
      {activeTab === 'sse' && sseAnalysis && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 14, marginBottom: 20 }}>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                成交量 P/C 比率
              </div>
              <div style={{ fontSize: 36, fontWeight: 700, color: getSentimentColor(sseAnalysis.sentiment) }}>
                {sseAnalysis.current_pc_ratio_volume.toFixed(3)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                分位: {sseAnalysis.percentile_volume.toFixed(0)}%
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                市场情绪
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: getSentimentColor(sseAnalysis.sentiment) }}>
                {sseAnalysis.sentiment}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                风险: <span style={{ color: getRiskColor(sseAnalysis.risk_level), fontWeight: 600 }}>{sseAnalysis.risk_level === 'high' ? '高' : sseAnalysis.risk_level === 'medium' ? '中' : '低'}</span>
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                持仓量 P/C 比率
              </div>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>
                {sseAnalysis.current_pc_ratio_oi.toFixed(3)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                分位: {sseAnalysis.percentile_oi.toFixed(0)}%
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                5日均值 (成交量)
              </div>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>
                {sseAnalysis.avg_5d_volume.toFixed(3)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                趋势: {sseAnalysis.trend}
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                20日波动率
              </div>
              <div style={{ fontSize: 28, fontWeight: 700, color: sseAnalysis.volatility_20d > 0.08 ? 'var(--accent-yellow)' : 'var(--text-primary)' }}>
                {sseAnalysis.volatility_20d.toFixed(3)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                20日均: {sseAnalysis.avg_20d_volume.toFixed(3)}
              </div>
            </div>
            <div className="trading-card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                总成交量
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>
                {formatNum(sseAnalysis.summary.total_call_volume + sseAnalysis.summary.total_put_volume)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Call: {formatNum(sseAnalysis.summary.total_call_volume)} / Put: {formatNum(sseAnalysis.summary.total_put_volume)}
              </div>
            </div>
          </div>

          {sseAnalysis.extremes && sseAnalysis.extremes.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
              {sseAnalysis.extremes.map((ext, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  padding: '10px 14px',
                  background: ext.type === 'warning' ? 'rgba(255,82,82,0.08)' : 'rgba(255,193,7,0.08)',
                  borderRadius: 6,
                  border: `1px solid ${ext.type === 'warning' ? 'rgba(255,82,82,0.2)' : 'rgba(255,193,7,0.2)'}`,
                }}>
                  {ext.type === 'warning' ? <AlertTriangle size={14} color="var(--accent-red)" /> : <Info size={14} color="var(--accent-yellow)" />}
                  <div style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5 }}>{ext.message}</div>
                </div>
              ))}
            </div>
          )}

          {sseAnalysis.report?.sections && (
            <div className="trading-card" style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Target size={14} color="var(--accent-yellow)" />
                每日跟踪分析报告
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {sseAnalysis.report.sections.map((s, i) => (
                  <div key={i} style={{
                    padding: '12px 16px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: 6,
                    border: '1px solid var(--border-color)',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-green)', marginBottom: 4 }}>
                      {s.title}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-line' }}>
                      {s.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="trading-card" style={{ marginBottom: 20 }}>
            <div style={{
              background: 'var(--bg-tertiary)',
              borderRadius: 6,
              padding: '16px 20px',
              border: '1px solid var(--border-color)',
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: getSentimentColor(sseAnalysis.sentiment),
                  marginTop: 4, flexShrink: 0,
                }} />
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
                    {sseAnalysis.signal}
                  </p>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    数据来源: {sseAnalysis.source}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 各标的详情卡片 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14, marginBottom: 20 }}>
            {sseAnalysis.records.map((r, i) => {
              const volRatio = r.pc_ratio_volume;
              const volTag = volRatio > 0.9 ? '恐慌' : volRatio > 0.75 ? '偏空' : volRatio > 0.55 ? '中性' : '乐观';
              const volColor = volRatio > 0.9 ? 'var(--accent-red)' : volRatio > 0.75 ? 'var(--accent-yellow)' : volRatio > 0.55 ? 'var(--text-primary)' : 'var(--accent-green)';
              return (
                <div key={i} className="trading-card" style={{ padding: 16 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{r.underlying_name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{r.underlying_code} | {r.contract_count}个合约</div>
                    </div>
                    <span style={{
                      fontSize: 11, padding: '3px 10px', borderRadius: 3, fontWeight: 600,
                      background: volRatio > 0.9 ? 'rgba(255,82,82,0.15)' : volRatio > 0.75 ? 'rgba(255,152,0,0.15)' : volRatio > 0.55 ? 'rgba(33,150,243,0.15)' : 'rgba(0,200,83,0.15)',
                      color: volColor,
                    }}>
                      {volTag}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>成交量P/C: </span>
                      <span style={{ fontWeight: 600, color: volColor }}>{volRatio.toFixed(3)}</span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>持仓量P/C: </span>
                      <span style={{ fontWeight: 600 }}>{r.pc_ratio_oi.toFixed(3)}</span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>认购: </span>
                      <span style={{ fontWeight: 600, color: 'var(--accent-green)' }}>{formatNum(r.call_volume)}</span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>认沽: </span>
                      <span style={{ fontWeight: 600, color: 'var(--accent-red)' }}>{formatNum(r.put_volume)}</span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>OI认购: </span>
                      <span style={{ fontWeight: 600 }}>{formatNum(r.call_oi)}</span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>OI认沽: </span>
                      <span style={{ fontWeight: 600 }}>{formatNum(r.put_oi)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

        </div>
      )}

      {/* 持续跟踪报告 */}
      {activeTab === 'tracking' && (
        <div>
          {/* 子 Tab */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border-color)' }}>
            {[
              { key: 'cftc_track', label: 'CFTC 周度跟踪', icon: BarChart3 },
              { key: 'cboe_track', label: 'CBOE 日度跟踪', icon: Activity },
              { key: 'sse_track', label: 'SSE 期权日度跟踪', icon: TrendingUp },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setTrackingSubTab(tab.key as 'cftc_track' | 'cboe_track' | 'sse_track')}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '8px 16px',
                  background: 'transparent',
                  border: 'none',
                  borderBottom: trackingSubTab === tab.key ? '2px solid var(--accent-blue)' : '2px solid transparent',
                  color: trackingSubTab === tab.key ? 'var(--accent-blue)' : 'var(--text-secondary)',
                  fontSize: 12,
                  fontWeight: trackingSubTab === tab.key ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                <tab.icon size={14} />
                {tab.label}
              </button>
            ))}
          </div>

          {/* CFTC 周度跟踪 */}
          {trackingSubTab === 'cftc_track' && cftcTracking && (
            <div>
              {/* 综合解读 */}
              <div className="trading-card" style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <FileText size={14} color="var(--accent-blue)" />
                  CFTC 持续跟踪解读
                </h3>
                <div style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 8,
                  padding: '16px 20px',
                  fontSize: 14,
                  color: 'var(--text-primary)',
                  lineHeight: 1.9,
                }}>
                  {cftcTracking.summary_interpretation}
                </div>
                <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 11, color: 'var(--text-muted)' }}>
                  <span>报告日期: {cftcTracking.report_date}</span>
                  {cftcTracking.previous_report_date && <span>对比基准: {cftcTracking.previous_report_date}</span>}
                  <span>历史快照: {cftcTracking.snapshot_count} 周</span>
                </div>
              </div>

              {/* 汇总信号 */}
              {cftcTracking.aggregate_signals.length > 0 && (
                <div className="trading-card" style={{ marginBottom: 20 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Target size={14} color="var(--accent-yellow)" />
                    趋势信号汇总
                  </h3>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {(() => {
                      const signalTypes: Record<string, number> = {};
                      cftcTracking.aggregate_signals.forEach(s => {
                        signalTypes[s.type] = (signalTypes[s.type] || 0) + 1;
                      });
                      return Object.entries(signalTypes).map(([type, count]) => {
                        const colors: Record<string, string> = {
                          '连续增持': 'rgba(0,200,83,0.15)',
                          '连续减持': 'rgba(255,82,82,0.15)',
                          '拐点信号': 'rgba(255,152,0,0.2)',
                          '趋势加速': 'rgba(33,150,243,0.15)',
                          '趋势减速': 'rgba(156,39,176,0.15)',
                        };
                        const textColors: Record<string, string> = {
                          '连续增持': '#00c853',
                          '连续减持': '#ff5252',
                          '拐点信号': '#ff9800',
                          '趋势加速': '#2196f3',
                          '趋势减速': '#9c27b0',
                        };
                        return (
                          <span key={type} style={{
                            padding: '6px 14px',
                            borderRadius: 20,
                            background: colors[type] || 'var(--bg-tertiary)',
                            color: textColors[type] || 'var(--text-primary)',
                            fontSize: 12,
                            fontWeight: 600,
                          }}>
                            {type} x{count}
                          </span>
                        );
                      });
                    })()}
                  </div>
                </div>
              )}

              {/* 品种解读 */}
              <div className="trading-card">
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Zap size={14} color="var(--accent-yellow)" />
                  各品种持仓变化解读
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {cftcTracking.instrument_analysis.map((ia, i) => {
                    const hasSignals = ia.trend_signals.length > 0;
                    const hasChange = Object.keys(ia.changes).length > 0;
                    return (
                      <div key={i} style={{
                        padding: '12px 16px',
                        background: hasSignals ? 'rgba(255,152,0,0.05)' : 'var(--bg-tertiary)',
                        borderRadius: 8,
                        border: `1px solid ${hasSignals ? 'rgba(255,152,0,0.2)' : 'var(--border-color)'}`,
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{ia.instrument}</span>
                            <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                              {ia.section}
                            </span>
                            {ia.current.flow_state && (
                              <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, fontWeight: 600, ...flowTagStyle(ia.current.flow_state) }}>
                                {ia.current.flow_state}
                              </span>
                            )}
                            {ia.current.crowding?.label && (
                              <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, ...crowdingStyle(ia.current.crowding.level) }}>
                                {ia.current.crowding.label}
                              </span>
                            )}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 11 }}>
                            <span style={{ color: ia.current.net > 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                              净{ia.current.net > 0 ? '多' : '空'} {formatNum(Math.abs(ia.current.net))}
                            </span>
                            {hasChange && ia.changes.net_ww != null && (
                              <span style={{
                                color: ia.changes.net_ww! > 0 ? 'var(--accent-green)' : ia.changes.net_ww! < 0 ? 'var(--accent-red)' : 'var(--text-muted)',
                                display: 'flex', alignItems: 'center', gap: 2,
                              }}>
                                {ia.changes.net_ww! > 0 ? <ArrowUp size={10} /> : ia.changes.net_ww! < 0 ? <ArrowDown size={10} /> : <Minus size={10} />}
                                周变化 {ia.changes.net_ww! > 0 ? '+' : ''}{formatNum(ia.changes.net_ww!)}
                              </span>
                            )}
                          </div>
                        </div>
                        {/* 趋势信号 */}
                        {hasSignals && (
                          <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
                            {ia.trend_signals.map((s, si) => (
                              <span key={si} style={{
                                fontSize: 10, padding: '2px 8px', borderRadius: 3,
                                background: s.type === '拐点信号' ? 'rgba(255,152,0,0.15)' :
                                  s.type === '趋势加速' ? 'rgba(33,150,243,0.15)' :
                                  s.type === '连续增持' ? 'rgba(0,200,83,0.15)' :
                                  'rgba(255,82,82,0.15)',
                                color: s.type === '拐点信号' ? '#ff9800' :
                                  s.type === '趋势加速' ? '#2196f3' :
                                  s.type === '连续增持' ? '#00c853' : '#ff5252',
                                fontWeight: 600,
                              }}>
                                {s.type}
                              </span>
                            ))}
                          </div>
                        )}
                        {/* 解读 */}
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                          {ia.interpretation}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* CBOE 日度跟踪 */}
          {trackingSubTab === 'cboe_track' && cboeTracking && (
            <div>
              {/* 综合解读 */}
              <div className="trading-card" style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <FileText size={14} color="var(--accent-blue)" />
                  CBOE Put/Call 持续跟踪解读
                </h3>
                <div style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 8,
                  padding: '16px 20px',
                  fontSize: 14,
                  color: 'var(--text-primary)',
                  lineHeight: 1.9,
                }}>
                  {cboeTracking.interpretation}
                </div>
                <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 11, color: 'var(--text-muted)' }}>
                  <span>数据来源: {cboeTracking.source}</span>
                  <span>历史快照: {cboeTracking.snapshot_count} 天</span>
                  <span>生成时间: {cboeTracking.generated_at}</span>
                </div>
              </div>

              {/* 日度变化 */}
              {Object.keys(cboeTracking.daily_change).length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 20 }}>
                  {cboeTracking.daily_change.ratio_change != null && (
                    <div className="trading-card" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>日度变化</div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: cboeTracking.daily_change.ratio_change! > 0 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                        {cboeTracking.daily_change.ratio_change! > 0 ? '+' : ''}{cboeTracking.daily_change.ratio_change!.toFixed(4)}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {cboeTracking.daily_change.ratio_change_pct! > 0 ? '+' : ''}{cboeTracking.daily_change.ratio_change_pct}%
                      </div>
                    </div>
                  )}
                  {cboeTracking.daily_change.sentiment_changed && (
                    <div className="trading-card" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>情绪转变</div>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>
                        <span style={{ color: getSentimentColor(cboeTracking.daily_change.sentiment_prev || '') }}>
                          {cboeTracking.daily_change.sentiment_prev}
                        </span>
                        <span style={{ color: 'var(--text-muted)', margin: '0 6px' }}>→</span>
                        <span style={{ color: getSentimentColor(cboeTracking.current.sentiment) }}>
                          {cboeTracking.current.sentiment}
                        </span>
                      </div>
                    </div>
                  )}
                  {cboeTracking.daily_change.risk_changed && (
                    <div className="trading-card" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>风险等级变化</div>
                      <div style={{ fontSize: 14, fontWeight: 600 }}>
                        <span style={{ color: getRiskColor(cboeTracking.daily_change.risk_prev || '') }}>
                          {cboeTracking.daily_change.risk_prev === 'high' ? '高' : cboeTracking.daily_change.risk_prev === 'medium' ? '中' : '低'}
                        </span>
                        <span style={{ color: 'var(--text-muted)', margin: '0 6px' }}>→</span>
                        <span style={{ color: getRiskColor(cboeTracking.current.risk_level) }}>
                          {cboeTracking.current.risk_level === 'high' ? '高' : cboeTracking.current.risk_level === 'medium' ? '中' : '低'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 累积信号 */}
              {cboeTracking.cumulative_signals.length > 0 && (
                <div className="trading-card" style={{ marginBottom: 20 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Target size={14} color="var(--accent-yellow)" />
                    多日累积信号
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {cboeTracking.cumulative_signals.map((s, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'flex-start', gap: 10,
                        padding: '10px 14px',
                        background: s.level === 'warning' ? 'rgba(255,82,82,0.08)' :
                          s.level === 'caution' ? 'rgba(255,152,0,0.08)' : 'var(--bg-tertiary)',
                        borderRadius: 6,
                        border: `1px solid ${s.level === 'warning' ? 'rgba(255,82,82,0.2)' :
                          s.level === 'caution' ? 'rgba(255,152,0,0.2)' : 'var(--border-color)'}`,
                      }}>
                        {s.level === 'warning' ? <AlertTriangle size={14} color="var(--accent-red)" /> :
                          s.level === 'caution' ? <Info size={14} color="var(--accent-yellow)" /> :
                          <Info size={14} color="var(--accent-blue)" />}
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                            {s.type}
                            {s.days ? `（${s.days}天）` : ''}
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                            {s.detail}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 趋势数据表 */}
              {cboeTracking.trend_data.length > 0 && (
                <div className="trading-card">
                  <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Clock size={14} color="var(--accent-blue)" />
                    日度跟踪数据
                  </h3>
                  <div style={{ overflow: 'auto' }}>
                    <table className="data-table" style={{ fontSize: 11 }}>
                      <thead>
                        <tr>
                          <th>日期</th>
                          <th style={{ textAlign: 'right' }}>Total P/C</th>
                          <th style={{ textAlign: 'right' }}>5日均</th>
                          <th style={{ textAlign: 'right' }}>20日均</th>
                          <th style={{ textAlign: 'right' }}>Equity</th>
                          <th style={{ textAlign: 'right' }}>Index</th>
                          <th style={{ textAlign: 'center' }}>情绪</th>
                        </tr>
                      </thead>
                      <tbody>
                        {cboeTracking.trend_data.slice(0, 30).map((point, i) => {
                          const ratio = point.ratio;
                          let tagStyle: React.CSSProperties = {};
                          if (point.sentiment.includes('恐慌')) tagStyle = { background: 'rgba(255,82,82,0.15)', color: '#ff5252' };
                          else if (point.sentiment.includes('空')) tagStyle = { background: 'rgba(255,152,0,0.15)', color: '#ff9800' };
                          else if (point.sentiment.includes('乐观')) tagStyle = { background: 'rgba(0,200,83,0.15)', color: '#00c853' };
                          else tagStyle = { background: 'rgba(33,150,243,0.15)', color: '#2196f3' };
                          return (
                            <tr key={i}>
                              <td>{point.date}</td>
                              <td style={{ textAlign: 'right', fontWeight: 600, color: ratio > 0.9 ? 'var(--accent-red)' : ratio < 0.5 ? 'var(--accent-green)' : 'var(--text-primary)' }}>
                                {ratio.toFixed(3)}
                              </td>
                              <td style={{ textAlign: 'right' }}>{point.avg_5d.toFixed(3)}</td>
                              <td style={{ textAlign: 'right' }}>{point.avg_20d.toFixed(3)}</td>
                              <td style={{ textAlign: 'right' }}>{point.equity_ratio.toFixed(3)}</td>
                              <td style={{ textAlign: 'right' }}>{point.index_ratio.toFixed(3)}</td>
                              <td style={{ textAlign: 'center' }}>
                                <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, fontWeight: 600, ...tagStyle }}>
                                  {point.sentiment}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
          </div>
        )}

          {/* SSE 期权日度跟踪 */}
          {trackingSubTab === 'sse_track' && sseTracking && (
            <div>
              {/* 综合解读 */}
              <div className="trading-card" style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <FileText size={14} color="var(--accent-blue)" />
                  SSE 上交所期权持续跟踪解读
                </h3>
                <div style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 8,
                  padding: '16px 20px',
                  fontSize: 14,
                  color: 'var(--text-primary)',
                  lineHeight: 1.9,
                }}>
                  {sseTracking.interpretation}
                </div>
                <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 11, color: 'var(--text-muted)' }}>
                  <span>数据来源: {sseTracking.source}</span>
                  <span>历史快照: {sseTracking.snapshot_count} 天</span>
                  <span>生成时间: {sseTracking.generated_at}</span>
                </div>
              </div>

              {/* 日度变化 */}
              {Object.keys(sseTracking.daily_change).length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 20 }}>
                  {sseTracking.daily_change.vol_change != null && (
                    <div className="trading-card" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>成交量P/C 日度变化</div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: sseTracking.daily_change.vol_change! > 0 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                        {sseTracking.daily_change.vol_change! > 0 ? '+' : ''}{sseTracking.daily_change.vol_change!.toFixed(4)}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {sseTracking.daily_change.vol_change_pct! > 0 ? '+' : ''}{sseTracking.daily_change.vol_change_pct}%
                      </div>
                    </div>
                  )}
                  {sseTracking.daily_change.oi_change != null && (
                    <div className="trading-card" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>持仓量P/C 日度变化</div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: sseTracking.daily_change.oi_change! > 0 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                        {sseTracking.daily_change.oi_change! > 0 ? '+' : ''}{sseTracking.daily_change.oi_change!.toFixed(4)}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {sseTracking.daily_change.oi_change_pct! > 0 ? '+' : ''}{sseTracking.daily_change.oi_change_pct}%
                      </div>
                    </div>
                  )}
                  {sseTracking.daily_change.prev_date && (
                    <div className="trading-card" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>对比基准日</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
                        {sseTracking.daily_change.prev_date}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 汇总卡片 */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 12, marginBottom: 20 }}>
                <div className="trading-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>成交量 P/C</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: getSentimentColor(sseTracking.current.sentiment) }}>
                    {sseTracking.current.pc_ratio_volume.toFixed(3)}
                  </div>
                </div>
                <div className="trading-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>持仓量 P/C</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {sseTracking.current.pc_ratio_oi.toFixed(3)}
                  </div>
                </div>
                <div className="trading-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>市场情绪</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: getSentimentColor(sseTracking.current.sentiment) }}>
                    {sseTracking.current.sentiment}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    风险: <span style={{ color: getRiskColor(sseTracking.current.risk_level), fontWeight: 600 }}>{sseTracking.current.risk_level === 'high' ? '高' : sseTracking.current.risk_level === 'medium' ? '中' : '低'}</span>
                  </div>
                </div>
                <div className="trading-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>5日均值</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {sseTracking.current.avg_5d_volume.toFixed(3)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    趋势: {sseTracking.current.trend}
                  </div>
                </div>
                <div className="trading-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>20日波动率</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: sseTracking.current.volatility_20d > 0.08 ? 'var(--accent-yellow)' : 'var(--text-primary)' }}>
                    {sseTracking.current.volatility_20d.toFixed(3)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    20日均: {sseTracking.current.avg_20d_volume.toFixed(3)}
                  </div>
                </div>
                <div className="trading-card" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>分位数</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {sseTracking.current.percentile_volume.toFixed(0)}%
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    信号: {sseTracking.current.signal?.substring(0, 20)}...
                  </div>
                </div>
              </div>

              {/* 累积信号 */}
              {sseTracking.cumulative_signals.length > 0 && (
                <div className="trading-card" style={{ marginBottom: 20 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Target size={14} color="var(--accent-yellow)" />
                    多日累积信号
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {sseTracking.cumulative_signals.map((s, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'flex-start', gap: 10,
                        padding: '10px 14px',
                        background: s.level === 'warning' ? 'rgba(255,82,82,0.08)' :
                          s.level === 'caution' ? 'rgba(255,152,0,0.08)' : 'var(--bg-tertiary)',
                        borderRadius: 6,
                        border: `1px solid ${s.level === 'warning' ? 'rgba(255,82,82,0.2)' :
                          s.level === 'caution' ? 'rgba(255,152,0,0.2)' : 'var(--border-color)'}`,
                      }}>
                        {s.level === 'warning' ? <AlertTriangle size={14} color="var(--accent-red)" /> :
                          s.level === 'caution' ? <Info size={14} color="var(--accent-yellow)" /> :
                          <Info size={14} color="var(--accent-blue)" />}
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                            {s.type}
                            {s.days ? `（${s.days}天）` : ''}
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                            {s.detail}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 各标的详情 */}
              {sseTracking.records && sseTracking.records.length > 0 && (
                <div className="trading-card" style={{ marginBottom: 20 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Zap size={14} color="var(--accent-yellow)" />
                    各标的 Put/Call 详情
                  </h3>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
                    {sseTracking.records.map((r, i) => {
                      const volRatio = r.pc_ratio_volume;
                      const volTag = volRatio > 0.9 ? '恐慌' : volRatio > 0.75 ? '偏空' : volRatio > 0.55 ? '中性' : '乐观';
                      const volColor = volRatio > 0.9 ? 'var(--accent-red)' : volRatio > 0.75 ? 'var(--accent-yellow)' : volRatio > 0.55 ? 'var(--text-primary)' : 'var(--accent-green)';
                      return (
                        <div key={i} style={{
                          padding: '12px 14px',
                          background: 'var(--bg-tertiary)',
                          borderRadius: 6,
                          border: '1px solid var(--border-color)',
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{r.underlying_name}</span>
                            <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 3, fontWeight: 600,
                              background: volRatio > 0.9 ? 'rgba(255,82,82,0.15)' : volRatio > 0.75 ? 'rgba(255,152,0,0.15)' : volRatio > 0.55 ? 'rgba(33,150,243,0.15)' : 'rgba(0,200,83,0.15)',
                              color: volColor,
                            }}>{volTag}</span>
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 12px', fontSize: 11 }}>
                            <div><span style={{ color: 'var(--text-muted)' }}>成交量P/C: </span><span style={{ fontWeight: 600, color: volColor }}>{volRatio.toFixed(3)}</span></div>
                            <div><span style={{ color: 'var(--text-muted)' }}>持仓量P/C: </span><span style={{ fontWeight: 600 }}>{r.pc_ratio_oi.toFixed(3)}</span></div>
                            <div><span style={{ color: 'var(--text-muted)' }}>认购: </span><span style={{ fontWeight: 600, color: 'var(--accent-green)' }}>{formatNum(r.call_volume)}</span></div>
                            <div><span style={{ color: 'var(--text-muted)' }}>认沽: </span><span style={{ fontWeight: 600, color: 'var(--accent-red)' }}>{formatNum(r.put_volume)}</span></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 趋势数据表 */}
              {sseTracking.trend_data.length > 0 && (
                <div className="trading-card">
                  <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Clock size={14} color="var(--accent-blue)" />
                    SSE 期权日度跟踪数据
                  </h3>
                  <div style={{ overflow: 'auto' }}>
                    <table className="data-table" style={{ fontSize: 11 }}>
                      <thead>
                        <tr>
                          <th>日期</th>
                          <th style={{ textAlign: 'right' }}>成交量 P/C</th>
                          <th style={{ textAlign: 'right' }}>持仓量 P/C</th>
                          <th style={{ textAlign: 'right' }}>认购量</th>
                          <th style={{ textAlign: 'right' }}>认沽量</th>
                          <th style={{ textAlign: 'center' }}>情绪</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sseTracking.trend_data.slice(0, 30).map((point, i) => {
                          const ratio = point.pc_ratio_volume;
                          let tagStyle: React.CSSProperties = {};
                          if (point.sentiment.includes('恐慌')) tagStyle = { background: 'rgba(255,82,82,0.15)', color: '#ff5252' };
                          else if (point.sentiment.includes('空')) tagStyle = { background: 'rgba(255,152,0,0.15)', color: '#ff9800' };
                          else if (point.sentiment.includes('乐观')) tagStyle = { background: 'rgba(0,200,83,0.15)', color: '#00c853' };
                          else tagStyle = { background: 'rgba(33,150,243,0.15)', color: '#2196f3' };
                          return (
                            <tr key={i}>
                              <td>{point.date}</td>
                              <td style={{ textAlign: 'right', fontWeight: 600, color: ratio > 0.85 ? 'var(--accent-red)' : ratio < 0.45 ? 'var(--accent-green)' : 'var(--text-primary)' }}>
                                {ratio.toFixed(3)}
                              </td>
                              <td style={{ textAlign: 'right' }}>{point.pc_ratio_oi.toFixed(3)}</td>
                              <td style={{ textAlign: 'right' }}>{formatNum(point.call_volume)}</td>
                              <td style={{ textAlign: 'right' }}>{formatNum(point.put_volume)}</td>
                              <td style={{ textAlign: 'center' }}>
                                <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, fontWeight: 600, ...tagStyle }}>
                                  {point.sentiment}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ========== CFTC 表格子组件 ==========

function CFTCTable({ items }: { items: CFTCItem[] }) {
  const sections = new Map<string, CFTCItem[]>();
  items.forEach(item => {
    const sec = item.section || '其他';
    if (!sections.has(sec)) sections.set(sec, []);
    sections.get(sec)!.push(item);
  });

  return (
    <div style={{ overflow: 'auto' }}>
      <table className="data-table" style={{ fontSize: 11 }}>
        <thead>
          <tr>
            <th>资产</th>
            <th style={{ textAlign: 'right' }}>净持仓</th>
            <th style={{ textAlign: 'center' }}>z</th>
            <th style={{ textAlign: 'right' }}>周变化</th>
            <th style={{ textAlign: 'right' }}>多头</th>
            <th style={{ textAlign: 'center' }}>z</th>
            <th style={{ textAlign: 'right' }}>周变化</th>
            <th style={{ textAlign: 'right' }}>空头</th>
            <th style={{ textAlign: 'center' }}>z</th>
            <th style={{ textAlign: 'right' }}>周变化</th>
            <th style={{ textAlign: 'center' }}>动作</th>
            <th style={{ textAlign: 'center' }}>拥挤度</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(sections.entries()).map(([section, secItems]) => (
            <>
              <tr key={section} style={{ background: 'var(--bg-tertiary)' }}>
                <td colSpan={12} style={{ fontWeight: 700, fontSize: 12, color: 'var(--accent-green)', padding: '6px 8px' }}>
                  {section}
                </td>
              </tr>
              {secItems.map((item, idx) => (
                <tr key={idx} style={{ background: idx % 2 === 0 ? 'transparent' : 'var(--bg-tertiary)' }}>
                  <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{item.instrument}</td>
                  <td style={{ textAlign: 'right', fontWeight: 600, color: item.net > 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                    {formatNum(item.net)}
                  </td>
                  <td><ZBar value={item.net_z} /></td>
                  <ChgTd chg={item.net_ww} z={item.net_ww_z} />
                  <td style={{ textAlign: 'right', fontSize: 11 }}>{formatNum(item.long)}</td>
                  <td><ZBar value={item.long_z} /></td>
                  <ChgTd chg={item.long_ww} z={item.long_ww_z} />
                  <td style={{ textAlign: 'right', fontSize: 11 }}>{formatNum(item.short)}</td>
                  <td><ZBar value={item.short_z} /></td>
                  <ChgTd chg={item.short_ww} z={item.short_ww_z} />
                  <td style={{ textAlign: 'center' }}>
                    {item.flow_state ? (
                      <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, fontWeight: 600, ...flowTagStyle(item.flow_state) }}>
                        {item.flow_state}
                      </span>
                    ) : '-'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    {item.crowding?.label ? (
                      <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, ...crowdingStyle(item.crowding.level) }}>
                        {item.crowding.label}
                      </span>
                    ) : '-'}
                  </td>
                </tr>
              ))}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}