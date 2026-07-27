import { useState, useEffect } from 'react';
import { newsApi } from '../../api';
import {
  Newspaper,
  Zap,
  TrendingUp,
  TrendingDown,
  Globe,
  Landmark,
  Mic2,
  Users,
  Building2,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  ExternalLink,
  RefreshCw,
  Calendar,
  AlertTriangle,
  DollarSign,
  Lightbulb,
  FileText,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface MarketEvent {
  id: string;
  time: string;
  title: string;
  country: string;
  category: string;
  impact: string;
  previous: string;
  forecast: string;
  actual: string;
  description: string;
  related_assets: string[];
}

interface DailyEventsData {
  date: string;
  summary: string;
  events: MarketEvent[];
  by_category: {
    economic_data: MarketEvent[];
    central_bank: MarketEvent[];
    speeches: MarketEvent[];
    meetings: MarketEvent[];
  };
  high_impact: MarketEvent[];
}

interface Insight {
  id: string;
  source: string;
  author: string;
  role: string;
  date: string;
  title: string;
  summary: string;
  topic: string;
  sentiment: string;
  tags: string[];
  url: string;
}

interface HoldingChange {
  symbol: string;
  name: string;
  shares?: number;
  value?: number;
  change_pct?: number;
}

interface Filing13F {
  id: string;
  institution: string;
  filing_date: string;
  period: string;
  portfolio_value: number;
  portfolio_value_change: number;
  top_holdings: HoldingChange[];
  new_positions: HoldingChange[];
  increased_positions: HoldingChange[];
  reduced_positions: HoldingChange[];
  closed_positions: HoldingChange[];
  strategy_note: string;
}

interface MonitorData {
  report_date: string;
  total_filings: number;
  institutions: {
    name: string;
    total_new_positions: number;
    total_closed_positions: number;
    total_value_change: number;
    filings: Filing13F[];
  }[];
  filings: Filing13F[];
}

export default function NewsPage() {
  const [events, setEvents] = useState<DailyEventsData | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [monitor13F, setMonitor13F] = useState<MonitorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'events' | 'insights' | '13f'>('events');
  const [expandedInsight, setExpandedInsight] = useState<string | null>(null);
  const [expandedFiling, setExpandedFiling] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [eventsRes, insightsRes, monitorRes] = await Promise.all([
        newsApi.getDailyEvents() as Promise<DailyEventsData>,
        newsApi.getInsights(3) as Promise<{ insights: Insight[] }>,
        newsApi.get13FMonitor(45) as Promise<MonitorData>,
      ]);
      setEvents(eventsRes);
      setInsights(insightsRes.insights || []);
      setMonitor13F(monitorRes);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '数据加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const formatMoney = (n: number) => {
    if (Math.abs(n) >= 1e12) return (n / 1e12).toFixed(2) + 'T';
    if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B';
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    return n.toLocaleString();
  };

  const getImpactLabel = (impact: string) => {
    if (impact === 'high') return '高';
    if (impact === 'medium') return '中';
    return '低';
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'economic_data': return <DollarSign size={14} />;
      case 'central_bank': return <Landmark size={14} />;
      case 'speech': return <Mic2 size={14} />;
      case 'meeting': return <Users size={14} />;
      default: return <Globe size={14} />;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'economic_data': return '经济数据';
      case 'central_bank': return '央行动态';
      case 'speech': return '官员讲话';
      case 'meeting': return '重要会议';
      default: return category;
    }
  };

  const getSentimentIcon = (sentiment: string) => {
    if (sentiment === 'bullish') return <TrendingUp size={14} color="var(--accent-green)" />;
    if (sentiment === 'bearish') return <TrendingDown size={14} color="var(--accent-red)" />;
    return <Minus size={14} color="var(--text-secondary)" />;
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <div className="loading-spinner" />
        <span style={{ marginLeft: 12, color: 'var(--text-secondary)' }}>加载新闻数据...</span>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* 标题 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>新闻推送</h1>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            市场事件日报 · 硅谷观点 · 13F 持仓监控
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchData} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <RefreshCw size={14} />
          刷新
        </button>
      </div>

      {error && (
        <div style={{ background: 'rgba(239,83,80,0.1)', border: '1px solid rgba(239,83,80,0.3)', borderRadius: 6, padding: '12px 16px', marginBottom: 16, color: 'var(--accent-red)', fontSize: 13 }}>
          <AlertTriangle size={14} style={{ display: 'inline', marginRight: 6 }} />
          {error}
        </div>
      )}

      {/* Tab 切换 */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border-color)' }}>
        {[
          { key: 'events', label: '市场事件日报', icon: Calendar },
          { key: 'insights', label: '硅谷顶级观点', icon: Lightbulb },
          { key: '13f', label: '13F 持仓监控', icon: FileText },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as typeof activeTab)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '10px 20px', background: 'transparent', border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid var(--accent-green)' : '2px solid transparent',
              color: activeTab === tab.key ? 'var(--accent-green)' : 'var(--text-secondary)',
              fontSize: 13, fontWeight: activeTab === tab.key ? 600 : 400,
              cursor: 'pointer', transition: 'all 0.2s',
            }}
          >
            <tab.icon size={16} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ===== 市场事件日报 ===== */}
      {activeTab === 'events' && events && (
        <div>
          {/* 摘要卡片 */}
          <div className="trading-card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 8, background: 'rgba(38,166,154,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Newspaper size={20} color="var(--accent-green)" />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {events.date} 市场事件日报
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                  {events.summary}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                {['economic_data', 'central_bank', 'speeches', 'meetings'].map(cat => {
                  const count = events.by_category[cat as keyof typeof events.by_category]?.length || 0;
                  return (
                    <div key={cat} style={{ textAlign: 'center', padding: '6px 10px', background: 'var(--bg-tertiary)', borderRadius: 6, border: '1px solid var(--border-color)' }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{getCategoryLabel(cat)}</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>{count}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* 高影响事件 */}
          {events.high_impact.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--accent-red)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Zap size={14} />
                高影响事件
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {events.high_impact.map(event => (
                  <div key={event.id} style={{
                    background: 'rgba(239,83,80,0.05)', border: '1px solid rgba(239,83,80,0.2)',
                    borderRadius: 8, padding: '14px 16px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                          <span className="tag tag-red">高影响</span>
                          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{event.time}</span>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{event.country}</span>
                        </div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>{event.title}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{event.description}</div>
                        <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                          {event.related_assets.map(asset => (
                            <span key={asset} style={{ fontSize: 10, padding: '2px 6px', background: 'var(--bg-tertiary)', borderRadius: 3, color: 'var(--text-muted)' }}>
                              {asset}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 16, textAlign: 'center', flexShrink: 0 }}>
                        <div>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>前值</div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>{event.previous}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>预期</div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent-blue)' }}>{event.forecast}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>实际</div>
                          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent-green)' }}>{event.actual}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 全部事件列表 */}
          <div className="trading-card">
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
              全部事件 ({events.events.length})
            </h3>
            <div style={{ overflow: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: 80 }}>时间</th>
                    <th style={{ width: 50 }}>类型</th>
                    <th>事件</th>
                    <th style={{ width: 50 }}>国家</th>
                    <th style={{ width: 50, textAlign: 'center' }}>影响</th>
                    <th style={{ width: 70, textAlign: 'right' }}>前值</th>
                    <th style={{ width: 70, textAlign: 'right' }}>预期</th>
                    <th style={{ width: 70, textAlign: 'right' }}>实际</th>
                  </tr>
                </thead>
                <tbody>
                  {events.events.map(event => (
                    <tr key={event.id}>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{event.time.split(' ')[1] || event.time}</td>
                      <td>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'var(--text-muted)' }}>
                          {getCategoryIcon(event.category)}
                          {getCategoryLabel(event.category)}
                        </span>
                      </td>
                      <td style={{ fontWeight: 500 }}>{event.title}</td>
                      <td>{event.country}</td>
                      <td style={{ textAlign: 'center' }}>
                        <span className={`tag ${event.impact === 'high' ? 'tag-red' : event.impact === 'medium' ? 'tag-yellow' : 'tag-blue'}`}>
                          {getImpactLabel(event.impact)}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right', color: 'var(--text-secondary)' }}>{event.previous}</td>
                      <td style={{ textAlign: 'right', color: 'var(--accent-blue)' }}>{event.forecast}</td>
                      <td style={{ textAlign: 'right', fontWeight: 600, color: event.actual === '待公布' ? 'var(--text-muted)' : 'var(--accent-green)' }}>
                        {event.actual}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ===== 硅谷顶级观点 ===== */}
      {activeTab === 'insights' && (
        <div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {insights.map(insight => (
              <div key={insight.id} className="trading-card" style={{ padding: '16px 20px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                  {/* 机构 Logo */}
                  <div style={{
                    width: 44, height: 44, borderRadius: 10,
                    background: 'linear-gradient(135deg, #1c2333, #2a3a5c)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, border: '1px solid var(--border-color)',
                  }}>
                    <Building2 size={20} color="var(--accent-blue)" />
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--accent-blue)' }}>{insight.source}</span>
                        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{insight.author}</span>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{insight.role}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span className={`tag ${insight.sentiment === 'bullish' ? 'tag-green' : insight.sentiment === 'bearish' ? 'tag-red' : 'tag-blue'}`}>
                          {getSentimentIcon(insight.sentiment)}
                          <span style={{ marginLeft: 4 }}>
                            {insight.sentiment === 'bullish' ? '看多' : insight.sentiment === 'bearish' ? '看空' : '中性'}
                          </span>
                        </span>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{insight.date}</span>
                      </div>
                    </div>

                    <div
                      style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6, cursor: 'pointer' }}
                      onClick={() => setExpandedInsight(expandedInsight === insight.id ? null : insight.id)}
                    >
                      {insight.title}
                    </div>

                    {expandedInsight === insight.id && (
                      <div className="animate-fade-in" style={{ marginBottom: 8 }}>
                        <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                          {insight.summary}
                        </p>
                      </div>
                    )}

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 }}>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {insight.tags.map(tag => (
                          <span key={tag} style={{ fontSize: 10, padding: '2px 6px', background: 'var(--bg-tertiary)', borderRadius: 3, color: 'var(--text-muted)' }}>
                            #{tag}
                          </span>
                        ))}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <button
                          onClick={() => setExpandedInsight(expandedInsight === insight.id ? null : insight.id)}
                          style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', gap: 2 }}
                        >
                          {expandedInsight === insight.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          {expandedInsight === insight.id ? '收起' : '展开'}
                        </button>
                        <ExternalLink size={12} color="var(--text-muted)" style={{ cursor: 'pointer' }} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ===== 13F 持仓监控 ===== */}
      {activeTab === '13f' && monitor13F && (
        <div>
          {/* 概览卡片 */}
          <div className="trading-card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 40, height: 40, borderRadius: 8, background: 'rgba(88,166,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <FileText size={20} color="var(--accent-blue)" />
              </div>
              <div>
                <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>
                  SEC EDGAR 13F 持仓监控
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                  报告日期: {monitor13F.report_date} · 共追踪 {monitor13F.total_filings} 份13F申报 · {monitor13F.institutions.length} 家机构
                </div>
              </div>
            </div>
          </div>

          {/* 机构列表 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {monitor13F.filings.map(filing => (
              <div key={filing.id} className="trading-card" style={{ padding: '16px 20px' }}>
                {/* 机构头部 */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 36, height: 36, borderRadius: 8, background: 'linear-gradient(135deg, #1a3a5c, #2a5a8c)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--border-color)' }}>
                      <Building2 size={18} color="var(--accent-blue)" />
                    </div>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>{filing.institution}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {filing.period} · 申报日期 {filing.filing_date} · 组合规模 {formatMoney(filing.portfolio_value)}
                        <span style={{ marginLeft: 8, color: filing.portfolio_value_change >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                          {filing.portfolio_value_change >= 0 ? '+' : ''}{formatMoney(filing.portfolio_value_change)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <button
                    className="btn-secondary"
                    onClick={() => setExpandedFiling(expandedFiling === filing.id ? null : filing.id)}
                    style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px' }}
                  >
                    {expandedFiling === filing.id ? '收起详情' : '查看详情'}
                    {expandedFiling === filing.id ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  </button>
                </div>

                {/* 前5大持仓 */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8, marginBottom: 12 }}>
                  {filing.top_holdings.map((h, i) => (
                    <div key={i} style={{ background: 'var(--bg-tertiary)', borderRadius: 6, padding: '8px 12px', border: '1px solid var(--border-color)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, fontSize: 12 }}>{h.symbol}</span>
                        <span style={{ fontSize: 10, color: (h.change_pct || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                          {(h.change_pct || 0) >= 0 ? '+' : ''}{h.change_pct?.toFixed(1)}%
                        </span>
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{h.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                        {formatMoney(h.value || 0)}
                      </div>
                    </div>
                  ))}
                </div>

                {/* 操作摘要标签 */}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {filing.new_positions.length > 0 && (
                    <span className="tag tag-green" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <ArrowUpRight size={10} />
                      新建仓 {filing.new_positions.length} 只
                    </span>
                  )}
                  {filing.increased_positions.length > 0 && (
                    <span className="tag tag-blue" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <TrendingUp size={10} />
                      加仓 {filing.increased_positions.length} 只
                    </span>
                  )}
                  {filing.reduced_positions.length > 0 && (
                    <span className="tag tag-yellow" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <TrendingDown size={10} />
                      减仓 {filing.reduced_positions.length} 只
                    </span>
                  )}
                  {filing.closed_positions.length > 0 && (
                    <span className="tag tag-red" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <ArrowDownRight size={10} />
                      清仓 {filing.closed_positions.length} 只
                    </span>
                  )}
                </div>

                {/* 展开详情 */}
                {expandedFiling === filing.id && (
                  <div className="animate-fade-in" style={{ marginTop: 14, borderTop: '1px solid var(--border-color)', paddingTop: 14 }}>
                    {/* 策略分析 */}
                    <div style={{ background: 'var(--bg-tertiary)', borderRadius: 6, padding: '12px 14px', marginBottom: 14, border: '1px solid var(--border-color)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>策略分析</div>
                      <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{filing.strategy_note}</div>
                    </div>

                    {/* 详细变动 */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      {/* 新建仓 & 加仓 */}
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase' }}>
                          新建仓 & 加仓
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {[...filing.new_positions, ...filing.increased_positions].map((item, i) => (
                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 8px', background: 'rgba(38,166,154,0.05)', borderRadius: 3, fontSize: 12 }}>
                              <span style={{ fontWeight: 500, color: 'var(--accent-green)' }}>{item.symbol}</span>
                              <span style={{ color: 'var(--text-secondary)' }}>{item.name}</span>
                              <span style={{ color: 'var(--text-muted)' }}>
                                {item.change_pct ? `+${item.change_pct}%` : item.value ? formatMoney(item.value) : '新建'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* 减仓 & 清仓 */}
                      <div>
                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase' }}>
                          减仓 & 清仓
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {[...filing.reduced_positions, ...filing.closed_positions].map((item, i) => (
                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 8px', background: 'rgba(239,83,80,0.05)', borderRadius: 3, fontSize: 12 }}>
                              <span style={{ fontWeight: 500, color: 'var(--accent-red)' }}>{item.symbol}</span>
                              <span style={{ color: 'var(--text-secondary)' }}>{item.name}</span>
                              <span style={{ color: 'var(--text-muted)' }}>
                                {item.change_pct ? `${item.change_pct}%` : '清仓'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}