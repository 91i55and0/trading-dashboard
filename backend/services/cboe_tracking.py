"""
CBOE Put/Call 比率持续跟踪服务
- 日度快照自动存档
- 日环比变化检测
- 多日累积信号（连续3/5/7日变化）
- 趋势拐点预警
- 持续跟踪解读报告
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np

from .cboe_service import get_put_call_analysis, get_put_call_data

# 内存缓存（避免短时间内重复请求）
_tracking_cache = None
_tracking_cache_time = 0

# 快照存档目录
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "cboe_snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 快照管理
# ============================================================================

def save_snapshot(analysis: dict) -> str:
    """保存当前分析为日度快照"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = SNAPSHOT_DIR / f"cboe_{date_str}.json"
    analysis["_saved_at"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, default=str)
    return str(path)


def load_snapshots(days: int = 30) -> List[dict]:
    """加载最近N天的历史快照"""
    files = sorted(SNAPSHOT_DIR.glob("cboe_*.json"), reverse=True)
    snapshots = []
    for fp in files[:days]:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                snapshots.append(json.load(f))
        except Exception:
            continue
    return snapshots


# ============================================================================
# 日度变化检测
# ============================================================================

def _daily_change(current: dict, previous: Optional[dict]) -> dict:
    """日度环比变化"""
    if not previous:
        return {}

    cr = current.get("current_ratio", 0)
    pr = previous.get("current_ratio", 0)

    return {
        "ratio_change": round(cr - pr, 4),
        "ratio_change_pct": round((cr - pr) / pr * 100, 2) if pr else 0,
        "sentiment_prev": previous.get("sentiment", ""),
        "sentiment_changed": current.get("sentiment") != previous.get("sentiment"),
        "trend_prev": previous.get("trend", ""),
        "trend_changed": current.get("trend") != previous.get("trend"),
        "risk_prev": previous.get("risk_level", ""),
        "risk_changed": current.get("risk_level") != previous.get("risk_level"),
    }


# ============================================================================
# 多日累积信号
# ============================================================================

def _cumulative_signals(snapshots: List[dict]) -> List[dict]:
    """多日累积信号检测"""
    signals = []
    if len(snapshots) < 3:
        return signals

    ratios = [s.get("current_ratio", 0) for s in snapshots]
    # snapshots 按时间倒序，取最近N天
    recent = ratios[:7]  # 最近7天

    # 连续上升/下降
    consecutive_up = 0
    consecutive_down = 0
    for i in range(len(recent) - 1):
        if recent[i] > recent[i + 1]:
            consecutive_up += 1
            consecutive_down = 0
        elif recent[i] < recent[i + 1]:
            consecutive_down += 1
            consecutive_up = 0
        else:
            consecutive_up = 0
            consecutive_down = 0

    if consecutive_up >= 5:
        signals.append({
            "type": "连续上升",
            "days": consecutive_up,
            "level": "warning",
            "detail": f"Put/Call 比率连续 {consecutive_up} 日上升，市场避险情绪持续升温，可能预示调整压力加大",
        })
    elif consecutive_up >= 3:
        signals.append({
            "type": "连续上升",
            "days": consecutive_up,
            "level": "caution",
            "detail": f"Put/Call 比率连续 {consecutive_up} 日上升，短期情绪转向谨慎",
        })

    if consecutive_down >= 5:
        signals.append({
            "type": "连续下降",
            "days": consecutive_down,
            "level": "warning",
            "detail": f"Put/Call 比率连续 {consecutive_down} 日下降，市场过度乐观，警惕回调风险",
        })
    elif consecutive_down >= 3:
        signals.append({
            "type": "连续下降",
            "days": consecutive_down,
            "level": "caution",
            "detail": f"Put/Call 比率连续 {consecutive_down} 日下降，市场情绪持续改善",
        })

    # 累积变化幅度
    if len(recent) >= 5:
        change_5d = recent[0] - recent[4]
        if abs(change_5d) > 0.15:
            direction = "上升" if change_5d > 0 else "下降"
            signals.append({
                "type": "大幅波动",
                "level": "warning",
                "detail": f"5日内 Put/Call 比率累计{direction} {abs(change_5d):.3f}，波动幅度显著，市场情绪剧烈变化",
            })

    # 突破关键阈值
    if recent[0] > 1.0 and recent[1] <= 1.0:
        signals.append({
            "type": "突破阈值",
            "level": "warning",
            "detail": "Put/Call 比率突破 1.0 关口，恐慌情绪蔓延，进入高风险区域",
        })
    elif recent[0] < 0.5 and recent[1] >= 0.5:
        signals.append({
            "type": "突破阈值",
            "level": "warning",
            "detail": "Put/Call 比率跌破 0.5 关口，市场过度乐观，回调风险显著增加",
        })

    # 5日与20日均线交叉
    if len(snapshots) >= 2:
        current_analysis = snapshots[0]
        avg_5d = current_analysis.get("avg_5d", 0)
        avg_20d = current_analysis.get("avg_20d", 0)
        if len(snapshots) >= 2:
            prev_analysis = snapshots[1]
            prev_5d = prev_analysis.get("avg_5d", 0)
            prev_20d = prev_analysis.get("avg_20d", 0)
            if prev_5d <= prev_20d and avg_5d > avg_20d:
                signals.append({
                    "type": "金叉信号",
                    "level": "info",
                    "detail": "5日均线上穿20日均线，短期情绪由冷转热，可能预示反弹机会",
                })
            elif prev_5d >= prev_20d and avg_5d < avg_20d:
                signals.append({
                    "type": "死叉信号",
                    "level": "warning",
                    "detail": "5日均线下穿20日均线，恐慌情绪加速蔓延，短期调整压力加大",
                })

    return signals


# ============================================================================
# 综合持续跟踪报告
# ============================================================================

def generate_tracking_report() -> Dict[str, Any]:
    """
    生成 CBOE Put/Call 比率持续跟踪报告
    包含：当前分析、历史快照、日度变化、累积信号、解读
    """
    global _tracking_cache, _tracking_cache_time

    # 60秒内存缓存，避免短时间内重复请求
    now = time.time()
    if _tracking_cache is not None and (now - _tracking_cache_time) < 60:
        return _tracking_cache

    # 获取最新分析
    current = get_put_call_analysis()
    save_snapshot(current)

    # 加载历史快照
    snapshots = load_snapshots(days=30)

    # 上一日
    previous = snapshots[1] if len(snapshots) >= 2 else None

    # 日度变化
    daily = _daily_change(current, previous)

    # 累积信号
    signals = _cumulative_signals(snapshots)

    # 生成趋势数据
    trend_data = []
    for s in reversed(snapshots):
        trend_data.append({
            "date": s.get("_saved_at", "")[:10],
            "ratio": s.get("current_ratio", 0),
            "equity_ratio": s.get("current_equity_ratio", 0),
            "index_ratio": s.get("current_index_ratio", 0),
            "avg_5d": s.get("avg_5d", 0),
            "avg_20d": s.get("avg_20d", 0),
            "sentiment": s.get("sentiment", ""),
        })

    # 生成综合解读
    interpretation = _generate_interpretation(current, daily, signals, snapshots)

    result = {
        "current": {
            "ratio": current.get("current_ratio"),
            "equity_ratio": current.get("current_equity_ratio"),
            "index_ratio": current.get("current_index_ratio"),
            "sentiment": current.get("sentiment"),
            "trend": current.get("trend"),
            "risk_level": current.get("risk_level"),
            "avg_5d": current.get("avg_5d"),
            "avg_20d": current.get("avg_20d"),
            "avg_30d": current.get("avg_30d"),
            "volatility_20d": current.get("volatility_20d"),
            "percentile": current.get("percentile"),
            "signal": current.get("signal"),
        },
        "daily_change": daily,
        "cumulative_signals": signals,
        "trend_data": trend_data,
        "snapshot_count": len(snapshots),
        "interpretation": interpretation,
        "source": current.get("source", "N/A"),
        "generated_at": datetime.now().isoformat(),
    }

    _tracking_cache = result
    _tracking_cache_time = now
    return result


def _generate_interpretation(
    current: dict, daily: dict, signals: List[dict], snapshots: List[dict]
) -> str:
    """生成综合解读报告"""
    parts = []

    ratio = current.get("current_ratio", 0)
    sentiment = current.get("sentiment", "")
    trend = current.get("trend", "")
    risk = current.get("risk_level", "")
    percentile = current.get("percentile", 50)

    # 1. 当前状态
    parts.append(f"当前 CBOE 总 Put/Call 比率为 {ratio:.3f}，处于历史 {percentile:.0f}% 分位")
    parts.append(f"市场情绪为「{sentiment}」，风险等级「{risk}」")

    # 2. 日度变化
    if daily:
        chg = daily.get("ratio_change", 0)
        if chg > 0.02:
            parts.append(f"较前日上升 {chg:.3f}，避险情绪升温")
        elif chg < -0.02:
            parts.append(f"较前日下降 {abs(chg):.3f}，情绪有所修复")
        else:
            parts.append("较前日变化不大，情绪稳定")

        if daily.get("sentiment_changed"):
            parts.append(f"情绪从「{daily['sentiment_prev']}」转为「{sentiment}」，市场心态发生转变")
        if daily.get("risk_changed"):
            parts.append(f"风险等级从「{daily['risk_prev']}」变为「{risk}」")

    # 3. 趋势判断
    avg_5d = current.get("avg_5d", 0)
    avg_20d = current.get("avg_20d", 0)
    parts.append(f"短期趋势「{trend}」，5日均值 {avg_5d:.3f} vs 20日均值 {avg_20d:.3f}")

    if avg_5d > avg_20d * 1.1:
        parts.append("短期均线显著高于长期均线，恐慌情绪积聚，关注情绪拐点")
    elif avg_5d < avg_20d * 0.9:
        parts.append("短期均线显著低于长期均线，市场过度乐观，需警惕回调风险")

    # 4. 累积信号
    if signals:
        for s in signals:
            if s.get("level") == "warning":
                parts.append(f"⚠️ {s['detail']}")
            elif s.get("level") == "caution":
                parts.append(s["detail"])
            else:
                parts.append(s["detail"])

    # 5. 波动率
    vol = current.get("volatility_20d", 0)
    if vol > 0.15:
        parts.append(f"20日波动率 {vol:.3f} 偏高，市场情绪不稳定，短期可能出现方向性选择")

    # 6. Equity vs Index
    eq = current.get("current_equity_ratio", 0)
    ix = current.get("current_index_ratio", 0)
    if eq > 0 and ix > 0:
        if eq > ix * 1.3:
            parts.append("个股期权 Put/Call 比率显著高于指数期权，个股层面避险需求更强")
        elif ix > eq * 1.3:
            parts.append("指数期权 Put/Call 比率显著高于个股期权，机构系统性对冲需求上升")

    # 7. 操作提示
    if risk == "high" and trend in ("上升", "显著上升"):
        parts.append("建议：高恐慌+趋势恶化，控制仓位至防御水平，等待情绪拐点确认")
    elif risk == "high" and trend in ("下降", "显著下降"):
        parts.append("建议：恐慌回落中，可分批试探性布局，但需严格止损")
    elif risk == "low" and trend in ("下降", "显著下降"):
        parts.append("建议：乐观情绪持续，但注意设置移动止盈，防范突发风险")
    else:
        parts.append("建议：维持正常仓位，关注 Put/Call 比率突破关键阈值的方向选择")

    return "。".join(parts) + "。"


# ============================================================================
# 单日快照对比
# ============================================================================

def get_daily_comparison(days: int = 7) -> Dict[str, Any]:
    """获取最近N天的日度对比数据"""
    snapshots = load_snapshots(days=days)

    comparisons = []
    for s in reversed(snapshots):
        comparisons.append({
            "date": s.get("_saved_at", "")[:10],
            "ratio": s.get("current_ratio", 0),
            "sentiment": s.get("sentiment", ""),
            "trend": s.get("trend", ""),
            "risk_level": s.get("risk_level", ""),
            "avg_5d": s.get("avg_5d", 0),
            "avg_20d": s.get("avg_20d", 0),
            "signal": s.get("signal", ""),
        })

    return {
        "days": days,
        "comparisons": comparisons,
        "generated_at": datetime.now().isoformat(),
    }