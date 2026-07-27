import { useState, useEffect } from 'react';
import { stockApi } from '../../api';
import {
  Search,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Shield,
  FileText,
  BarChart3,
  Loader2,
  CheckCircle,
  XCircle,
  MinusCircle,
  ChevronDown,
  ChevronRight,
  Key,
  Cpu,
} from 'lucide-react';

// ========== Types ==========

interface Quote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  amount: number;
  high: number;
  low: number;
  open: number;
  pre_close: number;
}

interface TechnicalIndicators {
  ma5: number;
  ma10: number;
  ma20: number;
  ma60: number;
  rsi: number;
  macd: number;
  macd_signal: number;
  macd_hist: number;
  bollinger_upper: number;
  bollinger_middle: number;
  bollinger_lower: number;
  volume_ratio: number;
}

interface FundamentalData {
  pe_ratio: number;
  pb_ratio: number;
  market_cap: number;
  revenue_growth?: number;
  profit_growth?: number;
  roe?: number;
  debt_ratio?: number;
  dividend_yield?: number;
}

interface Signal {
  type: string;
  indicator: string;
  message: string;
}

interface KlineData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface AnalysisResult {
  symbol: string;
  name: string;
  market: string;
  latest_price: number;
  change_pct: number;
  technical: TechnicalIndicators;
  fundamental: FundamentalData;
  signals: Signal[];
  risk_level: string;
  analysis_summary: string;
  charts: { kline: KlineData[] };
}

interface ResearchReport {
  symbol: string;
  name: string;
  market: string;
  report_markdown: string;
  report_time: string;
  sections: Record<string, unknown>;
}

// ========== Simple Markdown Renderer ==========

function MarkdownRenderer({ content }: { content: string }) {
  const renderLine = (line: string, key: number) => {
    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      return <hr key={key} style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '16px 0' }} />;
    }

    // Headers
    if (/^### (.+)/.test(line)) {
      return <h3 key={key} style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', margin: '16px 0 8px' }}>{line.replace(/^### /, '')}</h3>;
    }
    if (/^## (.+)/.test(line)) {
      return <h2 key={key} style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', margin: '20px 0 10px', paddingBottom: 6, borderBottom: '1px solid var(--border-color)' }}>{line.replace(/^## /, '')}</h2>;
    }
    if (/^# (.+)/.test(line)) {
      return <h1 key={key} style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', margin: '24px 0 12px' }}>{line.replace(/^# /, '')}</h1>;
    }

    // Blockquote
    if (/^> (.+)/.test(line)) {
      return (
        <div key={key} style={{
          borderLeft: '3px solid var(--accent-green)',
          paddingLeft: 12,
          margin: '8px 0',
          color: 'var(--text-secondary)',
          fontSize: 13,
          lineHeight: 1.6,
          background: 'rgba(38,166,154,0.05)',
          padding: '8px 12px',
          borderRadius: '0 4px 4px 0',
        }}>
          {renderInline(line.replace(/^> /, ''))}
        </div>
      );
    }

    // Bold list items
    if (/^\d+\.\s\*\*(.+)\*\*/.test(line)) {
      const match = line.match(/^\d+\.\s\*\*(.+)\*\*(.*)/);
      if (match) {
        return (
          <div key={key} style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '4px 0', paddingLeft: 16, lineHeight: 1.6 }}>
            <strong style={{ color: 'var(--text-primary)' }}>{match[1]}</strong>{match[2]}
          </div>
        );
      }
    }

    // Unordered list items
    if (/^-\s(.+)/.test(line)) {
      return (
        <div key={key} style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '4px 0', paddingLeft: 16, lineHeight: 1.6 }}>
          • {renderInline(line.replace(/^-\s/, ''))}
        </div>
      );
    }

    // Ordered list items
    if (/^\d+\.\s(.+)/.test(line)) {
      return (
        <div key={key} style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '4px 0', paddingLeft: 16, lineHeight: 1.6 }}>
          {renderInline(line)}
        </div>
      );
    }

    // Empty line
    if (!line.trim()) {
      return <div key={key} style={{ height: 4 }} />;
    }

    // Default paragraph
    return <p key={key} style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '4px 0', lineHeight: 1.6 }}>{renderInline(line)}</p>;
  };

  const renderInline = (text: string): React.ReactNode => {
    // Handle bold text
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{part.slice(2, -2)}</strong>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  // Split into sections: text, tables
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Detect table start (line with pipes, next line with dashes)
    if (line.includes('|') && i + 1 < lines.length && /^[|\-:\s]+$/.test(lines[i + 1])) {
      const headerLine = line;
      const rows: string[][] = [];
      const headers = headerLine.split('|').filter(c => c.trim()).map(c => c.trim());

      let j = i + 2;
      while (j < lines.length && lines[j].includes('|')) {
        const cells = lines[j].split('|').filter(c => c.trim()).map(c => c.trim());
        if (cells.length > 0) rows.push(cells);
        j++;
      }

      // Render table
      elements.push(
        <div key={`table-${i}`} style={{ overflowX: 'auto', margin: '12px 0' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 12,
          }}>
            <thead>
              <tr>
                {headers.map((h, hi) => (
                  <th key={hi} style={{
                    padding: '8px 12px',
                    textAlign: 'left',
                    borderBottom: '2px solid var(--border-color)',
                    color: 'var(--text-primary)',
                    fontWeight: 600,
                    fontSize: 12,
                    background: 'var(--bg-tertiary)',
                  }}>
                    {renderInline(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri} style={{
                  background: ri % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                }}>
                  {row.map((cell, ci) => (
                    <td key={ci} style={{
                      padding: '6px 12px',
                      borderBottom: '1px solid var(--border-color)',
                      color: 'var(--text-secondary)',
                      lineHeight: 1.5,
                    }}>
                      {renderInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

      i = j;
      continue;
    }

    // Regular line
    elements.push(renderLine(line, i));
    i++;
  }

  return <div style={{ lineHeight: 1.6 }}>{elements}</div>;
}

// ========== K线图组件 ==========

function KlineChart({ data, latestPrice, changePct }: { data: KlineData[]; latestPrice: number; changePct: number }) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const [hoverX, setHoverX] = useState(0);

  const svgRef = { current: null as SVGSVGElement | null };

  if (!data || data.length === 0) return null;

  const PADDING = { top: 20, right: 70, bottom: 50, left: 10 };
  const CHART_W = 800;
  const CHART_H = 380;
  const VOLUME_H = 60;
  const TOTAL_H = CHART_H + VOLUME_H;
  const PLOT_W = CHART_W - PADDING.left - PADDING.right;
  const PLOT_H = CHART_H - PADDING.top - PADDING.bottom;

  // 价格范围
  const prices = data.flatMap(k => [k.high, k.low]);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const priceRange = maxP - minP || 1;
  const priceMargin = priceRange * 0.05;
  const yMin = minP - priceMargin;
  const yMax = maxP + priceMargin;
  const yRange = yMax - yMin;

  // 成交量范围
  const volumes = data.map(k => k.volume);
  const maxVol = Math.max(...volumes, 1);

  // 坐标转换
  const toX = (i: number) => PADDING.left + (i / Math.max(data.length - 1, 1)) * PLOT_W;
  const toY = (price: number) => PADDING.top + ((yMax - price) / yRange) * PLOT_H;
  const barWidth = Math.max(1.5, Math.min(7, PLOT_W / data.length * 0.7));

  // Y轴刻度标签
  const yTicks = 5;
  const yTickValues = Array.from({ length: yTicks }, (_, i) => yMin + (yRange / (yTicks - 1)) * i);

  // X轴日期标签（约8-10个）
  const xTickCount = Math.min(8, data.length);
  const xTickInterval = Math.max(1, Math.floor(data.length / xTickCount));
  const xTickIndices: number[] = [];
  for (let i = 0; i < data.length; i += xTickInterval) {
    xTickIndices.push(i);
  }
  // 确保最后一个也显示
  if (xTickIndices[xTickIndices.length - 1] !== data.length - 1) {
    xTickIndices.push(data.length - 1);
  }

  const formatDate = (dateStr: string) => {
    // 格式: 2026-07-25 → 07-25, 或显示完整日期
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length === 3) return `${parts[1]}-${parts[2]}`;
    return dateStr;
  };

  const formatPrice = (p: number) => {
    if (p >= 1000) return p.toFixed(0);
    if (p >= 100) return p.toFixed(1);
    if (p >= 1) return p.toFixed(2);
    return p.toFixed(3);
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const scaleX = CHART_W / rect.width;
    const mx = (e.clientX - rect.left) * scaleX;

    setHoverX(mx);

    // 找到最近的K线
    let closest = 0;
    let minDist = Infinity;
    for (let i = 0; i < data.length; i++) {
      const cx = toX(i);
      const dist = Math.abs(mx - cx);
      if (dist < minDist) {
        minDist = dist;
        closest = i;
      }
    }
    setHoverIndex(closest);
  };

  const handleMouseLeave = () => {
    setHoverIndex(null);
  };

  const hoverK = hoverIndex !== null ? data[hoverIndex] : null;
  const isUp = changePct >= 0;
  const accentColor = isUp ? '#26a69a' : '#ef5350';

  return (
    <div className="trading-card" style={{ padding: '12px 0 0 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 16px', marginBottom: 8 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
          K线走势
        </h3>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          共 {data.length} 根K线 · {formatDate(data[0]?.date)} ~ {formatDate(data[data.length - 1]?.date)}
        </span>
      </div>

      <div style={{ position: 'relative', width: '100%', overflow: 'hidden' }}>
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          viewBox={`0 0 ${CHART_W} ${TOTAL_H}`}
          preserveAspectRatio="xMidYMid meet"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          style={{ display: 'block' }}
        >
          {/* 背景网格 */}
          {yTickValues.map((val, i) => {
            const y = toY(val);
            return (
              <g key={`grid-${i}`}>
                <line
                  x1={PADDING.left} y1={y} x2={CHART_W - PADDING.right + 10} y2={y}
                  stroke="var(--border-color)" strokeWidth="0.5" strokeDasharray="4,4" opacity="0.5"
                />
                <text
                  x={CHART_W - PADDING.right + 16} y={y + 4}
                  textAnchor="start"
                  fill="var(--text-secondary)"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {formatPrice(val)}
                </text>
              </g>
            );
          })}

          {/* 成交量区域分隔线 */}
          <line
            x1={PADDING.left} y1={CHART_H} x2={CHART_W - PADDING.right} y2={CHART_H}
            stroke="var(--border-color)" strokeWidth="1" opacity="0.3"
          />

          {/* K线 */}
          {data.map((k, i) => {
            const x = toX(i);
            const yH = toY(k.high);
            const yL = toY(k.low);
            const yO = toY(k.open);
            const yC = toY(k.close);
            const up = k.close >= k.open;
            const color = up ? '#26a69a' : '#ef5350';
            const bodyTop = Math.min(yO, yC);
            const bodyH = Math.max(Math.abs(yC - yO), 0.5);

            return (
              <g key={i}>
                {/* 影线 */}
                <line x1={x} y1={yH} x2={x} y2={yL} stroke={color} strokeWidth="1" />
                {/* 实体 */}
                <rect
                  x={x - barWidth / 2} y={bodyTop}
                  width={barWidth} height={bodyH}
                  fill={up ? color : color}
                />
              </g>
            );
          })}

          {/* 成交量柱 */}
          {data.map((k, i) => {
            const x = toX(i);
            const up = k.close >= k.open;
            const volColor = up ? 'rgba(38,166,154,0.35)' : 'rgba(239,83,80,0.35)';
            const volH = (k.volume / maxVol) * (VOLUME_H - 20);
            const volY = CHART_H + VOLUME_H - 5 - volH;

            return (
              <rect
                key={`vol-${i}`}
                x={x - barWidth / 2}
                y={volY}
                width={Math.max(barWidth, 0.8)}
                height={Math.max(volH, 0.5)}
                fill={volColor}
              />
            );
          })}

          {/* X轴日期标签 */}
          {xTickIndices.map(i => {
            const x = toX(i);
            return (
              <text
                key={`xlabel-${i}`}
                x={x}
                y={TOTAL_H - 6}
                textAnchor="middle"
                fill="var(--text-muted)"
                fontSize="10"
                fontFamily="monospace"
              >
                {formatDate(data[i].date)}
              </text>
            );
          })}

          {/* 十字线 */}
          {hoverIndex !== null && hoverK && (
            <>
              {/* 竖线 */}
              <line
                x1={toX(hoverIndex)} y1={PADDING.top}
                x2={toX(hoverIndex)} y2={TOTAL_H - 5}
                stroke="var(--text-muted)" strokeWidth="0.5" strokeDasharray="3,3"
              />
              {/* 横线 */}
              <line
                x1={PADDING.left} y1={toY(hoverK.close)}
                x2={CHART_W - PADDING.right + 10} y2={toY(hoverK.close)}
                stroke="var(--text-muted)" strokeWidth="0.5" strokeDasharray="3,3"
              />
              {/* 十字线交叉点 */}
              <circle
                cx={toX(hoverIndex)} cy={toY(hoverK.close)}
                r="3" fill={accentColor} stroke="#fff" strokeWidth="1"
              />
              {/* 价格标签 */}
              <rect
                x={CHART_W - PADDING.right + 8} y={toY(hoverK.close) - 8}
                width="56" height="16" rx="3"
                fill={accentColor} opacity="0.9"
              />
              <text
                x={CHART_W - PADDING.right + 36} y={toY(hoverK.close) + 4}
                textAnchor="middle" fill="#fff" fontSize="10" fontFamily="monospace" fontWeight="600"
              >
                {formatPrice(hoverK.close)}
              </text>
            </>
          )}

          {/* 最新价线 */}
          <line
            x1={PADDING.left} y1={toY(latestPrice)}
            x2={CHART_W - PADDING.right + 10} y2={toY(latestPrice)}
            stroke={accentColor} strokeWidth="0.5" strokeDasharray="2,4" opacity="0.6"
          />
        </svg>

        {/* Tooltip */}
        {hoverIndex !== null && hoverK && (
          <div style={{
            position: 'absolute',
            top: 8,
            left: Math.max(8, Math.min(
              (hoverX / CHART_W) * 100 - 10,
              85
            )) + '%',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: 6,
            padding: '8px 12px',
            fontSize: 12,
            fontFamily: 'monospace',
            zIndex: 10,
            pointerEvents: 'none',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
            minWidth: 140,
          }}>
            <div style={{ color: 'var(--text-primary)', fontWeight: 600, marginBottom: 4, fontSize: 11 }}>
              {hoverK.date}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '2px 8px', color: 'var(--text-secondary)' }}>
              <span style={{ color: 'var(--text-muted)' }}>开</span>
              <span style={{ textAlign: 'right' }}>{formatPrice(hoverK.open)}</span>
              <span style={{ color: 'var(--text-muted)' }}>高</span>
              <span style={{ textAlign: 'right', color: '#26a69a' }}>{formatPrice(hoverK.high)}</span>
              <span style={{ color: 'var(--text-muted)' }}>低</span>
              <span style={{ textAlign: 'right', color: '#ef5350' }}>{formatPrice(hoverK.low)}</span>
              <span style={{ color: 'var(--text-muted)' }}>收</span>
              <span style={{
                textAlign: 'right',
                fontWeight: 600,
                color: hoverK.close >= hoverK.open ? '#26a69a' : '#ef5350',
              }}>
                {formatPrice(hoverK.close)}
              </span>
              <span style={{ color: 'var(--text-muted)' }}>量</span>
              <span style={{ textAlign: 'right' }}>
                {hoverK.volume >= 1e8
                  ? (hoverK.volume / 1e8).toFixed(2) + '亿'
                  : hoverK.volume >= 1e4
                  ? (hoverK.volume / 1e4).toFixed(1) + '万'
                  : hoverK.volume.toLocaleString()}
              </span>
              <span style={{ color: 'var(--text-muted)' }}>涨幅</span>
              <span style={{
                textAlign: 'right',
                fontWeight: 600,
                color: hoverK.close >= hoverK.open ? '#26a69a' : '#ef5350',
              }}>
                {((hoverK.close - hoverK.open) / hoverK.open * 100).toFixed(2)}%
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ========== Main Component ==========

export default function StockAnalysisPage() {
  const [keyword, setKeyword] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [market, setMarket] = useState('A');
  const [searchResults, setSearchResults] = useState<{ code: string; name: string; market: string }[]>([]);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Research report state
  const [activeTab, setActiveTab] = useState<'technical' | 'research'>('technical');
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  // LLM Config state
  const [showLLMSettings, setShowLLMSettings] = useState(false);
  const [llmProvider, setLLMProvider] = useState('deepseek');
  const [llmApiKey, setLLMApiKey] = useState('');
  const [llmBaseUrl, setLLMBaseUrl] = useState('');
  const [llmModel, setLLMModel] = useState('');
  const [serverHasDefault, setServerHasDefault] = useState(false);

  // Load LLM config from localStorage and server info
  useEffect(() => {
    const saved = localStorage.getItem('llm_config');
    if (saved) {
      try {
        const cfg = JSON.parse(saved);
        setLLMProvider(cfg.provider || 'deepseek');
        setLLMApiKey(cfg.api_key || '');
        setLLMBaseUrl(cfg.base_url || '');
        setLLMModel(cfg.model || '');
      } catch { /* ignore */ }
    }
    // Fetch server provider info
    stockApi.getLLMProviders().then(res => {
      setServerHasDefault(res.server_has_default);
    }).catch(() => {});
  }, []);

  // Save LLM config to localStorage
  const saveLLMConfig = () => {
    const cfg = {
      provider: llmProvider,
      api_key: llmApiKey,
      base_url: llmBaseUrl,
      model: llmModel,
    };
    localStorage.setItem('llm_config', JSON.stringify(cfg));
    setShowLLMSettings(false);
  };

  // Get active LLM config for API requests
  const getActiveLLMConfig = () => {
    if (!llmApiKey) return undefined;
    const cfg: { provider: string; api_key: string; base_url?: string; model?: string } = {
      provider: llmProvider,
      api_key: llmApiKey,
    };
    if (llmProvider === 'custom') {
      cfg.base_url = llmBaseUrl;
      cfg.model = llmModel;
    }
    return cfg;
  };

  const handleSearch = async () => {
    if (!keyword.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await stockApi.search(keyword, market) as { results: { code: string; name: string; market: string }[] };
      setSearchResults(res.results || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '搜索失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectStock = async (code: string, mkt: string) => {
    setSelectedSymbol(code);
    setMarket(mkt);
    setSearchResults([]);
    setAnalysis(null);
    setReport(null);
    setActiveTab('technical');
    setLoading(true);
    setError('');
    try {
      const [quoteRes, analysisRes] = await Promise.all([
        stockApi.getQuote(code, mkt),
        stockApi.analyze({ symbol: code, market: mkt, analysis_types: ['technical', 'fundamental', 'valuation'] }),
      ]);
      setQuote(quoteRes as Quote);
      setAnalysis(analysisRes as AnalysisResult);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '分析失败');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!selectedSymbol) return;
    setReportLoading(true);
    setError('');
    try {
      const llmConfig = getActiveLLMConfig();
      const res = await stockApi.getResearchReport({
        symbol: selectedSymbol,
        market,
        deep_analysis: true,
        llm_config: llmConfig,
      });
      setReport(res as ResearchReport);
      setActiveTab('research');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '研报生成失败');
    } finally {
      setReportLoading(false);
    }
  };

  const formatMoney = (n: number) => {
    if (Math.abs(n) >= 1e12) return (n / 1e12).toFixed(2) + '万亿';
    if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿';
    if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(1) + '万';
    return n.toLocaleString();
  };

  const getRiskColor = (level: string) => {
    if (level.includes('高')) return 'var(--accent-red)';
    if (level.includes('中高')) return 'var(--accent-orange)';
    if (level.includes('中低')) return 'var(--accent-yellow)';
    if (level.includes('低')) return 'var(--accent-green)';
    return 'var(--text-secondary)';
  };

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>个股分析</h1>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            技术面分析 · 基本面分析 · 深度研报
          </p>
        </div>
      </div>

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

      {/* 搜索区域 */}
      <div className="trading-card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              搜索股票代码或名称
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                className="input-field"
                value={keyword}
                onChange={e => setKeyword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                placeholder="输入股票代码或名称，如 600519、茅台、AAPL"
              />
              <select
                className="select-field"
                value={market}
                onChange={e => setMarket(e.target.value)}
                style={{ width: 100 }}
              >
                <option value="A">A股</option>
                <option value="US">美股</option>
              </select>
              <button
                className="btn-primary"
                onClick={handleSearch}
                disabled={loading}
                style={{ display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
              >
                <Search size={14} />
                搜索
              </button>
            </div>
          </div>
        </div>

        {/* 搜索结果 */}
        {searchResults.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8 }}>
              搜索结果 ({searchResults.length})
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {searchResults.map((item, i) => (
                <button
                  key={i}
                  onClick={() => handleSelectStock(item.code, item.market)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '6px 14px',
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 6,
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'var(--accent-green)';
                    e.currentTarget.style.background = 'var(--bg-hover)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'var(--border-color)';
                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                  }}
                >
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{item.code}</span>
                  <span style={{ fontWeight: 500 }}>{item.name}</span>
                  <span className="tag tag-blue">{item.market === 'A' ? 'A股' : '美股'}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* AI模型设置 */}
      <div className="trading-card" style={{ marginBottom: 20 }}>
        <div
          onClick={() => setShowLLMSettings(!showLLMSettings)}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            cursor: 'pointer', userSelect: 'none',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Cpu size={14} style={{ color: llmApiKey ? 'var(--accent-green)' : 'var(--text-secondary)' }} />
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>
              AI研报模型设置
            </span>
            {llmApiKey ? (
              <span style={{ fontSize: 11, color: 'var(--accent-green)' }}>
                {llmProvider === 'deepseek' ? 'DeepSeek' : llmProvider === 'openai' ? 'OpenAI' : '自定义'} 已配置
              </span>
            ) : serverHasDefault ? (
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>使用服务端默认模型</span>
            ) : (
              <span style={{ fontSize: 11, color: 'var(--accent-orange)' }}>未配置（将使用模板生成）</span>
            )}
          </div>
          {showLLMSettings ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>

        {showLLMSettings && (
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border-color)' }}>
            {/* Provider选择 */}
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>模型服务商</label>
              <div style={{ display: 'flex', gap: 8 }}>
                {[
                  { id: 'deepseek', name: 'DeepSeek', desc: '性价比最高' },
                  { id: 'openai', name: 'OpenAI', desc: '能力最强' },
                  { id: 'custom', name: '自定义', desc: '兼容OpenAI接口' },
                ].map(p => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setLLMProvider(p.id);
                      if (p.id !== 'custom') { setLLMBaseUrl(''); setLLMModel(''); }
                    }}
                    style={{
                      flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid',
                      borderColor: llmProvider === p.id ? 'var(--accent-green)' : 'var(--border-color)',
                      background: llmProvider === p.id ? 'rgba(76,175,80,0.1)' : 'var(--bg-secondary)',
                      color: llmProvider === p.id ? 'var(--accent-green)' : 'var(--text-secondary)',
                      cursor: 'pointer', fontSize: 12, textAlign: 'center',
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{p.name}</div>
                    <div style={{ fontSize: 10, opacity: 0.7 }}>{p.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* API Key */}
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                API Key
                {llmProvider === 'deepseek' && (
                  <a href="https://platform.deepseek.com" target="_blank" rel="noopener noreferrer"
                    style={{ marginLeft: 8, fontSize: 10, color: 'var(--accent-blue)' }}>
                    获取Key
                  </a>
                )}
                {llmProvider === 'openai' && (
                  <a href="https://platform.openai.com" target="_blank" rel="noopener noreferrer"
                    style={{ marginLeft: 8, fontSize: 10, color: 'var(--accent-blue)' }}>
                    获取Key
                  </a>
                )}
              </label>
              <input
                className="input-field"
                type="password"
                value={llmApiKey}
                onChange={e => setLLMApiKey(e.target.value)}
                placeholder={llmProvider === 'deepseek' ? 'sk-xxx...' : llmProvider === 'openai' ? 'sk-xxx...' : '输入你的API Key'}
              />
            </div>

            {/* 自定义配置 */}
            {llmProvider === 'custom' && (
              <>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    Base URL（兼容OpenAI接口）
                  </label>
                  <input
                    className="input-field"
                    value={llmBaseUrl}
                    onChange={e => setLLMBaseUrl(e.target.value)}
                    placeholder="如 https://api.deepseek.com 或 http://localhost:11434/v1"
                  />
                </div>
                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                    模型名称
                  </label>
                  <input
                    className="input-field"
                    value={llmModel}
                    onChange={e => setLLMModel(e.target.value)}
                    placeholder="如 deepseek-chat、gpt-4o、qwen3:14b"
                  />
                </div>
              </>
            )}

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              {llmApiKey && (
                <button
                  onClick={() => {
                    setLLMApiKey('');
                    setLLMBaseUrl('');
                    setLLMModel('');
                    localStorage.removeItem('llm_config');
                    setShowLLMSettings(false);
                  }}
                  style={{
                    padding: '6px 16px', borderRadius: 6, border: '1px solid var(--border-color)',
                    background: 'transparent', color: 'var(--accent-red)', cursor: 'pointer', fontSize: 12,
                  }}
                >
                  清除配置
                </button>
              )}
              <button
                onClick={saveLLMConfig}
                className="btn-primary"
                style={{ padding: '6px 16px', fontSize: 12 }}
              >
                保存设置
              </button>
            </div>

            <div style={{ marginTop: 12, padding: '8px 12px', background: 'var(--bg-tertiary)', borderRadius: 6, fontSize: 11, color: 'var(--text-muted)' }}>
              <Key size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: -2 }} />
              API Key 仅保存在浏览器本地（localStorage），不会上传到服务器。{serverHasDefault && '如不配置，将使用服务端默认模型。'}
            </div>
          </div>
        )}
      </div>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
          <div className="loading-spinner" />
          <span style={{ marginLeft: 12, color: 'var(--text-secondary)' }}>加载分析数据...</span>
        </div>
      )}

      {/* 行情与基本信息 */}
      {quote && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 16, marginBottom: 20 }}>
          {/* 行情卡片 */}
          <div className="trading-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <h2 style={{ fontSize: 18, fontWeight: 700 }}>{quote.name}</h2>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{quote.symbol}</span>
                </div>
              </div>
              <span className={`tag ${quote.change_pct >= 0 ? 'tag-green' : 'tag-red'}`}>
                {market === 'A' ? 'A股' : '美股'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
              <span style={{ fontSize: 36, fontWeight: 700, color: quote.change_pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                {quote.price.toFixed(2)}
              </span>
              <div>
                <div style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: quote.change_pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                }}>
                  {quote.change >= 0 ? '+' : ''}{quote.change.toFixed(2)} ({quote.change_pct >= 0 ? '+' : ''}{quote.change_pct.toFixed(2)}%)
                </div>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px', marginTop: 16, fontSize: 12 }}>
              {[
                { label: '开盘', value: quote.open.toFixed(2) },
                { label: '昨收', value: quote.pre_close.toFixed(2) },
                { label: '最高', value: quote.high.toFixed(2), color: 'var(--accent-green)' },
                { label: '最低', value: quote.low.toFixed(2), color: 'var(--accent-red)' },
                { label: '成交量', value: formatMoney(quote.volume) },
                { label: '成交额', value: formatMoney(quote.amount) },
              ].map((item, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                  <span style={{ color: item.color || 'var(--text-primary)', fontWeight: 500 }}>{item.value}</span>
                </div>
              ))}
            </div>
            {/* 生成研报按钮 */}
            <button
              onClick={handleGenerateReport}
              disabled={reportLoading}
              className="btn-primary"
              style={{
                marginTop: 16,
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                padding: '10px 0',
              }}
            >
              {reportLoading ? (
                <><Loader2 size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> 生成研报中...</>
              ) : (
                <><FileText size={14} /> 生成深度研报</>
              )}
            </button>
          </div>

          {/* 分析摘要 */}
          {analysis && activeTab === 'technical' && (
            <div className="trading-card">
              <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
                分析摘要
              </h3>
              <div style={{
                background: 'var(--bg-tertiary)',
                borderRadius: 6,
                padding: 12,
                marginBottom: 12,
                border: '1px solid var(--border-color)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <Shield size={16} color={getRiskColor(analysis.risk_level)} />
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>风险等级：</span>
                  <span style={{
                    fontSize: 14,
                    fontWeight: 700,
                    color: getRiskColor(analysis.risk_level),
                  }}>
                    {analysis.risk_level}
                  </span>
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {analysis.analysis_summary}
                </p>
              </div>

              {/* 信号列表 */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {analysis.signals.map((signal, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '6px 10px',
                    borderRadius: 4,
                    background: signal.type === 'bullish' ? 'rgba(38,166,154,0.08)' : 'rgba(239,83,80,0.08)',
                    border: `1px solid ${signal.type === 'bullish' ? 'rgba(38,166,154,0.2)' : 'rgba(239,83,80,0.2)'}`,
                  }}>
                    {signal.type === 'bullish' ? (
                      <TrendingUp size={14} color="var(--accent-green)" />
                    ) : (
                      <TrendingDown size={14} color="var(--accent-red)" />
                    )}
                    <div>
                      <div style={{ fontSize: 11, color: signal.type === 'bullish' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                        {signal.indicator}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        {signal.message}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 研报预览卡片 */}
          {report && activeTab === 'research' && (
            <div className="trading-card">
              <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
                研报概览
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {(() => {
                  const sections = report.sections as Record<string, unknown>;
                  const summary = sections?.summary as Record<string, unknown> | undefined;
                  const debate = sections?.debate as Record<string, unknown> | undefined;
                  const ratingIcon = summary?.rating === '买入'
                    ? <CheckCircle size={16} color="var(--accent-green)" />
                    : summary?.rating === '卖出'
                    ? <XCircle size={16} color="var(--accent-red)" />
                    : <MinusCircle size={16} color="var(--accent-orange)" />;

                  return (
                    <>
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '10px 12px',
                        background: 'var(--bg-tertiary)',
                        borderRadius: 6,
                        border: '1px solid var(--border-color)',
                      }}>
                        {ratingIcon}
                        <div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>最终评级</div>
                          <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>
                            {summary?.rating as string || '—'}
                          </div>
                        </div>
                        <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>确信度</div>
                          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                            {summary?.conviction as string || '—'}
                          </div>
                        </div>
                      </div>
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        padding: '10px 12px',
                        background: 'var(--bg-tertiary)',
                        borderRadius: 6,
                        border: '1px solid var(--border-color)',
                      }}>
                        <BarChart3 size={14} color="var(--text-muted)" />
                        <div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>预期持仓周期</div>
                          <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                            {summary?.holding_period as string || '—'}
                          </div>
                        </div>
                      </div>
                      <div style={{
                        padding: '10px 12px',
                        background: 'rgba(38,166,154,0.05)',
                        borderRadius: 6,
                        border: '1px solid rgba(38,166,154,0.15)',
                        fontSize: 12,
                        color: 'var(--text-secondary)',
                        lineHeight: 1.5,
                      }}>
                        <div style={{ fontSize: 11, color: 'var(--accent-green)', marginBottom: 4, fontWeight: 600 }}>
                          {debate?.rating as string || '—'}
                        </div>
                        {debate?.rating_reason as string || '—'}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                        生成时间：{report.report_time}
                      </div>
                    </>
                  );
                })()}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 切换 */}
      {analysis && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border-color)', marginBottom: 16 }}>
            <button
              onClick={() => setActiveTab('technical')}
              style={{
                padding: '8px 16px',
                fontSize: 13,
                fontWeight: activeTab === 'technical' ? 600 : 400,
                color: activeTab === 'technical' ? 'var(--accent-green)' : 'var(--text-secondary)',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'technical' ? '2px solid var(--accent-green)' : '2px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <BarChart3 size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />
              技术分析
            </button>
            <button
              onClick={() => setActiveTab('research')}
              style={{
                padding: '8px 16px',
                fontSize: 13,
                fontWeight: activeTab === 'research' ? 600 : 400,
                color: activeTab === 'research' ? 'var(--accent-green)' : 'var(--text-secondary)',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'research' ? '2px solid var(--accent-green)' : '2px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <FileText size={14} style={{ display: 'inline', marginRight: 6, verticalAlign: -2 }} />
              深度研报
              {report && (
                <span style={{
                  marginLeft: 6,
                  padding: '1px 6px',
                  borderRadius: 10,
                  background: 'var(--accent-green)',
                  color: '#fff',
                  fontSize: 10,
                  fontWeight: 600,
                }}>
                  已生成
                </span>
              )}
            </button>
          </div>

          {/* 技术分析内容 */}
          {activeTab === 'technical' && (
            <>
              {/* 技术指标详情 */}
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
                  技术指标
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
                  {/* 均线 */}
                  <div className="trading-card">
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase' }}>
                      移动均线
                    </div>
                    {[
                      { label: 'MA5', value: analysis.technical.ma5 },
                      { label: 'MA10', value: analysis.technical.ma10 },
                      { label: 'MA20', value: analysis.technical.ma20 },
                      { label: 'MA60', value: analysis.technical.ma60 },
                    ].map((ma, i) => {
                      const price = quote?.price || 0;
                      const above = price > ma.value;
                      return (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                          <span style={{ color: 'var(--text-muted)' }}>{ma.label}</span>
                          <span style={{ color: above ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 500 }}>
                            {ma.value.toFixed(2)}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  {/* RSI */}
                  <div className="trading-card" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase' }}>
                      RSI (14)
                    </div>
                    <div style={{
                      fontSize: 32,
                      fontWeight: 700,
                      color: analysis.technical.rsi > 70 ? 'var(--accent-red)' :
                             analysis.technical.rsi > 50 ? 'var(--accent-green)' :
                             analysis.technical.rsi > 30 ? 'var(--text-secondary)' : 'var(--accent-green)',
                    }}>
                      {analysis.technical.rsi.toFixed(1)}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                      {analysis.technical.rsi > 70 ? '超买区域' : analysis.technical.rsi > 50 ? '偏强' : analysis.technical.rsi > 30 ? '偏弱' : '超卖区域'}
                    </div>
                  </div>

                  {/* MACD */}
                  <div className="trading-card" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase' }}>
                      MACD
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
                      {analysis.technical.macd.toFixed(3)}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 8, fontSize: 11 }}>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Signal </span>
                        <span style={{ color: 'var(--text-secondary)' }}>{analysis.technical.macd_signal.toFixed(3)}</span>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Hist </span>
                        <span style={{
                          color: analysis.technical.macd_hist >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                        }}>
                          {analysis.technical.macd_hist.toFixed(3)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* 布林带 */}
                  <div className="trading-card">
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase' }}>
                      布林带 (20,2)
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                      <span style={{ color: 'var(--accent-red)' }}>上轨</span>
                      <span style={{ color: 'var(--accent-red)' }}>{analysis.technical.bollinger_upper.toFixed(2)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
                      <span style={{ color: 'var(--text-secondary)' }}>中轨</span>
                      <span style={{ color: 'var(--text-secondary)' }}>{analysis.technical.bollinger_middle.toFixed(2)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                      <span style={{ color: 'var(--accent-green)' }}>下轨</span>
                      <span style={{ color: 'var(--accent-green)' }}>{analysis.technical.bollinger_lower.toFixed(2)}</span>
                    </div>
                  </div>

                  {/* 成交量比 */}
                  <div className="trading-card" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase' }}>
                      量比 (5/20)
                    </div>
                    <div style={{
                      fontSize: 28,
                      fontWeight: 700,
                      color: analysis.technical.volume_ratio > 1.5 ? 'var(--accent-orange)' :
                             analysis.technical.volume_ratio > 1 ? 'var(--accent-green)' : 'var(--text-secondary)',
                    }}>
                      {analysis.technical.volume_ratio.toFixed(2)}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                      {analysis.technical.volume_ratio > 1.5 ? '放量' : analysis.technical.volume_ratio > 1 ? '温和放量' : '缩量'}
                    </div>
                  </div>
                </div>
              </div>

              {/* 基本面 */}
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
                  基本面数据
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
                  {[
                    { label: '市盈率 (PE)', value: analysis.fundamental.pe_ratio.toFixed(2), suffix: '' },
                    { label: '市净率 (PB)', value: analysis.fundamental.pb_ratio.toFixed(2), suffix: '' },
                    { label: '总市值', value: formatMoney(analysis.fundamental.market_cap), suffix: '' },
                    { label: 'ROE', value: analysis.fundamental.roe?.toFixed(1) || '-', suffix: '%' },
                    { label: '营收增长', value: analysis.fundamental.revenue_growth?.toFixed(1) || '-', suffix: '%' },
                    { label: '利润增长', value: analysis.fundamental.profit_growth?.toFixed(1) || '-', suffix: '%' },
                    { label: '负债率', value: analysis.fundamental.debt_ratio?.toFixed(1) || '-', suffix: '%' },
                    { label: '股息率', value: analysis.fundamental.dividend_yield?.toFixed(2) || '-', suffix: '%' },
                  ].map((item, i) => (
                    <div key={i} className="trading-card" style={{ textAlign: 'center', padding: '12px' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6 }}>
                        {item.label}
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
                        {item.value}{item.suffix}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* K线图 */}
              {analysis.charts?.kline && analysis.charts.kline.length > 0 && (
                <KlineChart
                  data={analysis.charts.kline}
                  latestPrice={analysis.latest_price}
                  changePct={analysis.change_pct}
                />
              )}
            </>
          )}

          {/* 深度研报内容 */}
          {activeTab === 'research' && (
            <>
              {reportLoading ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
                  <div className="loading-spinner" />
                  <span style={{ marginLeft: 12, color: 'var(--text-secondary)' }}>正在生成深度研报，五阶引擎推演中...</span>
                </div>
              ) : report ? (
                <div className="trading-card" style={{ padding: '20px 24px' }}>
                  <MarkdownRenderer content={report.report_markdown} />
                </div>
              ) : (
                <div className="trading-card" style={{
                  padding: '60px 24px',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                }}>
                  <FileText size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
                  <p style={{ fontSize: 14, marginBottom: 8 }}>尚未生成深度研报</p>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    点击上方「生成深度研报」按钮，启动五阶逻辑引擎
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}