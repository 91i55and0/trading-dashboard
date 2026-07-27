import { useState, useEffect } from 'react';
import { backtestApi } from '../../api';
import {
  Play,
  Upload,
  Trash2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  BarChart3,
  Target,
  Shield,
  Percent,
  RefreshCw,
  AlertTriangle,
  Activity,
  Code2,
  Sparkles,
  Copy,
  Check,
  Save,
  FileText,
} from 'lucide-react';

interface Strategy {
  name: string;
  file: string;
  preview: string;
  engine: string;
  size: number;
}

interface Trade {
  date: string;
  type: string;
  price: number;
  shares: number;
  amount: number;
  profit?: number;
  profit_pct?: number;
  reason: string;
}

interface EquityPoint {
  date: string;
  equity: number;
  return_pct: number;
}

interface BacktestResult {
  strategy: string;
  symbol: string;
  market: string;
  period: string;
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  total_trades: number;
  profit_trades: number;
  loss_trades: number;
  avg_profit: number;
  avg_loss: number;
  profit_factor: number;
  equity_curve: EquityPoint[];
  trades: Trade[];
  engine?: string;
}

type TabType = 'strategy' | 'code';

// 预设股票池
const PRESET_POOLS: Record<string, { label: string; symbols: string[] }> = {
  'hs300_sample': {
    label: '沪深300样本（16只）',
    symbols: ['600519', '000858', '600036', '000333', '601318', '000651', '600276', '002415',
              '601166', '600900', '601398', '600030', '000001', '601288', '601328', '600000'],
  },
  'hs300_top10': {
    label: '沪深300权重TOP10',
    symbols: ['600519', '300750', '000858', '600036', '000333', '601318', '601899', '600900', '601398', '000651'],
  },
  'blue_chip': {
    label: 'A股蓝筹（8只）',
    symbols: ['600519', '000858', '600036', '000333', '601318', '600276', '601166', '600900'],
  },
};

const DEFAULT_CODE_TEMPLATE = `import backtrader as bt

class MyStrategy(bt.Strategy):
    params = (
        ('ma_short', 5),
        ('ma_long', 20),
    )

    def __init__(self):
        self.sma_short = bt.indicators.SMA(
            self.data.close, period=self.p.ma_short)
        self.sma_long = bt.indicators.SMA(
            self.data.close, period=self.p.ma_long)
        self.crossover = bt.indicators.CrossOver(
            self.sma_short, self.sma_long)
        self.order = None

    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print(f'{dt} {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入成交 @ {order.executed.price:.2f}')
            else:
                self.log(f'卖出成交 @ {order.executed.price:.2f}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单失败/取消')
        self.order = None

    def next(self):
        if self.order:
            return
        if not self.position:
            if self.crossover > 0:
                self.order = self.buy()
        else:
            if self.crossover < 0:
                self.order = self.sell()
`;

export default function BacktestPage() {
  const [activeTab, setActiveTab] = useState<TabType>('strategy');

  // ===== 策略回测 Tab =====
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState('');

  // ===== 代码编辑器 Tab =====
  const [code, setCode] = useState(DEFAULT_CODE_TEMPLATE);
  const [strategyName, setStrategyName] = useState('');
  const [aiDescription, setAiDescription] = useState('');
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // ===== 共享参数 =====
  const [symbolsInput, setSymbolsInput] = useState('600519');
  const [market, setMarket] = useState('A');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2025-12-31');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [commission, setCommission] = useState(0.0003);
  const [paramsJson, setParamsJson] = useState('');

  // 解析股票池（支持逗号、空格、换行分隔）
  const parseSymbols = (input: string): string[] => {
    return input
      .split(/[,，\s]+/)
      .map(s => s.trim())
      .filter(s => s.length > 0);
  };

  const symbols = parseSymbols(symbolsInput);
  const isMultiSymbol = symbols.length > 1;

  // ===== 结果 =====
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchStrategies = async () => {
    try {
      const res = await backtestApi.getStrategies();
      setStrategies(res.strategies);
      if (res.strategies.length > 0 && !selectedStrategy) {
        setSelectedStrategy(res.strategies[0].name);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchStrategies();
  }, []);

  // ===== 策略回测 =====
  const runBacktest = async () => {
    if (!selectedStrategy || symbols.length === 0) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      let params: Record<string, unknown> | undefined;
      if (paramsJson.trim()) {
        params = JSON.parse(paramsJson);
      }
      const res = isMultiSymbol
        ? await backtestApi.runMulti({
            strategy_name: selectedStrategy,
            symbols,
            market,
            start_date: startDate,
            end_date: endDate,
            initial_capital: initialCapital,
            commission,
            params,
          })
        : await backtestApi.run({
            strategy_name: selectedStrategy,
            symbol: symbols[0],
            market,
            start_date: startDate,
            end_date: endDate,
            initial_capital: initialCapital,
            commission,
            params,
          });
      setResult(res as BacktestResult);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '回测执行失败');
    } finally {
      setLoading(false);
    }
  };

  // ===== 代码运行 =====
  const runCodeBacktest = async () => {
    if (!code.trim() || symbols.length === 0) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = isMultiSymbol
        ? await backtestApi.runMultiCode({
            code,
            symbols,
            market,
            start_date: startDate,
            end_date: endDate,
            initial_capital: initialCapital,
            commission,
          })
        : await backtestApi.runCode({
            code,
            symbol: symbols[0],
            market,
            start_date: startDate,
            end_date: endDate,
            initial_capital: initialCapital,
            commission,
          });
      setResult(res as BacktestResult);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '代码执行失败');
    } finally {
      setLoading(false);
    }
  };

  // ===== 保存策略 =====
  const saveStrategy = async () => {
    if (!strategyName.trim() || !code.trim()) {
      setError('请填写策略名称和代码');
      return;
    }
    setError('');
    try {
      await backtestApi.saveCode({ name: strategyName, code, overwrite: true });
      setStrategyName('');
      await fetchStrategies();
      setError('');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '保存失败');
    }
  };

  // ===== 加载策略到编辑器 =====
  const loadStrategyToEditor = async (name: string) => {
    try {
      const res = await backtestApi.getCode(name);
      setCode(res.code);
      setStrategyName(res.name);
      setActiveTab('code');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载失败');
    }
  };

  // ===== AI 提示词 =====
  const generateAiPrompt = async () => {
    if (!aiDescription.trim()) return;
    setAiLoading(true);
    setError('');
    try {
      const res = await backtestApi.getAiPrompt({
        description: aiDescription,
        symbol: symbols[0] || '',
        market,
      });
      setAiPrompt(res.prompt);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '生成提示词失败');
    } finally {
      setAiLoading(false);
    }
  };

  const copyAiPrompt = async () => {
    try {
      await navigator.clipboard.writeText(aiPrompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
      const ta = document.createElement('textarea');
      ta.value = aiPrompt;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // ===== 上传/删除 =====
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await backtestApi.uploadStrategy(file);
      fetchStrategies();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '上传失败');
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`确定删除策略 "${name}" 吗？`)) return;
    try {
      await backtestApi.deleteStrategy(name);
      if (selectedStrategy === name) setSelectedStrategy('');
      fetchStrategies();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const formatMoney = (n: number | null | undefined) => {
    if (n == null || isNaN(n)) return '-';
    if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + '亿';
    if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(1) + '万';
    return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>量化回测</h1>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            策略回测 · 代码编辑器 · 绩效分析
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

      {/* ===== Tab 切换 ===== */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: '1px solid var(--border-color)' }}>
        {([
          { key: 'strategy' as TabType, label: '策略回测', icon: BarChart3 },
          { key: 'code' as TabType, label: '代码编辑器', icon: Code2 },
        ]).map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '10px 20px',
              fontSize: 13, fontWeight: 500,
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid var(--accent-green)' : '2px solid transparent',
              color: activeTab === tab.key ? 'var(--accent-green)' : 'var(--text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <tab.icon size={14} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ===== 策略回测 Tab 内容 ===== */}
      {activeTab === 'strategy' && (
        <>
          {/* 回测配置 */}
          <div className="trading-card" style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--text-primary)' }}>
              回测配置
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>策略</label>
                <select
                  className="select-field"
                  value={selectedStrategy}
                  onChange={e => setSelectedStrategy(e.target.value)}
                >
                  {strategies.map(s => (
                    <option key={s.name} value={s.name}>{s.name}{s.engine === 'backtrader' ? ' [BT]' : ''}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>股票池</label>
                <div style={{ display: 'flex', gap: 4, marginBottom: 4, flexWrap: 'wrap' }}>
                  {Object.entries(PRESET_POOLS).map(([key, pool]) => (
                    <button
                      key={key}
                      onClick={() => setSymbolsInput(pool.symbols.join(', '))}
                      style={{
                        fontSize: 10,
                        padding: '2px 8px',
                        borderRadius: 4,
                        border: '1px solid var(--border-color)',
                        background: 'var(--bg-tertiary)',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                      }}
                      title={pool.symbols.join(', ')}
                    >
                      {pool.label}
                    </button>
                  ))}
                </div>
                <textarea
                  className="input-field"
                  value={symbolsInput}
                  onChange={e => setSymbolsInput(e.target.value)}
                  placeholder="输入股票代码，多个用逗号/空格/换行分隔"
                  rows={2}
                  style={{ resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
                />
                {symbols.length > 1 && (
                  <div style={{ fontSize: 10, color: 'var(--accent-green)', marginTop: 2 }}>
                    已识别 {symbols.length} 只股票，将使用多股票池回测
                  </div>
                )}
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>市场</label>
                <select className="select-field" value={market} onChange={e => setMarket(e.target.value)}>
                  <option value="A">A股</option>
                  <option value="US">美股</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>起始日期</label>
                <input className="input-field" type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>结束日期</label>
                <input className="input-field" type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>初始资金</label>
                <input className="input-field" type="number" value={initialCapital} onChange={e => setInitialCapital(Number(e.target.value))} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>手续费率</label>
                <input className="input-field" type="number" step="0.0001" value={commission} onChange={e => setCommission(Number(e.target.value))} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>策略参数 (JSON)</label>
                <input className="input-field" value={paramsJson} onChange={e => setParamsJson(e.target.value)} placeholder='{"ma_short": 5, "ma_long": 20}' />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              <button className="btn-primary" onClick={runBacktest} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {loading ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                {loading ? '回测中...' : '开始回测'}
              </button>
              <label className="btn-secondary" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Upload size={14} />
                上传策略
                <input type="file" accept=".py" onChange={handleUpload} style={{ display: 'none' }} />
              </label>
            </div>
          </div>

          {/* 策略列表 */}
          {strategies.length > 0 && (
            <div className="trading-card" style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                  已加载策略
                </h3>
                <button
                  className="btn-secondary"
                  onClick={fetchStrategies}
                  style={{ fontSize: 12, padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  <RefreshCw size={12} />
                  刷新
                </button>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {strategies.map(s => (
                  <div key={s.name} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    background: 'var(--bg-tertiary)',
                    border: selectedStrategy === s.name ? '1px solid var(--accent-green)' : '1px solid var(--border-color)',
                    borderRadius: 6, padding: '6px 12px',
                    fontSize: 12,
                  }}>
                    <BarChart3 size={14} color={s.engine === 'backtrader' ? 'var(--accent-purple)' : 'var(--accent-green)'} />
                    <span style={{ color: 'var(--text-primary)' }}>{s.name}</span>
                    {s.engine === 'backtrader' && (
                      <span className="tag tag-blue" style={{ fontSize: 10 }}>BT</span>
                    )}
                    <button
                      onClick={() => loadStrategyToEditor(s.name)}
                      style={{
                        background: 'transparent', border: 'none', cursor: 'pointer',
                        color: 'var(--text-muted)', padding: '2px',
                      }}
                      title="在编辑器中打开"
                    >
                      <Code2 size={12} />
                    </button>
                    <Trash2
                      size={14}
                      color="var(--text-muted)"
                      style={{ cursor: 'pointer' }}
                      onClick={() => handleDelete(s.name)}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ===== 代码编辑器 Tab 内容 ===== */}
      {activeTab === 'code' && (
        <>
          {/* 代码编辑器 */}
          <div className="trading-card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Code2 size={14} />
                策略代码
              </h3>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  className="btn-secondary"
                  onClick={() => setCode(DEFAULT_CODE_TEMPLATE)}
                  style={{ fontSize: 12, padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  <FileText size={12} />
                  重置模板
                </button>
              </div>
            </div>
            <textarea
              value={code}
              onChange={e => setCode(e.target.value)}
              spellCheck={false}
              style={{
                width: '100%',
                minHeight: 360,
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 4,
                padding: 14,
                color: 'var(--text-primary)',
                fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
                fontSize: 13,
                lineHeight: 1.6,
                resize: 'vertical',
                outline: 'none',
                tabSize: 4,
              }}
              placeholder="在此粘贴 Backtrader 策略代码..."
            />
          </div>

          {/* 回测参数 */}
          <div className="trading-card" style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--text-primary)' }}>
              回测参数
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12 }}>
              <div style={{ gridColumn: '1 / -1' }}>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>股票池</label>
                <div style={{ display: 'flex', gap: 4, marginBottom: 4, flexWrap: 'wrap' }}>
                  {Object.entries(PRESET_POOLS).map(([key, pool]) => (
                    <button
                      key={key}
                      onClick={() => setSymbolsInput(pool.symbols.join(', '))}
                      style={{
                        fontSize: 10,
                        padding: '2px 8px',
                        borderRadius: 4,
                        border: '1px solid var(--border-color)',
                        background: 'var(--bg-tertiary)',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                      }}
                      title={pool.symbols.join(', ')}
                    >
                      {pool.label}
                    </button>
                  ))}
                </div>
                <textarea
                  className="input-field"
                  value={symbolsInput}
                  onChange={e => setSymbolsInput(e.target.value)}
                  placeholder="输入股票代码，多个用逗号/空格/换行分隔"
                  rows={2}
                  style={{ resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
                />
                {symbols.length > 1 && (
                  <div style={{ fontSize: 10, color: 'var(--accent-green)', marginTop: 2 }}>
                    已识别 {symbols.length} 只股票，将使用多股票池回测
                  </div>
                )}
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>市场</label>
                <select className="select-field" value={market} onChange={e => setMarket(e.target.value)}>
                  <option value="A">A股</option>
                  <option value="US">美股</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>起始日期</label>
                <input className="input-field" type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>结束日期</label>
                <input className="input-field" type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>初始资金</label>
                <input className="input-field" type="number" value={initialCapital} onChange={e => setInitialCapital(Number(e.target.value))} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>手续费率</label>
                <input className="input-field" type="number" step="0.0001" value={commission} onChange={e => setCommission(Number(e.target.value))} />
              </div>
            </div>

            {/* 保存策略 */}
            <div style={{ display: 'flex', gap: 8, marginTop: 16, alignItems: 'center' }}>
              <input
                className="input-field"
                value={strategyName}
                onChange={e => setStrategyName(e.target.value)}
                placeholder="策略名称（保存用）"
                style={{ maxWidth: 200 }}
              />
              <button
                className="btn-secondary"
                onClick={saveStrategy}
                disabled={!strategyName.trim() || !code.trim()}
                style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}
              >
                <Save size={14} />
                保存策略
              </button>
              <button
                className="btn-primary"
                onClick={runCodeBacktest}
                disabled={loading || !code.trim()}
                style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto' }}
              >
                {loading ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                {loading ? '运行中...' : '运行代码'}
              </button>
            </div>
          </div>

          {/* AI 策略生成 */}
          <div className="trading-card" style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Sparkles size={14} color="var(--accent-yellow)" />
              AI 策略生成（TRAE 联动）
            </h3>

            {/* 步骤说明 */}
            <div style={{
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: 6,
              padding: 14,
              marginBottom: 14,
            }}>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                在 TRAE 中直接描述策略，AI 会自动生成代码并保存到策略库，在 app 中即可运行：
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[
                  {
                    step: '1',
                    text: '在 TRAE 中输入策略需求',
                    desc: '例如："用 Backtrader 写一个 MACD 金叉死叉策略，保存到 strategies 目录"',
                    color: 'var(--accent-blue)',
                  },
                  {
                    step: '2',
                    text: 'AI 自动生成代码并保存',
                    desc: '策略文件自动写入 strategies 目录',
                    color: 'var(--accent-green)',
                  },
                  {
                    step: '3',
                    text: '刷新策略列表，立即运行',
                    desc: '切换到"策略回测"Tab，选择策略即可回测',
                    color: 'var(--accent-purple)',
                  },
                ].map((item, i) => (
                  <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      width: 22, height: 22,
                      borderRadius: '50%',
                      background: item.color + '20',
                      border: '1px solid ' + item.color,
                      color: item.color,
                      fontSize: 11, fontWeight: 700,
                      flexShrink: 0,
                    }}>
                      {item.step}
                    </span>
                    <div>
                      <div style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>{item.text}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{item.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 快速输入区 */}
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
              也可以在这里快速生成策略描述文本，复制到 TRAE 中使用：
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                className="input-field"
                value={aiDescription}
                onChange={e => setAiDescription(e.target.value)}
                placeholder="例如：双均线策略，5日均线上穿20日均线买入，下穿卖出"
                style={{ flex: 1 }}
              />
              <button
                className="btn-secondary"
                onClick={generateAiPrompt}
                disabled={aiLoading || !aiDescription.trim()}
                style={{ display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap', fontSize: 12 }}
              >
                {aiLoading ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}
                生成描述
              </button>
            </div>
            {aiPrompt && (
              <div style={{ position: 'relative', marginTop: 10 }}>
                <textarea
                  readOnly
                  value={aiPrompt}
                  style={{
                    width: '100%',
                    minHeight: 160,
                    background: 'var(--bg-primary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 4,
                    padding: 12,
                    color: 'var(--text-secondary)',
                    fontFamily: "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
                    fontSize: 11,
                    lineHeight: 1.5,
                    resize: 'vertical',
                    outline: 'none',
                  }}
                />
                <button
                  onClick={copyAiPrompt}
                  style={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    background: copied ? 'rgba(38,166,154,0.2)' : 'var(--bg-tertiary)',
                    border: '1px solid ' + (copied ? 'var(--accent-green)' : 'var(--border-color)'),
                    borderRadius: 4,
                    padding: '4px 10px',
                    color: copied ? 'var(--accent-green)' : 'var(--text-secondary)',
                    fontSize: 12,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                  {copied ? '已复制' : '复制到 TRAE'}
                </button>
              </div>
            )}
          </div>
        </>
      )}

      {/* ===== 回测结果（两个 Tab 共用） ===== */}
      {result && (
        <div className="animate-fade-in">
          {/* 结果标题 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
              回测结果
            </h3>
            {result.engine === 'backtrader' && (
              <span className="tag tag-blue" style={{ fontSize: 10 }}>Backtrader</span>
            )}
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {result.strategy} · {result.symbol} · {result.period}
            </span>
          </div>

          {/* 绩效指标 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 20 }}>
            {[
              { label: '总收益率', value: `${result.total_return.toFixed(2)}%`, icon: Percent, color: result.total_return >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' },
              { label: '年化收益率', value: `${result.annual_return.toFixed(2)}%`, icon: TrendingUp, color: result.annual_return >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' },
              { label: '最大回撤', value: `${result.max_drawdown.toFixed(2)}%`, icon: TrendingDown, color: 'var(--accent-red)' },
              { label: '夏普比率', value: result.sharpe_ratio.toFixed(2), icon: Target, color: result.sharpe_ratio >= 1 ? 'var(--accent-green)' : 'var(--accent-yellow)' },
              { label: '胜率', value: `${result.win_rate.toFixed(1)}%`, icon: Shield, color: result.win_rate >= 50 ? 'var(--accent-green)' : 'var(--accent-red)' },
              { label: '盈亏比', value: result.profit_factor.toFixed(2), icon: DollarSign, color: result.profit_factor >= 1.5 ? 'var(--accent-green)' : 'var(--accent-yellow)' },
              { label: '交易次数', value: String(result.total_trades), icon: BarChart3, color: 'var(--text-primary)' },
              { label: '盈利/亏损', value: `${result.profit_trades} / ${result.loss_trades}`, icon: Activity, color: 'var(--text-primary)' },
            ].map((item, i) => (
              <div key={i} className="trading-card" style={{ textAlign: 'center', padding: '12px' }}>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 6, textTransform: 'uppercase' }}>
                  {item.label}
                </div>
                <div style={{ fontSize: 22, fontWeight: 700, color: item.color }}>
                  {item.value}
                </div>
              </div>
            ))}
          </div>

          {/* 净值曲线 */}
          <div className="trading-card" style={{ marginBottom: 20 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
              净值曲线
            </h3>
            <div style={{ height: 300, position: 'relative' }}>
              <svg width="100%" height="100%" viewBox="0 0 800 300" preserveAspectRatio="xMidYMid meet">
                {[0, 0.25, 0.5, 0.75, 1].map((pct) => (
                  <line key={pct}
                    x1="0" y1={pct * 300} x2="800" y2={pct * 300}
                    stroke="var(--border-color)" strokeWidth="0.5" strokeDasharray="4,4"
                  />
                ))}
                {result.equity_curve.length > 1 && (() => {
                  const minE = Math.min(...result.equity_curve.map(p => p.equity));
                  const maxE = Math.max(...result.equity_curve.map(p => p.equity));
                  const range = maxE - minE || 1;
                  const points = result.equity_curve.map((p, i) => {
                    const x = (i / (result.equity_curve.length - 1)) * 780 + 10;
                    const y = 290 - ((p.equity - minE) / range) * 280;
                    return `${x},${y}`;
                  }).join(' ');
                  return (
                    <>
                      <polyline
                        points={points}
                        fill="none"
                        stroke="var(--accent-green)"
                        strokeWidth="2"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                      />
                      <defs>
                        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--accent-green)" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="var(--accent-green)" stopOpacity="0" />
                        </linearGradient>
                      </defs>
                      <polygon
                        points={`${points} 790,300 10,300`}
                        fill="url(#equityGrad)"
                      />
                    </>
                  );
                })()}
              </svg>
            </div>
          </div>

          {/* 交易记录 */}
          <div className="trading-card">
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: 'var(--text-primary)' }}>
              交易记录
            </h3>
            <div style={{ overflow: 'auto', maxHeight: 400 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>类型</th>
                    <th style={{ textAlign: 'right' }}>价格</th>
                    <th style={{ textAlign: 'right' }}>数量</th>
                    <th style={{ textAlign: 'right' }}>金额</th>
                    <th style={{ textAlign: 'right' }}>盈亏</th>
                    <th style={{ textAlign: 'right' }}>盈亏%</th>
                    <th>原因</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((trade, i) => (
                    <tr key={i}>
                      <td>{trade.date}</td>
                      <td>
                        <span className={`tag ${trade.type === 'buy' ? 'tag-green' : 'tag-red'}`}>
                          {trade.type === 'buy' ? '买入' : '卖出'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>{trade.price.toFixed(2)}</td>
                      <td style={{ textAlign: 'right' }}>{trade.shares}</td>
                      <td style={{ textAlign: 'right' }}>{formatMoney(trade.amount)}</td>
                      <td style={{
                        textAlign: 'right',
                        fontWeight: 600,
                        color: (trade.profit || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                      }}>
                        {trade.profit !== undefined ? `${trade.profit >= 0 ? '+' : ''}${formatMoney(trade.profit)}` : '-'}
                      </td>
                      <td style={{
                        textAlign: 'right',
                        color: (trade.profit_pct || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                      }}>
                        {trade.profit_pct !== undefined ? `${trade.profit_pct >= 0 ? '+' : ''}${trade.profit_pct.toFixed(2)}%` : '-'}
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{trade.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}