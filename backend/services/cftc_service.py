"""
CFTC 持仓数据服务 - 基于 Socrata Open Data API
数据来源: publicreporting.cftc.gov (需VPN/代理)
"""
import pandas as pd
import numpy as np
import requests
import json
import time
import os
from datetime import datetime, timedelta
from pathlib import Path

# 缓存目录
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cftc_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE_DIR / "latest_report.json"
CACHE_TTL = 7200  # 2小时

# Socrata API 端点
CFTC_TFF_URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
CFTC_DISAGG_URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"

LOOKBACK_DAYS = 1200
ZSCORE_WINDOW = 156

# 代理配置（从环境变量读取）
CFTC_PROXY = os.environ.get("CFTC_PROXY", "")

# ============================================================================
# 合约映射
# ============================================================================

TFF_CONTRACTS = [
    {"name": "标普500",        "cftc": "E-MINI S&P 500 -",   "section": "股指"},
    {"name": "纳斯达克100",    "cftc": "NASDAQ MINI",          "section": "股指"},
    {"name": "罗素2000",       "cftc": "RUSSELL E-MINI",       "section": "股指"},
    {"name": "MSCI新兴市场",   "cftc": "MSCI EM INDEX",        "section": "股指"},
    {"name": "MSCI发达市场",   "cftc": "MSCI EAFE",            "section": "股指"},
    {"name": "日经225",        "cftc": "NIKKEI STOCK AVERAGE",  "section": "股指"},
    {"name": "2年期美债",      "cftc": "UST 2Y NOTE",          "section": "债券"},
    {"name": "10年期美债",     "cftc": "UST 10Y NOTE",         "section": "债券"},
    {"name": "超长期美债",     "cftc": "ULTRA UST BOND",       "section": "债券"},
    {"name": "联邦基金",       "cftc": "FED FUNDS",            "section": "利率"},
    {"name": "欧元/美元",      "cftc": "EURO FX - CHICAGO",             "section": "外汇/加密"},
    {"name": "英镑/美元",      "cftc": "BRITISH POUND",                 "section": "外汇/加密"},
    {"name": "日元/美元",      "cftc": "JAPANESE YEN",                  "section": "外汇/加密"},
    {"name": "澳元/美元",      "cftc": "AUSTRALIAN DOLLAR",             "section": "外汇/加密"},
    {"name": "比特币",         "cftc": "BITCOIN - CHICAGO MERCANTILE",  "section": "外汇/加密"},
]

DISAGG_CONTRACTS = [
    {"name": "WTI原油",     "cftc": "WTI-PHYSICAL",         "section": "能源"},
    {"name": "天然气",      "cftc": "NAT GAS NYME",         "section": "能源"},
    {"name": "铜",          "cftc": "COPPER- #1",           "section": "金属"},
    {"name": "黄金",        "cftc": "GOLD - COMMODITY",     "section": "金属"},
    {"name": "白银",        "cftc": "SILVER - COMMODITY",   "section": "金属"},
    {"name": "玉米",        "cftc": "CORN - CHICAGO",       "section": "农产品"},
]


# ============================================================================
# 数据获取
# ============================================================================

def _get_session():
    """创建带代理配置的 requests session"""
    session = requests.Session()
    if CFTC_PROXY:
        session.proxies = {"http": CFTC_PROXY, "https": CFTC_PROXY}
    return session


def fetch_cftc(endpoint, start_date, limit=50000):
    """从 CFTC Socrata API 获取数据"""
    params = {
        "$where": f"report_date_as_yyyy_mm_dd >= '{start_date}'",
        "$limit": limit,
        "$order": "report_date_as_yyyy_mm_dd ASC",
    }
    session = _get_session()

    for attempt in range(3):
        try:
            resp = session.get(endpoint, params=params, timeout=120)
            resp.raise_for_status()
            break
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            if attempt < 2:
                time.sleep(3)
            else:
                raise e

    data = resp.json()
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # 跳过非数值列
    skip_cols = {
        "market_and_exchange_names", "report_date_as_yyyy_mm_dd",
        "cftc_contract_market_code", "cftc_market_code", "cftc_commodity_code",
        "cftc_region_code", "cftc_subgroup_code", "contract_market_name",
        "contract_units", "futonly_or_combined", "id", "commodity",
        "commodity_group_name", "commodity_name", "commodity_subgroup_name",
        "report_date_as_mm_dd_yyyy", "yyyy_report_week_ww",
    }
    for col in df.columns:
        if col not in skip_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["report_date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    return df


def match_cftc(df, search_pattern):
    """按名称匹配 CFTC 合约"""
    if search_pattern is None or df.empty:
        return None
    names_upper = df["market_and_exchange_names"].str.upper()
    pattern_upper = search_pattern.upper()

    mask = names_upper == pattern_upper
    if not mask.any():
        mask = names_upper.str.startswith(pattern_upper, na=False)
    if not mask.any():
        mask = df["market_and_exchange_names"].str.contains(search_pattern, case=False, na=False)

    matched = df[mask].copy()
    if matched.empty:
        return None

    # 去重：优先选 Consolidated
    if matched["market_and_exchange_names"].nunique() > 1:
        names = matched["market_and_exchange_names"].unique()
        for n in names:
            if "Consolidated" in n:
                matched = matched[matched["market_and_exchange_names"] == n]
                break
        else:
            avg_oi = matched.groupby("market_and_exchange_names")["open_interest_all"].mean()
            matched = matched[matched["market_and_exchange_names"] == avg_oi.idxmax()]

    return matched.sort_values("report_date").reset_index(drop=True)


# ============================================================================
# 计算
# ============================================================================

def calc_zscore(series, window=ZSCORE_WINDOW):
    s = series.dropna()
    if len(s) < 10:
        return np.nan
    tail = s.tail(window)
    mean, std = tail.mean(), tail.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return round(float((s.iloc[-1] - mean) / std), 1)


def calc_change_zscore(series, window=ZSCORE_WINDOW):
    changes = series.diff().dropna()
    if len(changes) < 10:
        return np.nan
    tail = changes.tail(window)
    mean, std = tail.mean(), tail.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return round(float((changes.iloc[-1] - mean) / std), 1)


def _flow_state(z_dlong, z_dshort):
    """根据多空变化 z-score 判定 flow state"""
    if z_dlong is None or z_dshort is None:
        return ""
    if isinstance(z_dlong, float) and np.isnan(z_dlong):
        return ""
    if isinstance(z_dshort, float) and np.isnan(z_dshort):
        return ""
    zl, zs = float(z_dlong), float(z_dshort)

    if zl >= 0.8 and zs <= -0.8:
        return "多头挤压"
    if zl <= -0.8 and zs >= 0.8:
        return "空头施压"
    if zl >= 0.8 and zs >= 0.8:
        return "多空双增"
    if zl <= -0.8 and zs <= -0.8:
        return "多空双减"
    if zl >= 0.8 and abs(zs) < 0.5:
        return "多头建仓"
    if zs <= -0.8 and abs(zl) < 0.5:
        return "空头回补"
    if zs >= 0.8 and abs(zl) < 0.5:
        return "空头建仓"
    if zl <= -0.8 and abs(zs) < 0.5:
        return "多头平仓"
    return ""


def _pos_group(matched, long_col, short_col):
    """计算一组持仓的 net/long/short 的 position, z-score, w/w change"""
    long_s = matched[long_col].fillna(0)
    short_s = matched[short_col].fillna(0)
    net_s = long_s - short_s
    oi = matched["open_interest_all"].fillna(0).replace(0, np.nan)

    long_oi = long_s / oi
    short_oi = short_s / oi
    net_oi = net_s / oi

    latest_long = float(long_s.iloc[-1])
    latest_short = float(short_s.iloc[-1])
    latest_net = latest_long - latest_short

    z_dlong = calc_change_zscore(long_s)
    z_dshort = calc_change_zscore(short_s)

    return {
        "net": int(latest_net),
        "net_z": calc_zscore(net_oi),
        "net_ww": int(net_s.diff().iloc[-1]) if len(net_s) > 1 else 0,
        "net_ww_z": calc_change_zscore(net_s),
        "long": int(latest_long),
        "long_z": calc_zscore(long_oi),
        "long_ww": int(long_s.diff().iloc[-1]) if len(long_s) > 1 else 0,
        "long_ww_z": z_dlong,
        "short": int(latest_short),
        "short_z": calc_zscore(short_oi),
        "short_ww": int(short_s.diff().iloc[-1]) if len(short_s) > 1 else 0,
        "short_ww_z": z_dshort,
        "flow_state": _flow_state(z_dlong, z_dshort),
    }


def _crowding(net_z, long_z=None, short_z=None):
    """判定拥挤度"""
    def _safe(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return 0.0
        return float(v)
    nz, lz, sz = _safe(net_z), _safe(long_z), _safe(short_z)

    if nz >= 2.75 or lz >= 2.75:
        return {"level": "extreme", "label": "极端多头", "direction": "long"}
    if nz >= 2.0 or lz >= 2.0:
        return {"level": "crowded", "label": "拥挤多头", "direction": "long"}
    if nz <= -2.75 or sz >= 2.75:
        return {"level": "extreme", "label": "极端空头", "direction": "short"}
    if nz <= -2.0 or sz >= 2.0:
        return {"level": "crowded", "label": "拥挤空头", "direction": "short"}
    return {"level": "normal", "label": "", "direction": ""}


# ============================================================================
# 分析报告生成
# ============================================================================

def _generate_analysis(tff_items, disagg_items, report_date):
    """生成持仓分析报告"""
    all_items = tff_items + disagg_items
    findings = []

    # 统计概览
    net_bull = sum(1 for item in all_items if item.get("net", 0) > 0)
    net_bear = sum(1 for item in all_items if item.get("net", 0) < 0)
    extreme_count = sum(1 for item in all_items if item.get("crowding", {}).get("level") == "extreme")
    crowded_count = sum(1 for item in all_items if item.get("crowding", {}).get("level") == "crowded")

    # 按 section 汇总
    section_summary = {}
    for item in all_items:
        sec = item.get("section", "其他")
        if sec not in section_summary:
            section_summary[sec] = {"net_bull": 0, "net_bear": 0, "items": []}
        if item.get("net", 0) > 0:
            section_summary[sec]["net_bull"] += 1
        elif item.get("net", 0) < 0:
            section_summary[sec]["net_bear"] += 1
        section_summary[sec]["items"].append(item.get("instrument", ""))

    # 极端拥挤预警
    for item in all_items:
        c = item.get("crowding", {})
        if c.get("level") == "extreme":
            findings.append({
                "type": "warning",
                "title": f"{item['instrument']} - {c['label']}",
                "detail": f"净持仓 z-score: {item.get('net_z', 'N/A')}，多头 z: {item.get('long_z', 'N/A')}，空头 z: {item.get('short_z', 'N/A')}。{item.get('flow_state', '')}，需关注反转风险。",
            })

    # 拥挤但未极端的
    for item in all_items:
        c = item.get("crowding", {})
        if c.get("level") == "crowded":
            findings.append({
                "type": "info",
                "title": f"{item['instrument']} - {c['label']}",
                "detail": f"净持仓 z-score: {item.get('net_z', 'N/A')}，当前处于拥挤区间，{item.get('flow_state', '')}。",
            })

    # 多空双增/双减 特殊信号
    special_flows = ["多空双增", "多空双减", "多头挤压", "空头施压"]
    for item in all_items:
        if item.get("flow_state") in special_flows:
            findings.append({
                "type": "info",
                "title": f"{item['instrument']} - {item['flow_state']}",
                "detail": f"多空博弈加剧，多头变化 z: {item.get('long_ww_z', 'N/A')}，空头变化 z: {item.get('short_ww_z', 'N/A')}，需关注方向选择。",
            })

    return {
        "report_date": report_date,
        "summary": {
            "total_instruments": len(all_items),
            "net_bull": net_bull,
            "net_bear": net_bear,
            "extreme_count": extreme_count,
            "crowded_count": crowded_count,
        },
        "section_summary": section_summary,
        "findings": findings,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ============================================================================
# 主入口
# ============================================================================

def _load_cache():
    """加载缓存"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            age = time.time() - data.get("_cached_at", 0)
            if age < CACHE_TTL:
                return data
        except Exception:
            pass
    return None


def _save_cache(report):
    """保存缓存"""
    report["_cached_at"] = time.time()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, default=str)


def get_latest_cftc_report(force_refresh=False):
    """获取最新 CFTC 持仓报告"""
    # 读缓存
    if not force_refresh:
        cached = _load_cache()
        if cached:
            cached["source"] = "CFTC Socrata API (cached)"
            return cached

    start_date = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    # 获取数据
    df_tff = fetch_cftc(CFTC_TFF_URL, start_date)
    df_disagg = fetch_cftc(CFTC_DISAGG_URL, start_date)

    if df_tff.empty and df_disagg.empty:
        raise RuntimeError("CFTC 数据为空，请检查网络/VPN连接")

    report_date = df_tff["report_date"].max().strftime("%Y-%m-%d") if not df_tff.empty else "N/A"

    # 构建 TFF 数据
    tff_items = []
    for c in TFF_CONTRACTS:
        matched = match_cftc(df_tff, c["cftc"])
        if matched is None or matched.empty:
            continue
        pos = _pos_group(matched, "lev_money_positions_long", "lev_money_positions_short")
        item = {
            "instrument": c["name"],
            "section": c["section"],
            "trader_type": "Leveraged Funds",
            **pos,
            "crowding": _crowding(pos.get("net_z"), pos.get("long_z"), pos.get("short_z")),
        }
        tff_items.append(item)

    # 构建 Disaggregated 数据
    disagg_items = []
    for c in DISAGG_CONTRACTS:
        matched = match_cftc(df_disagg, c["cftc"])
        if matched is None or matched.empty:
            continue
        pos = _pos_group(matched, "m_money_positions_long_all", "m_money_positions_short_all")
        item = {
            "instrument": c["name"],
            "section": c["section"],
            "trader_type": "Managed Money",
            **pos,
            "crowding": _crowding(pos.get("net_z"), pos.get("long_z"), pos.get("short_z")),
        }
        disagg_items.append(item)

    # 生成分析
    analysis = _generate_analysis(tff_items, disagg_items, report_date)

    report = {
        "report_date": report_date,
        "tff_items": tff_items,
        "disagg_items": disagg_items,
        "analysis": analysis,
        "source": "CFTC Socrata API",
        "updated_at": datetime.now().isoformat(),
    }

    _save_cache(report)
    return report


def get_cftc_history(commodity="", weeks=12):
    """获取 CFTC 历史数据（简化版，返回近期数据摘要）"""
    start_date = (datetime.now() - timedelta(days=weeks * 10)).strftime("%Y-%m-%d")

    df_tff = fetch_cftc(CFTC_TFF_URL, start_date, limit=5000)
    df_disagg = fetch_cftc(CFTC_DISAGG_URL, start_date, limit=5000)

    history = []

    for source_name, df, contracts, long_col, short_col in [
        ("TFF", df_tff, TFF_CONTRACTS, "lev_money_positions_long", "lev_money_positions_short"),
        ("Disagg", df_disagg, DISAGG_CONTRACTS, "m_money_positions_long_all", "m_money_positions_short_all"),
    ]:
        for c in contracts:
            if commodity and commodity not in c["name"]:
                continue
            matched = match_cftc(df, c["cftc"])
            if matched is None or matched.empty:
                continue
            records = []
            for _, row in matched.iterrows():
                net = float(row.get(long_col, 0) or 0) - float(row.get(short_col, 0) or 0)
                records.append({
                    "date": str(row.get("report_date", ""))[:10],
                    "net": int(net),
                    "long": int(row.get(long_col, 0) or 0),
                    "short": int(row.get(short_col, 0) or 0),
                })
            history.append({
                "instrument": c["name"],
                "section": c["section"],
                "source": source_name,
                "records": records[-weeks:],
            })

    return {"history": history, "weeks": weeks}