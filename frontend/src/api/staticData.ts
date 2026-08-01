/**
 * 静态数据加载模块
 * 在 GitHub Pages 等静态部署环境中，从 JSON 文件加载数据
 * 作为云端 API 的备用数据源
 */

// 基础路径 - 在 GitHub Pages 上需要根据仓库名调整
const basePath = () => {
  const bp = import.meta.env.VITE_BASE_PATH || '';
  return `${bp}/data`;
};

/** 判断是否处于静态部署模式（GitHub Pages） */
function isStaticMode(): boolean {
  return import.meta.env.VITE_STATIC_MODE === 'true';
}

async function loadJSON<T>(path: string): Promise<T | null> {
  try {
    const fullPath = `${basePath()}${path}`;
    const res = await fetch(fullPath);
    if (!res.ok) {
      console.warn(`静态数据加载失败: ${fullPath} (${res.status})`);
      return null;
    }
    return res.json();
  } catch (e) {
    console.warn(`静态数据加载异常: ${path}`, e);
    return null;
  }
}

// ========== CBOE 数据 ==========

export interface CBOEData {
  report_date: string;
  total_put_call_ratio: number;
  total_calls: number;
  total_puts: number;
  total_volume: number;
  latest_time: string;
  index_put_call_ratio: number | null;
  equity_put_call_ratio: number | null;
  intraday: Array<{
    time: string;
    calls: number;
    puts: number;
    total_volume: number;
    pc_ratio: number;
  }>;
  source: string;
  fetched_at: string;
}

export interface DailyEventsData {
  date: string;
  summary: string;
  events: Array<{
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
  }>;
  by_category: {
    economic_data: unknown[];
    central_bank: unknown[];
    speeches: unknown[];
    meetings: unknown[];
  };
  high_impact: unknown[];
}

export interface InsightsData {
  total_insights: number;
  insights: Array<{
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
  }>;
  by_topic: Record<string, unknown[]>;
  period: string;
  source: string;
}

export interface ManifestData {
  generated_at: string;
  date: string;
  files: Array<{
    path: string;
    size: number;
    modified: string;
  }>;
}

// 获取最新的 CBOE 数据文件
async function getLatestCBOE(): Promise<CBOEData | null> {
  // 尝试加载今日数据
  const today = new Date().toISOString().split('T')[0];
  let data = await loadJSON<CBOEData>(`/cboe/cboe_${today}.json`);
  if (data) return data;

  // 如果今日数据不存在，加载最新缓存
  const manifest = await loadJSON<ManifestData>('/manifest.json');
  if (manifest) {
    const cboeFiles = manifest.files
      .filter(f => f.path.startsWith('data/cboe/cboe_'))
      .sort()
      .reverse();
    if (cboeFiles.length > 0) {
      const latestFile = cboeFiles[0].path.replace('data', '');
      data = await loadJSON<CBOEData>(latestFile);
    }
  }
  return data;
}

export const staticDataApi = {
  /** 获取 CBOE Put/Call 比率数据 */
  getCBOELatest: () => getLatestCBOE(),

  /** 获取每日市场事件 */
  getDailyEvents: () => loadJSON<DailyEventsData>('/news/daily_events.json'),

  /** 获取新闻观点 */
  getInsights: () => loadJSON<InsightsData>('/news/insights.json'),

  /** 获取数据清单 */
  getManifest: () => loadJSON<ManifestData>('/manifest.json'),

  /** 是否处于静态部署模式 */
  isStaticMode,
};