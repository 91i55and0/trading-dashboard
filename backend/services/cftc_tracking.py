"""
CFTC 持续跟踪报告服务
- 历史快照自动存档
- 周度环比变化检测
- 趋势加速/减速/拐点信号
- 持续跟踪解读报告
"""
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np

from .cftc_service import get_latest_cftc_report, TFF_CONTRACTS, DISAGG_CONTRACTS

# 内存缓存
_cftc_tracking_cache = None
_cftc_tracking_cache_time = 0

# 快照存档目录
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "cftc_snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 快照管理
# ============================================================================

def _snapshot_path(report_date: str) -> Path:
    return SNAPSHOT_DIR / f"cftc_{report_date}.json"


def save_snapshot(report: dict) -> str:
    """保存当前报告为历史快照"""
    report_date = report.get("report_date", datetime.now().strftime("%Y-%m-%d"))
    path = _snapshot_path(report_date)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, default=str)
    return str(path)


def load_snapshots(weeks: int = 12) -> List[dict]:
    """加载最近N周的历史快照"""
    files = sorted(SNAPSHOT_DIR.glob("cftc_*.json"), reverse=True)
    snapshots = []
    for fp in files[:weeks]:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                snapshots.append(json.load(f))
        except Exception:
            continue
    return snapshots


# ============================================================================
# 单项品种变化分析
# ============================================================================

def _analyze_instrument_trend(
    current: dict, previous: Optional[dict], snapshots: List[dict]
) -> dict:
    """分析单个品种的持仓趋势"""
    name = current.get("instrument", "")
    result = {
        "instrument": name,
        "section": current.get("section", ""),
        "trader_type": current.get("trader_type", ""),
        "current": {
            "net": current.get("net", 0),
            "long": current.get("long", 0),
            "short": current.get("short", 0),
            "net_z": current.get("net_z"),
            "flow_state": current.get("flow_state", ""),
            "crowding": current.get("crowding", {}),
        },
        "changes": {},
        "trend_signals": [],
        "interpretation": "",
    }

    # 周度环比变化
    if previous:
        result["changes"] = {
            "net_ww": current.get("net", 0) - previous.get("net", 0),
            "long_ww": current.get("long", 0) - previous.get("long", 0),
            "short_ww": current.get("short", 0) - previous.get("short", 0),
            "net_z_ww": (current.get("net_z") or 0) - (previous.get("net_z") or 0),
            "flow_prev": previous.get("flow_state", ""),
        }

    # 4周趋势分析
    if len(snapshots) >= 2:
        net_series = []
        for s in snapshots:
            all_items = s.get("tff_items", []) + s.get("disagg_items", [])
            for item in all_items:
                if item.get("instrument") == name:
                    net_series.append(item.get("net", 0))
                    break
            else:
                net_series.append(None)

        net_series = [x for x in net_series if x is not None]
        if len(net_series) >= 3:
            # 连续方向检测
            diffs = [net_series[i] - net_series[i + 1] for i in range(len(net_series) - 1)]
            consecutive_up = 0
            consecutive_down = 0
            for d in diffs:
                if d > 0:
                    consecutive_up += 1
                    consecutive_down = 0
                elif d < 0:
                    consecutive_down += 1
                    consecutive_up = 0
                else:
                    consecutive_up = 0
                    consecutive_down = 0

            if consecutive_up >= 3:
                result["trend_signals"].append({
                    "type": "连续增持",
                    "weeks": consecutive_up,
                    "detail": f"连续 {consecutive_up} 周净多增持，趋势强化中",
                })
            elif consecutive_down >= 3:
                result["trend_signals"].append({
                    "type": "连续减持",
                    "weeks": consecutive_down,
                    "detail": f"连续 {consecutive_down} 周净多减持，趋势恶化中",
                })

            # 趋势加速/减速
            if len(diffs) >= 3:
                recent = abs(diffs[0])
                older = abs(diffs[-1]) if len(diffs) >= 2 else 0
                if older > 0 and recent > older * 1.5:
                    direction = "增持" if diffs[0] > 0 else "减持"
                    result["trend_signals"].append({
                        "type": "趋势加速",
                        "detail": f"{direction}速度加快，近周变化幅度为前周 {recent / older:.1f} 倍",
                    })
                elif older > 0 and recent < older * 0.5 and recent > 0:
                    result["trend_signals"].append({
                        "type": "趋势减速",
                        "detail": "持仓变化幅度收窄，动能减弱，可能接近拐点",
                    })

            # 拐点检测
            if len(diffs) >= 3:
                if diffs[0] > 0 and diffs[1] < 0 and diffs[2] < 0:
                    result["trend_signals"].append({
                        "type": "拐点信号",
                        "detail": "最新一周由减转增，可能形成持仓拐点，关注后续确认",
                    })
                elif diffs[0] < 0 and diffs[1] > 0 and diffs[2] > 0:
                    result["trend_signals"].append({
                        "type": "拐点信号",
                        "detail": "最新一周由增转减，多头动能逆转，关注风险",
                    })

    # 生成解读文案
    result["interpretation"] = _generate_instrument_interpretation(result)

    return result


def _generate_instrument_interpretation(analysis: dict) -> str:
    """为单个品种生成解读文案"""
    name = analysis["instrument"]
    cur = analysis["current"]
    chg = analysis.get("changes", {})
    crowding = cur.get("crowding", {})
    flow = cur.get("flow_state", "")
    signals = analysis.get("trend_signals", [])

    parts = []

    # 1. 当前持仓状态
    if cur["net"] > 0:
        parts.append(f"{name}当前为净多头（{cur['net']:,}手）")
    elif cur["net"] < 0:
        parts.append(f"{name}当前为净空头（{cur['net']:,}手）")
    else:
        parts.append(f"{name}当前多空均衡")

    # 2. 拥挤度
    if crowding.get("label"):
        parts.append(f"处于{crowding['label']}区间，{'需关注反转风险' if crowding['level'] == 'extreme' else '持仓偏拥挤'}")

    # 3. 资金流向
    if flow:
        parts.append(f"资金流向为「{flow}」")

    # 4. 周度变化
    if chg:
        net_ww = chg.get("net_ww", 0)
        if net_ww > 1000:
            parts.append(f"本周净多增持 {net_ww:,} 手")
        elif net_ww < -1000:
            parts.append(f"本周净多减持 {abs(net_ww):,} 手")

        if chg.get("flow_prev") and chg["flow_prev"] != flow and flow:
            parts.append(f"资金流向从「{chg['flow_prev']}」转为「{flow}」")

    # 5. 趋势信号综合
    if signals:
        signal_types = [s["type"] for s in signals]
        if "连续增持" in signal_types:
            parts.append("连续增持显示多头信心持续增强，趋势延续概率较高")
        elif "连续减持" in signal_types:
            parts.append("连续减持显示多头信心持续减弱，趋势转弱风险加大")
        if "拐点信号" in signal_types:
            parts.append("出现拐点信号，需密切关注下周数据确认方向")
        if "趋势加速" in signal_types:
            parts.append("趋势正在加速，短期动量较强")
        if "趋势减速" in signal_types:
            parts.append("趋势动能减弱，持仓变化趋于收敛，可能面临方向选择")

    return "。".join(parts) + "。"


# ============================================================================
# 板块级别分析
# ============================================================================

def _analyze_section_trend(
    current_items: List[dict], previous_items: Optional[List[dict]]
) -> dict:
    """板块级别持仓趋势分析"""
    sections = {}
    for item in current_items:
        sec = item.get("section", "其他")
        if sec not in sections:
            sections[sec] = {"net_total": 0, "count": 0, "bull": 0, "bear": 0}
        sections[sec]["net_total"] += item.get("net", 0)
        sections[sec]["count"] += 1
        if item.get("net", 0) > 0:
            sections[sec]["bull"] += 1
        elif item.get("net", 0) < 0:
            sections[sec]["bear"] += 1

    if previous_items:
        prev_sections = {}
        for item in previous_items:
            sec = item.get("section", "其他")
            if sec not in prev_sections:
                prev_sections[sec] = {"net_total": 0, "count": 0}
            prev_sections[sec]["net_total"] += item.get("net", 0)
            prev_sections[sec]["count"] += 1

        for sec, data in sections.items():
            prev = prev_sections.get(sec, {})
            data["net_change"] = data["net_total"] - prev.get("net_total", 0)

    return sections


# ============================================================================
# 综合持续跟踪报告
# ============================================================================

def generate_tracking_report(force_refresh: bool = False) -> Dict[str, Any]:
    """
    生成 CFTC 持续跟踪报告
    包含：当前快照、历史快照、周度变化、趋势信号、解读
    """
    # 获取最新数据（同时保存快照）
    current = get_latest_cftc_report(force_refresh=force_refresh)
    if current:
        save_snapshot(current)

    report_date = current.get("report_date", "N/A")

    # 加载历史快照
    snapshots = load_snapshots(weeks=12)
    previous = snapshots[1] if len(snapshots) >= 2 else None

    # 当前与上周的 items
    current_tff = current.get("tff_items", [])
    current_disagg = current.get("disagg_items", [])
    current_all = current_tff + current_disagg

    prev_tff = previous.get("tff_items", []) if previous else []
    prev_disagg = previous.get("disagg_items", []) if previous else []
    prev_all = prev_tff + prev_disagg

    # 建立品种索引
    def _index(items):
        return {item.get("instrument", ""): item for item in items}

    prev_idx = _index(prev_all)

    # 逐个品种分析
    instrument_analysis = []
    for item in current_all:
        prev_item = prev_idx.get(item.get("instrument"))
        analysis = _analyze_instrument_trend(item, prev_item, snapshots)
        instrument_analysis.append(analysis)

    # 板块分析
    section_analysis = _analyze_section_trend(current_all, prev_all if previous else None)

    # 汇总信号
    all_signals = []
    for ia in instrument_analysis:
        all_signals.extend(ia["trend_signals"])

    # 生成综合解读
    summary_interpretation = _generate_summary_interpretation(
        current, previous, instrument_analysis, section_analysis, all_signals
    )

    return {
        "report_date": report_date,
        "previous_report_date": previous.get("report_date") if previous else None,
        "snapshot_count": len(snapshots),
        "instrument_analysis": instrument_analysis,
        "section_analysis": section_analysis,
        "aggregate_signals": all_signals,
        "summary": current.get("analysis", {}).get("summary", {}),
        "summary_interpretation": summary_interpretation,
        "source": current.get("source", "N/A"),
        "generated_at": datetime.now().isoformat(),
    }


def _generate_summary_interpretation(
    current: dict, previous: Optional[dict],
    instrument_analysis: List[dict], section_analysis: dict,
    all_signals: List[dict],
) -> str:
    """生成综合解读报告"""
    parts = []
    report_date = current.get("report_date", "")

    # 1. 总体概况
    summary = current.get("analysis", {}).get("summary", {})
    total = summary.get("total_instruments", 0)
    net_bull = summary.get("net_bull", 0)
    net_bear = summary.get("net_bear", 0)
    extreme = summary.get("extreme_count", 0)
    crowded = summary.get("crowded_count", 0)

    parts.append(f"截至 {report_date}，CFTC 持仓报告覆盖 {total} 个品种")
    parts.append(f"其中净多头 {net_bull} 个、净空头 {net_bear} 个")

    if extreme > 0:
        parts.append(f"⚠️ {extreme} 个品种处于极端拥挤区间，需高度关注反转风险")
    if crowded > 0:
        parts.append(f"{crowded} 个品种处于拥挤区间")

    # 2. 板块对比
    if section_analysis:
        sec_parts = []
        for sec, data in section_analysis.items():
            direction = "偏多" if data["bull"] > data["bear"] else "偏空" if data["bear"] > data["bull"] else "中性"
            chg = data.get("net_change", 0)
            chg_text = ""
            if chg > 10000:
                chg_text = "，净多大幅增加"
            elif chg < -10000:
                chg_text = "，净多大幅减少"
            elif chg > 0:
                chg_text = "，净多小幅增加"
            elif chg < 0:
                chg_text = "，净多小幅减少"
            sec_parts.append(f"{sec}板块整体{direction}{chg_text}")
        parts.append("；".join(sec_parts))

    # 3. 关键信号汇总
    if all_signals:
        signal_types = {}
        for s in all_signals:
            t = s["type"]
            signal_types[t] = signal_types.get(t, 0) + 1

        sig_parts = []
        for st, count in signal_types.items():
            if st == "连续增持":
                sig_parts.append(f"{count} 个品种连续增持，多头趋势延续")
            elif st == "连续减持":
                sig_parts.append(f"{count} 个品种连续减持，空头压力加大")
            elif st == "拐点信号":
                sig_parts.append(f"{count} 个品种出现持仓拐点信号")
            elif st == "趋势加速":
                sig_parts.append(f"{count} 个品种持仓变化加速")
            elif st == "趋势减速":
                sig_parts.append(f"{count} 个品种持仓动能减弱")
        parts.append("；".join(sig_parts))

    # 4. 重要品种变化
    significant_changes = []
    for ia in instrument_analysis:
        chg = ia.get("changes", {})
        net_ww = chg.get("net_ww", 0)
        if abs(net_ww) > 5000:
            direction = "大幅增持" if net_ww > 0 else "大幅减持"
            significant_changes.append(f"{ia['instrument']}{direction}（{abs(net_ww):,}手）")

    if significant_changes:
        parts.append("重要变化：" + "；".join(significant_changes[:5]))

    # 5. 风险提示
    if extreme >= 3:
        parts.append("⚠️ 多个品种处于极端拥挤，市场可能出现系统性持仓调整，建议控制风险敞口")
    if crowded >= 5:
        parts.append("多数品种持仓偏拥挤，市场分歧加大，短期波动可能加剧")

    return "。".join(parts) + "。"


# ============================================================================
# 单品种持续跟踪
# ============================================================================

def get_instrument_tracking(instrument: str, weeks: int = 12) -> Dict[str, Any]:
    """获取单个品种的持续跟踪数据"""
    snapshots = load_snapshots(weeks=weeks)

    records = []
    for s in reversed(snapshots):
        all_items = s.get("tff_items", []) + s.get("disagg_items", [])
        for item in all_items:
            if item.get("instrument") == instrument:
                records.append({
                    "date": s.get("report_date", ""),
                    "net": item.get("net", 0),
                    "long": item.get("long", 0),
                    "short": item.get("short", 0),
                    "net_z": item.get("net_z"),
                    "flow_state": item.get("flow_state", ""),
                    "crowding": item.get("crowding", {}),
                })
                break

    # 趋势计算
    trend = "震荡"
    if len(records) >= 4:
        nets = [r["net"] for r in records[-4:]]
        if all(nets[i] > nets[i - 1] for i in range(1, len(nets))):
            trend = "持续增持"
        elif all(nets[i] < nets[i - 1] for i in range(1, len(nets))):
            trend = "持续减持"
        elif nets[-1] > nets[0]:
            trend = "震荡偏多"
        elif nets[-1] < nets[0]:
            trend = "震荡偏空"

    current = records[-1] if records else None

    return {
        "instrument": instrument,
        "weeks": weeks,
        "records": records,
        "trend": trend,
        "current": current,
        "generated_at": datetime.now().isoformat(),
    }