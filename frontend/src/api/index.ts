/**
 * API 基础 URL
 * 本地开发时使用 Vite 代理 (/api → localhost:8000)
 * 回测和个股分析等需要本地后端的接口强制使用 /api
 */
function getBaseUrl(useLocal = false): string {
  return '/api';
}

async function request<T>(url: string, options?: RequestInit, useLocal = false): Promise<T> {
  const baseUrl = getBaseUrl(useLocal);
  const res = await fetch(`${baseUrl}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '请求失败');
  }
  return res.json();
}

// ========== 回测 API（强制使用本地后端）==========
export const backtestApi = {
  getStrategies: () => request<{ strategies: { name: string; file: string; preview: string; engine: string; size: number }[] }>('/backtest/strategies', undefined, true),
  run: (params: {
    strategy_name: string;
    symbol: string;
    market: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    commission: number;
    params?: Record<string, unknown>;
  }) => request('/backtest/run', { method: 'POST', body: JSON.stringify(params) }, true),
  runMulti: (params: {
    strategy_name: string;
    symbols: string[];
    market: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    commission: number;
    params?: Record<string, unknown>;
  }) => request('/backtest/run-multi', { method: 'POST', body: JSON.stringify(params) }, true),
  runCode: (params: {
    code: string;
    symbol: string;
    market: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    commission: number;
  }) => request('/backtest/run-code', { method: 'POST', body: JSON.stringify(params) }, true),
  runMultiCode: (params: {
    code: string;
    symbols: string[];
    market: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    commission: number;
  }) => request('/backtest/run-multi-code', { method: 'POST', body: JSON.stringify(params) }, true),
  saveCode: (params: { name: string; code: string; overwrite?: boolean }) =>
    request('/backtest/strategies/save', { method: 'POST', body: JSON.stringify(params) }, true),
  getCode: (name: string) => request<{ name: string; code: string }>(`/backtest/strategies/${name}/code`, undefined, true),
  getAiPrompt: (params: { description: string; symbol?: string; market?: string }) =>
    request<{ prompt: string; description: string; market: string; symbol: string }>(
      '/backtest/ai-prompt', { method: 'POST', body: JSON.stringify(params) }, true
    ),
  uploadStrategy: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${getBaseUrl(true)}/backtest/strategies/upload`, {
      method: 'POST',
      body: formData,
    }).then(r => r.json());
  },
  deleteStrategy: (name: string) =>
    request(`/backtest/strategies/${name}`, { method: 'DELETE' }, true),
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

// ========== 个股分析 API（强制使用本地后端）==========
export const stockApi = {
  search: (keyword: string, market?: string) => request(`/stock/search?keyword=${encodeURIComponent(keyword)}&market=${market || 'A'}`, undefined, true),
  getQuote: (symbol: string, market?: string) =>
    request(`/stock/quote?symbol=${symbol}&market=${market || 'A'}`, undefined, true),
  analyze: (params: {
    symbol: string;
    market: string;
    analysis_types: string[];
  }) => request('/stock/analyze', { method: 'POST', body: JSON.stringify(params) }, true),
  getKline: (symbol: string, market?: string, period?: string, count?: number) =>
    request(`/stock/kline?symbol=${symbol}&market=${market || 'A'}&period=${period || 'daily'}&count=${count || 250}`, undefined, true),
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
  }>('/stock/research-report', { method: 'POST', body: JSON.stringify(params) }, true),
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
  }>('/stock/llm-providers', undefined, true),
};

// ========== 系统 ==========
export const systemApi = {
  healthCheck: () => request<{ status: string; service: string }>('/health'),
};