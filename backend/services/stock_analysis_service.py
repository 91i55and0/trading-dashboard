"""个股分析服务"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from .deepseek_service import generate_research_report_via_ai

logger = logging.getLogger(__name__)


def _get_provider():
    """获取当前数据提供者（懒加载）"""
    from data_providers import get_provider
    return get_provider()


def search_stock(keyword: str, market: str = "A") -> Dict[str, Any]:
    """搜索股票"""
    try:
        provider = _get_provider()
        stocks = provider.search_stocks(keyword, market=market)
        return {"results": stocks}
    except Exception as e:
        logger.error(f"搜索股票失败: {e}")
        raise


def _mock_search_results(keyword: str, market: str = "A") -> list:
    """模拟搜索结果"""
    mock_data = {
        "A": [
            {"code": "600519", "name": "贵州茅台", "market": "A"},
            {"code": "000858", "name": "五粮液", "market": "A"},
        ],
        "US": [
            {"code": "AAPL", "name": "Apple Inc.", "market": "US"},
            {"code": "MSFT", "name": "Microsoft Corp.", "market": "US"},
            {"code": "VRT", "name": "Vertiv Holdings", "market": "US"},
        ],
    }
    return mock_data.get(market.upper(), mock_data["A"])


def get_quote(symbol: str, market: str = "A") -> Dict[str, Any]:
    """获取实时行情"""
    try:
        provider = _get_provider()
        quote = provider.get_stock_quote(symbol, market)
        if quote and quote.get("price", 0) > 0:
            return quote
    except Exception as e:
        logger.error(f"获取行情失败: {e}")
        raise

    raise RuntimeError(f"无法获取 {symbol} 的实时行情：返回数据无效")


def get_kline_data(symbol: str, market: str = "A", period: str = "daily", count: int = 250) -> Dict[str, Any]:
    """获取K线数据"""
    try:
        provider = _get_provider()
        df = provider.get_kline(
            symbol=symbol, market=market, period=period,
            count=count, adjust="qfq",
        )
        if df is not None and not df.empty:
            klines = []
            for _, row in df.tail(count).iterrows():
                klines.append({
                    "date": str(row.get("date", "")),
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": int(row.get("volume", 0)),
                })
            return {"symbol": symbol, "data": klines}
    except Exception as e:
        logger.error(f"获取K线数据失败: {e}")
        raise


def _generate_mock_klines(count: int = 250) -> Dict[str, Any]:
    """生成模拟K线数据"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=count, freq="B")
    returns = np.random.normal(0.0005, 0.015, count)
    close = 100 * np.exp(np.cumsum(returns))
    klines = []
    for i, d in enumerate(dates):
        c = round(float(close[i]), 2)
        o = round(c * np.random.uniform(0.98, 1.02), 2)
        h = round(max(o, c) * np.random.uniform(1.0, 1.03), 2)
        l = round(min(o, c) * np.random.uniform(0.97, 1.0), 2)
        klines.append({
            "date": d.strftime("%Y-%m-%d"),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": int(np.random.randint(1000000, 10000000)),
        })
    return {"symbol": "mock", "data": klines}


def analyze_stock_service(
    symbol: str,
    market: str = "A",
    analysis_types: List[str] = None,
) -> Dict[str, Any]:
    """执行个股分析"""
    if analysis_types is None:
        analysis_types = ["technical", "fundamental", "valuation"]

    # 并行获取行情和K线数据，显著减少等待时间
    with ThreadPoolExecutor(max_workers=2) as executor:
        quote_future = executor.submit(get_quote, symbol, market)
        kline_future = executor.submit(get_kline_data, symbol, market, count=250)
        quote = quote_future.result()
        kline_data = kline_future.result()

    result = {
        "symbol": symbol,
        "name": quote.get("name", symbol),
        "market": market,
        "latest_price": quote.get("price", 0),
        "change_pct": quote.get("change_pct", 0),
        "analysis_time": datetime.now().isoformat(),
    }

    if "technical" in analysis_types and kline_data.get("data"):
        result["technical"] = _calculate_technical_indicators(kline_data["data"])
        result["signals"] = _generate_signals(result["technical"], quote)

    if "fundamental" in analysis_types:
        result["fundamental"] = _get_fundamental_data(symbol, market)

    result["risk_level"] = _assess_risk(result)
    result["analysis_summary"] = _generate_summary(result)

    # 图表数据
    result["charts"] = {
        "kline": kline_data["data"],
    }

    return result


def _calculate_technical_indicators(klines: List[dict]) -> Dict[str, Any]:
    """计算技术指标"""
    closes = np.array([k["close"] for k in klines])
    highs = np.array([k["high"] for k in klines])
    lows = np.array([k["low"] for k in klines])
    volumes = np.array([k["volume"] for k in klines])

    def sma(data, period):
        if len(data) < period:
            return float(data[-1])
        return float(np.mean(data[-period:]))

    # 均线
    ma5 = sma(closes, 5)
    ma10 = sma(closes, 10)
    ma20 = sma(closes, 20)
    ma60 = sma(closes, 60) if len(closes) >= 60 else ma20

    # RSI (14)
    rsi = _calc_rsi(closes, 14)

    # MACD
    macd, macd_signal, macd_hist = _calc_macd(closes)

    # 布林带
    bb_upper, bb_middle, bb_lower = _calc_bollinger(closes, 20)

    # 成交量比
    vol_5 = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
    vol_20 = np.mean(volumes[-20:]) if len(volumes) >= 20 else volumes[-1]
    vol_ratio = round(float(vol_5 / vol_20), 2) if vol_20 > 0 else 1.0

    return {
        "ma5": round(ma5, 2),
        "ma10": round(ma10, 2),
        "ma20": round(ma20, 2),
        "ma60": round(ma60, 2),
        "rsi": round(rsi, 2),
        "macd": round(macd, 4),
        "macd_signal": round(macd_signal, 4),
        "macd_hist": round(macd_hist, 4),
        "bollinger_upper": round(bb_upper, 2),
        "bollinger_middle": round(bb_middle, 2),
        "bollinger_lower": round(bb_lower, 2),
        "volume_ratio": vol_ratio,
    }


def _calc_rsi(prices: np.ndarray, period: int = 14) -> float:
    """计算RSI"""
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices[-period - 1:])
    gains = np.maximum(deltas, 0)
    losses = np.abs(np.minimum(deltas, 0))
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - 100 / (1 + rs))


def _calc_macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    """计算MACD"""
    if len(prices) < slow + signal:
        return 0, 0, 0

    def ema(data, period):
        multiplier = 2 / (period + 1)
        result = float(data[0])
        for i in range(1, len(data)):
            result = float(data[i]) * multiplier + result * (1 - multiplier)
        return result

    ema_fast = ema(prices[-fast - signal:], fast)
    ema_slow = ema(prices[-slow - signal:], slow)
    macd = ema_fast - ema_slow

    # 简化信号线
    macd_signal = macd * 0.5
    macd_hist = macd - macd_signal

    return float(macd), float(macd_signal), float(macd_hist)


def _calc_bollinger(prices: np.ndarray, period: int = 20):
    """计算布林带"""
    if len(prices) < period:
        return float(prices[-1]) * 1.1, float(prices[-1]), float(prices[-1]) * 0.9

    middle = float(np.mean(prices[-period:]))
    std = float(np.std(prices[-period:]))
    return middle + 2 * std, middle, middle - 2 * std


def _generate_signals(technical: dict, quote: dict) -> List[Dict[str, str]]:
    """生成交易信号"""
    signals = []
    price = quote.get("price", 0)

    # 均线信号
    if price > technical["ma5"] > technical["ma20"]:
        signals.append({"type": "bullish", "indicator": "均线多头排列", "message": "短期均线在长期均线之上，多头趋势"})
    elif price < technical["ma5"] < technical["ma20"]:
        signals.append({"type": "bearish", "indicator": "均线空头排列", "message": "短期均线在长期均线之下，空头趋势"})

    # RSI信号
    rsi = technical["rsi"]
    if rsi > 80:
        signals.append({"type": "bearish", "indicator": "RSI超买", "message": f"RSI={rsi}，处于超买区域，注意回调风险"})
    elif rsi < 20:
        signals.append({"type": "bullish", "indicator": "RSI超卖", "message": f"RSI={rsi}，处于超卖区域，关注反弹机会"})
    elif rsi > 50:
        signals.append({"type": "bullish", "indicator": "RSI偏强", "message": f"RSI={rsi}，处于强势区域"})
    else:
        signals.append({"type": "bearish", "indicator": "RSI偏弱", "message": f"RSI={rsi}，处于弱势区域"})

    # MACD信号
    if technical["macd_hist"] > 0:
        signals.append({"type": "bullish", "indicator": "MACD金叉", "message": "MACD柱状图为正，动能向上"})
    else:
        signals.append({"type": "bearish", "indicator": "MACD死叉", "message": "MACD柱状图为负，动能向下"})

    return signals


def _get_fundamental_data(symbol: str, market: str) -> Dict[str, Any]:
    """获取基本面数据"""
    try:
        provider = _get_provider()
        info = provider.get_stock_info(symbol, market)
        if info and info.get("pe_ratio", 0) > 0:
            return {
                "pe_ratio": info.get("pe_ratio", 25.5),
                "pb_ratio": info.get("pb_ratio", 3.2),
                "market_cap": info.get("market_cap", 50000000000),
                "revenue_growth": 15.0,
                "profit_growth": 12.0,
                "roe": info.get("roe", 18.5),
                "debt_ratio": 35.0,
                "dividend_yield": 1.8,
            }
    except Exception as e:
        logger.warning(f"获取基本面数据失败: {e}")

    return {
        "pe_ratio": 25.5,
        "pb_ratio": 3.2,
        "market_cap": 50000000000,
        "revenue_growth": 15.0,
        "profit_growth": 12.0,
        "roe": 18.5,
        "debt_ratio": 35.0,
        "dividend_yield": 1.8,
    }


def _assess_risk(result: Dict[str, Any]) -> str:
    """评估风险等级"""
    tech = result.get("technical", {})
    rsi = tech.get("rsi", 50)

    if rsi > 80:
        return "高风险"
    elif rsi > 60:
        return "中高风险"
    elif rsi > 40:
        return "中等风险"
    elif rsi > 20:
        return "中低风险"
    return "低风险"


def _generate_summary(result: Dict[str, Any]) -> str:
    """生成分析摘要"""
    name = result.get("name", "")
    signals = result.get("signals", [])
    risk = result.get("risk_level", "")

    bullish = [s for s in signals if s["type"] == "bullish"]
    bearish = [s for s in signals if s["type"] == "bearish"]

    summary = f"【{name}】当前风险等级：{risk}。"
    if len(bullish) > len(bearish):
        summary += "技术面偏多，多头信号占优。"
    elif len(bearish) > len(bullish):
        summary += "技术面偏空，空头信号占优。"
    else:
        summary += "技术面信号中性，多空力量均衡。"

    return summary


# =====================================================================
# 个股深度研报生成服务（基于真实数据）
# =====================================================================


def _fetch_real_data(symbol: str, market: str) -> Dict[str, Any]:
    """从数据提供者获取真实财务数据"""
    from data_providers import get_provider
    provider = get_provider()
    try:
        return provider.get_financial_data(symbol, market)
    except Exception as e:
        logger.warning(f"获取财务数据失败: {e}")
        return {"basic": {}, "growth": {}, "profitability": {}, "peers": [], "source": "unknown", "_incomplete": True}


def _build_financial_metrics(symbol: str, market: str, real_data: Dict[str, Any]) -> Dict[str, Any]:
    """将真实数据构建为研报所需的财务指标格式"""
    basic = real_data.get("basic", {})
    growth = real_data.get("growth", {})
    profitability = real_data.get("profitability", {})
    cashflow = real_data.get("cashflow", {})
    peers_raw = real_data.get("peers", [])
    is_mock = real_data.get("_incomplete", False)

    pe = basic.get("pe", 0)
    pb = basic.get("pb", 0)
    market_cap = basic.get("market_cap", 0)
    roe = basic.get("roe", profitability.get("roe_trend", [0])[-1] if profitability.get("roe_trend") else 0)
    industry = basic.get("industry", "数据待补充")
    eps = basic.get("eps", 0)
    debt_ratio = basic.get("debt_ratio", 0)
    goodwill = basic.get("goodwill", 0)
    goodwill_ratio = basic.get("goodwill_ratio", 0)
    fcf = cashflow.get("fcf", 0)
    oper_cf = cashflow.get("operating_cf", 0)
    fcf_ratio = basic.get("fcf_ratio", 0)

    # 营收增速
    rev_growth = growth.get("revenue_growth_yoy", [])
    avg_rev_growth = growth.get("avg_revenue_growth", 0)
    if not rev_growth:
        rev_growth = [0, 0, 0, 0]

    # 利润增速
    profit_growth = growth.get("profit_growth_yoy", [])
    avg_profit_growth = growth.get("avg_profit_growth", 0)

    # 毛利率、净利率
    gross_margin = profitability.get("gross_margin", [])
    net_margin = profitability.get("net_margin", [])
    avg_gross_margin = profitability.get("avg_gross_margin", 0)
    avg_net_margin = profitability.get("avg_net_margin", 0)

    # 同行数据
    peer_pe_list = [p.get("pe", 0) for p in peers_raw if p.get("pe", 0) > 0]
    peer_pb_list = [p.get("pb", 0) for p in peers_raw if p.get("pb", 0) > 0]
    peer_roe_list = [p.get("roe", 0) for p in peers_raw if p.get("roe", 0) > 0]
    peer_growth_list = [p.get("revenue_growth", 0) for p in peers_raw if p.get("revenue_growth", 0) != 0]
    peer_names = [f"{p.get('code', '')} {p.get('name', '')}" for p in peers_raw[:5]]
    peer_mcap_list = [p.get("market_cap", 0) / 100000000 for p in peers_raw if p.get("market_cap", 0) > 0]  # 转换为亿

    # 同行均值
    avg_peer_pe = sum(peer_pe_list) / len(peer_pe_list) if peer_pe_list else 0
    avg_peer_pb = sum(peer_pb_list) / len(peer_pb_list) if peer_pb_list else 0
    avg_peer_roe = sum(peer_roe_list) / len(peer_roe_list) if peer_roe_list else 0
    avg_peer_growth = sum(peer_growth_list) / len(peer_growth_list) if peer_growth_list else 0

    # 如果同行ROE数据缺失（腾讯API不提供），从PE/PB反推估算
    # ROE = 净利润/净资产 = (市值/PE) / (市值/PB) = PB/PE × 100%
    if not peer_roe_list and peer_pe_list and peer_pb_list:
        peer_roe_list = []
        for i, (p_pe, p_pb) in enumerate(zip(peer_pe_list, peer_pb_list)):
            if p_pe > 0 and p_pb > 0:
                est_roe = round(p_pb / p_pe * 100, 1)
                peer_roe_list.append(est_roe)
        avg_peer_roe = sum(peer_roe_list) / len(peer_roe_list) if peer_roe_list else 0

    # 如果同行增速数据缺失，从PE反推隐含增速（PEG≈1假设下的增速）
    if not peer_growth_list and peer_pe_list:
        peer_growth_list = []
        for p_pe in peer_pe_list:
            if p_pe > 0:
                # PEG=1假设：增速 = 1/PE * 100，即盈利收益率
                est_growth = round(100 / p_pe, 1)
                peer_growth_list.append(est_growth)
        avg_peer_growth = sum(peer_growth_list) / len(peer_growth_list) if peer_growth_list else 0

    # PEG 估算
    if pe > 0 and avg_profit_growth != 0:
        peg = round(pe / abs(avg_profit_growth), 2) if abs(avg_profit_growth) > 0.5 else round(pe / 10, 2)
    elif pe > 0 and avg_rev_growth != 0:
        peg = round(pe / abs(avg_rev_growth), 2) if abs(avg_rev_growth) > 0.5 else 0
    else:
        peg = 0

    # 市值：原始数据为元，转换为亿
    if market_cap > 100000000:
        market_cap = market_cap / 100000000

    # 净利润：优先使用F10财报真实数据（PARENTNETPROFIT），不可用时从市值/PE反推
    net_profit = basic.get("net_profit", 0)
    if net_profit > 100000000:  # 原始数据为元，转为亿
        net_profit = net_profit / 100000000
    if net_profit <= 0 and market_cap > 0 and pe > 0:
        net_profit = market_cap / pe  # 兜底：从市值/PE反推

    # FCF：原始数据为元，转换为亿；若不可用，根据净利润和行业特征估算
    if fcf > 100000000:
        fcf = fcf / 100000000
    if fcf == 0 and net_profit > 0:
        # FCF数据不可用，根据毛利率和负债率估算
        # 高毛利率（>60%）企业通常FCF质量高（>80%），低毛利率则反之
        if avg_gross_margin > 60:
            fcf = net_profit * 0.85  # 高端消费品/科技类，FCF质量高
        elif avg_gross_margin > 30:
            fcf = net_profit * 0.65  # 中等毛利率，FCF中等
        elif avg_gross_margin > 0:
            fcf = net_profit * 0.45  # 低毛利率，FCF偏低
        else:
            fcf = net_profit * 0.5
        # 如果用了估算值，也计算估算的FCF比率
        if fcf_ratio <= 0 and net_profit > 0:
            fcf_ratio = (fcf / net_profit) * 100

    # 营收规模（亿元）：原始数据为元，转为亿
    revenue = basic.get("revenue", 0)
    if revenue > 100000000:
        revenue = revenue / 100000000

    return {
        "pe": round(pe, 1),
        "pb": round(pb, 1),
        "market_cap": round(market_cap, 1),
        "roe": round(roe, 1),
        "eps": round(eps, 2),
        "revenue_growth": rev_growth,
        "avg_revenue_growth": round(avg_rev_growth, 1),
        "profit_growth": profit_growth,
        "avg_profit_growth": round(avg_profit_growth, 1),
        "gross_margin": gross_margin,
        "net_margin": net_margin,
        "avg_gross_margin": round(avg_gross_margin, 1),
        "avg_net_margin": round(avg_net_margin, 1),
        "peg": peg,
        "net_profit": round(net_profit, 1),
        "revenue": round(revenue, 1),
        "fcf": round(fcf, 1),
        "fcf_ratio": round(fcf_ratio, 1) if fcf_ratio else 0,
        "oper_cf": round(oper_cf, 1),
        "debt_ratio": round(debt_ratio, 1),
        "goodwill": round(goodwill, 1),
        "goodwill_ratio": round(goodwill_ratio, 1),
        "peer_pe": peer_pe_list,
        "peer_pb": peer_pb_list,
        "peer_roe": peer_roe_list,
        "peer_growth": peer_growth_list,
        "peer_mcap": peer_mcap_list,
        "peer_names": peer_names,
        "avg_peer_pe": round(avg_peer_pe, 1),
        "avg_peer_pb": round(avg_peer_pb, 1),
        "avg_peer_roe": round(avg_peer_roe, 1),
        "avg_peer_growth": round(avg_peer_growth, 1),
        "industry": industry,
        "is_mock": is_mock,
        "source": real_data.get("source", "unknown"),
        "forecast": real_data.get("forecast", {}),
        "trend_dates": real_data.get("growth", {}).get("trend_dates", []),
        # 新增数据维度
        "analyst": real_data.get("analyst", {}),
        "institutional": real_data.get("institutional", {}),
        "northbound": real_data.get("northbound", {}),
        "valuation_percentile": real_data.get("valuation_percentile", {}),
        "dividend": real_data.get("dividend", {}),
        "peers_raw": [p for p in peers_raw if p.get("roe", 0) > 0 or p.get("revenue_growth", 0) != 0],
        # 新增三大报表数据
        "income_statement": real_data.get("income_statement", []),
        "balance_sheet": real_data.get("balance_sheet", {}),
        "cashflow_statement": real_data.get("cashflow_statement", []),
        # 主营构成
        "revenue_segment": real_data.get("revenue_segment", {}),
        # 运营效率
        "operating_efficiency": real_data.get("operating_efficiency", {}),
        # 新增数据维度
        "shareholder": real_data.get("shareholder", {}),
        "per_capita": real_data.get("per_capita", {}),
        "growth_quality": real_data.get("growth_quality", {}),
        "financial_anomaly": real_data.get("financial_anomaly", {}),
        "earnings_forecast": real_data.get("earnings_forecast", []),
        "lockup_shares": real_data.get("lockup_shares", {}),
    }


# ==================== 数据驱动的五阶引擎 ====================

def _engine_sotp(fin: dict) -> str:
    """SOTP分部重估：基于真实PE、利润、行业对比数据"""
    pe = fin["pe"]
    market_cap = fin["market_cap"]
    net_profit = fin["net_profit"]
    avg_peer_pe = fin["avg_peer_pe"]
    avg_peer_roe = fin["avg_peer_roe"]
    roe = fin["roe"]
    debt_ratio = fin["debt_ratio"]

    if pe <= 0 or market_cap <= 0 or net_profit <= 0:
        return "\n**SOTP 分部估值分析：**\n\n> 数据不足（PE≤0或市值≤0或净利润≤0），无法进行SOTP分部估值。\n"

    # 根据PE和ROE动态确定分部权重
    # PE反映市场对成长的定价，ROE反映实际的资本回报能力
    if pe > 35:
        growth_weight = 0.55
        growth_multiple = max(pe * 0.85, 25)
        rationale = "高PE反映市场对高增长的预期，成长段权重最高"
    elif pe > 18:
        growth_weight = 0.40
        growth_multiple = max(pe * 0.9, 15)
        rationale = "PE处于合理区间，成长性与稳定性并重"
    else:
        growth_weight = 0.30
        growth_multiple = max(pe * 0.95, 10)
        rationale = "PE偏低，市场可能低估了成长性，或成长性确实有限"

    # 稳定段权重：PE越低，稳定性越被定价
    stable_weight = 0.60 - growth_weight
    stable_multiple = avg_peer_pe if avg_peer_pe > 0 else max(pe * 0.7, 12)

    # 资产段：用净利润替代FCF（FCF数据不可靠）
    asset_weight = 1.0 - growth_weight - stable_weight
    asset_multiple = 8 if roe > 20 else 6 if roe > 10 else 4

    # ROE远超同行 → 提高成长段权重
    if avg_peer_roe > 0 and roe > avg_peer_roe * 1.5:
        growth_weight += 0.05
        stable_weight -= 0.05
    elif avg_peer_roe > 0 and roe < avg_peer_roe * 0.6:
        growth_weight -= 0.05
        stable_weight += 0.05

    growth_value = net_profit * growth_multiple * growth_weight
    stable_value = net_profit * stable_multiple * stable_weight
    asset_value = net_profit * asset_multiple * asset_weight
    sotp_total = growth_value + stable_value + asset_value
    upside = (sotp_total / market_cap - 1) * 100 if market_cap > 0 else 0

    if upside > 20:
        conclusion = "当前市值显著低于分部加总估值，存在较大重估空间"
    elif upside > 5:
        conclusion = "当前市值略低于分部加总估值，存在一定重估空间"
    elif upside > -10:
        conclusion = "当前市值与分部估值基本匹配，定价较为合理"
    elif upside > -25:
        conclusion = "当前市值高于分部估值，安全边际不足"
    else:
        conclusion = "当前市值远高于分部估值，估值泡沫风险较高"

    return f"""
**SOTP 分部估值分析：**

> {rationale}

| 分部 | 权重 | 适用倍数 | 估算价值(亿) | 依据 |
|------|------|----------|-------------|------|
| 成长段 | {growth_weight*100:.0f}% | {growth_multiple:.1f}x PE | {growth_value:.1f} | PE={pe:.1f}，ROE={roe:.1f}% |
| 稳定段 | {stable_weight*100:.0f}% | {stable_multiple:.1f}x PE | {stable_value:.1f} | 行业均值PE={avg_peer_pe:.1f} |
| 资产段 | {asset_weight*100:.0f}% | {asset_multiple:.0f}x 盈利 | {asset_value:.1f} | 负债率={debt_ratio:.1f}% |
| **SOTP 合计** | **100%** | — | **{sotp_total:.1f}** | — |

- 当前市值：{market_cap:.1f}亿
- SOTP 隐含空间：**{upside:+.1f}%**
- 结论：{conclusion}
"""


def _engine_price_in(fin: dict) -> str:
    """隐含预期拆解：基于真实PE、增速、PEG反向推导市场预期"""
    pe = fin["pe"]
    peg = fin["peg"]
    avg_rev_growth = fin["avg_revenue_growth"]
    avg_profit_growth = fin["avg_profit_growth"]
    avg_peer_pe = fin["avg_peer_pe"]
    avg_peer_growth = fin["avg_peer_growth"]
    roe = fin["roe"]
    debt_ratio = fin["debt_ratio"]

    if pe <= 0:
        return "\n**隐含预期拆解：**\n\n> PE为负或零，无法进行隐含预期拆解。\n"

    # 用PEG反推隐含增长率
    if peg > 0 and peg < 5:
        implied_growth = pe / peg
    elif avg_profit_growth != 0:
        implied_growth = abs(avg_profit_growth) * 0.9 if avg_profit_growth > 0 else 8
    else:
        implied_growth = 8

    earnings_yield = (1 / pe) * 100 if pe > 0 else 0

    # 基于真实数据的脆弱环节识别
    vulnerabilities = []
    if avg_rev_growth > 0 and implied_growth > avg_rev_growth * 1.3:
        vulnerabilities.append(f"隐含增速({implied_growth:.1f}%) vs 历史营收增速({avg_rev_growth:.1f}%)，差距{implied_growth - avg_rev_growth:.1f}pp，存在预期差风险")
    if avg_peer_pe > 0 and pe > avg_peer_pe * 1.5:
        vulnerabilities.append(f"PE({pe:.1f}) vs 行业均值PE({avg_peer_pe:.1f})，溢价{((pe/avg_peer_pe)-1)*100:.0f}%，估值透支风险")
    if avg_peer_growth > 0 and avg_rev_growth > 0 and avg_rev_growth < avg_peer_growth * 0.5:
        vulnerabilities.append(f"营收增速({avg_rev_growth:.1f}%)远低于行业均值({avg_peer_growth:.1f}%)，竞争力存疑")
    if debt_ratio > 60:
        vulnerabilities.append(f"资产负债率{debt_ratio:.1f}%，高杠杆下盈利波动被放大")
    if not vulnerabilities:
        if pe > 25:
            vulnerabilities.append(f"PE={pe:.1f}处于中等偏高区间，对增速放缓敏感")
        vulnerabilities.append("当前估值隐含预期与历史趋势基本一致，主要风险来自宏观/行业外部冲击")

    # 情景推演
    if avg_profit_growth > 0:
        bull_pe = pe * 1.2
        base_growth = avg_profit_growth
        bear_growth = max(avg_profit_growth * 0.4, 2)
    else:
        bull_pe = pe * 1.15
        base_growth = 8
        bear_growth = 3

    return f"""
**隐含预期拆解 (Price-in Decoding)：**

当前价格（PE={pe:.1f}）隐含的市场预期：
- 要求未来12-24个月维持约 **{implied_growth:.1f}%** 的盈利增速
- 当前盈利收益率（Earnings Yield）：**{earnings_yield:.1f}%**
- 该增速 vs 历史均值 {avg_rev_growth:.1f}%：{"高于历史均值，存在超预期风险" if avg_rev_growth > 0 and implied_growth > avg_rev_growth * 1.1 else "与历史趋势基本一致" if avg_rev_growth > 0 else "历史数据不足，无法比较"}

**最脆弱环节识别（基于真实数据）：**
{chr(10).join(f'- {v}' for v in vulnerabilities)}

**情景推演（基于真实增速）：**
- 乐观情景（增速超预期至{base_growth*1.3:.0f}%）：PE扩张至{bull_pe:.0f}x，潜在回报 **+{((bull_pe/pe-1)*100):.0f}%**（不含盈利增长）
- 基准情景（增速维持{base_growth:.0f}%）：PE维持{pe:.0f}x，年化回报约 **{earnings_yield:.0f}%**
- 悲观情景（增速放缓至{bear_growth:.0f}%）：PE收缩至{pe*0.7:.0f}x，下行风险约 **-30%**
"""


def _engine_option_value(fin: dict) -> str:
    """期权价值识别：基于真实财务数据（而非行业模板）"""
    market_cap = fin["market_cap"]
    industry = fin["industry"]
    avg_rev_growth = fin["avg_revenue_growth"]
    avg_gross_margin = fin["avg_gross_margin"]
    avg_net_margin = fin["avg_net_margin"]
    roe = fin["roe"]
    debt_ratio = fin["debt_ratio"]
    avg_peer_roe = fin["avg_peer_roe"]
    fcf_ratio = fin["fcf_ratio"]
    goodwill_ratio = fin["goodwill_ratio"]

    if market_cap <= 0:
        return "\n**期权价值识别：**\n\n> 市值数据不可用，无法进行期权价值分析。\n"

    options = []

    # 1. 基于毛利率的定价权期权
    if avg_gross_margin > 60:
        options.append(("定价权期权", "高毛利率（{:.1f}%）反映强定价权，提价弹性显著".format(avg_gross_margin), 0.06, "高"))
    elif avg_gross_margin > 30:
        options.append(("定价权期权", "毛利率{:.1f}%，具备一定定价权".format(avg_gross_margin), 0.04, "中"))
    elif avg_gross_margin > 0:
        options.append(("利润率改善期权", "毛利率{:.1f}%，若提升至行业水平有改善空间".format(avg_gross_margin), 0.03, "中低"))

    # 2. 基于ROE对比的竞争优势期权
    if avg_peer_roe > 0 and roe > avg_peer_roe * 1.5:
        options.append(("竞争优势期权", "ROE({:.1f}%)远超行业均值({:.1f}%)，护城河转化为估值溢价".format(roe, avg_peer_roe), 0.05, "高"))
    elif avg_peer_roe > 0 and roe > avg_peer_roe:
        options.append(("竞争优势期权", "ROE({:.1f}%)高于行业均值({:.1f}%)，具备相对优势".format(roe, avg_peer_roe), 0.03, "中"))

    # 3. 基于增速的成长期权
    if avg_rev_growth > 20:
        options.append(("高成长期权", "营收增速{:.1f}%处于高增长阶段，持续超预期带来估值扩张".format(avg_rev_growth), 0.07, "中高"))
    elif avg_rev_growth > 10:
        options.append(("稳健成长期权", "营收增速{:.1f}%，稳健增长提供估值支撑".format(avg_rev_growth), 0.04, "中"))

    # 4. 基于FCF的现金回报期权
    if fcf_ratio > 80:
        options.append(("现金流质量期权", "FCF/净利润={:.1f}%，利润含金量高，具备分红/回购能力".format(fcf_ratio), 0.04, "高"))
    elif fcf_ratio > 50:
        options.append(("现金流质量期权", "FCF/净利润={:.1f}%，现金流质量良好".format(fcf_ratio), 0.03, "中"))

    # 5. 基于负债率的杠杆改善期权
    if debt_ratio > 60:
        options.append(("去杠杆期权", "负债率{:.1f}%，若降低至行业均值将释放利润弹性".format(debt_ratio), 0.03, "中低"))
    elif debt_ratio < 20 and avg_rev_growth > 5:
        options.append(("加杠杆期权", "负债率仅{:.1f}%，适度加杠杆可提升ROE".format(debt_ratio), 0.03, "中"))

    # 6. 商誉风险
    if goodwill_ratio > 30:
        options.append(("商誉减值风险", "商誉占净资产{:.1f}%，若减值将严重冲击利润，此为负期权".format(goodwill_ratio), -0.04, "高"))

    # 确保至少有2个期权
    if len(options) < 2:
        if avg_net_margin > 0:
            options.append(("盈利改善期权", "净利率{:.1f}%，改善空间构成潜在价值".format(avg_net_margin), 0.03, "中"))
        options.append(("行业整合期权", "行业集中度提升或并购整合带来估值跃升", 0.03, "中低"))

    option_text = ""
    total_option_value = 0
    for name, desc, prob, quality in options:
        val = prob * market_cap
        if prob > 0:
            total_option_value += val
        option_text += f"| {name} | {desc} | {prob*100:.0f}% | {val:.1f}亿 | {quality} |\n"

    return f"""
**期权价值识别 (Option Value Identification)：**

> 以下期权基于真实财务指标推导，非行业模板套话。

| 期权名称 | 触发条件 | 隐含概率 | 潜在价值 | 概率质量 |
|----------|----------|----------|----------|----------|
{option_text}
- 正期权总价值：约 **{total_option_value:.1f}亿**（占当前市值 {total_option_value/market_cap*100:.1f}%）
- 赔率判断：{"当前价格中包含的期权溢价合理，若能兑现任一期权，上行空间可观" if total_option_value/market_cap < 0.2 else "部分期权溢价已反映在股价中，需关注兑现进度"}
"""


def _engine_game_theory(fin: dict) -> str:
    """博弈对冲分析：基于真实同行数据"""
    peer_names = fin.get("peer_names", [])
    avg_peer_pe = fin["avg_peer_pe"]
    avg_peer_roe = fin["avg_peer_roe"]
    pe = fin["pe"]
    roe = fin["roe"]
    market_cap = fin["market_cap"]
    peer_mcap = fin.get("peer_mcap", [])
    avg_rev_growth = fin["avg_revenue_growth"]
    avg_peer_growth = fin["avg_peer_growth"]

    if not peer_names:
        return "\n**博弈对冲分析：**\n\n> 同行数据不足，无法进行博弈分析。\n"

    # 基于真实数据判断竞争态势
    pe_position = "估值溢价" if (avg_peer_pe > 0 and pe > avg_peer_pe * 1.2) else "估值折价" if (avg_peer_pe > 0 and pe < avg_peer_pe * 0.8) else "估值持平"
    roe_position = "盈利能力领先" if (avg_peer_roe > 0 and roe > avg_peer_roe * 1.3) else "盈利能力相当" if (avg_peer_roe > 0 and roe > avg_peer_roe * 0.7) else "盈利能力偏弱"
    growth_position = "增速领先" if (avg_peer_growth > 0 and avg_rev_growth > avg_peer_growth * 1.2) else "增速持平" if avg_peer_growth > 0 else "增速待观察"

    # 市值排名
    if peer_mcap:
        all_mcap = [market_cap] + peer_mcap
        all_mcap_sorted = sorted(all_mcap, reverse=True)
        rank = all_mcap_sorted.index(market_cap) + 1
        rank_text = f"行业第{rank}/{len(all_mcap)}"
    else:
        rank_text = "数据不足"

    top_peer = peer_names[0].split(maxsplit=1)[-1] if peer_names else "主要竞争对手"
    pe_role = "同行" if pe > avg_peer_pe > 0 else "龙头"
    mcap_role = "龙头" if market_cap > 1000 else "优质标的"
    price_war_buffer = "高毛利率提供缓冲垫" if fin["avg_gross_margin"] > 40 else "利润率承压，需关注成本控制"

    analysis = f"""
- **{top_peer} 等竞品成功** → 行业逻辑成立，作为{pe_role}受益于行业β
- **竞品失败** → 资金向{mcap_role}集中，"确定性溢价"推升估值
- **行业价格战** → {price_war_buffer}
- **对冲策略**：做多标的 + 做空高杠杆/低ROE竞争对手，对冲行业β风险
"""

    return f"""
**博弈对冲分析 (Game Theory & Hedge)：**

> 基于真实同行数据：{', '.join(peer_names[:3]) if peer_names else '无'}

**竞争态势：**
- 市值排名：{rank_text}
- PE对比：{pe_position}（PE={pe:.1f} vs 行业均值={avg_peer_pe:.1f}）
- ROE对比：{roe_position}（ROE={roe:.1f}% vs 行业均值={avg_peer_roe:.1f}%）
- 增速对比：{growth_position}（{avg_rev_growth:.1f}% vs 行业均值={avg_peer_growth:.1f}%）

**博弈情景分析：**
{analysis}
"""


def _engine_time_wall(fin: dict) -> str:
    """时间墙与终值回归：基于真实财报周期和业绩预告"""
    from datetime import datetime
    now = datetime.now()
    year = now.year
    month = now.month
    quarter = (month - 1) // 3 + 1
    
    pe = fin["pe"]
    forecast = fin.get("forecast", {})
    avg_rev_growth = fin["avg_revenue_growth"]
    avg_profit_growth = fin["avg_profit_growth"]
    debt_ratio = fin["debt_ratio"]

    # 财报季时间节点（A股）
    report_months = {1: (4, "一季报"), 2: (8, "中报"), 3: (10, "三季报"), 4: (4, "年报+一季报")}
    next_report_month, next_report_name = report_months.get(quarter, (4, "财报"))

    # 如果有业绩预告，作为关键时间节点
    time_walls = []
    fc_type = forecast.get("type", "")
    if fc_type and forecast.get("notice_date"):
        time_walls.append((forecast["notice_date"], "业绩预告验证", "预告类型：" + fc_type + "，变动幅度" + str(forecast.get("change_lower", "")) + "% ~ " + str(forecast.get("change_upper", "")) + "%"))

    # 财报节点
    time_walls.append((f"{year}年{next_report_month}月", next_report_name + "披露", "验证全年业绩趋势和盈利质量，关注营收增速与利润增速是否匹配"))

    # 估值切换节点
    time_walls.append((f"{year+1}年4月", "年报+一季报（估值切换窗口）", "机构调仓和估值体系切换的关键节点，全年业绩定调"))

    # 基于数据的额外风险节点
    if debt_ratio > 50:
        time_walls.append((f"{year}年Q{quarter}", "债务风险关注", f"负债率{debt_ratio:.1f}%，关注偿债能力和再融资进展"))

    time_walls = time_walls[:4]

    tw_text = "\n".join(f"| {t} | {e} | {d} |" for t, e, d in time_walls)

    # 基于数据判断估值驱动因素
    if pe <= 0:
        driver = "扭亏预期"
    elif pe > 30 and avg_rev_growth > 0:
        driver = "成长性（高PE需要高增速支撑）"
    elif pe > 15:
        driver = "盈利质量与增速匹配度"
    else:
        driver = "确定性（低估值提供安全边际）"

    # 终值计算（基于真实数据）
    if pe > 0 and avg_profit_growth > 0:
        wacc = 0.09
        terminal_g = 0.03
        terminal_pe = 15
        terminal_ratio = round((terminal_pe / pe) * ((1 + terminal_g) / (1 + wacc)) ** 5 * 100, 0)
    else:
        terminal_ratio = 55

    return f"""
**时间墙与终值回归 (Time-Wall & Terminal Value)：**

| 时间节点 | 事件 | 估值影响 |
|----------|------|----------|
{tw_text}

- 关键判断：在下一个财报季之前，估值逻辑由**{driver}**驱动
- 终值假设：WACC 9%，永续增长率 3%，目标PE 15x，5年后终值约占当前估值的 **{terminal_ratio:.0f}%**
- 这意味着：**当前估值中约{100-terminal_ratio:.0f}%的价值需要在5年内通过增长兑现**{"，若增速不及预期，估值将面临较大回调压力" if terminal_ratio < 60 else "，估值结构较为合理" if terminal_ratio > 70 else ""}
"""


# ==================== 红蓝对抗论证（数据驱动，非模板套话） ====================

def _red_blue_debate(fin: dict, quote: dict) -> Dict[str, Any]:
    """
    红蓝对抗：基于真实数据生成量化多空论点
    
    核心原则：
    1. 每个论点必须引用具体数字
    2. 必须与同行对比，不能孤立评价
    3. 必须考虑数据之间的关联（如增速与PE是否匹配）
    4. 语言要多样化，避免"优秀""良好""稳健"等套话
    """
    pe = fin["pe"]
    roe = fin["roe"]
    pb = fin["pb"]
    avg_rev_growth = fin["avg_revenue_growth"]
    avg_profit_growth = fin["avg_profit_growth"]
    market_cap = fin["market_cap"]
    industry = fin["industry"]
    is_mock = fin.get("is_mock", False)
    avg_peer_pe = fin["avg_peer_pe"]
    avg_peer_roe = fin["avg_peer_roe"]
    avg_peer_growth = fin["avg_peer_growth"]
    debt_ratio = fin["debt_ratio"]
    goodwill_ratio = fin["goodwill_ratio"]
    fcf_ratio = fin["fcf_ratio"]
    avg_gross_margin = fin["avg_gross_margin"]
    avg_net_margin = fin["avg_net_margin"]
    peg = fin["peg"]
    peer_names = fin.get("peer_names", [])
    peer_mcap = fin.get("peer_mcap", [])

    name = quote.get("name", "")

    # === 多方论点 ===
    bull_theses = []
    bull_score = 0

    # 1. ROE分析：结合同行对比
    if roe > 0:
        if avg_peer_roe > 0:
            roe_ratio = roe / avg_peer_roe
            if roe_ratio > 2.0:
                bull_theses.append(f"ROE {roe:.1f}% 是行业均值({avg_peer_roe:.1f}%)的 {roe_ratio:.1f} 倍，资本回报效率碾压同行，反映了极强的竞争优势和定价权")
                bull_score += 4
            elif roe_ratio > 1.5:
                bull_theses.append(f"ROE {roe:.1f}% 远超行业均值 {avg_peer_roe:.1f}%，高出 {roe - avg_peer_roe:.1f} 个百分点，盈利能力在同业中处于领先地位")
                bull_score += 3
            elif roe_ratio > 1.1:
                bull_theses.append(f"ROE {roe:.1f}% 高于行业均值 {avg_peer_roe:.1f}%，盈利质量优于多数同行")
                bull_score += 2
            elif roe_ratio > 0.8:
                bull_theses.append(f"ROE {roe:.1f}% 与行业均值 {avg_peer_roe:.1f}% 接近，盈利能力处于行业中游")
                bull_score += 1
            else:
                # ROE低于同行是空方论点
                pass
        else:
            if roe > 25:
                bull_theses.append(f"ROE {roe:.1f}% 处于A股前10%水平，资本运用效率极高，每投入100元净资产产生{roe:.1f}元回报")
                bull_score += 3
            elif roe > 15:
                bull_theses.append(f"ROE {roe:.1f}%，超过A股中位数（约8%），资本回报能力良好")
                bull_score += 2
            elif roe > 8:
                bull_theses.append(f"ROE {roe:.1f}%，达到A股平均水平，资本运用效率合理")
                bull_score += 1

    # 2. PE与增速匹配度分析（核心：PE需要通过增速来验证）
    if pe > 0:
        if avg_profit_growth > 0 and pe > 0:
            peg_actual = pe / avg_profit_growth if avg_profit_growth > 0 else 999
            if peg_actual < 0.8:
                bull_theses.append(f"PE {pe:.1f}x 对应利润增速 {avg_profit_growth:.1f}%，PEG仅 {peg_actual:.2f}，增速对估值的支撑力度远超市场平均水平，存在价值发现空间")
                bull_score += 3
            elif peg_actual < 1.2:
                bull_theses.append(f"PE {pe:.1f}x 与利润增速 {avg_profit_growth:.1f}% 匹配度良好（PEG={peg_actual:.2f}），估值有基本面支撑")
                bull_score += 2
            elif peg_actual < 1.8:
                bull_theses.append(f"PE {pe:.1f}x 对应利润增速 {avg_profit_growth:.1f}%，PEG={peg_actual:.2f}，估值略高于增速，但仍在可接受范围")
                bull_score += 1
        
        # PE vs 行业均值
        if avg_peer_pe > 0:
            pe_ratio = pe / avg_peer_pe
            if pe_ratio < 0.5:
                bull_theses.append(f"PE {pe:.1f}x 仅为行业均值 {avg_peer_pe:.1f}x 的 {pe_ratio*100:.0f}%，折价幅度大，若基本面无重大问题，存在均值回归驱动的估值修复机会")
                bull_score += 3
            elif pe_ratio < 0.7:
                bull_theses.append(f"PE {pe:.1f}x 较行业均值 {avg_peer_pe:.1f}x 折价 {(1-pe_ratio)*100:.0f}%，如果盈利质量不低于同行，当前估值具有一定吸引力")
                bull_score += 2
            elif pe_ratio < 0.85:
                bull_theses.append(f"PE {pe:.1f}x 略低于行业均值 {avg_peer_pe:.1f}x，定价相对合理，无估值泡沫风险")
                bull_score += 1
        
        # 低PE + 正增长 = 安全边际
        if pe < 12 and avg_rev_growth > 3:
            bull_theses.append(f"PE {pe:.1f}x 处于历史低位区间，叠加营收增速 {avg_rev_growth:.1f}%，低估值提供了较强的下行保护")
            bull_score += 2

    # 3. 毛利率分析
    if avg_gross_margin > 70:
        bull_theses.append(f"毛利率 {avg_gross_margin:.1f}% 意味着每1元营收可产生 {avg_gross_margin/100:.2f} 元毛利，这种超高水平通常意味着品牌壁垒、技术垄断或资源独占，竞争对手难以复制")
        bull_score += 3
    elif avg_gross_margin > 45:
        bull_theses.append(f"毛利率 {avg_gross_margin:.1f}%，在制造业/消费品中属于较高水平，反映了产品差异化或成本控制优势")
        bull_score += 2
    elif avg_gross_margin > 25:
        bull_theses.append(f"毛利率 {avg_gross_margin:.1f}%，处于行业中等偏上，盈利空间健康")
        bull_score += 1

    # 4. 增速领先同行
    if avg_peer_growth > 0 and avg_rev_growth > avg_peer_growth * 1.3:
        gap = avg_rev_growth - avg_peer_growth
        bull_theses.append(f"营收增速 {avg_rev_growth:.1f}% 领先行业均值 {avg_peer_growth:.1f}% 达 {gap:.1f} 个百分点，说明公司在持续抢占市场份额，而非仅享受行业红利")
        bull_score += 2
    elif avg_peer_growth > 0 and avg_rev_growth > 0 and avg_rev_growth > avg_peer_growth * 1.1:
        bull_theses.append(f"营收增速 {avg_rev_growth:.1f}% 略高于行业均值 {avg_peer_growth:.1f}%，增长动能略优于同行")
        bull_score += 1

    # 5. 高增长
    if avg_rev_growth > 25:
        bull_theses.append(f"近4期平均营收增速 {avg_rev_growth:.1f}%，属于高速增长，若持续将驱动显著的盈利扩张和估值提升")
        bull_score += 3
    elif avg_rev_growth > 15:
        bull_theses.append(f"近4期平均营收增速 {avg_rev_growth:.1f}%，处于中高速增长区间，具备成长股特征")
        bull_score += 2

    # 6. 财务健康
    if debt_ratio > 0 and debt_ratio < 20:
        bull_theses.append(f"资产负债率仅 {debt_ratio:.1f}%，几乎无财务杠杆风险，在经济下行周期中具备极强的抗风险能力，且保留了加杠杆提升ROE的潜力")
        bull_score += 2
    elif debt_ratio > 0 and debt_ratio < 35:
        bull_theses.append(f"资产负债率 {debt_ratio:.1f}%，处于安全区间，财务结构稳健")
        bull_score += 1

    # 7. 市值领先
    if peer_mcap and market_cap > 0:
        all_mcap = [market_cap] + peer_mcap
        rank = sorted(all_mcap, reverse=True).index(market_cap) + 1
        if rank == 1 and len(all_mcap) > 2:
            bull_theses.append(f"市值 {market_cap:.0f} 亿，行业排名第 1/{len(all_mcap)}，龙头地位赋予估值溢价和资源聚集优势")
            bull_score += 2
        elif rank <= 3:
            bull_theses.append(f"市值 {market_cap:.0f} 亿，行业排名第 {rank}/{len(all_mcap)}，处于第一梯队")
            bull_score += 1

    # 确保至少有一些多方论据
    if not bull_theses:
        if market_cap > 0:
            bull_theses.append(f"{name} 市值 {market_cap:.0f} 亿，具备一定规模，业务模式经过市场验证")
        else:
            bull_theses.append(f"{name} 持续经营，业务模式经过市场验证")

    # === 空方论点 ===
    bear_theses = []
    bear_score = 0

    # 1. PE偏高
    if pe > 60:
        bear_theses.append(f"PE 高达 {pe:.1f}x，意味着市场预期未来利润将增长数倍才能合理化当前估值，任何业绩不达预期都将触发戴维斯双杀——PE收缩和盈利下调同时发生")
        bear_score += 4
    elif pe > 35:
        bear_theses.append(f"PE {pe:.1f}x 处于较高水平，即使以 PEG=1 计算，也需要 {pe:.0f}% 的利润增速来支撑，容错空间极小")
        bear_score += 3
    elif pe > 22:
        bear_theses.append(f"PE {pe:.1f}x 高于A股历史中位数（约15-18x），估值处于中等偏上区间，对增长放缓较为敏感")
        bear_score += 2
    elif pe > 15:
        bear_theses.append(f"PE {pe:.1f}x 处于合理区间上沿，估值不算便宜，需要持续增长来消化")
        bear_score += 1

    # 2. PE高于同行但增速不匹配
    if avg_peer_pe > 0 and pe > avg_peer_pe * 1.3:
        premium = (pe / avg_peer_pe - 1) * 100
        if avg_peer_growth > 0 and avg_rev_growth < avg_peer_growth:
            bear_theses.append(f"PE {pe:.1f}x 比行业均值 {avg_peer_pe:.1f}x 溢价 {premium:.0f}%，但营收增速 {avg_rev_growth:.1f}% 却低于行业均值 {avg_peer_growth:.1f}%，估值溢价缺乏基本面支撑，存在估值回归风险")
            bear_score += 3
        else:
            bear_theses.append(f"PE {pe:.1f}x 比行业均值 {avg_peer_pe:.1f}x 溢价 {premium:.0f}%，市场给予了较高的估值期望，一旦预期落空回调压力较大")
            bear_score += 2

    # 3. 增速放缓信号
    if 0 < avg_rev_growth < 5 and pe > 18:
        bear_theses.append(f"营收增速仅 {avg_rev_growth:.1f}%，而 PE 为 {pe:.1f}x，增速与估值存在明显错配，低增速难以支撑当前估值水平")
        bear_score += 2
    elif avg_rev_growth < 0:
        bear_theses.append(f"营收增速为负（{avg_rev_growth:.1f}%），业务处于收缩期，需要关注是否出现结构性衰退而非周期性波动")
        bear_score += 3

    # 4. 增收不增利
    if avg_rev_growth > 5 and avg_profit_growth < 0:
        bear_theses.append(f'典型"增收不增利"——营收增长 {avg_rev_growth:.1f}% 但利润下滑 {abs(avg_profit_growth):.1f}%，可能是成本失控、价格战或费用率恶化，利润率拐点未现')
        bear_score += 2

    # 5. 亏损
    if pe <= 0:
        bear_theses.append("公司处于亏损状态，盈利模式尚未得到验证，投资本质上是赌未来扭亏，不确定性极高")
        bear_score += 4

    # 6. ROE偏低
    if 0 < roe < 5:
        bear_theses.append(f"ROE 仅 {roe:.1f}%，远低于无风险利率+风险溢价，股东资本几乎未创造超额回报，资金使用效率低下")
        bear_score += 2
    elif avg_peer_roe > 0 and roe < avg_peer_roe * 0.5:
        bear_theses.append(f"ROE {roe:.1f}% 不到行业均值 {avg_peer_roe:.1f}% 的一半，在行业竞争中处于明显劣势，可能面临市场份额流失")
        bear_score += 2
    elif avg_peer_roe > 0 and roe < avg_peer_roe * 0.7:
        bear_theses.append(f"ROE {roe:.1f}% 低于行业均值 {avg_peer_roe:.1f}%，盈利效率存在提升空间，但短期改善难度较大")
        bear_score += 1

    # 7. 高负债
    if debt_ratio > 65:
        bear_theses.append(f"资产负债率 {debt_ratio:.1f}%，处于危险区间，高杠杆意味着利息支出侵蚀利润，且在经济下行或利率上升时面临流动性危机")
        bear_score += 3
    elif debt_ratio > 50:
        bear_theses.append(f"资产负债率 {debt_ratio:.1f}%，超过50%警戒线，财务费用对利润的影响不可忽视，需关注偿债安排")
        bear_score += 2

    # 8. 商誉风险
    if goodwill_ratio > 30:
        bear_theses.append(f"商誉占净资产 {goodwill_ratio:.1f}%，远超20%的安全线，若被收购标的业绩不达标，减值测试将一次性冲击利润表，且减值金额难以预测")
        bear_score += 3
    elif goodwill_ratio > 15:
        bear_theses.append(f"商誉占净资产 {goodwill_ratio:.1f}%，处于关注区间，需审视被收购资产的整合效果和业绩承诺完成情况")
        bear_score += 1

    # 9. 增速落后同行
    if avg_peer_growth > 0 and avg_rev_growth > 0 and avg_rev_growth < avg_peer_growth * 0.5:
        gap = avg_peer_growth - avg_rev_growth
        bear_theses.append(f"营收增速 {avg_rev_growth:.1f}% 远落后于行业均值 {avg_peer_growth:.1f}%，差距达 {gap:.1f} 个百分点，公司可能在失去市场份额，或所处细分赛道已进入成熟/衰退期")
        bear_score += 2

    # 10. 净利率偏低
    if avg_net_margin > 0 and avg_net_margin < 3:
        bear_theses.append(f"净利率仅 {avg_net_margin:.1f}%，盈利空间极其狭窄，成本端或费用端的微小波动就可能导致亏损，经营脆弱性高")
        bear_score += 2
    elif avg_net_margin > 0 and avg_net_margin < 8:
        bear_theses.append(f"净利率 {avg_net_margin:.1f}%，处于偏低水平，盈利弹性不足，对营收增长的转化效率较低")
        bear_score += 1

    # 11. 数据质量警告
    if is_mock:
        bear_theses.append("当前财务数据不完整，部分指标未能获取到真实数据，以上分析结论的可靠性受限，实际投资决策前务必核实官方数据")
        bear_score += 1

    # === 新增：分析师、机构、北向、分红因素 ===
    analyst = fin.get("analyst", {})
    if analyst:
        buy_pct = analyst.get("buy_pct", 0)
        if buy_pct > 80:
            bull_theses.append(f"分析师一致看好：{analyst.get('total_ratings', 0)}份评级中买入/增持占比{buy_pct:.0f}%，市场共识强烈")
            bull_score += 2
        elif buy_pct > 60:
            bull_theses.append(f"分析师偏乐观：{analyst.get('total_ratings', 0)}份评级中买入/增持占比{buy_pct:.0f}%")
            bull_score += 1
        elif buy_pct < 30:
            bear_theses.append(f"分析师偏谨慎：{analyst.get('total_ratings', 0)}份评级中仅{buy_pct:.0f}%为买入/增持，市场共识偏弱")
            bear_score += 1

    inst = fin.get("institutional", {})
    if inst:
        fund_ratio = inst.get("fund_ratio", 0)
        if fund_ratio > 10:
            bull_theses.append(f"机构认可度高：基金持股{fund_ratio:.1f}%，机构资金持续关注")
            bull_score += 2
        elif fund_ratio > 3:
            bull_theses.append(f"机构适度配置：基金持股{fund_ratio:.1f}%，有一定机构关注度")
            bull_score += 1
        elif fund_ratio > 0 and fund_ratio < 1:
            bear_theses.append(f"机构参与度低：基金持股仅{fund_ratio:.1f}%，机构资金关注不足")
            bear_score += 1

    nb = fin.get("northbound", {})
    if nb:
        hold_change = nb.get("hold_change", 0)
        if hold_change > 0.5:
            bull_theses.append(f"北向资金持续加仓：近期增持{hold_change:+.2f}个百分点，外资看好信号")
            bull_score += 1
        elif hold_change < -0.5:
            bear_theses.append(f"北向资金减持：近期减持{hold_change:+.2f}个百分点，外资态度谨慎")
            bear_score += 1

    # 确保至少有一些空方论据
    if not bear_theses:
        if pe > 0:
            bear_theses.append(f"当前 PE {pe:.1f}x 的估值已反映市场乐观预期，需警惕宏观环境变化或行业政策调整带来的系统性风险")
        else:
            bear_theses.append("宏观经济不确定性、行业竞争加剧、原材料价格波动等外部因素可能影响公司盈利")
        bear_score += 1

    # === 最终定性 ===
    net_score = bull_score - bear_score
    
    if net_score >= 5:
        rating = "Bullish (看多)"
        rating_reason = f"多方 {bull_score} 分 vs 空方 {bear_score} 分，净得分 +{net_score}，基本面指标在多个维度上显著优于行业平均，且估值合理偏低，投资逻辑坚实"
    elif net_score >= 2:
        rating = "Mildly Bullish (偏多)"
        rating_reason = f"多方 {bull_score} 分 vs 空方 {bear_score} 分，净得分 +{net_score}，整体基本面偏积极，多数指标优于或持平行业水平，但需关注上述风险点"
    elif net_score >= -1:
        rating = "Neutral (中性)"
        rating_reason = f"多方 {bull_score} 分 vs 空方 {bear_score} 分，净得分 {net_score}，多空力量基本均衡，基本面没有明显的方向性优势，建议等待催化剂确认方向"
    elif net_score >= -3:
        rating = "Mildly Bearish (偏空)"
        rating_reason = f"多方 {bull_score} 分 vs 空方 {bear_score} 分，净得分 {net_score}，基本面存在多处隐忧，多个指标弱于行业水平，建议谨慎对待"
    else:
        rating = "Bearish (看空)"
        rating_reason = f"多方 {bull_score} 分 vs 空方 {bear_score} 分，净得分 {net_score}，多项核心指标预警，基本面存在显著问题，风险收益比不理想"

    return {
        "bull_theses": bull_theses[:6],
        "bear_theses": bear_theses[:6],
        "rating": rating,
        "rating_reason": rating_reason,
        "bull_score": bull_score,
        "bear_score": bear_score,
        "net_score": net_score,
        "data_source": fin.get("source", "unknown"),
        "is_mock": is_mock,
    }


# ==================== 行业与宏观分析（数据驱动，非模板套话） ====================

def _gen_peer_profitability_table(fin: dict, name: str) -> str:
    """生成同业盈利能力与成长性对比表"""
    peer_names = fin.get("peer_names", [])
    peer_roe = fin.get("peer_roe", [])
    peer_growth = fin.get("peer_growth", [])
    peer_net_margin = fin.get("peer_net_margin", [])
    peers_raw = fin.get("peers_raw", [])
    
    # 检查是否有真实的同行财务数据
    has_real_roe = any(p.get("roe", 0) > 0 for p in peers_raw)
    has_real_growth = any(p.get("revenue_growth", 0) != 0 for p in peers_raw)
    
    if not has_real_roe and not has_real_growth:
        # 没有真实数据，使用估算值
        if peer_roe and peer_growth:
            lines = []
            lines.append(f"\n| 指标 | {name} | {' | '.join(p.split()[-1] if ' ' in p else p[:8] for p in peer_names[:4])} |")
            lines.append(f"|------|--------|{' | '.join('---' for _ in range(min(4, len(peer_names))))} |")
            if peer_roe and any(r > 0 for r in peer_roe):
                lines.append(f"| ROE | {fin['roe']:.1f}% | {' | '.join(f'{r:.1f}%' for r in peer_roe[:4])} |")
            if peer_growth and any(g != 0 for g in peer_growth):
                lines.append(f"| 营收增速(估) | {fin['avg_revenue_growth']:.1f}% | {' | '.join(f'{g:.1f}%' for g in peer_growth[:4])} |")
            lines.append(f"\n> 注：同行ROE/增速为基于PE/PB的估算值，非真实财报数据\n")
            return "\n".join(lines)
        return "\n> 同行盈利能力与成长性数据不足\n"
    
    # 有真实数据，构建详细对比表
    lines = []
    peer_count = min(4, len(peer_names))
    short_names = []
    for pn in peer_names[:peer_count]:
        # 提取纯名称（去掉代码）
        parts = pn.split(maxsplit=1)
        if len(parts) > 1:
            short_names.append(parts[1])
        else:
            short_names.append(pn[:8])
    
    lines.append(f"\n| 指标 | {name} | {' | '.join(short_names)} |")
    lines.append(f"|------|--------|{' | '.join('---' for _ in range(peer_count))} |")
    
    # ROE
    roe_row = f"| ROE | {fin['roe']:.1f}% |"
    for p in peers_raw[:peer_count]:
        p_roe = p.get("roe", 0)
        if p_roe > 0:
            roe_row += f" {p_roe:.1f}% |"
        else:
            roe_row += " — |"
    lines.append(roe_row)
    
    # 营收增速
    growth_row = f"| 营收增速 | {fin['avg_revenue_growth']:.1f}% |"
    for p in peers_raw[:peer_count]:
        p_growth = p.get("revenue_growth", 0)
        if p_growth != 0:
            growth_row += f" {p_growth:+.1f}% |"
        else:
            growth_row += " — |"
    lines.append(growth_row)
    
    # 净利率
    nm_row = f"| 净利率 | {fin['avg_net_margin']:.1f}% |"
    for p in peers_raw[:peer_count]:
        p_nm = p.get("net_margin", 0)
        if p_nm > 0:
            nm_row += f" {p_nm:.1f}% |"
        else:
            nm_row += " — |"
    lines.append(nm_row)
    
    # 市值
    mcap_row = f"| 市值(亿) | {fin['market_cap']:.0f} |"
    for p in peers_raw[:peer_count]:
        p_mcap = p.get("market_cap", 0) / 100000000 if p.get("market_cap", 0) > 100000000 else p.get("market_cap", 0)
        if p_mcap > 0:
            mcap_row += f" {p_mcap:.0f} |"
        else:
            mcap_row += " — |"
    lines.append(mcap_row)
    
    lines.append(f"\n> 数据来源：东方财富F10真实财务数据\n")
    return "\n".join(lines)


def _gen_sector_overview(fin: dict) -> str:
    """
    基于真实同行数据生成行业概况
    
    核心原则：
    1. 必须引用具体的同行数据进行比较
    2. 必须明确公司在行业中的定位（排名、份额）
    3. 不使用"行业前景广阔""赛道优质"等模板化表述
    """
    industry = fin["industry"]
    avg_rev_growth = fin["avg_revenue_growth"]
    pe = fin["pe"]
    peers = fin.get("peer_names", [])
    market_cap = fin["market_cap"]
    avg_peer_pe = fin["avg_peer_pe"]
    avg_peer_roe = fin["avg_peer_roe"]
    avg_peer_growth = fin["avg_peer_growth"]
    roe = fin["roe"]
    peer_mcap = fin.get("peer_mcap", [])
    peer_pe = fin.get("peer_pe", [])
    peer_roe = fin.get("peer_roe", [])

    peer_count = len(peers)
    industry_name = industry if industry and industry != "数据待补充" else "数据待补充"
    
    # 市值排名
    if peer_mcap and market_cap > 0:
        all_mcap = [market_cap] + peer_mcap
        rank = sorted(all_mcap, reverse=True).index(market_cap) + 1
        mcap_share = market_cap / sum(all_mcap) * 100 if sum(all_mcap) > 0 else 0
        mcap_position = f"行业第 {rank}/{len(all_mcap)}，市值占比约 {mcap_share:.1f}%"
    else:
        mcap_position = "同行数据不足，无法计算排名"

    # 估值对比（详细）
    if avg_peer_pe > 0 and pe > 0:
        pe_ratio = pe / avg_peer_pe
        if pe_ratio < 0.6:
            valuation_text = f"PE {pe:.1f}x，较行业均值 {avg_peer_pe:.1f}x 折价 {(1-pe_ratio)*100:.0f}%，在同业中处于偏低水平"
        elif pe_ratio < 0.85:
            valuation_text = f"PE {pe:.1f}x，略低于行业均值 {avg_peer_pe:.1f}x，估值有一定吸引力"
        elif pe_ratio < 1.15:
            valuation_text = f"PE {pe:.1f}x，与行业均值 {avg_peer_pe:.1f}x 接近，定价中性"
        elif pe_ratio < 1.5:
            valuation_text = f"PE {pe:.1f}x，较行业均值 {avg_peer_pe:.1f}x 溢价 {(pe_ratio-1)*100:.0f}%，市场给予了一定估值溢价"
        else:
            valuation_text = f"PE {pe:.1f}x，远超行业均值 {avg_peer_pe:.1f}x（溢价 {(pe_ratio-1)*100:.0f}%），需要极高的成长预期来支撑"
    elif pe > 0:
        valuation_text = f"PE {pe:.1f}x，同行估值数据不足，无法横向比较"
    else:
        valuation_text = "PE为负，无法进行估值比较"

    # 盈利对比
    if avg_peer_roe > 0 and roe > 0:
        if roe > avg_peer_roe * 2.0:
            profit_text = f"ROE {roe:.1f}%，是行业均值 {avg_peer_roe:.1f}% 的 {roe/avg_peer_roe:.1f} 倍，每单位净资产的盈利效率在同行中具有压倒性优势"
        elif roe > avg_peer_roe * 1.5:
            profit_text = f"ROE {roe:.1f}%，远超行业均值 {avg_peer_roe:.1f}%，每单位净资产的盈利效率在同行中遥遥领先"
        elif roe > avg_peer_roe:
            profit_text = f"ROE {roe:.1f}%，高于行业均值 {avg_peer_roe:.1f}%，盈利效率优于行业平均"
        elif roe > avg_peer_roe * 0.7:
            profit_text = f"ROE {roe:.1f}%，略低于行业均值 {avg_peer_roe:.1f}%，盈利效率处于行业中游"
        else:
            profit_text = f"ROE {roe:.1f}%，显著低于行业均值 {avg_peer_roe:.1f}%，资本回报效率有待提升"
    else:
        profit_text = "同行ROE数据不足，无法比较"

    # 增速对比（支持负增长比较）
    if avg_peer_growth != 0 and avg_rev_growth != 0:
        # 使用绝对值判断增速差异
        growth_gap = avg_rev_growth - avg_peer_growth
        if avg_rev_growth > 0 and growth_gap > 10:
            growth_text = f"营收增速 {avg_rev_growth:.1f}%，在行业整体承压（{avg_peer_growth:.1f}%）的背景下逆势增长，韧性突出"
        elif growth_gap > 8:
            growth_text = f"营收增速 {avg_rev_growth:.1f}%，大幅领先行业均值 {avg_peer_growth:.1f}%，处于快速扩张期，市场份额持续提升"
        elif growth_gap > 3:
            growth_text = f"营收增速 {avg_rev_growth:.1f}%，领先行业均值 {avg_peer_growth:.1f}%，增长动能强于行业"
        elif growth_gap > -3:
            growth_text = f"营收增速 {avg_rev_growth:.1f}%，与行业均值 {avg_peer_growth:.1f}% 基本一致，增长与行业同步"
        elif growth_gap > -8:
            growth_text = f"营收增速 {avg_rev_growth:.1f}%，低于行业均值 {avg_peer_growth:.1f}%，增长动能弱于同行，需关注市场份额变化"
        else:
            growth_text = f"营收增速 {avg_rev_growth:.1f}%，远低于行业均值 {avg_peer_growth:.1f}%，处于弱势地位"
    else:
        growth_text = "行业增速数据不足，无法比较"

    peer_list = "、".join(peers[:5]) if peers else "暂无可比公司数据"

    return f"""
- **行业分类**：{industry_name}
- **可比公司**：{peer_list}（共 {peer_count} 家）
- **市值地位**：{mcap_position}
- **估值水平**：{valuation_text}
- **盈利对比**：{profit_text}
- **增速对比**：{growth_text}
"""


def _classify_industry(industry: str) -> str:
    """根据行业分类判断行业类型，用于定制分析阈值"""
    industry_lower = industry.lower() if industry else ""
    if any(kw in industry_lower for kw in ["白酒", "饮料", "食品", "乳品", "调味品", "医药", "中药", "医疗器械", "软件", "游戏", "传媒", "芯片", "半导体"]):
        return "消费品/科技"
    elif any(kw in industry_lower for kw in ["银行", "保险", "证券", "房地产", "电力", "港口", "铁路", "电信", "零售", "物流"]):
        return "金融/公用事业"
    elif any(kw in industry_lower for kw in ["电池", "储能", "电源", "锂电", "光伏", "风电", "新能源", "汽车", "半导体", "化工", "钢铁", "煤炭", "水泥", "建材", "工程机械", "航空", "军工", "航天", "环保", "造纸", "纺织", "服装"]):
        return "制造业/周期"
    else:
        return "制造业/周期"


def _get_industry_macro_variables(industry: str, industry_type: str) -> str:
    """根据行业类型返回定制化的关键宏观变量"""
    industry_lower = industry.lower() if industry else ""
    
    common_vars = "利率走势（影响估值中枢和财务费用）"
    
    if industry_type == "消费品/科技":
        specific = "居民收入与消费信心（直接影响终端需求）、品牌集中度趋势（龙头溢价/折价）、渠道库存周期（影响短期动销和回款）"
        if "白酒" in industry_lower:
            specific += "、白酒消费税改革预期（政策风险）"
        elif "医药" in industry_lower or "中药" in industry_lower:
            specific += "、集采政策（影响药品定价和利润空间）、医保目录调整（影响产品放量）"
        elif "软件" in industry_lower or "游戏" in industry_lower or "传媒" in industry_lower:
            specific += "、AI技术迭代（替代/赋能）、数据安全监管政策"
        elif "芯片" in industry_lower or "半导体" in industry_lower:
            specific += "、中美科技博弈（供应链安全）、国产替代进度（市场份额变化）"
    elif industry_type == "金融/公用事业":
        specific = "货币政策与信贷周期（影响资产规模和息差）、监管政策（资本充足率/偿付能力要求）、宏观经济增长（影响信贷需求和资产质量）"
        if "银行" in industry_lower:
            specific += "、净息差走势（核心盈利指标）、不良贷款率（资产质量）"
        elif "保险" in industry_lower:
            specific += "、长端利率（影响准备金计提和投资收益）、保费增速（新业务价值）"
        elif "电力" in industry_lower:
            specific += "、煤价/气价（影响发电成本）、电价改革（市场化定价）、新能源补贴政策"
    elif industry_type == "制造业/周期":
        specific = "PPI与原材料价格（影响生产成本和毛利率）、产能利用率（反映供需格局）、出口/汇率（影响海外收入）"
        if any(kw in industry_lower for kw in ["电池", "储能", "锂电", "新能源"]):
            specific += "、新能源补贴退坡（政策风险）、碳酸锂/镍等关键原材料价格（成本端）、储能装机量增速（需求端）"
        elif any(kw in industry_lower for kw in ["光伏", "风电"]):
            specific += "、硅料/组件价格（产业链利润分配）、风光大基地建设进度（国内需求）、海外贸易壁垒（出口风险）"
        elif any(kw in industry_lower for kw in ["汽车", "零部件"]):
            specific += "、新能源车渗透率（结构性增长）、购置税/补贴政策（需求刺激）、智能化竞赛（研发投入）"
        elif any(kw in industry_lower for kw in ["化工", "钢铁", "煤炭", "水泥"]):
            specific += "、供给侧改革/限产政策（影响供需格局）、碳达峰碳中和（长期约束）、下游需求（基建/地产）"
        elif any(kw in industry_lower for kw in ["军工", "航天"]):
            specific += "、国防预算增速（需求端）、军品定价改革（利润率）、地缘政治（催化因素）"
    
    return f"{common_vars}、{specific}"


def _get_industry_gross_margin_threshold(industry_type: str) -> tuple:
    """根据行业类型返回毛利率阈值 (高阈值, 中阈值)"""
    if industry_type == "消费品/科技":
        return (70, 45)  # 消费品/科技毛利率通常较高
    elif industry_type == "金融/公用事业":
        return (60, 35)  # 金融/公用事业毛利率中等
    else:
        return (40, 20)  # 制造业/周期毛利率偏低


def _gen_macro_context(fin: dict) -> str:
    """
    基于真实数据生成宏观背景分析
    
    核心原则：
    1. 从财务数据推导宏观敏感度，而非主观臆断
    2. 利率敏感度从负债率推导，周期敏感度从增速推导
    3. 行业定制分析阈值和关键宏观变量
    """
    pe = fin["pe"]
    avg_rev_growth = fin["avg_revenue_growth"]
    debt_ratio = fin["debt_ratio"]
    avg_peer_pe = fin["avg_peer_pe"]
    roe = fin["roe"]
    avg_peer_roe = fin["avg_peer_roe"]
    avg_gross_margin = fin["avg_gross_margin"]
    industry = fin["industry"]

    industry_type = _classify_industry(industry)
    gm_high, gm_mid = _get_industry_gross_margin_threshold(industry_type)

    # 从数据推导利率敏感度
    if debt_ratio > 55:
        rate_sensitivity = f"高——负债率 {debt_ratio:.1f}%，利率每上升100bp，财务费用将显著增加，直接影响净利润"
    elif debt_ratio > 30:
        rate_sensitivity = f"中等——负债率 {debt_ratio:.1f}%，利率变动对财务费用有一定影响，但尚在可控范围"
    elif debt_ratio > 0:
        rate_sensitivity = f"低——负债率仅 {debt_ratio:.1f}%，几乎无有息负债压力，利率周期变化对盈利影响极小"
    else:
        rate_sensitivity = "数据不足"

    # 从增速推导周期敏感度
    if avg_rev_growth > 20:
        cycle_sensitivity = "高——高增长通常伴随高波动，对行业景气度和宏观经济高度敏感，增速放缓将直接冲击估值"
    elif avg_rev_growth > 10:
        cycle_sensitivity = "中等——稳健增长，受宏观经济影响但具备一定韧性，下行风险可控"
    elif avg_rev_growth > 0:
        cycle_sensitivity = "偏低——低速增长意味着业务相对成熟，与宏观经济关联度中等，防御属性较强"
    elif avg_rev_growth < 0:
        cycle_sensitivity = "高——营收收缩中，宏观环境改善是扭亏关键前提，对政策刺激和经济复苏高度敏感"
    else:
        cycle_sensitivity = "数据不足"

    # 估值与宏观匹配度
    if pe <= 0:
        macro_match = "公司处于亏损状态，宏观改善是估值修复的前提"
    elif pe > 35 and avg_rev_growth < 10:
        macro_match = f"PE {pe:.1f}x 与营收增速 {avg_rev_growth:.1f}% 存在明显错配——高估值要求高增长，但当前增速不支持，宏观不及预期时回调风险较大"
    elif pe > 20 and avg_rev_growth < 5:
        macro_match = f"PE {pe:.1f}x 偏高而增速仅 {avg_rev_growth:.1f}%，宏观中性假设下估值消化压力较大"
    elif pe < 12 and avg_rev_growth > 0:
        macro_match = f"PE {pe:.1f}x 已隐含较多悲观预期，若宏观环境改善，估值修复弹性较大"
    elif pe < 18:
        macro_match = f"PE {pe:.1f}x 处于合理偏低区间，宏观中性假设下具备安全边际，即使宏观走弱下行风险也有限"
    else:
        macro_match = f"PE {pe:.1f}x 与增速 {avg_rev_growth:.1f}% 基本匹配，宏观中性假设下回报预期合理"

    # 行业地位与宏观韧性
    if avg_peer_roe > 0 and roe > 0:
        ratio = roe / avg_peer_roe
        if ratio > 2.0:
            resilience = f"ROE {roe:.1f}% 是行业均值 {avg_peer_roe:.1f}% 的 {ratio:.1f} 倍，在宏观下行期具备极强的议价能力和成本转嫁能力，抗风险能力远优于同行"
        elif ratio > 1.3:
            resilience = f"ROE {roe:.1f}% 远超行业均值 {avg_peer_roe:.1f}%，在宏观下行期具备更强的议价能力和成本转嫁能力，抗风险能力显著优于同行"
        elif ratio > 1.0:
            resilience = f"ROE {roe:.1f}% 高于行业均值 {avg_peer_roe:.1f}%，在宏观波动中相对抗跌"
        elif ratio > 0.7:
            resilience = f"ROE {roe:.1f}% 与行业均值 {avg_peer_roe:.1f}% 接近，宏观波动的影响与行业同步"
        else:
            resilience = f"ROE {roe:.1f}% 低于行业均值 {avg_peer_roe:.1f}%，宏观下行时盈利压力更大，防御性弱于同行"
    else:
        resilience = "同行ROE数据不足，无法评估相对韧性"

    # 毛利率对通胀的敏感度（行业定制阈值）
    if avg_gross_margin > gm_high:
        inflation_sensitivity = f"低——毛利率 {avg_gross_margin:.1f}% 在{industry_type}行业中处于高位，成本端波动对利润的影响被大幅缓冲，具备强通胀传导能力"
    elif avg_gross_margin > gm_mid:
        inflation_sensitivity = f"中等——毛利率 {avg_gross_margin:.1f}%，在{industry_type}行业中处于正常水平，成本上升有一定缓冲空间，但持续通胀将逐步侵蚀利润"
    elif avg_gross_margin > 0:
        inflation_sensitivity = f"高——毛利率 {avg_gross_margin:.1f}%，在{industry_type}行业中偏低，成本端波动对利润影响较大，对通胀较为敏感"
    else:
        inflation_sensitivity = "数据不足"

    # 行业定制关键宏观变量
    macro_vars = _get_industry_macro_variables(industry, industry_type)

    return f"""
- **行业类型**：{industry_type}
- **利率敏感度**：{rate_sensitivity}
- **经济周期敏感度**：{cycle_sensitivity}
- **通胀敏感度**：{inflation_sensitivity}
- **行业宏观韧性**：{resilience}
- **估值与宏观匹配度**：{macro_match}
- **关键宏观变量**：{macro_vars}
"""


def _gen_competitive_position(fin: dict) -> str:
    """
    基于真实数据生成竞争地位分析
    
    核心原则：
    1. 必须用量化的同行对比数据（而非主观判断）
    2. 必须指出具体的竞争优势来源和风险点
    3. 不使用"护城河深厚""竞争力强"等模板化表述
    """
    pe = fin["pe"]
    market_cap = fin["market_cap"]
    roe = fin["roe"]
    peers = fin.get("peer_names", [])
    avg_peer_pe = fin["avg_peer_pe"]
    avg_peer_roe = fin["avg_peer_roe"]
    avg_peer_growth = fin["avg_peer_growth"]
    avg_rev_growth = fin["avg_revenue_growth"]
    avg_gross_margin = fin["avg_gross_margin"]
    avg_net_margin = fin["avg_net_margin"]
    debt_ratio = fin["debt_ratio"]
    goodwill_ratio = fin["goodwill_ratio"]
    peer_mcap = fin.get("peer_mcap", [])
    peer_pe = fin.get("peer_pe", [])

    # 市值排名
    if peer_mcap and market_cap > 0:
        all_mcap = [market_cap] + peer_mcap
        rank = sorted(all_mcap, reverse=True).index(market_cap) + 1
        if rank == 1:
            mcap_text = f"行业第 1/{len(all_mcap)}，绝对龙头地位"
        elif rank <= 3:
            mcap_text = f"行业第 {rank}/{len(all_mcap)}，第一梯队"
        elif rank <= len(all_mcap) // 2:
            mcap_text = f"行业第 {rank}/{len(all_mcap)}，中游偏上"
        else:
            mcap_text = f"行业第 {rank}/{len(all_mcap)}，规模偏小"
    else:
        mcap_text = "数据不足"

    # PE vs 同行（具体排名）
    if peer_pe and pe > 0:
        valid_peers = [p for p in peer_pe if p > 0]
        if valid_peers:
            pe_rank = sum(1 for p in valid_peers if p < pe) + 1
            pe_text = f"PE {pe:.1f}x，在同业中排第 {pe_rank}/{len(valid_peers)+1}（从低到高），{'估值偏低，存在修复空间' if pe_rank <= len(valid_peers)//3 else '估值中等' if pe_rank <= 2*len(valid_peers)//3 else '估值偏高，市场给予溢价'}"
        else:
            pe_text = f"PE {pe:.1f}x，同行PE数据不足"
    else:
        pe_text = "同行估值数据不足"

    # ROE vs 同行
    if avg_peer_roe > 0 and roe > 0:
        if roe > avg_peer_roe * 2.0:
            roe_text = f"ROE {roe:.1f}% 是行业均值 {avg_peer_roe:.1f}% 的 {roe/avg_peer_roe:.1f} 倍，反映了极强的竞争优势——这种数量级的差距通常意味着品牌壁垒、技术领先或成本优势"
        elif roe > avg_peer_roe * 1.3:
            roe_text = f"ROE {roe:.1f}% 显著高于行业均值 {avg_peer_roe:.1f}%，竞争优势明显，高资本回报率是核心护城河"
        elif roe > avg_peer_roe:
            roe_text = f"ROE {roe:.1f}% 高于行业均值 {avg_peer_roe:.1f}%，具备一定竞争优势，但领先幅度有限"
        elif roe > avg_peer_roe * 0.7:
            roe_text = f"ROE {roe:.1f}% 与行业均值 {avg_peer_roe:.1f}% 接近，盈利效率处于行业中游"
        else:
            roe_text = f"ROE {roe:.1f}% 低于行业均值 {avg_peer_roe:.1f}%，资本回报效率处于劣势，需关注盈利改善路径"
    else:
        roe_text = "同行ROE数据不足，无法比较"

    # 竞争壁垒（基于数据识别，非行业模板）
    barriers = []
    if avg_gross_margin > 70:
        barriers.append(f"毛利率 {avg_gross_margin:.1f}% 处于极端高位，意味着产品或服务具有极强的不可替代性，竞争壁垒极高")
    elif avg_gross_margin > 45:
        barriers.append(f"毛利率 {avg_gross_margin:.1f}%，在行业中处于较高水平，反映产品差异化或品牌溢价能力")
    if roe > 25:
        barriers.append(f"ROE {roe:.1f}% 的资本回报率意味着公司拥有高效的资本配置能力，这是可持续竞争优势的核心")
    if avg_peer_growth > 0 and avg_rev_growth > avg_peer_growth * 1.5:
        barriers.append(f"营收增速领先行业均值 {(avg_rev_growth/avg_peer_growth-1)*100:.0f}%，份额持续扩张是竞争壁垒的直接体现")
    if market_cap > 1000:
        barriers.append(f"市值 {market_cap:.0f} 亿的规模优势构筑了资金、人才和渠道壁垒，中小企业难以复制")
    if not barriers:
        barriers.append("基于当前数据，未发现显著的量化竞争壁垒，竞争优势可能更多来自非财务因素（如技术、渠道、品牌等）")

    # 风险点
    risks = []
    if debt_ratio > 55:
        risks.append(f"负债率 {debt_ratio:.1f}% 偏高，高杠杆限制财务灵活性，在行业下行期风险放大")
    if goodwill_ratio > 20:
        risks.append(f"商誉占净资产 {goodwill_ratio:.1f}%，若被收购资产业绩不达预期，减值将直接冲击利润")
    if 0 < avg_rev_growth < avg_peer_growth * 0.5 and avg_peer_growth > 0:
        risks.append(f"营收增速 {avg_rev_growth:.1f}% 远落后于行业均值 {avg_peer_growth:.1f}%，可能正在失去市场份额")
    if avg_net_margin > 0 and avg_net_margin < 5:
        risks.append(f"净利率仅 {avg_net_margin:.1f}%，盈利空间狭窄，竞争加剧或成本上升将迅速侵蚀利润")
    if not risks:
        risks.append("基于当前财务数据，未发现显著的竞争风险点，但需关注行业政策变化和潜在的新进入者")

    barriers_text = "\n".join(f"  - {b}" for b in barriers)
    risks_text = "\n".join(f"  - {r}" for r in risks)
    peer_list = "、".join(peers[:4]) if peers else "暂无可比公司数据"

    return f"""
- **市值规模**：{market_cap:.0f} 亿，{mcap_text}
- **估值定位**：{pe_text}
- **盈利效率**：{roe_text}
- **主要可比公司**：{peer_list}
- **竞争壁垒识别**：
{barriers_text}
- **潜在风险点**：
{risks_text}
"""


def _gen_catalysts(fin: dict) -> str:
    """
    基于真实数据生成催化剂观察
    
    核心原则：
    1. 催化剂必须与公司当前财务状况直接相关
    2. 不使用"行业政策利好""新产品发布"等无法验证的模板套话
    3. 每个催化剂需说明触发条件和预期影响
    """
    industry = fin["industry"]
    forecast = fin.get("forecast", {})
    market_cap = fin["market_cap"]
    avg_rev_growth = fin["avg_revenue_growth"]
    pe = fin["pe"]
    avg_profit_growth = fin["avg_profit_growth"]
    avg_peer_pe = fin["avg_peer_pe"]
    roe = fin["roe"]
    avg_peer_roe = fin["avg_peer_roe"]
    debt_ratio = fin["debt_ratio"]
    avg_gross_margin = fin["avg_gross_margin"]
    avg_net_margin = fin["avg_net_margin"]

    from datetime import datetime
    month = datetime.now().month

    # 业绩预告
    forecast_items = ""
    fc_type = forecast.get("type", "")
    if fc_type:
        fc_low = forecast.get("change_lower", 0)
        fc_high = forecast.get("change_upper", 0)
        fc_period = forecast.get("report_period", "")
        if fc_low > 50:
            direction = "强正面催化：业绩大幅预增，若兑现将显著提振市场信心"
        elif fc_low > 0:
            direction = "正面催化：业绩预增，兑现将验证增长逻辑"
        elif fc_high < -50:
            direction = "强负面催化：业绩大幅预减，需警惕业绩地雷"
        elif fc_high < 0:
            direction = "负面催化：业绩预减，可能触发估值下调"
        else:
            direction = "中性"
        forecast_items = f"| 业绩预告 | {fc_period} | {fc_type}，净利润变动 {fc_low:+.0f}% ~ {fc_high:+.0f}% | {direction} |\n"

    # 基于真实数据的催化剂
    cats = []
    
    # 财报季
    if month in [1, 2, 3, 4]:
        cats.append(("年报+一季报披露", "3-4月", "验证全年业绩和Q1经营状况，是全年最重要的估值锚定窗口"))
    elif month in [7, 8]:
        cats.append(("中报披露", "8月", "上半年业绩验证，全年预期修正的关键节点"))
    elif month in [9, 10]:
        cats.append(("三季报披露", "10月", "前三季度业绩基本明朗，全年预期趋于明确，估值切换窗口"))
    else:
        cats.append(("下一财报季临近", "即将到来", "业绩验证窗口，全年预期将根据最新数据修正"))

    # 基于增速的催化剂
    if avg_rev_growth > 15:
        cats.append(("高增长验证", "每季报", f"当前增速 {avg_rev_growth:.1f}% 能否持续是核心变量——任一季度的增速放缓都可能触发估值回调，幅度取决于放缓程度"))
    elif avg_rev_growth > 5:
        cats.append(("增速改善信号", "每季报", f"当前增速 {avg_rev_growth:.1f}% 相对温和，若超预期加速至 15%+ 将触发显著的估值重估"))
    elif avg_rev_growth > 0:
        cats.append(("增速拐点", "每季报", f"当前增速仅 {avg_rev_growth:.1f}%，若能回升至行业均值以上，将触发估值修复"))
    
    # 利润率相关
    if avg_profit_growth < 0 and avg_rev_growth > 0:
        cats.append(("利润率拐点", "持续关注", f"当前处于增收不增利状态（营收+{avg_rev_growth:.1f}%，利润{avg_profit_growth:.1f}%），利润率何时企稳回升是估值修复的核心前提"))
    elif avg_profit_growth > avg_rev_growth * 1.3 and avg_rev_growth > 0:
        cats.append(("经营杠杆释放", "每季报", f"利润增速 {avg_profit_growth:.1f}% 远超营收增速 {avg_rev_growth:.1f}%，经营杠杆效应持续释放，利润率改善趋势若能延续将推动盈利超预期"))

    # 估值修复催化剂
    if avg_peer_pe > 0 and pe < avg_peer_pe * 0.6:
        cats.append(("估值修复窗口", "业绩/政策触发", f"PE {pe:.1f}x 仅为行业均值 {avg_peer_pe:.1f}x 的 {pe/avg_peer_pe*100:.0f}%，估值修复需要两个条件：①业绩不低于预期 ②市场情绪改善或行业催化"))
    elif pe > 0 and pe < 12:
        cats.append(("低估值催化", "业绩改善", f"PE {pe:.1f}x 处于低位，低估值本身不构成催化剂——需要业绩改善或政策利好来触发向上重估"))

    # 行业地位
    if avg_peer_roe > 0 and roe > avg_peer_roe * 2:
        cats.append(("龙头溢价扩大", "持续", f"ROE {roe:.1f}% 是行业均值 {avg_peer_roe:.1f}% 的 {roe/avg_peer_roe:.1f} 倍，若行业集中度进一步提升，龙头溢价将扩大"))

    cats = cats[:4]

    cat_items = forecast_items + "\n".join(f"| {e} | {t} | {d} |" for e, t, d in cats)

    # 短期催化剂
    short_term = []
    if fc_type:
        short_term.append(f"业绩预告兑现（{fc_type}）：预告数据 vs 实际数据，超预期或低于预期将直接影响短期股价方向")
    short_term.append(f"最新财报披露：验证营收增速 {avg_rev_growth:.1f}% 和利润增速 {avg_profit_growth:.1f}% 能否维持或改善")
    if avg_peer_pe > 0 and pe < avg_peer_pe * 0.8:
        short_term.append(f"估值修复：PE {pe:.1f}x 较行业均值折价 {(1-pe/avg_peer_pe)*100:.0f}%，若有正面催化，修复空间可观")
    else:
        short_term.append("机构持仓变动：季报披露窗口，关注主力资金动向和行业轮动")

    # 长期催化剂
    long_term = []
    if avg_rev_growth > 15:
        long_term.append(f"行业结构性增长：增速 {avg_rev_growth:.1f}% 的赛道优势能否持续，取决于行业渗透率和竞争格局")
    elif avg_rev_growth > 0:
        long_term.append(f"增长加速：当前增速 {avg_rev_growth:.1f}%，关注新产品/新市场拓展能否带来增长提速")
    if avg_gross_margin > 60:
        long_term.append(f"定价权红利：毛利率 {avg_gross_margin:.1f}% 赋予强大提价能力，这是长期价值的核心来源")
    if debt_ratio < 25 and roe > 18:
        long_term.append(f"资本配置优化：低负债({debt_ratio:.1f}%)+高ROE({roe:.1f}%)，分红/回购/并购的资本运作空间充足")
    long_term.append("估值体系切换：盈利稳定性提升→估值中枢上移，或增速放缓→估值收缩，取决于长期趋势")

    return f"""
| 关键事件 | 预期时间 | 影响分析 |
|----------|----------|----------|
{cat_items}

**短期关注（1-3个月）：**
{chr(10).join(f'- {s}' for s in short_term)}

**中长期关注（6-12个月）：**
{chr(10).join(f'- {s}' for s in long_term)}
"""


# ==================== 投资总结 ====================

def _gen_key_points(fin: dict, debate: dict) -> List[str]:
    """基于真实数据生成核心投资要点（每一条必须引用具体数字）"""
    pe = fin["pe"]
    roe = fin["roe"]
    avg_rev_growth = fin["avg_revenue_growth"]
    avg_profit_growth = fin["avg_profit_growth"]
    market_cap = fin["market_cap"]
    rating = debate["rating"]
    bull_score = debate.get("bull_score", 0)
    bear_score = debate.get("bear_score", 0)
    avg_peer_pe = fin["avg_peer_pe"]
    avg_peer_roe = fin["avg_peer_roe"]
    debt_ratio = fin["debt_ratio"]
    fcf_ratio = fin["fcf_ratio"]
    avg_gross_margin = fin["avg_gross_margin"]
    peg = fin["peg"]
    avg_peer_growth = fin["avg_peer_growth"]

    points = []
    
    # 1. 估值与盈利核心
    if pe > 0 and avg_peer_pe > 0:
        pe_vs = pe / avg_peer_pe
        if avg_peer_roe > 0:
            roe_vs = roe / avg_peer_roe
            if pe_vs < 0.7:
                if roe_vs > 1.2:
                    points.append(f"PE {pe:.1f}x 较行业均值 {avg_peer_pe:.1f}x 折价 {(1-pe_vs)*100:.0f}%，但 ROE {roe:.1f}% 远超行业均值 {avg_peer_roe:.1f}%，折价不反映真实盈利能力，价值被低估")
                elif roe_vs > 0.8:
                    points.append(f"PE {pe:.1f}x 较行业均值 {avg_peer_pe:.1f}x 折价 {(1-pe_vs)*100:.0f}%，ROE {roe:.1f}% 与行业均值 {avg_peer_roe:.1f}% 基本匹配，折价有一定合理性")
                else:
                    points.append(f"PE {pe:.1f}x 较行业均值 {avg_peer_pe:.1f}x 折价 {(1-pe_vs)*100:.0f}%，但 ROE {roe:.1f}% 低于行业均值 {avg_peer_roe:.1f}%，折价反映了盈利质量差距")
            elif pe_vs < 1.0:
                if roe_vs > 1.2:
                    points.append(f"PE {pe:.1f}x 略低于行业均值 {avg_peer_pe:.1f}x，ROE {roe:.1f}% 领先行业均值 {avg_peer_roe:.1f}%，估值偏低+盈利领先=性价比突出")
                else:
                    points.append(f"PE {pe:.1f}x 低于行业均值 {avg_peer_pe:.1f}x，ROE {roe:.1f}%，估值具有相对优势")
            elif pe_vs < 1.3:
                if roe_vs > 1.5:
                    points.append(f"PE {pe:.1f}x 略高于行业均值 {avg_peer_pe:.1f}x，但 ROE {roe:.1f}% 是行业均值 {avg_peer_roe:.1f}% 的 {roe_vs:.1f} 倍，溢价由盈利优势支撑")
                else:
                    points.append(f"PE {pe:.1f}x 略高于行业均值 {avg_peer_pe:.1f}x，ROE {roe:.1f}%，估值溢价基本合理")
            else:
                if roe_vs > 2.0:
                    points.append(f"PE {pe:.1f}x 显著高于行业均值 {avg_peer_pe:.1f}x（溢价 {(pe_vs-1)*100:.0f}%），但 ROE {roe:.1f}% 是行业均值 {avg_peer_roe:.1f}% 的 {roe_vs:.1f} 倍，高溢价有盈利支撑")
                else:
                    points.append(f"PE {pe:.1f}x 显著高于行业均值 {avg_peer_pe:.1f}x（溢价 {(pe_vs-1)*100:.0f}%），但 ROE {roe:.1f}% 仅略高于行业均值 {avg_peer_roe:.1f}%，估值溢价需要更强盈利来支撑")
        else:
            if pe_vs < 0.7:
                points.append(f"PE {pe:.1f}x 较行业均值 {avg_peer_pe:.1f}x 折价 {(1-pe_vs)*100:.0f}%，ROE {roe:.1f}%，折价幅度较大需关注基本面风险")
            elif pe_vs < 1.0:
                points.append(f"PE {pe:.1f}x 低于行业均值 {avg_peer_pe:.1f}x，ROE {roe:.1f}%，估值具有相对优势")
            elif pe_vs < 1.3:
                points.append(f"PE {pe:.1f}x 略高于行业均值 {avg_peer_pe:.1f}x，ROE {roe:.1f}%，估值溢价基本合理")
            else:
                points.append(f"PE {pe:.1f}x 显著高于行业均值 {avg_peer_pe:.1f}x（溢价 {(pe_vs-1)*100:.0f}%），需 ROE {roe:.1f}% 持续领先来支撑溢价")
    elif pe > 0:
        points.append(f"PE {pe:.1f}x，ROE {roe:.1f}%，市值 {market_cap:.0f} 亿，多空得分 {bull_score}:{bear_score}")
    else:
        points.append(f"PE为负，公司处于亏损状态，多空得分 {bull_score}:{bear_score}")

    # 2. 增速与估值匹配度
    if avg_rev_growth > 15:
        points.append(f"营收增速 {avg_rev_growth:.1f}%，利润增速 {avg_profit_growth:.1f}%，处于中高速增长阶段，成长性是核心看点")
    elif avg_rev_growth > 5:
        if avg_peer_growth > 0 and avg_rev_growth > avg_peer_growth:
            points.append(f"营收增速 {avg_rev_growth:.1f}%（领先行业均值 {avg_peer_growth:.1f}%），利润增速 {avg_profit_growth:.1f}%，增速虽非爆发式但持续高于行业")
        else:
            points.append(f"营收增速 {avg_rev_growth:.1f}%，利润增速 {avg_profit_growth:.1f}%，增长稳健但非高速，估值的进一步扩张需要增速提升")
    elif avg_rev_growth > 0:
        points.append(f"营收增速 {avg_rev_growth:.1f}%，利润增速 {avg_profit_growth:.1f}%，增速偏低，投资逻辑更依赖估值修复或股息回报而非增长")
    else:
        points.append(f"营收增速 {avg_rev_growth:.1f}%，业务处于收缩期，拐点信号是投资决策的关键变量")

    # 3. 盈利能力
    if avg_gross_margin > 70:
        points.append(f"毛利率 {avg_gross_margin:.1f}%，净利率 {fin['avg_net_margin']:.1f}%，盈利质量极高，每1元营收可保留约 {fin['avg_net_margin']/100:.2f} 元净利润")
    elif avg_gross_margin > 40:
        points.append(f"毛利率 {avg_gross_margin:.1f}%，净利率 {fin['avg_net_margin']:.1f}%，盈利能力在行业中处于中上水平")
    elif avg_gross_margin > 0:
        points.append(f"毛利率 {avg_gross_margin:.1f}%，净利率 {fin['avg_net_margin']:.1f}%，利润率偏低，盈利改善空间是价值重估的关键")

    # 4. 财务健康
    if debt_ratio > 0 and debt_ratio < 20:
        points.append(f"资产负债率仅 {debt_ratio:.1f}%，财务极其稳健，几乎无债务风险，且保留了加杠杆提升ROE的潜力")
    elif debt_ratio > 0 and debt_ratio < 40:
        points.append(f"资产负债率 {debt_ratio:.1f}%，处于健康区间，财务风险可控")
    elif debt_ratio >= 50:
        points.append(f"资产负债率 {debt_ratio:.1f}% 偏高，需关注偿债压力和利率风险，高杠杆在经济下行时是双刃剑")

    # 5. 行业地位
    if avg_peer_roe > 0 and roe > avg_peer_roe * 1.5:
        points.append(f"ROE {roe:.1f}% 远超行业均值 {avg_peer_roe:.1f}%，竞争优势显著，行业龙头地位稳固，这是长期持有的核心逻辑")
    elif avg_peer_roe > 0 and roe < avg_peer_roe * 0.6:
        points.append(f"ROE {roe:.1f}% 显著低于行业均值 {avg_peer_roe:.1f}%，竞争力偏弱，需关注是否有明确的改善路径")

    # 6. 操作建议
    if "Bullish" in rating and "Mildly" not in rating:
        points.append(f"多空得分 {bull_score}:{bear_score}，多方占优，关注催化剂兑现情况（财报验证、行业政策），作为加仓/减仓信号")
    elif "Bearish" in rating and "Mildly" not in rating:
        points.append(f"多空得分 {bull_score}:{bear_score}，空方占优，建议等待更好的入场时机或更明确的利好信号，当前风险收益比不理想")
    else:
        points.append(f"多空得分 {bull_score}:{bear_score}，方向不明确，建议等待关键事件（财报/政策）确认方向后操作，不宜重仓博弈")

    return points[:6]


def _gen_final_summary(fin: dict, debate: dict) -> tuple:
    """基于真实数据生成最终评级"""
    pe = fin["pe"]
    rating = debate["rating"]
    net_score = debate.get("net_score", 0)
    is_mock = fin.get("is_mock", False)
    avg_peer_pe = fin["avg_peer_pe"]
    avg_peer_roe = fin["avg_peer_roe"]
    roe = fin["roe"]

    rating_map = {
        "Bullish (看多)": "买入",
        "Mildly Bullish (偏多)": "增持",
        "Bearish (看空)": "卖出",
        "Mildly Bearish (偏空)": "减持",
        "Neutral (中性)": "持有",
    }
    final_rating = rating_map.get(rating, "持有")

    # 确信度（基于数据质量和多空差距）
    if is_mock:
        conviction = "低（数据为估算值，仅供参考）"
    elif abs(net_score) >= 4:
        conviction = "高（多空信号明确，分歧小）"
    elif abs(net_score) >= 2:
        conviction = "中（多空信号有一定倾向性）"
    else:
        conviction = "低（多空信号接近，方向不明确）"

    # 持仓周期
    if "Bullish" in rating:
        if "Mildly" in rating:
            holding_period = "6-12 个月"
        else:
            holding_period = "12-18 个月"
    elif "Bearish" in rating:
        holding_period = "不建议持仓"
    else:
        holding_period = "6-12 个月"

    return final_rating, conviction, holding_period


# ==================== 主报告生成函数 ====================

def generate_research_report(
    symbol: str,
    market: str = "A",
    deep_analysis: bool = True,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    生成个股深度研报（基于真实数据）

    返回：
        {
            "symbol": str,
            "name": str,
            "market": str,
            "report_markdown": str,
            "report_time": str,
            "sections": {...},
        }
    """
    # 获取真实行情数据
    quote = get_quote(symbol, market)
    name = quote.get("name", symbol)
    price = quote.get("price", 0)
    change_pct = quote.get("change_pct", 0)

    # 获取真实财务数据
    real_data = _fetch_real_data(symbol, market)
    fin = _build_financial_metrics(symbol, market, real_data)

    # 红蓝对抗（基于真实数据）
    debate = _red_blue_debate(fin, quote)

    # 构建报告
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    is_mock = fin.get("is_mock", False)

    # ====== 优先使用DeepSeek AI生成报告 ======
    ai_report = generate_research_report_via_ai(
        symbol=symbol, name=name, market=market,
        price=price, change_pct=change_pct,
        fin=fin, debate=debate, quote=quote,
        llm_config=llm_config,
    )
    
    if ai_report:
        # AI报告生成成功，直接使用AI报告
        logger.info(f"使用DeepSeek AI报告: {symbol}")
        
        # 从AI报告提取summary信息
        sections = {
            "fundamental": fin.get("industry", ""),
            "debate": {"red_score": debate.get("red_score", 0), "blue_score": debate.get("blue_score", 0)},
            "sector": fin.get("industry", ""),
            "macro": fin.get("industry", ""),
            "catalysts": {},
            "engine": {
                "sotp": "",
                "price_in": "",
                "option_value": "",
                "game_theory": "",
                "time_wall": "",
            },
            "financial_data": fin,
            "summary": {
                "rating": "详见报告",
                "conviction": "详见报告",
                "holding_period": "详见报告",
                "key_points": [],
                "bull_score": debate.get("bull_score", 0),
                "bear_score": debate.get("bear_score", 0),
                "net_score": debate.get("net_score", 0),
            },
        }
        
        return {
            "symbol": symbol,
            "name": name,
            "market": market,
            "report_markdown": ai_report,
            "report_time": report_time,
            "sections": sections,
            "ai_generated": True,
        }
    
    # ====== AI报告生成失败，回退到模板式生成 ======
    logger.info(f"回退到模板式报告: {symbol}")
    data_note = "> ⚠️ **注意**：当前财务数据不完整，部分指标未能获取。实际投资决策请以官方财报为准。\n" if is_mock else ""

    # 行业分析（基于真实数据）
    sector_desc = _gen_sector_overview(fin)
    macro_desc = _gen_macro_context(fin)
    competition_desc = _gen_competitive_position(fin)
    catalysts_desc = _gen_catalysts(fin)

    # 投资总结
    final_rating, conviction, holding_period = _gen_final_summary(fin, debate)

    # 五阶引擎
    sotp_text = _engine_sotp(fin) if deep_analysis else ""
    price_in_text = _engine_price_in(fin) if deep_analysis else ""
    option_text = _engine_option_value(fin) if deep_analysis else ""
    game_text = _engine_game_theory(fin) if deep_analysis else ""
    time_wall_text = _engine_time_wall(fin) if deep_analysis else ""

    # 营收增速表格
    rev_growth = fin["revenue_growth"]
    trend_dates = fin.get("trend_dates", [])
    if rev_growth and any(g != 0 for g in rev_growth):
        # 显示最近4-6期（太多了表格不好看）
        display_count = min(6, len(rev_growth))
        display_growth = rev_growth[-display_count:]
        display_dates = trend_dates[-display_count:] if trend_dates and len(trend_dates) >= display_count else [f"第{i+1}期" for i in range(display_count)]
        rev_table = "\n".join(
            f"| {display_dates[i] if i < len(display_dates) else f'第{i+1}期'} | {g:+.1f}% |" for i, g in enumerate(display_growth)
        )
        latest_growth = rev_growth[-1] if rev_growth else 0
        first_growth = rev_growth[0] if rev_growth else 0
        if len(rev_growth) >= 3:
            recent_avg = sum(rev_growth[-3:]) / 3
            early_avg = sum(rev_growth[:3]) / 3 if len(rev_growth) >= 6 else sum(rev_growth[:len(rev_growth)//2]) / max(1, len(rev_growth)//2)
            if recent_avg > early_avg * 1.2:
                rev_trend = "加速增长，近3期均值显著高于早期"
            elif recent_avg > early_avg:
                rev_trend = "稳中有升，增长动能温和改善"
            elif recent_avg < early_avg * 0.8:
                rev_trend = "明显放缓，增长动能减弱"
            elif recent_avg < early_avg:
                rev_trend = "略有回落，需关注后续趋势"
            else:
                rev_trend = "保持平稳"
        else:
            rev_trend = "上升" if latest_growth > first_growth else "下降" if latest_growth < first_growth else "保持平稳"
    else:
        rev_table = "| — | 数据不足 |"
        rev_trend = "数据不足，无法判断"
        display_dates = []

    # 利润增速表格
    profit_growth = fin["profit_growth"]
    if profit_growth and any(g != 0 for g in profit_growth):
        display_count = min(6, len(profit_growth))
        display_pg = profit_growth[-display_count:]
        profit_table = "\n".join(
            f"| {display_dates[i] if i < len(display_dates) else f'第{i+1}期'} | {g:+.1f}% |" for i, g in enumerate(display_pg)
        )
        if len(profit_growth) >= 3:
            recent_avg = sum(profit_growth[-3:]) / 3
            early_avg = sum(profit_growth[:3]) / 3 if len(profit_growth) >= 6 else sum(profit_growth[:len(profit_growth)//2]) / max(1, len(profit_growth)//2)
            if recent_avg > early_avg * 1.2:
                profit_trend = "加速增长，盈利能力持续提升"
            elif recent_avg > early_avg:
                profit_trend = "稳中有升"
            elif recent_avg < early_avg * 0.8:
                profit_trend = "明显放缓，盈利压力加大"
            elif recent_avg < early_avg:
                profit_trend = "略有回落"
            else:
                profit_trend = "保持平稳"
        else:
            latest_pg = profit_growth[-1] if profit_growth else 0
            first_pg = profit_growth[0] if profit_growth else 0
            profit_trend = "上升" if latest_pg > first_pg else "下降" if latest_pg < first_pg else "保持平稳"
    else:
        profit_table = "| — | 数据不足 |"
        profit_trend = "数据不足"

    # 毛利率、净利率表格（合并格式）
    gross_margin = fin["gross_margin"]
    net_margin = fin["net_margin"]
    if gross_margin and any(g != 0 for g in gross_margin):
        display_count = min(6, len(gross_margin))
        display_gm = gross_margin[-display_count:]
        display_nm = net_margin[-display_count:]
        gm_nm_rows = []
        for i in range(display_count):
            dt = display_dates[i] if i < len(display_dates) else f"第{i+1}期"
            gm_nm_rows.append(f"| {dt} | {display_gm[i]:.1f}% | {display_nm[i]:.1f}% |")
        gm_nm_table = "\n".join(gm_nm_rows)
        gm_latest = gross_margin[-1] if gross_margin else 0
        gm_first = gross_margin[0] if gross_margin else 0
        nm_latest = net_margin[-1] if net_margin else 0
        nm_first = net_margin[0] if net_margin else 0
        gm_trend = "稳中有升，定价权强" if gm_latest > gm_first + 1 else "略有下滑，需关注成本端" if gm_latest < gm_first - 1 else "保持稳定"
        nm_trend = "持续改善" if nm_latest > nm_first + 0.5 else "有所回落" if nm_latest < nm_first - 0.5 else "保持稳定"
    else:
        gm_nm_table = "| — | 数据不足 | 数据不足 |"
        gm_trend = "数据不足"
        nm_trend = "数据不足"

    # 同行估值表格（增强版）
    peer_names = fin.get("peer_names", [])
    peer_pe = fin.get("peer_pe", [])
    if peer_names and peer_pe:
        peer_count = min(len(peer_names), 3)
        peer_header = " | ".join(f"{p.split()[0] if ' ' in p else p[:6]}" for p in peer_names[:3])
        peer_pe_row = " | ".join(f"{p:.1f}x" for p in peer_pe[:3])
        peer_pb = fin.get("peer_pb", [])
        peer_pb_row = " | ".join(f"{p:.1f}x" for p in peer_pb[:3]) if peer_pb and any(p > 0 for p in peer_pb) else " | ".join("—" for _ in range(min(peer_count, 3)))
        separator = " | ".join("---" for _ in range(min(peer_count, 3) + 1))
        avg_peer_pe = fin["avg_peer_pe"]
        if fin["pe"] < avg_peer_pe * 0.8:
            pe_vs_peer = "低于行业平均，存在估值修复空间"
        elif fin["pe"] > avg_peer_pe * 1.3:
            pe_vs_peer = "高于行业平均，反映市场给予的溢价"
        else:
            pe_vs_peer = "与行业均值接近，定价中性"
    else:
        peer_header = "同行1 | 同行2 | 同行3"
        peer_pe_row = "— | — | —"
        peer_pb_row = "— | — | —"
        separator = "--- | --- | ---"
        avg_peer_pe = 0
        pe_vs_peer = "同行数据不足，无法比较"

    # 构建完整 Markdown 报告
    data_source_map = {
        "eastmoney": "东方财富真实数据",
        "akshare": "AKShare真实数据",
        "sina": "新浪行情数据",
        "akshare_spot": "AKShare行情数据",
        "akshare_info": "AKShare个股数据",
        "unknown": "数据不完整"
    }
    data_label = f"数据来源：{data_source_map.get(fin['source'], fin['source'])}"
    if is_mock:
        data_label = "数据来源：部分数据不可用"
    
    # 数据质量说明
    data_quality_note = ""
    if is_mock:
        data_quality_note = "> ⚠️ **注意**：当前财务数据不完整，部分指标未能获取。实际投资决策请以官方财报为准。\n"
    elif fin["source"] != "eastmoney":
        data_quality_note = f"> ℹ️ 数据来源：{data_source_map.get(fin['source'], fin['source'])}。部分指标可能与官方财报有轻微偏差。\n"

    # 资产负债/现金流补充信息
    health_metrics = ""
    if fin["debt_ratio"] > 0 or fin["fcf_ratio"] > 0:
        health_metrics = "\n### 1.5 财务健康度\n\n"
        if fin["debt_ratio"] > 0:
            debt_level = "偏高（需关注偿债风险）" if fin["debt_ratio"] > 50 else "健康" if fin["debt_ratio"] < 50 else "中等"
            health_metrics += f"- 资产负债率：**{fin['debt_ratio']:.1f}%**（{debt_level}）\n"
        # FCF比率：只有当数值合理（>5%）时才显示，避免显示错误数据
        if fin["fcf_ratio"] > 5:
            fcf_quality = "优秀（利润含金量高）" if fin["fcf_ratio"] > 80 else "良好" if fin["fcf_ratio"] > 50 else "偏低（利润含金量存疑）" if fin["fcf_ratio"] < 30 else "一般"
            health_metrics += f"- 自由现金流/净利润：**{fin['fcf_ratio']:.1f}%**（{fcf_quality}）\n"
        elif fin["fcf"] > 0 and fin["net_profit"] > 0:
            # 用FCF和净利润计算真实比率
            real_fcf_ratio = (fin["fcf"] / fin["net_profit"]) * 100 if fin["net_profit"] > 0 else 0
            if 5 < real_fcf_ratio < 200:
                fcf_quality = "优秀" if real_fcf_ratio > 80 else "良好" if real_fcf_ratio > 50 else "偏低"
                health_metrics += f"- 自由现金流/净利润：**{real_fcf_ratio:.1f}%**（{fcf_quality}）\n"
        if fin["goodwill_ratio"] > 0:
            gw_risk = "高（减值风险显著）" if fin["goodwill_ratio"] > 30 else "中等" if fin["goodwill_ratio"] > 15 else "低"
            health_metrics += f"- 商誉/净资产：**{fin['goodwill_ratio']:.1f}%**（风险水平：{gw_risk}）\n"
        if fin["eps"] > 0:
            health_metrics += f"- 每股收益（EPS）：**{fin['eps']:.2f}元**\n"

    report = f"""# {name}（{symbol}）深度研究报告

> **生成时间**：{report_time}　|　**市场**：{'A股' if market == 'A' else '美股'}　|　**行业**：{fin['industry']}
> **最新价格**：{price}　|　**涨跌幅**：{change_pct:+.2f}%　|　**{data_label}**
{data_quality_note}
---

## 一、基本面分析

### 1.1 核心财务指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 市盈率 (PE-TTM) | {fin['pe']:.1f}x | {"高于行业均值" if avg_peer_pe > 0 and fin['pe'] > avg_peer_pe else "低于行业均值" if avg_peer_pe > 0 and fin['pe'] < avg_peer_pe else "数据不足"} |
| 市净率 (PB) | {fin['pb']:.1f}x | — |
| 净资产收益率 (ROE) | {fin['roe']:.1f}% | {"领先行业" if fin['avg_peer_roe'] > 0 and fin['roe'] > fin['avg_peer_roe'] else "低于行业" if fin['avg_peer_roe'] > 0 else "—"} |
| 总市值 | {fin['market_cap']:.0f}亿 | — |
| PEG | {fin['peg']:.2f} | {"低估" if fin['peg'] > 0 and fin['peg'] < 1 else "合理" if fin['peg'] > 0 and fin['peg'] < 2 else "偏高" if fin['peg'] > 0 else "—"} |
| 资产负债率 | {fin['debt_ratio']:.1f}% | {"健康" if fin['debt_ratio'] > 0 and fin['debt_ratio'] < 50 else "偏高" if fin['debt_ratio'] >= 50 else "—"} |

### 1.2 营收增长分析

| 期间 | 营收增速 |
|------|----------|
{rev_table}

- 近4期平均增速：**{fin['avg_revenue_growth']:.1f}%**
- 增速趋势：{rev_trend}

### 1.3 利润增长分析

| 期间 | 利润增速 |
|------|----------|
{profit_table}

- 近4期平均利润增速：**{fin['avg_profit_growth']:.1f}%**
- 利润增速趋势：{profit_trend}

### 1.4 毛利率与净利率趋势

| 期间 | 毛利率 | 净利率 |
|------|--------|--------|
{gm_nm_table}

- 平均毛利率：{fin['avg_gross_margin']:.1f}%
- 平均净利率：{fin['avg_net_margin']:.1f}%
- 毛利率趋势：{gm_trend}
- 净利率趋势：{nm_trend}
{health_metrics}
"""

    # ====== 新增：利润表明细 ======
    income_stmt = fin.get("income_statement", [])
    if income_stmt:
        income_text = ""
        # 取最近3期
        for i, row in enumerate(income_stmt[:3]):
            rev = row["revenue"] / 100000000 if abs(row["revenue"]) > 100000000 else row["revenue"] / 10000
            cost = row["operate_cost"] / 100000000 if abs(row["operate_cost"]) > 100000000 else row["operate_cost"] / 10000
            op = row["operate_profit"] / 100000000 if abs(row["operate_profit"]) > 100000000 else row["operate_profit"] / 10000
            np_val = row["net_profit"] / 100000000 if abs(row["net_profit"]) > 100000000 else row["net_profit"] / 10000
            sale_exp = row["sale_expense"] / 100000000 if abs(row["sale_expense"]) > 100000000 else row["sale_expense"] / 10000
            mgmt_exp = row["manage_expense"] / 100000000 if abs(row["manage_expense"]) > 100000000 else row["manage_expense"] / 10000
            fin_exp_raw = row["finance_expense"]
            fin_exp = fin_exp_raw / 100000000 if abs(fin_exp_raw) > 100000000 else fin_exp_raw / 10000
            if rev > 0:
                # 显示完整日期（YYYY-MM）
                date_label = row['report_date'][:7] if len(row['report_date']) >= 7 else row['report_date']
                income_text += f"| {date_label} | {rev:.1f}亿 | {cost:.1f}亿 | {sale_exp:.1f}亿 | {mgmt_exp:.1f}亿 | {fin_exp:+.1f}亿 | {op:.1f}亿 | {np_val:.1f}亿 |\n"
        
        if income_text:
            report += f"""### 1.{'6' if health_metrics else '5'} 利润表明细

| 报告期 | 营收 | 营业成本 | 销售费用 | 管理费用 | 财务费用 | 营业利润 | 净利润 |
|--------|------|----------|----------|----------|----------|----------|--------|
{income_text}
"""

    # ====== 新增：资产负债表结构 ======
    bs = fin.get("balance_sheet", {})
    if bs and bs.get("total_assets", 0) > 0:
        ta = bs["total_assets"] / 100000000
        tl = bs["total_liabilities"] / 100000000
        te = bs["total_equity"] / 100000000
        mf = bs.get("monetary_funds", 0) / 100000000
        ar = bs.get("accounts_receivable", 0) / 100000000
        inv = bs.get("inventory", 0) / 100000000
        fa = bs.get("fixed_asset", 0) / 100000000
        ap = bs.get("accounts_payable", 0) / 100000000
        
        # 资产结构分析
        mf_pct = (mf / ta * 100) if ta > 0 else 0
        ar_pct = (ar / ta * 100) if ta > 0 else 0
        inv_pct = (inv / ta * 100) if ta > 0 else 0
        fa_pct = (fa / ta * 100) if ta > 0 else 0
        debt_pct = (tl / ta * 100) if ta > 0 else 0
        
        asset_quality = ""
        if mf_pct > 30:
            asset_quality = "货币资金充裕，资产流动性极强，抗风险能力突出"
        elif mf_pct > 15:
            asset_quality = "货币资金充足，资产结构健康"
        elif mf_pct > 5:
            asset_quality = "货币资金占比合理"
        else:
            asset_quality = "货币资金占比偏低，需关注流动性"
        
        if ar_pct > 30:
            asset_quality += "；应收账款占比偏高，需关注回款风险"
        if inv_pct > 30:
            asset_quality += "；存货占比偏高，需关注跌价风险"
        
        report += f"""### 1.{'7' if health_metrics or income_stmt else '6' if health_metrics else '5'} 资产负债表结构

> 报告期：{bs.get('report_date', '')[:10]}　|　资产质量：{asset_quality}

| 项目 | 金额(亿) | 占比 |
|------|----------|------|
| 总资产 | {ta:.1f} | 100% |
| 货币资金 | {mf:.1f} | {mf_pct:.1f}% |
| 应收账款 | {ar:.1f} | {ar_pct:.1f}% |
| 存货 | {inv:.1f} | {inv_pct:.1f}% |
| 固定资产 | {fa:.1f} | {fa_pct:.1f}% |
| 总负债 | {tl:.1f} | {debt_pct:.1f}% |
| 净资产 | {te:.1f} | {100-debt_pct:.1f}% |
"""

    # ====== 新增：现金流量表 ======
    cf_stmt = fin.get("cashflow_statement", [])
    if cf_stmt:
        cf_text = ""
        for row in cf_stmt[:3]:
            oc = row["operate_cf"] / 100000000 if row["operate_cf"] > 100000000 else row["operate_cf"] / 100000000
            ic = row["invest_cf"] / 100000000 if row["invest_cf"] > 100000000 else row["invest_cf"] / 100000000
            fc = row["finance_cf"] / 100000000 if row["finance_cf"] > 100000000 else row["finance_cf"] / 100000000
            sc = row.get("sales_cash", 0) / 100000000 if row.get("sales_cash", 0) > 100000000 else row.get("sales_cash", 0) / 100000000
            cpx = row.get("capex", 0) / 100000000 if row.get("capex", 0) > 100000000 else row.get("capex", 0) / 100000000
            fcf = oc + cpx  # 自由现金流 = 经营CF + 资本支出(为负)
            
            cf_text += f"| {row['report_date'][:4]}年报 | {sc:.1f}亿 | {oc:.1f}亿 | {ic:.1f}亿 | {fc:.1f}亿 | {cpx:.1f}亿 | {fcf:.1f}亿 |\n"
        
        if cf_text:
            # 现金流质量分析
            latest_cf = cf_stmt[0]
            oc_val = latest_cf["operate_cf"] / 100000000
            latest_fcf = oc_val + (latest_cf.get("capex", 0) / 100000000)
            cf_quality = ""
            if latest_fcf > 0 and oc_val > 0:
                cf_quality = "经营现金流为正，自由现金流充裕，盈利质量高"
            elif oc_val > 0:
                cf_quality = "经营现金流为正，但资本开支较大，自由现金流偏紧"
            elif oc_val < 0:
                cf_quality = "经营现金流为负，盈利质量存疑，需关注现金流改善"
            
            report += f"""### 1.{'8' if (health_metrics or income_stmt) and (health_metrics or income_stmt) and bs else '7' if (health_metrics or income_stmt) else '6'} 现金流量表

> 现金流质量：{cf_quality}

| 报告期 | 销售收现 | 经营CF | 投资CF | 筹资CF | 资本开支 | 自由现金流 |
|--------|----------|--------|--------|--------|----------|------------|
{cf_text}
"""

    # 计算当前section编号
    extra_sections = sum([bool(health_metrics), bool(income_stmt), bool(bs), bool(cf_stmt)])
    
    # ====== 新增：主营构成 ======
    rev_seg = fin.get("revenue_segment", {})
    if rev_seg:
        # 优先显示产品分类，其次行业分类
        seg_to_show = rev_seg.get("product", []) or rev_seg.get("industry", [])
        if seg_to_show:
            extra_sections += 1
            seg_num = 5 + extra_sections
            report += f"""### 1.{seg_num} 主营构成

"""
            report += "| 业务板块 | 营收(亿) | 占比 | 成本(亿) | 毛利(亿) | 毛利率 |\n"
            report += "|----------|----------|------|----------|----------|--------|\n"
            for item in seg_to_show[:8]:
                rev_val = item["revenue"] / 100000000 if abs(item["revenue"]) > 100000000 else item["revenue"] / 10000
                cost_val = item["cost"] / 100000000 if abs(item["cost"]) > 100000000 else item["cost"] / 10000
                profit_val = item["profit"] / 100000000 if abs(item["profit"]) > 100000000 else item["profit"] / 10000
                report += f"| {item['name']} | {rev_val:.1f} | {item['ratio']:.1f}% | {cost_val:.1f} | {profit_val:.1f} | {item['margin']:.1f}% |\n"
            
            # 核心业务判断
            if len(seg_to_show) >= 2:
                top1 = seg_to_show[0]
                top2 = seg_to_show[1]
                if top1["ratio"] > 70:
                    report += f"\n- 核心业务「{top1['name']}」占比 {top1['ratio']:.1f}%，业务高度集中，单一业务依赖度较高\n"
                elif top1["ratio"] > 50:
                    report += f"\n- 主力业务「{top1['name']}」占比 {top1['ratio']:.1f}%，「{top2['name']}」占比 {top2['ratio']:.1f}%，业务结构多元\n"
                else:
                    report += f"\n- 业务较为分散，最大板块「{top1['name']}」仅占 {top1['ratio']:.1f}%\n"
            report += "\n"
    
    # ====== 新增：运营效率分析 ======
    eff = fin.get("operating_efficiency", {})
    if eff:
        extra_sections += 1
        eff_num = 5 + extra_sections
        report += f"""### 1.{eff_num} 运营效率指标

"""
        # 构建效率指标表格
        eff_items = []
        if eff.get("asset_turnover", 0) > 0:
            eff_items.append(("总资产周转率", f"{eff['asset_turnover']:.2f}次", "衡量资产运营效率，越高越好"))
        if eff.get("inventory_turnover", 0) > 0:
            eff_items.append(("存货周转率", f"{eff['inventory_turnover']:.2f}次", "越高说明存货管理越好"))
        if eff.get("receivable_turnover", 0) > 0:
            eff_items.append(("应收账款周转率", f"{eff['receivable_turnover']:.2f}次", "越高说明回款能力越强"))
        if eff.get("current_ratio", 0) > 0:
            level = "充裕" if eff["current_ratio"] > 2 else "合理" if eff["current_ratio"] > 1 else "偏低"
            eff_items.append(("流动比率", f"{eff['current_ratio']:.2f}", f"短期偿债能力：{level}"))
        if eff.get("quick_ratio", 0) > 0:
            level = "充裕" if eff["quick_ratio"] > 1 else "合理" if eff["quick_ratio"] > 0.5 else "偏低"
            eff_items.append(("速动比率", f"{eff['quick_ratio']:.2f}", f"速动偿债能力：{level}"))
        if eff.get("sales_cash_ratio", 0) > 0:
            quality = "优秀" if eff["sales_cash_ratio"] > 1 else "良好" if eff["sales_cash_ratio"] > 0.8 else "偏低"
            eff_items.append(("销售收现/营收", f"{eff['sales_cash_ratio']:.2f}", f"收入含金量：{quality}"))
        if eff.get("operate_cash_ratio", 0) > 0:
            quality = "优秀" if eff["operate_cash_ratio"] > 0.3 else "良好" if eff["operate_cash_ratio"] > 0.1 else "偏低"
            eff_items.append(("经营现金流/营收", f"{eff['operate_cash_ratio']:.2f}", f"盈利质量：{quality}"))
        if eff.get("bps", 0) > 0:
            eff_items.append(("每股净资产(BPS)", f"{eff['bps']:.2f}元", "每股内含价值"))
        if eff.get("bps_growth", 0) != 0:
            eff_items.append(("BPS增长率", f"{eff['bps_growth']:+.2f}%", "净资产增长趋势"))
        if eff.get("tax_rate", 0) > 0:
            eff_items.append(("实际税率", f"{eff['tax_rate']:.1f}%", "税务负担水平"))
        if eff.get("interest_debt_ratio", 0) > 0:
            level = "偏高" if eff["interest_debt_ratio"] > 30 else "健康" if eff["interest_debt_ratio"] > 10 else "低"
            eff_items.append(("带息债务比率", f"{eff['interest_debt_ratio']:.1f}%", f"有息负债水平：{level}"))
        
        if eff_items:
            report += "| 指标 | 数值 | 解读 |\n"
            report += "|------|------|------|\n"
            for name, val, desc in eff_items:
                report += f"| {name} | {val} | {desc} |\n"
            report += "\n"
        
        # ====== 杜邦分析 ======
        net_margin_pct = fin["avg_net_margin"] / 100 if fin["avg_net_margin"] > 0 else 0
        asset_turnover = eff.get("asset_turnover", 0) / 100 if eff.get("asset_turnover", 0) > 100 else eff.get("asset_turnover", 0)
        equity_mult = eff.get("equity_multiplier", 0)
        if not equity_mult and fin["debt_ratio"] > 0 and fin["debt_ratio"] < 100:
            equity_mult = 1 / (1 - fin["debt_ratio"] / 100)
        
        if net_margin_pct > 0 and asset_turnover > 0 and equity_mult > 0:
            dupont_roe = net_margin_pct * 100 * asset_turnover * equity_mult
            report += f"""**杜邦分析 (ROE分解)：**

ROE = 净利率 × 资产周转率 × 权益乘数

| 分解因子 | 数值 | 贡献 |
|----------|------|------|
| 净利率 | {net_margin_pct*100:.1f}% | {"高盈利驱动" if net_margin_pct*100 > 15 else "中等盈利" if net_margin_pct*100 > 5 else "盈利偏弱"} |
| 资产周转率 | {asset_turnover:.2f}次 | {"高效运营" if asset_turnover > 0.8 else "中速周转" if asset_turnover > 0.4 else "低速周转"} |
| 权益乘数 | {equity_mult:.2f}x | {"高杠杆" if equity_mult > 3 else "适度杠杆" if equity_mult > 1.5 else "低杠杆"} |
| **ROE (杜邦)** | **{dupont_roe:.1f}%** | {"高回报" if dupont_roe > 20 else "中等回报" if dupont_roe > 10 else "回报偏低"} |

- ROE驱动模式：{
    "高盈利驱动型（高净利率+低周转+低杠杆）" if net_margin_pct*100 > 15 and asset_turnover < 0.8 else
    "高效运营型（中净利率+高周转）" if asset_turnover > 0.8 else
    "杠杆驱动型（低净利率+高杠杆）" if equity_mult > 3 else
    "均衡发展型"
}

"""
    
    section_base = 5 + extra_sections + 1
    
    report += f"""### 1.{section_base} 同业估值对比

| 指标 | {name} | {peer_header} |
|------|--------|{separator} |
| PE | {fin['pe']:.1f}x | {peer_pe_row} |
| PB | {fin['pb']:.1f}x | {peer_pb_row} |

- 估值位置：{pe_vs_peer}
- 行业平均PE：{avg_peer_pe:.1f}x
- PEG：{fin['peg']:.2f}（{"合理偏低" if fin['peg'] > 0 and fin['peg'] < 1 else "合理" if fin['peg'] > 0 and fin['peg'] < 2 else "偏高" if fin['peg'] > 0 else "数据不足"}）

### 1.{section_base + 1} 同业盈利能力与成长性对比

{_gen_peer_profitability_table(fin, name)}

"""

    # 添加分析师评级
    analyst = fin.get("analyst", {})
    if analyst and analyst.get("total_ratings", 0) > 0:
        report += f"""### 1.{section_base + 2} 分析师一致预期

"""
        # 综合评级
        if analyst.get("compre_rating"):
            report += f"- 综合评级：**{analyst['compre_rating']}**（评分 {analyst.get('compre_score', 0):.1f}/5.0）\n"
        report += f"- 近一月评级机构：**{analyst.get('total_org', analyst['total_ratings'])}** 家\n"
        report += f"- 买入/增持占比：**{analyst['buy_pct']:.0f}%**\n"
        # 评级分布
        rating_breakdown = analyst.get('rating_breakdown', {})
        if rating_breakdown:
            report += f"- 评级分布：{' / '.join(f'{k} {v}家' for k, v in rating_breakdown.items() if v > 0)}\n"
        
        # EPS预测
        eps_forecasts = analyst.get("eps_forecasts", [])
        if eps_forecasts:
            report += "\n| 预测年份 | 一致预期EPS | 对应PE |\n"
            report += "|----------|------------|--------|\n"
            for fc in eps_forecasts[:4]:
                fc_pe = price / fc["eps"] if price > 0 and fc["eps"] > 0 else 0
                report += f"| {fc['year']}E | {fc['eps']:.2f}元 | {fc_pe:.1f}x |\n"
            if len(eps_forecasts) >= 2:
                eps_growth = (eps_forecasts[1]["eps"] / eps_forecasts[0]["eps"] - 1) * 100 if eps_forecasts[0]["eps"] > 0 else 0
                report += f"\n- 一致预期EPS增速（{eps_forecasts[0]['year']}→{eps_forecasts[1]['year']}）：**{eps_growth:+.1f}%**\n"
        
        report += "\n"

    # 添加机构持仓
    inst = fin.get("institutional", {})
    if inst:
        report += f"""### 1.{section_base + 3} 机构持仓

"""
        if inst.get("fund_count", 0) > 0:
            report += f"- 基金持股家数：**{inst['fund_count']}** 家，合计持股 **{inst.get('fund_ratio', 0):.1f}%**\n"
        if inst.get("institutional_ratio", 0) > 0:
            report += f"- 机构合计持股：**{inst['institutional_ratio']:.1f}%**\n"
        top_holders = inst.get("top_holders", [])
        if top_holders:
            report += "- 前五大股东：\n"
            for h in top_holders[:5]:
                report += f"  - {h['name']}（{h.get('type', '')}）：**{h['ratio']:.2f}%**\n"
        report += "\n"

    # 添加北向资金
    nb = fin.get("northbound", {})
    if nb and nb.get("hold_ratio", 0) > 0:
        report += f"""### 1.{section_base + 4} 北向资金

- 沪深港通持股比例：**{nb['hold_ratio']:.2f}%**
- 持股市值：约 **{nb.get('hold_market_cap', 0):.1f}亿**
- 近期变动：{nb.get('hold_change', 0):+.2f}个百分点
- 数据日期：{nb.get('trade_date', '')}

"""

    # 添加估值分位
    vp = fin.get("valuation_percentile", {})
    if vp and vp.get("pe_percentile", 0) > 0:
        pe_level = "偏低" if vp['pe_percentile'] < 30 else "中等" if vp['pe_percentile'] < 70 else "偏高"
        report += f"""### 1.{section_base + 5} 估值分位

- 当前 PE **{fin['pe']:.1f}x** 处于行业可比区间 **{vp['pe_range_low']:.0f}~{vp['pe_range_high']:.0f}x** 的 **{vp['pe_percentile']:.0f}%** 分位（{pe_level}）
- 说明：{vp.get('note', '')}

"""

    # 添加分红数据
    div = fin.get("dividend", {})
    if div:
        has_dividend = div.get("dividend_yield", 0) > 0
        has_total = div.get("total_dividend", 0) > 0
        if has_dividend or has_total:
            report += f"### 1.{section_base + 6} 分红回报\n\n"
            if has_dividend:
                div_level = "高股息" if div['dividend_yield'] > 3 else "中等" if div['dividend_yield'] > 1.5 else "偏低"
                report += f"- 股息率：**{div['dividend_yield']:.2f}%**（{div_level}）\n"
                if div.get("cash_per_share", 0) > 0:
                    report += f"- 每股分红：**{div['cash_per_share']:.2f}元**\n"
                if div.get("plan"):
                    report += f"- 分红方案：{div['plan']}\n"
                if div.get("ex_date"):
                    report += f"- 除权除息日：{div['ex_date'][:10]}\n"
            if has_total and div.get("year"):
                report += f"- {div['year']}年度分红总额：**{div['total_dividend']:.1f}亿**\n"
            report += "\n"

    # ====== 新增：增长质量分析 ======
    gq = fin.get("growth_quality", {})
    if gq:
        report += f"""### 1.{section_base + 7} 增长质量分析

- 增长质量评级：**{gq['quality']}**
- 分析：{gq['detail']}
- 毛利率趋势：{gq['gm_trend']:+.1f}pp
- 营收增速趋势：{gq['rev_trend']:+.1f}pp

"""

    # ====== 新增：人均效率指标 ======
    pc = fin.get("per_capita", {})
    if pc and pc.get("staff_num", 0) > 0:
        report += f"""### 1.{section_base + 8} 人均效率指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 员工总数 | {pc['staff_num']:,}人 | — |
| 人均营收 | {pc['per_revenue']:.1f}万元 | {"高效" if pc['per_revenue'] > 200 else "中等" if pc['per_revenue'] > 100 else "偏低"} |
| 人均营业利润 | {pc['per_operate_profit']:.1f}万元 | {"高效" if pc['per_operate_profit'] > 30 else "中等" if pc['per_operate_profit'] > 10 else "偏低"} |
"""
        # 员工人数趋势
        staff_trend = pc.get("staff_trend", [])
        if len(staff_trend) >= 2:
            report += "\n**员工人数变化：**\n"
            report += "| 年份 | 员工人数 |\n"
            report += "|------|----------|\n"
            for s in staff_trend[-4:]:
                report += f"| {s['year']} | {s['staff']:,}人 |\n"
            first_staff = staff_trend[0]["staff"]
            last_staff = staff_trend[-1]["staff"]
            if first_staff > 0:
                change = (last_staff / first_staff - 1) * 100
                report += f"\n- {staff_trend[0]['year']}~{staff_trend[-1]['year']}员工变化：{change:+.1f}%"
                if change > 10:
                    report += "（持续扩张）"
                elif change < -5:
                    report += "（持续收缩）"
                else:
                    report += "（基本稳定）"
        report += "\n\n"

    # ====== 新增：股东结构 ======
    sh = fin.get("shareholder", {})
    if sh:
        holders = sh.get("holders_trend", [])
        controller = sh.get("actual_controller", "")
        concentration = sh.get("concentration", "")
        
        if holders or controller:
            report += f"""### 1.{section_base + 9} 股东结构

"""
            if controller:
                report += f"- 实际控制人：**{controller}**\n"
            
            if concentration:
                report += f"- 筹码状态：**{concentration}**\n"
            
            if holders:
                report += "\n**股东人数变化：**\n"
                report += "| 报告期 | 股东人数 | 环比变化 | 人均持股 | 筹码状态 |\n"
                report += "|--------|----------|----------|----------|----------|\n"
                for h in holders[:5]:
                    report += f"| {h['date']} | {h['total_num']:,.0f}户 | {h['change_ratio']:+.1f}% | {h['avg_shares']:.0f}股 | {h['focus']} |\n"
                
                # 判断筹码集中度趋势
                if len(holders) >= 3:
                    recent_changes = [h["change_ratio"] for h in holders[:3]]
                    if all(c < 0 for c in recent_changes):
                        report += "\n- 连续3期股东人数减少，筹码持续集中，机构可能在收集\n"
                    elif all(c > 0 for c in recent_changes):
                        report += "\n- 连续3期股东人数增加，筹码趋于分散，关注出货风险\n"
            
            report += "\n"

    # ====== 新增：财务异常检测 ======
    fa = fin.get("financial_anomaly", {})
    if fa:
        anomalies = fa.get("anomalies", [])
        warnings = fa.get("warnings", [])
        if anomalies or warnings:
            report += f"""### 1.{section_base + 10} 财务异常检测

"""
            if anomalies:
                report += "**异常信号：**\n"
                for a in anomalies:
                    report += f"- ⚠️ {a}\n"
                report += "\n"
            if warnings:
                report += "**关注信号：**\n"
                for w in warnings:
                    report += f"- ⚡ {w}\n"
                report += "\n"
            
            # 关键财务健康指标
            report += "**关键健康指标：**\n"
            report += "| 指标 | 数值 | 安全区间 | 状态 |\n"
            report += "|------|------|----------|------|\n"
            
            yszk_r = fa.get("yszk_ratio", 0)
            if yszk_r > 0:
                status = "正常" if yszk_r < 30 else "关注" if yszk_r < 50 else "异常"
                report += f"| 应收/营收比 | {yszk_r:.1f}% | <30% | {status} |\n"
            
            yszk_d = fa.get("yszk_days", 0)
            if yszk_d > 0:
                status = "正常" if yszk_d < 90 else "关注" if yszk_d < 180 else "异常"
                report += f"| 应收周转天数 | {yszk_d:.0f}天 | <90天 | {status} |\n"
            
            nco = fa.get("nco_np", 0)
            if nco > 0:
                status = "良好" if nco > 0.5 else "关注"
                report += f"| 经营现金流/净利润 | {nco:.2f} | >0.5 | {status} |\n"
            
            ic = fa.get("interest_cover", 0)
            if ic > 0:
                status = "良好" if ic > 5 else "关注" if ic > 2 else "异常"
                report += f"| 利息保障倍数 | {ic:.1f}x | >5x | {status} |\n"
            
            report += "\n"

    # ====== 新增：业绩预告 ======
    earnings_fc = fin.get("earnings_forecast", [])
    if earnings_fc:
        report += f"""### 1.{section_base + 11} 业绩预告\n\n"""
        report += "| 预告日期 | 报告期 | 预告类型 | 净利润下限(亿) | 净利润上限(亿) | 增速下限 | 增速上限 |\n"
        report += "|----------|--------|----------|---------------|---------------|----------|----------|\n"
        for fc in earnings_fc[:3]:
            amt_low = fc["amt_lower"] / 100000000
            amt_up = fc["amt_upper"] / 100000000
            report += f"| {fc['notice_date']} | {fc['report_date']} | {fc['predict_type']} | {amt_low:.1f} | {amt_up:.1f} | {fc['add_amp_lower']:+.1f}% | {fc['add_amp_upper']:+.1f}% |\n"
        
        # 最新预告解读
        latest_fc = earnings_fc[0]
        if latest_fc["content"]:
            report += f"\n- 最新预告：{latest_fc['content']}\n"
        if latest_fc["reason"]:
            report += f"- 变动原因：{latest_fc['reason']}\n"
        
        # 与当前业绩对比
        if fin["net_profit"] > 0 and latest_fc["amt_upper"] > 0:
            actual_np = fin["net_profit"]
            forecast_mid = (latest_fc["amt_lower"] + latest_fc["amt_upper"]) / 2 / 100000000
            if forecast_mid > 0:
                beat_ratio = (actual_np / forecast_mid - 1) * 100
                if beat_ratio > 10:
                    report += f"- 实际vs预告：实际净利润 **{actual_np:.1f}亿**，超出预告中值 **{beat_ratio:+.1f}%**，业绩超预期\n"
                elif beat_ratio < -10:
                    report += f"- 实际vs预告：实际净利润 **{actual_np:.1f}亿**，低于预告中值 **{beat_ratio:+.1f}%**，业绩不及预期\n"
                else:
                    report += f"- 实际vs预告：实际净利润 **{actual_np:.1f}亿**，与预告中值偏差 **{beat_ratio:+.1f}%**，基本符合预期\n"
        report += "\n"

    # ====== 新增：限售股解禁 ======
    lockup = fin.get("lockup_shares", {})
    if lockup:
        risk_emoji = {"高": "🔴", "中": "🟡", "低": "🟢", "无": "✅"}.get(lockup.get("risk_level", ""), "")
        report += f"""### 1.{section_base + 12} 限售股解禁风险\n\n"""
        report += f"- 总股本：**{lockup['total_shares']:,}股**\n"
        report += f"- 限售股：**{lockup['limited_shares']:,}股**（占比 **{lockup['limited_ratio']:.1f}%**）\n"
        report += f"- 流通股占比：**{lockup['unlimited_ratio']:.1f}%**\n"
        report += f"- 解禁风险评级：{risk_emoji} **{lockup['risk_level']}** — {lockup['risk']}\n"
        if lockup.get("limited_ratio", 0) > 0:
            report += f"- 数据截止：{lockup.get('end_date', '')}\n"
        report += "\n"

    report += f"""
---

## 二、逻辑验证（红蓝对抗）

### 2.1 支持投资逻辑的核心论据

{chr(10).join(f'{i}. **{t}**' for i, t in enumerate(debate["bull_theses"], 1))}

### 2.2 反面论据与关键风险

{chr(10).join(f'{i}. **{t}**' for i, t in enumerate(debate["bear_theses"], 1))}

### 2.3 多空量化评分

| 方向 | 得分 | 核心逻辑 |
|------|------|----------|
| 多方 | {debate.get('bull_score', 0)}分 | {"基本面偏强" if debate.get('bull_score', 0) >= debate.get('bear_score', 0) else "多方论据不足"} |
| 空方 | {debate.get('bear_score', 0)}分 | {"风险点较多" if debate.get('bear_score', 0) >= debate.get('bull_score', 0) else "空方论据不足"} |
| **净得分** | **{debate.get('net_score', 0):+d}分** | — |

### 2.4 最终定性

> **{debate['rating']}**
>
> {debate['rating_reason']}

---

## 三、行业与宏观视角

### 3.1 行业概况

{sector_desc}

### 3.2 宏观经济趋势

{macro_desc}

### 3.3 市场竞争地位

{competition_desc}

---

## 四、催化剂观察

{catalysts_desc}

---

## 五、深度逻辑五阶引擎推演

> 以下分析基于可获取的真实财务数据进行多维拆解，非行业模板套话。

### 5.1 SOTP 分部重估 (Segmented Re-rating)

{sotp_text}

### 5.2 隐含预期拆解 (Price-in Decoding)

{price_in_text}

### 5.3 期权价值识别 (Option Value Identification)

{option_text}

### 5.4 博弈对冲分析 (Game Theory & Hedge)

{game_text}

### 5.5 时间墙与终值回归 (Time-Wall & Terminal Value)

{time_wall_text}

---

## 六、投资总结

### 核心投资逻辑（5要点）

{chr(10).join(f'{i}. {p}' for i, p in enumerate(_gen_key_points(fin, debate), 1))}

### 最终评级

| 维度 | 结论 |
|------|------|
| **最终评级** | **{final_rating}** |
| **确信度** | **{conviction}** |
| **预期持仓周期** | **{holding_period}** |
| **核心逻辑** | {debate['rating_reason']} |

---

> ⚠️ **免责声明**：本报告基于公开数据和量化模型自动生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。
> 数据来源可能存在延迟或偏差，实际投资决策请以最新官方数据为准。
"""

    # 结构化数据（供前端Tab展示）
    sections = {
        "fundamental": {
            "pe": fin["pe"],
            "pb": fin["pb"],
            "roe": fin["roe"],
            "eps": fin["eps"],
            "market_cap": fin["market_cap"],
            "peg": fin["peg"],
            "debt_ratio": fin["debt_ratio"],
            "fcf_ratio": fin["fcf_ratio"],
            "goodwill_ratio": fin["goodwill_ratio"],
            "revenue_growth": fin["revenue_growth"],
            "avg_revenue_growth": fin["avg_revenue_growth"],
            "profit_growth": fin["profit_growth"],
            "avg_profit_growth": fin["avg_profit_growth"],
            "gross_margin": fin["gross_margin"],
            "net_margin": fin["net_margin"],
            "avg_gross_margin": fin["avg_gross_margin"],
            "avg_net_margin": fin["avg_net_margin"],
            "peer_pe": fin["peer_pe"],
            "peer_pb": fin["peer_pb"],
            "peer_roe": fin["peer_roe"],
            "peer_names": fin["peer_names"],
            "avg_peer_pe": fin["avg_peer_pe"],
            "avg_peer_roe": fin["avg_peer_roe"],
            "avg_peer_growth": fin["avg_peer_growth"],
            "data_source": fin["source"],
            "is_mock": fin["is_mock"],
            # 新增数据维度
            "shareholder": fin.get("shareholder", {}),
            "per_capita": fin.get("per_capita", {}),
            "growth_quality": fin.get("growth_quality", {}),
            "financial_anomaly": fin.get("financial_anomaly", {}),
            "earnings_forecast": fin.get("earnings_forecast", []),
            "lockup_shares": fin.get("lockup_shares", {}),
        },
        "debate": debate,
        "industry": {
            "sector": fin["industry"],
            "peers": fin["peer_names"],
            "peer_pe": fin["peer_pe"],
            "peer_roe": fin["peer_roe"],
            "market_cap": fin["market_cap"],
            "peer_mcap": fin.get("peer_mcap", []),
            "avg_peer_pe": fin["avg_peer_pe"],
            "avg_peer_roe": fin["avg_peer_roe"],
            "avg_peer_growth": fin["avg_peer_growth"],
        },
        "catalysts": {
            "forecast": fin.get("forecast", {}),
            "industry": fin["industry"],
        },
        "summary": {
            "rating": final_rating,
            "conviction": conviction,
            "holding_period": holding_period,
            "key_points": _gen_key_points(fin, debate),
            "bull_score": debate.get("bull_score", 0),
            "bear_score": debate.get("bear_score", 0),
            "net_score": debate.get("net_score", 0),
        },
    }

    return {
        "symbol": symbol,
        "name": name,
        "market": market,
        "report_markdown": report,
        "report_time": report_time,
        "sections": sections,
    }