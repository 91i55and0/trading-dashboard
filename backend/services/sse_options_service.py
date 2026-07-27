"""
上交所（SSE）ETF期权 Put/Call 比率服务
数据来源: 上交所官网 (通过 AKShare option_daily_stats_sse)
https://www.sse.com.cn/assortment/options/date/

包含: 每日 Put/Call 比率（成交量/OI）、历史趋势、情绪分析、多标的跟踪
"""
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# 历史数据存储路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "sse_options_history.json")

# 默认标的列表
DEFAULT_UNDERLYINGS = ["510050", "510300", "510500", "588000", "588080"]


# ============================================================================
# 数据获取
# ============================================================================

def _fetch_sse_daily_stats(date_str: str = None) -> Optional[pd.DataFrame]:
    """
    从 AKShare 获取上交所期权每日统计
    
    参数:
        date_str: 日期，格式 'YYYYMMDD'，默认为最近交易日
    
    返回: DataFrame 包含成交量/OI Put/Call 数据
    """
    try:
        import akshare as ak
        
        # 尝试多个日期（从指定日期往前找，最多尝试7天）
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        from datetime import timedelta
        base_date = datetime.strptime(date_str, '%Y%m%d')
        
        for offset in range(7):
            try_date = (base_date - timedelta(days=offset)).strftime('%Y%m%d')
            try:
                df = ak.option_daily_stats_sse(date=try_date)
                if df is not None and not df.empty and '认沽/认购' in df.columns:
                    logger.info(f"SSE期权数据获取成功: date={try_date}, rows={len(df)}")
                    return df
            except Exception:
                continue
        
        logger.warning(f"SSE期权数据为空: 尝试了 {date_str} 及前7天均无数据")
        return None
    except Exception as e:
        logger.warning(f"获取SSE期权数据失败: {e}")
        return None


def _load_history() -> List[Dict]:
    """加载历史数据"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"加载SSE期权历史数据失败: {e}")
        return []


def _save_history(records: List[Dict]):
    """保存历史数据"""
    os.makedirs(DATA_DIR, exist_ok=True)
    # 去重：按日期去重，保留最新
    seen = {}
    for r in records:
        key = (r.get('date'), r.get('underlying_code'))
        seen[key] = r
    unique = list(seen.values())
    # 按日期排序
    unique.sort(key=lambda x: (x.get('date', ''), x.get('underlying_code', '')))
    # 只保留最近 252 个交易日（约一年）
    if len(unique) > 252 * len(DEFAULT_UNDERLYINGS):
        unique = unique[-252 * len(DEFAULT_UNDERLYINGS):]
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(unique, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"保存SSE期权历史数据失败: {e}")


# ============================================================================
# 核心服务函数
# ============================================================================

def get_daily_stats(date_str: str = None) -> Dict[str, Any]:
    """
    获取上交所期权每日统计（最新一天）
    
    返回:
        {
            "date": "2026-07-24",
            "records": [...],  # 各标的详细数据
            "summary": {...},  # 汇总数据
            "source": "SSE via AKShare",
        }
    """
    df = _fetch_sse_daily_stats(date_str)
    if df is None:
        return {"error": "无法获取上交所期权数据", "date": date_str}

    records = []
    for _, row in df.iterrows():
        records.append({
            "underlying_code": str(row.get("合约标的代码", "")),
            "underlying_name": str(row.get("合约标的名称", "")),
            "contract_count": int(row.get("合约数量", 0)),
            "turnover": float(row.get("总成交额", 0)),
            "total_volume": int(row.get("总成交量", 0)),
            "call_volume": int(row.get("认购成交量", 0)),
            "put_volume": int(row.get("认沽成交量", 0)),
            "pc_ratio_volume": float(row.get("认沽/认购", 0)) / 100,  # 转为小数
            "total_oi": int(row.get("未平仓合约总数", 0)),
            "call_oi": int(row.get("未平仓认购合约数", 0)),
            "put_oi": int(row.get("未平仓认沽合约数", 0)),
            "pc_ratio_oi": round(
                int(row.get("未平仓认沽合约数", 0)) / max(int(row.get("未平仓认购合约数", 1)), 1), 4
            ),
            "trade_date": str(row.get("交易日", "")),
        })

    # 汇总（加权平均 Put/Call）
    total_call_vol = sum(r["call_volume"] for r in records)
    total_put_vol = sum(r["put_volume"] for r in records)
    total_call_oi = sum(r["call_oi"] for r in records)
    total_put_oi = sum(r["put_oi"] for r in records)

    summary = {
        "total_call_volume": total_call_vol,
        "total_put_volume": total_put_vol,
        "pc_ratio_volume": round(total_put_vol / max(total_call_vol, 1), 4),
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "pc_ratio_oi": round(total_put_oi / max(total_call_oi, 1), 4),
        "total_turnover": sum(r["turnover"] for r in records),
        "underlying_count": len(records),
    }

    return {
        "date": records[0]["trade_date"] if records else date_str,
        "records": records,
        "summary": summary,
        "source": "上交所 (SSE) via AKShare",
        "fetched_at": datetime.now().isoformat(),
    }


def get_sse_put_call_analysis() -> Dict[str, Any]:
    """
    SSE Put/Call 比率分析报告
    包含: 最新数据、历史趋势、情绪判断、分析报告
    """
    # 1. 获取最新数据
    stats = get_daily_stats()
    if "error" in stats:
        return stats

    # 2. 保存到历史
    history = _load_history()
    today = stats["date"]
    for r in stats["records"]:
        history.append({
            "date": today,
            "underlying_code": r["underlying_code"],
            "underlying_name": r["underlying_name"],
            "call_volume": r["call_volume"],
            "put_volume": r["put_volume"],
            "pc_ratio_volume": r["pc_ratio_volume"],
            "call_oi": r["call_oi"],
            "put_oi": r["put_oi"],
            "pc_ratio_oi": r["pc_ratio_oi"],
            "total_oi": r["total_oi"],
        })
    _save_history(history)

    # 3. 计算历史趋势
    summary = stats["summary"]
    current_pc_vol = summary["pc_ratio_volume"]
    current_pc_oi = summary["pc_ratio_oi"]

    # 从历史中提取每日汇总数据
    daily_summary = _compute_daily_summary(history)

    # 提取时间序列用于趋势分析
    pc_vol_series = [d["pc_ratio_volume"] for d in daily_summary]
    pc_oi_series = [d["pc_ratio_oi"] for d in daily_summary]
    dates = [d["date"] for d in daily_summary]

    # 4. 计算指标
    n = len(pc_vol_series)
    if n >= 5:
        avg_5d_vol = float(np.mean(pc_vol_series[-5:]))
        avg_5d_oi = float(np.mean(pc_oi_series[-5:]))
    else:
        avg_5d_vol = current_pc_vol
        avg_5d_oi = current_pc_oi

    if n >= 10:
        avg_10d_vol = float(np.mean(pc_vol_series[-10:]))
        avg_10d_oi = float(np.mean(pc_oi_series[-10:]))
    else:
        avg_10d_vol = avg_5d_vol
        avg_10d_oi = avg_5d_oi

    if n >= 20:
        avg_20d_vol = float(np.mean(pc_vol_series[-20:]))
        avg_20d_oi = float(np.mean(pc_oi_series[-20:]))
        std_20d_vol = float(np.std(pc_vol_series[-20:]))
    else:
        avg_20d_vol = avg_5d_vol
        avg_20d_oi = avg_5d_oi
        std_20d_vol = 0

    # 分位数
    if n > 0:
        percentile_vol = float(sum(1 for v in pc_vol_series if v < current_pc_vol) / n * 100)
        percentile_oi = float(sum(1 for v in pc_oi_series if v < current_pc_oi) / n * 100)
    else:
        percentile_vol = 50
        percentile_oi = 50

    # 5. 趋势判断
    if n >= 5:
        if avg_5d_vol > avg_20d_vol * 1.05:
            trend = "显著上升"
            trend_strength = "strong_up"
        elif avg_5d_vol > avg_20d_vol:
            trend = "上升"
            trend_strength = "up"
        elif avg_5d_vol < avg_20d_vol * 0.95:
            trend = "显著下降"
            trend_strength = "strong_down"
        elif avg_5d_vol < avg_20d_vol:
            trend = "下降"
            trend_strength = "down"
        else:
            trend = "横盘"
            trend_strength = "flat"
    else:
        trend = "数据不足"
        trend_strength = "unknown"

    # 6. 情绪判断（A股期权市场特征：Put/Call通常低于美股）
    sentiment, signal, risk_level = _analyze_sse_sentiment(
        current_pc_vol, current_pc_oi, avg_5d_vol, avg_20d_vol,
        percentile_vol, trend_strength
    )

    # 7. 极端值检测
    extremes = _detect_extremes(current_pc_vol, current_pc_oi, percentile_vol, std_20d_vol, n)

    # 8. 生成分析报告
    report = _generate_sse_report(
        current_pc_vol, current_pc_oi, avg_5d_vol, avg_20d_vol,
        sentiment, signal, trend, percentile_vol, percentile_oi,
        stats["records"], daily_summary[-30:], extremes
    )

    return {
        "date": today,
        "current_pc_ratio_volume": round(current_pc_vol, 4),
        "current_pc_ratio_oi": round(current_pc_oi, 4),
        "avg_5d_volume": round(avg_5d_vol, 4),
        "avg_5d_oi": round(avg_5d_oi, 4),
        "avg_10d_volume": round(avg_10d_vol, 4),
        "avg_10d_oi": round(avg_10d_oi, 4),
        "avg_20d_volume": round(avg_20d_vol, 4),
        "avg_20d_oi": round(avg_20d_oi, 4),
        "volatility_20d": round(std_20d_vol, 4),
        "percentile_volume": round(percentile_vol, 1),
        "percentile_oi": round(percentile_oi, 1),
        "sentiment": sentiment,
        "signal": signal,
        "risk_level": risk_level,
        "trend": trend,
        "trend_strength": trend_strength,
        "summary": summary,
        "records": stats["records"],
        "extremes": extremes,
        "report": report,
        "history": daily_summary[-30:],
        "source": stats["source"],
        "analysis_time": datetime.now().isoformat(),
    }


def _compute_daily_summary(history: List[Dict]) -> List[Dict]:
    """从历史记录计算每日汇总"""
    from collections import defaultdict
    daily = defaultdict(lambda: {
        "total_call_vol": 0, "total_put_vol": 0,
        "total_call_oi": 0, "total_put_oi": 0,
    })
    for r in history:
        d = daily[r["date"]]
        d["total_call_vol"] += r.get("call_volume", 0)
        d["total_put_vol"] += r.get("put_volume", 0)
        d["total_call_oi"] += r.get("call_oi", 0)
        d["total_put_oi"] += r.get("put_oi", 0)

    result = []
    for date in sorted(daily.keys()):
        d = daily[date]
        total_call_vol = d["total_call_vol"]
        total_put_vol = d["total_put_vol"]
        total_call_oi = d["total_call_oi"]
        total_put_oi = d["total_put_oi"]
        result.append({
            "date": date,
            "call_volume": total_call_vol,
            "put_volume": total_put_vol,
            "pc_ratio_volume": round(total_put_vol / max(total_call_vol, 1), 4),
            "call_oi": total_call_oi,
            "put_oi": total_put_oi,
            "pc_ratio_oi": round(total_put_oi / max(total_call_oi, 1), 4),
        })
    return result


def _analyze_sse_sentiment(
    current_vol: float, current_oi: float,
    avg_5d_vol: float, avg_20d_vol: float,
    percentile: float, trend_strength: str,
) -> tuple:
    """
    分析A股期权市场情绪
    A股期权Put/Call通常低于美股（0.5-0.9区间），需要调整阈值
    """
    # 基于成交量 Put/Call 的情绪判断（A股阈值）
    if current_vol > 1.0:
        sentiment = "极度恐慌"
        base_signal = "Put/Call比率突破1.0，市场恐慌情绪严重，看跌期权需求激增，可能接近阶段性底部，但也需防范持续下跌"
        risk_level = "high"
    elif current_vol > 0.9:
        sentiment = "恐慌"
        base_signal = "Put/Call比率高于0.9，市场避险情绪升温，看跌期权需求旺盛，短期或有超跌反弹机会"
        risk_level = "high"
    elif current_vol > 0.80:
        sentiment = "偏空"
        base_signal = "Put/Call比率处于偏高区间，市场情绪偏向谨慎，对冲需求增加"
        risk_level = "medium"
    elif current_vol > 0.70:
        sentiment = "中性偏谨慎"
        base_signal = "Put/Call比率处于正常偏高区间，市场保持谨慎但未出现恐慌"
        risk_level = "medium"
    elif current_vol > 0.55:
        sentiment = "中性"
        base_signal = "Put/Call比率处于正常区间，市场情绪平稳，无明显方向性信号"
        risk_level = "low"
    elif current_vol > 0.40:
        sentiment = "中性偏乐观"
        base_signal = "Put/Call比率偏低，市场情绪较为乐观，但需警惕过度乐观"
        risk_level = "low"
    elif current_vol > 0.30:
        sentiment = "乐观"
        base_signal = "Put/Call比率处于低位，市场情绪乐观，投资者偏好风险资产，但需注意回调风险"
        risk_level = "medium"
    else:
        sentiment = "极度乐观"
        base_signal = "Put/Call比率极低，市场过度乐观，卖盘保护严重不足，大幅回调风险显著增加"
        risk_level = "high"

    # 结合趋势调整
    if trend_strength in ('strong_up',) and '恐慌' in sentiment:
        signal = f"{base_signal}。同时Put/Call比率持续上升，恐慌情绪可能进一步加剧，建议减仓观望。"
    elif trend_strength in ('strong_up',) and '乐观' in sentiment:
        signal = f"{base_signal}。但Put/Call比率正在快速上升，情绪可能正在转向谨慎，建议密切关注。"
    elif trend_strength in ('strong_down',) and '恐慌' in sentiment:
        signal = f"{base_signal}。Put/Call比率回落，恐慌情绪正在缓解，可能迎来修复行情。"
    elif trend_strength in ('strong_down',) and '乐观' in sentiment:
        signal = f"{base_signal}。Put/Call比率持续下降，市场可能过度乐观，建议逐步减仓锁定利润。"
    else:
        signal = base_signal

    return sentiment, signal, risk_level


def _detect_extremes(
    current_vol: float, current_oi: float,
    percentile_vol: float, std_20d_vol: float, n: int,
) -> List[Dict]:
    """检测极端值"""
    extremes = []
    
    if current_vol > 1.1:
        extremes.append({
            "type": "warning",
            "message": f"成交量Put/Call比率处于极端高位({current_vol:.3f})，市场恐慌情绪浓重，可能接近阶段性底部"
        })
    elif current_vol > 0.95:
        extremes.append({
            "type": "caution",
            "message": f"成交量Put/Call比率偏高({current_vol:.3f})，市场避险情绪上升"
        })
    
    if current_vol < 0.35:
        extremes.append({
            "type": "warning",
            "message": f"成交量Put/Call比率极低({current_vol:.3f})，市场过度乐观，回调风险加大"
        })
    elif current_vol < 0.45:
        extremes.append({
            "type": "caution",
            "message": f"成交量Put/Call比率偏低({current_vol:.3f})，市场情绪偏乐观"
        })
    
    if current_oi > 1.0:
        extremes.append({
            "type": "info",
            "message": f"持仓量Put/Call比率偏高({current_oi:.3f})，中长期看跌保护需求增加"
        })
    
    if n >= 20 and std_20d_vol > 0.12:
        extremes.append({
            "type": "info",
            "message": f"Put/Call比率波动率偏高({std_20d_vol:.3f})，市场情绪不稳定"
        })
    
    if percentile_vol > 90:
        extremes.append({
            "type": "warning",
            "message": f"当前Put/Call比率处于历史 {percentile_vol:.0f}% 分位，处于极高水平"
        })
    elif percentile_vol < 10:
        extremes.append({
            "type": "warning",
            "message": f"当前Put/Call比率处于历史 {percentile_vol:.0f}% 分位，处于极低水平"
        })
    
    return extremes


def _generate_sse_report(
    current_vol: float, current_oi: float,
    avg_5d_vol: float, avg_20d_vol: float,
    sentiment: str, signal: str, trend: str,
    percentile_vol: float, percentile_oi: float,
    records: List[Dict], recent_history: List[Dict],
    extremes: List[Dict],
) -> Dict[str, Any]:
    """生成每日分析报告"""
    sections = []

    # 1. 概况
    underlying_names = [r["underlying_name"] for r in records]
    sections.append({
        "title": "当前概况",
        "content": (
            f"截至最新交易日，上交所ETF期权成交量Put/Call比率为 {current_vol:.3f}，"
            f"持仓量Put/Call比率为 {current_oi:.3f}。"
            f"市场情绪处于「{sentiment}」状态，当前值处于历史 {percentile_vol:.0f}% 分位水平。"
            f"跟踪标的：{'、'.join(underlying_names)}。"
        ),
    })

    # 2. 趋势分析
    sections.append({
        "title": "趋势分析",
        "content": (
            f"成交量Put/Call比率近5日均值为 {avg_5d_vol:.3f}，20日均值为 {avg_20d_vol:.3f}，"
            f"短期趋势为「{trend}」。"
            f"成交量与持仓量比率{'一致' if (current_vol > 0.7) == (current_oi > 0.7) else '出现分化'}，"
            f"{'市场观点较为统一' if (current_vol > 0.7) == (current_oi > 0.7) else '短期交易情绪与中长期持仓情绪存在分歧'}。"
        ),
    })

    # 3. 各标的分析
    underlying_detail = ""
    for r in records:
        vol_ratio = r["pc_ratio_volume"]
        oi_ratio = r["pc_ratio_oi"]
        vol_tag = "恐慌" if vol_ratio > 0.9 else ("偏空" if vol_ratio > 0.75 else ("中性" if vol_ratio > 0.55 else "乐观"))
        underlying_detail += (
            f"  - {r['underlying_name']}({r['underlying_code']})：成交量P/C={vol_ratio:.3f}({vol_tag})，"
            f"持仓量P/C={oi_ratio:.3f}，"
            f"认购{format_num(r['call_volume'])}/认沽{format_num(r['put_volume'])}\n"
        )
    sections.append({
        "title": "各标的分析",
        "content": f"各标的Put/Call比率详情：\n{underlying_detail}",
    })

    # 4. 极端情况
    if extremes:
        for ext in extremes:
            sections.append({
                "title": "风险提示" if ext["type"] == "warning" else "关注事项",
                "content": ext["message"],
            })

    # 5. 操作建议
    advice = _generate_sse_advice(sentiment, trend, risk_level="medium")
    sections.append({
        "title": "操作建议",
        "content": advice,
    })

    return {
        "sections": sections,
        "generated_at": datetime.now().isoformat(),
    }


def _generate_sse_advice(sentiment: str, trend: str, risk_level: str) -> str:
    """生成A股期权操作建议"""
    if "恐慌" in sentiment and trend in ("上升", "显著上升"):
        return (
            "市场处于恐慌且趋势恶化阶段，建议：\n"
            "1. 降低仓位至防御水平（建议30-50%仓位）\n"
            "2. 关注上证50、沪深300ETF期权Put/Call拐点信号\n"
            "3. 等待Put/Call比率回落至0.8以下再考虑加仓\n"
            "4. 可关注认沽期权波动率变化，判断恐慌是否见顶"
        )
    elif "恐慌" in sentiment and trend in ("下降", "显著下降"):
        return (
            "恐慌情绪正在缓解，可考虑逢低布局：\n"
            "1. 分批次小幅加仓（每次5-10%仓位）\n"
            "2. 优先关注超跌优质标的（沪深300/上证50成分股）\n"
            "3. 设置严格止损（建议5-8%）\n"
            "4. 等待Put/Call比率回到0.7以下确认情绪修复"
        )
    elif "乐观" in sentiment and trend in ("上升", "显著上升"):
        return (
            "市场情绪正在从乐观转向谨慎：\n"
            "1. 适当减仓锁定利润（建议减至50-60%仓位）\n"
            "2. 关注是否有重大利空事件驱动\n"
            "3. 若Put/Call比率突破0.85，进一步降低风险敞口"
        )
    elif "乐观" in sentiment and trend in ("下降", "显著下降"):
        return (
            "市场情绪持续乐观，但需警惕过度自信：\n"
            "1. 保持正常仓位，但设置移动止盈\n"
            "2. 关注Put/Call比率是否跌破0.35（极端信号）\n"
            "3. 建议配置部分对冲头寸以防突发风险\n"
            "4. 关注期权隐含波动率变化，判断市场是否过热"
        )
    elif "中性" in sentiment:
        return (
            "市场情绪中性，可按正常策略操作：\n"
            "1. 维持现有仓位，关注方向性突破信号\n"
            "2. 关注Put/Call比率突破0.80或跌破0.50的方向选择\n"
            "3. 结合股指期货升贴水、北向资金等指标综合判断\n"
            "4. 保持灵活，随时准备应对方向性变化"
        )
    else:
        return (
            "建议持续关注Put/Call比率变化：\n"
            "1. 关注5日与20日均线的交叉信号\n"
            "2. 极端值（>1.0或<0.35）通常预示反转机会\n"
            "3. 结合成交量与持仓量比率差异判断情绪持续性"
        )


def get_sse_history(days: int = 30) -> Dict[str, Any]:
    """获取SSE期权历史数据"""
    history = _load_history()
    daily = _compute_daily_summary(history)
    return {
        "data": daily[-days:],
        "total_days": len(daily),
        "source": "上交所 (SSE) via AKShare",
        "fetched_at": datetime.now().isoformat(),
    }


def get_sse_tracking() -> Dict[str, Any]:
    """获取SSE Put/Call持续跟踪报告"""
    analysis = get_sse_put_call_analysis()
    if "error" in analysis:
        return analysis

    history = _load_history()
    daily = _compute_daily_summary(history)

    # 计算日度变化
    daily_change = {}
    if len(daily) >= 2:
        prev = daily[-2]
        curr = daily[-1]
        vol_change = curr["pc_ratio_volume"] - prev["pc_ratio_volume"]
        oi_change = curr["pc_ratio_oi"] - prev["pc_ratio_oi"]
        daily_change = {
            "vol_change": round(vol_change, 4),
            "vol_change_pct": round(vol_change / max(prev["pc_ratio_volume"], 0.001) * 100, 1),
            "oi_change": round(oi_change, 4),
            "oi_change_pct": round(oi_change / max(prev["pc_ratio_oi"], 0.001) * 100, 1),
            "prev_date": prev["date"],
        }

    # 累积信号
    cumulative_signals = []
    if len(daily) >= 5:
        recent_vol = [d["pc_ratio_volume"] for d in daily[-5:]]
        if all(recent_vol[i] > recent_vol[i - 1] for i in range(1, len(recent_vol))):
            cumulative_signals.append({
                "type": "连续上升",
                "days": 5,
                "level": "warning",
                "detail": "成交量Put/Call比率连续5日上升，恐慌情绪持续累积",
            })
        elif all(recent_vol[i] < recent_vol[i - 1] for i in range(1, len(recent_vol))):
            cumulative_signals.append({
                "type": "连续下降",
                "days": 5,
                "level": "info",
                "detail": "成交量Put/Call比率连续5日下降，市场情绪持续改善",
            })

    if len(daily) >= 3:
        recent_oi = [d["pc_ratio_oi"] for d in daily[-3:]]
        if all(recent_oi[i] > recent_oi[i - 1] for i in range(1, len(recent_oi))):
            cumulative_signals.append({
                "type": "OI连续上升",
                "days": 3,
                "level": "caution",
                "detail": "持仓量Put/Call比率连续3日上升，中长期对冲需求增加",
            })

    # 趋势数据
    trend_data = []
    for d in daily[-30:]:
        vol = d["pc_ratio_volume"]
        if vol > 0.9:
            sent = "恐慌"
        elif vol > 0.75:
            sent = "偏空"
        elif vol > 0.55:
            sent = "中性"
        else:
            sent = "乐观"
        trend_data.append({
            "date": d["date"],
            "pc_ratio_volume": d["pc_ratio_volume"],
            "pc_ratio_oi": d["pc_ratio_oi"],
            "call_volume": d["call_volume"],
            "put_volume": d["put_volume"],
            "sentiment": sent,
        })

    # 综合解读
    interpretation = _generate_interpretation(analysis, daily_change, cumulative_signals)

    return {
        "current": {
            "pc_ratio_volume": analysis["current_pc_ratio_volume"],
            "pc_ratio_oi": analysis["current_pc_ratio_oi"],
            "sentiment": analysis["sentiment"],
            "trend": analysis["trend"],
            "risk_level": analysis["risk_level"],
            "avg_5d_volume": analysis["avg_5d_volume"],
            "avg_20d_volume": analysis["avg_20d_volume"],
            "volatility_20d": analysis["volatility_20d"],
            "percentile_volume": analysis["percentile_volume"],
            "signal": analysis["signal"],
        },
        "daily_change": daily_change,
        "cumulative_signals": cumulative_signals,
        "trend_data": trend_data,
        "records": analysis["records"],
        "summary": analysis["summary"],
        "snapshot_count": len(daily),
        "interpretation": interpretation,
        "source": analysis["source"],
        "generated_at": datetime.now().isoformat(),
    }


def _generate_interpretation(analysis: Dict, daily_change: Dict, signals: List[Dict]) -> str:
    """生成综合解读"""
    parts = []
    sentiment = analysis["sentiment"]
    trend = analysis["trend"]
    current_vol = analysis["current_pc_ratio_volume"]
    current_oi = analysis["current_pc_ratio_oi"]

    parts.append(
        f"上交所ETF期权市场当前情绪处于「{sentiment}」状态。"
        f"成交量Put/Call比率为 {current_vol:.3f}，"
        f"持仓量Put/Call比率为 {current_oi:.3f}。"
    )

    if daily_change:
        vol_chg = daily_change.get("vol_change", 0)
        if vol_chg > 0:
            parts.append(f"较上一交易日上升 {vol_chg:.3f}（+{daily_change.get('vol_change_pct', 0)}%），市场避险情绪有所增加。")
        elif vol_chg < 0:
            parts.append(f"较上一交易日下降 {abs(vol_chg):.3f}（{daily_change.get('vol_change_pct', 0)}%），市场情绪有所改善。")

    parts.append(f"短期趋势为「{trend}」，近5日均值 {analysis['avg_5d_volume']:.3f}，20日均值 {analysis['avg_20d_volume']:.3f}。")

    if signals:
        signal_texts = [s["detail"] for s in signals]
        parts.append("累积信号：" + "；".join(signal_texts) + "。")

    # 结合各标的
    if analysis.get("records"):
        high_pc = [r for r in analysis["records"] if r["pc_ratio_volume"] > 0.85]
        if high_pc:
            names = [r["underlying_name"] for r in high_pc]
            parts.append(f"需要关注的高Put/Call标的：{'、'.join(names)}。")

    return "".join(parts)


def format_num(n: int) -> str:
    """格式化数字显示"""
    if abs(n) >= 1e8:
        return f"{n / 1e8:.2f}亿"
    if abs(n) >= 1e4:
        return f"{n / 1e4:.1f}万"
    return str(n)