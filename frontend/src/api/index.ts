const BASE_URL = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '请求失败');
  }
  return res.json();
}

// ========== 回测 API ==========
export const backtestApi = {
  getStrategies: () => request<{ strategies: { name: string; file: string; preview: string; engine: string; size: number }[] }>('/backtest/strategies'),
  run: (params: {
    strategy_name: string;
    symbol: string;
    market: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    commission: number;
    params?: Record<string, unknown>;
  }) => request('/backtest/run', { method: 'POST', body: JSON.stringify(params) }),
  // 多股票组合回测
  runMulti: (params: {
    strategy_name: string;
    symbols: string[];
    market: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    commission: number;
    params?: Record<string, unknown>;
  }) => request('/backtest/run-multi', { method: 'POST', body: JSON.stringify(params) }),
  // 直接运行代码
  runCode: (params: {
    code: string;
    symbol: string;
    market: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    commission: number;
  }) => request('/backtest/run-code', { method: 'POST', body: JSON.stringify(params) }),
  // 多股票代码直接运行
  runMultiCode: (params: {
    code: string;
    symbols: string[];
    market: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    commission: number;
  }) => request('/backtest/run-multi-code', { method: 'POST', body: JSON.stringify(params) }),
  // 保存策略代码
  saveCode: (params: { name: string; code: string; overwrite?: boolean }) =>
    request('/backtest/strategies/save', { method: 'POST', body: JSON.stringify(params) }),
  // 获取策略源码
  getCode: (name: string) => request<{ name: string; code: string }>(`/backtest/strategies/${name}/code`),
  // 生成 AI 提示词
  getAiPrompt: (params: { description: string; symbol?: string; market?: string }) =>
    request<{ prompt: string; description: string; market: string; symbol: string }>(
      '/backtest/ai-prompt', { method: 'POST', body: JSON.stringify(params) }
    ),
  uploadStrategy: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${BASE_URL}/backtest/strategies/upload`, {
      method: 'POST',
      body: formData,
    }).then(r => r.json());
  },
  deleteStrategy: (name: string) =>
    request(`/backtest/strategies/${name}`, { method: 'DELETE' }),
};

// ========== 市场数据 API ==========
export const marketApi = {
  // CFTC
  getCFTCLatest: () => request('/market/cftc/latest'),
  refreshCFTC: () => request('/market/cftc/refresh'),
  getCFTCAnalysis: () => request('/market/cftc/analysis'),
  getCFTCTFF: () => request('/market/cftc/tff'),
  getCFTCDisagg: () => request('/market/cftc/disagg'),
  getCFTCHistory: (commodity?: string, weeks?: number) =>
    request(`/market/cftc/history?commodity=${commodity || ''}&weeks=${weeks || 12}`),
  // CBOE
  getPutCall: (days?: number) => request(`/market/cboe/putcall?days=${days || 30}`),
  getPutCallAnalysis: () => request('/market/cboe/analysis'),
  getPutCallLatest: () => request('/market/cboe/latest'),
  // SSE 上交所期权
  getSSEOptionsDaily: (date?: string) =>
    request(`/market/sse/options/daily${date ? `?date=${date}` : ''}`),
  getSSEOptionsAnalysis: () => request('/market/sse/options/analysis'),
  getSSEOptionsLatest: () => request('/market/sse/options/latest'),
  getSSEOptionsHistory: (days?: number) =>
    request(`/market/sse/options/history?days=${days || 30}`),
  getSSEOptionsTracking: () => request('/market/sse/options/tracking'),
  // 持续跟踪
  getCFTCTracking: (forceRefresh?: boolean) =>
    request(`/market/cftc/tracking?force_refresh=${forceRefresh || false}`),
  getCFTCInstrumentTracking: (instrument: string, weeks?: number) =>
    request(`/market/cftc/tracking/${encodeURIComponent(instrument)}?weeks=${weeks || 12}`),
  getCBOETracking: () => request('/market/cboe/tracking'),
  getCBOEDailyComparison: (days?: number) =>
    request(`/market/cboe/tracking/daily?days=${days || 7}`),
  // 总览
  getOverview: () => request('/market/overview'),
};

// ========== 新闻推送 API ==========
export const newsApi = {
  getDailyEvents: (date?: string) =>
    request(`/news/daily-events${date ? `?date=${date}` : ''}`),
  getInsights: (days?: number) =>
    request(`/news/insights?days=${days || 3}`),
  get13FMonitor: (lookbackDays?: number) =>
    request(`/news/13f?lookback_days=${lookbackDays || 45}`),
  getDigest: () => request('/news/digest'),
};

// ========== 个股分析 API ==========
export const stockApi = {
  search: (keyword: string, market?: string) => request(`/stock/search?keyword=${encodeURIComponent(keyword)}&market=${market || 'A'}`),
  getQuote: (symbol: string, market?: string) =>
    request(`/stock/quote?symbol=${symbol}&market=${market || 'A'}`),
  analyze: (params: {
    symbol: string;
    market: string;
    analysis_types: string[];
  }) => request('/stock/analyze', { method: 'POST', body: JSON.stringify(params) }),
  getKline: (symbol: string, market?: string, period?: string, count?: number) =>
    request(`/stock/kline?symbol=${symbol}&market=${market || 'A'}&period=${period || 'daily'}&count=${count || 250}`),
  // 深度研报
  getResearchReport: (params: {
    symbol: string;
    market: string;
    deep_analysis?: boolean;
    llm_config?: {
      provider: string;
      api_key: string;
      base_url?: string;
      model?: string;
    };
  }) => request<{
    symbol: string;
    name: string;
    market: string;
    report_markdown: string;
    report_time: string;
    ai_generated?: boolean;
    sections: Record<string, unknown>;
  }>('/stock/research-report', { method: 'POST', body: JSON.stringify(params) }),
  // LLM Provider信息
  getLLMProviders: () => request<{
    providers: Array<{
      id: string;
      name: string;
      description: string;
      default_model: string;
      base_url: string;
      register_url: string;
    }>;
    server_has_default: boolean;
    server_default_provider: string | null;
  }>('/stock/llm-providers'),
};