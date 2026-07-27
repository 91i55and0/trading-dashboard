"""
CBOE Put/Call 比率服务
数据来源: CBOE 旧版市场统计页面 (ww2.cboe.com)
https://ww2.cboe.com/us/options/market_statistics/

包含: 日内Put/Call比率跟踪、历史趋势、情绪分析、每日分析报告
"""
import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ============================================================================
# CBOE DATA ENDPOINTS
# ============================================================================

# CBOE 旧版市场统计页面（可用，返回 HTML 表格）
# 使用 ?iframe=1 参数获得更简洁的表格结构（4个表格：市场份额、Total、Index、Equity）
CBOE_WW2_URL = "https://ww2.cboe.com/us/options/market_statistics/?iframe=1"

# CBOE 新版市场统计页面（Next.js SPA，数据嵌入 RSC payload）
CBOE_MARKET_STATS_URL = "https://www.cboe.com/markets/us/options/market-statistics"


# ============================================================================
# DATA FETCHING
# ============================================================================

def _fetch_cboe_ww2_tables() -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]]:
    """
    从 ww2.cboe.com 旧版页面获取 Put/Call 比率表格数据
    
    返回: (total_df, index_df, equity_df, report_date) 或 None
    - total_df: 综合期权 Put/Call 数据
    - index_df: 指数期权 Put/Call 数据
    - equity_df: 个股期权 Put/Call 数据
    - report_date: 报告日期字符串
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        resp = requests.get(CBOE_WW2_URL, headers=headers, timeout=8)
        if resp.status_code != 200:
            logger.warning(f"ww2.cboe.com 请求失败: {resp.status_code}")
            return None

        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        # 提取报告日期
        report_date = datetime.now().strftime('%Y-%m-%d')
        title_tag = soup.find('title')
        if title_tag:
            # 标题格式: "Cboe Exchange Market Statistics for Friday, July 24, 2026"
            date_match = re.search(
                r'(\w+day)?,?\s*(\w+)\s+(\d{1,2}),?\s*(\d{4})',
                title_tag.text
            )
            if date_match:
                try:
                    date_str = f"{date_match.group(2)} {date_match.group(3)}, {date_match.group(4)}"
                    report_date = datetime.strptime(date_str, '%B %d, %Y').strftime('%Y-%m-%d')
                except ValueError:
                    pass

        # 解析所有表格，通过表头内容识别 Put/Call 表格
        tables = soup.find_all('table')

        def parse_pc_table(table) -> Optional[pd.DataFrame]:
            """解析 Put/Call 比率表格"""
            rows = table.find_all('tr')
            data_rows = []
            for row in rows:
                cols = row.find_all(['td', 'th'])
                cols_text = [c.get_text(strip=True) for c in cols]
                if len(cols_text) >= 5 and cols_text[0] and 'TIME' not in cols_text[0].upper():
                    try:
                        time_str = cols_text[0]
                        calls = int(cols_text[1].replace(',', ''))
                        puts = int(cols_text[2].replace(',', ''))
                        total = int(cols_text[3].replace(',', ''))
                        pc_ratio = float(cols_text[4])
                        data_rows.append({
                            'time': time_str,
                            'calls': calls,
                            'puts': puts,
                            'total_volume': total,
                            'pc_ratio': pc_ratio,
                        })
                    except (ValueError, IndexError):
                        continue

            if not data_rows:
                return None
            return pd.DataFrame(data_rows)

        def is_pc_table(table) -> bool:
            """检查表格是否为 Put/Call 比率表格"""
            header = table.find('tr')
            if header:
                header_text = ' '.join([
                    c.get_text(strip=True) for c in header.find_all(['td', 'th'])
                ])
                return 'P/C RATIO' in header_text.upper()
            return False

        # 找出所有 Put/Call 表格
        pc_tables = [t for t in tables if is_pc_table(t)]

        if len(pc_tables) < 1:
            logger.warning(f"ww2.cboe.com 未找到 Put/Call 表格: 总表格={len(tables)}")
            return None

        # 根据表格标题识别类型
        total_df = None
        index_df = None
        equity_df = None

        for table in pc_tables:
            # 查找表格前的标题
            prev_elem = table.find_previous(['h2', 'h3', 'h4', 'b', 'strong'])
            title = prev_elem.get_text(strip=True).lower() if prev_elem else ''

            df = parse_pc_table(table)
            if df is None:
                continue

            if 'index' in title:
                index_df = df
            elif 'equity' in title:
                equity_df = df
            else:
                # 第一个匹配的作为 total
                if total_df is None:
                    total_df = df
                elif index_df is None:
                    index_df = df
                elif equity_df is None:
                    equity_df = df

        if total_df is None:
            # 如果没能通过标题识别，使用索引顺序：第一个是 Total，第二个是 Index，第三个是 Equity
            for i, table in enumerate(pc_tables):
                df = parse_pc_table(table)
                if df is not None:
                    if i == 0:
                        total_df = df
                    elif i == 1:
                        index_df = df
                    elif i == 2:
                        equity_df = df

        if total_df is None:
            logger.warning("无法解析 Total Put/Call 表格")
            return None

        logger.info(
            f"CBOE ww2 数据获取成功: date={report_date}, "
            f"total_rows={len(total_df)}, index_rows={len(index_df) if index_df is not None else 0}, "
            f"equity_rows={len(equity_df) if equity_df is not None else 0}"
        )
        return total_df, index_df, equity_df, report_date

    except Exception as e:
        logger.warning(f"获取 ww2.cboe.com 数据失败: {e}")
        return None


def _fetch_cboe_web_data() -> Optional[Dict[str, Any]]:
    """从 ww2.cboe.com 网页抓取最新的 Put/Call 比率摘要数据"""
    result = _fetch_cboe_ww2_tables()
    if result is None:
        return None

    total_df, index_df, equity_df, report_date = result

    # 提取最新一行数据
    data = {'report_date': report_date}

    if total_df is not None and not total_df.empty:
        latest = total_df.iloc[-1]
        data['total_put_call_ratio'] = float(latest['pc_ratio'])
        data['total_calls'] = int(latest['calls'])
        data['total_puts'] = int(latest['puts'])
        data['total_volume'] = int(latest['total_volume'])
        data['latest_time'] = str(latest['time'])

    if index_df is not None and not index_df.empty:
        latest = index_df.iloc[-1]
        data['index_put_call_ratio'] = float(latest['pc_ratio'])
        data['index_calls'] = int(latest['calls'])
        data['index_puts'] = int(latest['puts'])

    if equity_df is not None and not equity_df.empty:
        latest = equity_df.iloc[-1]
        data['equity_put_call_ratio'] = float(latest['pc_ratio'])
        data['equity_calls'] = int(latest['calls'])
        data['equity_puts'] = int(latest['puts'])

    return data


# ============================================================================
# 核心服务函数
# ============================================================================

def get_put_call_data(days: int = 30) -> Dict[str, Any]:
    """
    获取CBOE Put/Call比率数据
    从 ww2.cboe.com 获取真实数据，失败则抛出异常
    """
    data = []
    intraday = []
    source = "未知"
    report_date = datetime.now().strftime('%Y-%m-%d')

    try:
        result = _fetch_cboe_ww2_tables()
        if result is not None:
            total_df, index_df, equity_df, report_date = result
            source = "CBOE ww2"

            # 提取最新汇总数据
            if total_df is not None and not total_df.empty:
                latest = total_df.iloc[-1]
                data.append({
                    "date": report_date,
                    "total_put_call_ratio": float(latest['pc_ratio']),
                    "equity_put_call_ratio": float(equity_df.iloc[-1]['pc_ratio']) if equity_df is not None and not equity_df.empty else 0,
                    "index_put_call_ratio": float(index_df.iloc[-1]['pc_ratio']) if index_df is not None and not index_df.empty else 0,
                    "total_calls": int(latest['calls']),
                    "total_puts": int(latest['puts']),
                    "total_volume": int(latest['total_volume']),
                    "latest_time": str(latest['time']),
                })

                # 提取日内分时数据
                for _, row in total_df.iterrows():
                    intraday.append({
                        "time": str(row['time']),
                        "total_calls": int(row['calls']),
                        "total_puts": int(row['puts']),
                        "total_volume": int(row['total_volume']),
                        "total_pc_ratio": float(row['pc_ratio']),
                    })

                # 如果有 Index 和 Equity 分时数据，也加入
                if index_df is not None and not index_df.empty:
                    for i, row in index_df.iterrows():
                        if i < len(intraday):
                            intraday[i]['index_pc_ratio'] = float(row['pc_ratio'])
                            intraday[i]['index_calls'] = int(row['calls'])
                            intraday[i]['index_puts'] = int(row['puts'])

                if equity_df is not None and not equity_df.empty:
                    for i, row in equity_df.iterrows():
                        if i < len(intraday):
                            intraday[i]['equity_pc_ratio'] = float(row['pc_ratio'])
                            intraday[i]['equity_calls'] = int(row['calls'])
                            intraday[i]['equity_puts'] = int(row['puts'])

    except Exception as e:
        logger.warning(f"处理 CBOE ww2 数据失败: {e}")

    # 如果真实数据获取失败，抛出错误
    if not data:
        raise RuntimeError(
            "无法获取CBOE Put/Call比率数据：CBOE ww2 页面无法访问或数据解析失败。"
            "请检查网络连接，或稍后重试。"
        )

    return {
        "data": data,
        "intraday": intraday,
        "source": source,
        "report_date": report_date,
        "updated_at": datetime.now().isoformat(),
    }


def get_put_call_analysis() -> Dict[str, Any]:
    """
    Put/Call比率每日分析报告
    包含: 当前比率、移动平均、情绪判断、趋势分析、操作建议
    """
    pc_data = get_put_call_data(days=60)

    if not pc_data.get("data"):
        return {"error": "无法获取数据"}

    values = [d["total_put_call_ratio"] for d in pc_data["data"]]
    equity_values = [d.get("equity_put_call_ratio", 0) for d in pc_data["data"]]
    index_values = [d.get("index_put_call_ratio", 0) for d in pc_data["data"]]

    current = values[-1] if values else 0
    current_equity = equity_values[-1] if equity_values else 0
    current_index = index_values[-1] if index_values else 0

    # 移动平均
    avg_5d = float(np.mean(values[-5:])) if len(values) >= 5 else current
    avg_10d = float(np.mean(values[-10:])) if len(values) >= 10 else current
    avg_20d = float(np.mean(values[-20:])) if len(values) >= 20 else current
    avg_30d = float(np.mean(values[-30:])) if len(values) >= 30 else current

    # 波动率
    std_20d = float(np.std(values[-20:])) if len(values) >= 20 else 0

    # 当前值在历史中的分位
    percentile = float(sum(1 for v in values if v < current) / len(values) * 100) if values else 50

    # 趋势判断
    if avg_5d > avg_20d * 1.05:
        trend = "显著上升"
        trend_strength = "strong_up"
    elif avg_5d > avg_20d:
        trend = "上升"
        trend_strength = "up"
    elif avg_5d < avg_20d * 0.95:
        trend = "显著下降"
        trend_strength = "strong_down"
    elif avg_5d < avg_20d:
        trend = "下降"
        trend_strength = "down"
    else:
        trend = "横盘"
        trend_strength = "flat"

    # 情绪判断
    sentiment, signal, risk_level = _analyze_sentiment(current, avg_5d, avg_20d, percentile, trend_strength)

    # 极端值检测
    extremes = []
    if current > 1.3:
        extremes.append({'type': 'warning', 'message': 'Put/Call比率处于极端高位(>1.3)，市场恐慌情绪浓重，可能接近阶段性底部'})
    elif current > 1.1:
        extremes.append({'type': 'caution', 'message': 'Put/Call比率偏高(>1.1)，市场避险情绪上升'})
    if current < 0.45:
        extremes.append({'type': 'warning', 'message': 'Put/Call比率极低(<0.45)，市场过度乐观，回调风险加大'})
    elif current < 0.55:
        extremes.append({'type': 'caution', 'message': 'Put/Call比率偏低(<0.55)，市场情绪偏乐观'})

    if std_20d > 0.15:
        extremes.append({'type': 'info', 'message': f'Put/Call比率波动率偏高({std_20d:.3f})，市场情绪不稳定'})

    # 生成分析报告
    report = _generate_daily_report(
        current, current_equity, current_index,
        avg_5d, avg_10d, avg_20d, avg_30d,
        sentiment, signal, risk_level, trend,
        percentile, std_20d, extremes,
        pc_data["data"][-30:],
    )

    return {
        "current_ratio": round(current, 3),
        "current_equity_ratio": round(current_equity, 3),
        "current_index_ratio": round(current_index, 3),
        "avg_5d": round(avg_5d, 3),
        "avg_10d": round(avg_10d, 3),
        "avg_20d": round(avg_20d, 3),
        "avg_30d": round(avg_30d, 3),
        "volatility_20d": round(std_20d, 3),
        "percentile": round(percentile, 1),
        "sentiment": sentiment,
        "signal": signal,
        "risk_level": risk_level,
        "trend": trend,
        "trend_strength": trend_strength,
        "trend_detail": f"近5日均值({round(avg_5d, 3)}){'高于' if avg_5d > avg_20d else '低于'}20日均值({round(avg_20d, 3)})",
        "extremes": extremes,
        "report": report,
        "data": pc_data["data"][-30:],
        "source": pc_data.get("source", "未知"),
        "analysis_time": datetime.now().isoformat(),
    }


def _analyze_sentiment(
    current: float, avg_5d: float, avg_20d: float,
    percentile: float, trend_strength: str
) -> tuple:
    """分析市场情绪，返回 (sentiment, signal, risk_level)"""
    # 基本情绪判断
    if current > 1.2:
        sentiment = "极度恐慌"
        base_signal = "Put/Call比率处于极度高位，市场恐慌情绪严重，可能接近阶段性底部，但也需防范持续下跌风险"
        risk_level = "high"
    elif current > 1.0:
        sentiment = "恐慌"
        base_signal = "Put/Call比率高于1.0，市场恐慌情绪较浓，看跌期权需求旺盛，短期或有反弹机会"
        risk_level = "high"
    elif current > 0.85:
        sentiment = "偏空"
        base_signal = "Put/Call比率处于偏高区间，市场避险情绪上升，投资者偏向谨慎，注意控制仓位"
        risk_level = "medium"
    elif current > 0.7:
        sentiment = "中性偏谨慎"
        base_signal = "Put/Call比率处于正常偏高区间，市场保持谨慎但未出现恐慌"
        risk_level = "medium"
    elif current > 0.55:
        sentiment = "中性"
        base_signal = "Put/Call比率处于正常区间，市场情绪平稳，无明显方向性信号"
        risk_level = "low"
    elif current > 0.45:
        sentiment = "中性偏乐观"
        base_signal = "Put/Call比率偏低，市场情绪较为乐观，但需警惕过度乐观"
        risk_level = "low"
    elif current > 0.35:
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


def _generate_daily_report(
    current: float, current_equity: float, current_index: float,
    avg_5d: float, avg_10d: float, avg_20d: float, avg_30d: float,
    sentiment: str, signal: str, risk_level: str, trend: str,
    percentile: float, std_20d: float, extremes: list,
    recent_data: list,
) -> Dict[str, Any]:
    """生成每日跟踪分析报告"""

    # 计算 Equity vs Index 的差异
    equity_vs_index = ""
    if current_equity > 0 and current_index > 0:
        if current_equity > current_index * 1.2:
            equity_vs_index = "个股期权Put/Call比率显著高于指数期权，表明个股层面的对冲需求更强，市场对个股风险更为担忧。"
        elif current_index > current_equity * 1.2:
            equity_vs_index = "指数期权Put/Call比率显著高于个股期权，表明机构投资者在指数层面进行对冲，系统性风险担忧上升。"
        else:
            equity_vs_index = "个股与指数期权Put/Call比率基本持平，市场在个股和指数层面的风险定价趋于一致。"

    # 生成报告段落
    sections = []

    # 1. 概况
    sections.append({
        'title': '当前概况',
        'content': f"截至最新交易日，CBOE总Put/Call比率为 {current:.3f}，市场情绪处于「{sentiment}」状态。"
                  f"当前值处于近期的 {percentile:.0f}% 分位水平。",
    })

    # 2. 趋势分析
    sections.append({
        'title': '趋势分析',
        'content': f"Put/Call比率近5日均值为 {avg_5d:.3f}，20日均值为 {avg_20d:.3f}，"
                  f"短期趋势为「{trend}」。{equity_vs_index}",
    })

    # 3. 波动率分析
    if std_20d > 0.1:
        sections.append({
            'title': '波动率关注',
            'content': f"20日波动率为 {std_20d:.3f}，处于较高水平，表明市场情绪波动较大，"
                      f"短期内可能出现方向性选择。",
        })

    # 4. 极端情况
    if extremes:
        for ext in extremes:
            sections.append({
                'title': '风险提示' if ext['type'] == 'warning' else '关注事项',
                'content': ext['message'],
            })

    # 5. 操作建议
    advice = _generate_advice(sentiment, trend, risk_level, avg_5d, avg_20d)
    sections.append({
        'title': '操作建议',
        'content': advice,
    })

    return {
        'sections': sections,
        'equity_vs_index': equity_vs_index,
        'generated_at': datetime.now().isoformat(),
    }


def _generate_advice(sentiment: str, trend: str, risk_level: str, avg_5d: float, avg_20d: float) -> str:
    """生成操作建议"""
    advice = ""

    if '恐慌' in sentiment and trend in ('上升', '显著上升'):
        advice = (
            "市场处于恐慌且趋势恶化阶段，建议：\n"
            "1. 降低仓位至防御水平（建议30-50%仓位）\n"
            "2. 增加对冲保护（买入Put或增加反向ETF配置）\n"
            "3. 等待Put/Call比率出现拐点后再考虑加仓\n"
            "4. 关注VIX指数，若VIX同步飙升则进一步确认恐慌"
        )
    elif '恐慌' in sentiment and trend in ('下降', '显著下降'):
        advice = (
            "恐慌情绪正在缓解，可考虑逢低布局：\n"
            "1. 分批次小幅加仓（每次5-10%仓位）\n"
            "2. 优先关注超跌优质标的\n"
            "3. 设置严格止损（建议5-8%）\n"
            "4. 等待Put/Call比率回到0.8以下确认情绪修复"
        )
    elif '乐观' in sentiment and trend in ('上升', '显著上升'):
        advice = (
            "市场情绪正在从乐观转向谨慎：\n"
            "1. 适当减仓锁定利润（建议减至50-60%仓位）\n"
            "2. 关注是否有重大利空事件驱动\n"
            "3. 若Put/Call比率突破0.85，进一步降低风险敞口"
        )
    elif '乐观' in sentiment and trend in ('下降', '显著下降'):
        advice = (
            "市场情绪持续乐观，但需警惕过度自信：\n"
            "1. 保持正常仓位，但设置移动止盈\n"
            "2. 关注Put/Call比率是否跌破0.45（极端信号）\n"
            "3. 建议配置部分对冲头寸以防突发风险\n"
            "4. 定期检查市场广度指标确认上涨健康度"
        )
    elif '中性' in sentiment:
        advice = (
            "市场情绪中性，可按正常策略操作：\n"
            "1. 维持现有仓位，关注方向性突破信号\n"
            "2. 关注Put/Call比率突破0.85或跌破0.55的方向选择\n"
            "3. 结合其他指标（如VIX、市场广度）综合判断\n"
            "4. 保持灵活，随时准备应对方向性变化"
        )
    else:
        advice = (
            "建议持续关注Put/Call比率变化：\n"
            "1. 关注5日与20日均线的交叉信号\n"
            "2. 极端值（>1.0或<0.5）通常预示反转机会\n"
            "3. 结合个股/指数Put/Call比率差异判断风险偏好"
        )

    return advice


def _generate_mock_put_call_data(days: int = 30) -> List[Dict]:
    """生成模拟Put/Call数据（API不可用时的回退）"""
    import random
    random.seed(42)

    data = []
    base_ratio = 0.72

    for i in range(days):
        day = (datetime.now() - timedelta(days=days - 1 - i)).strftime('%Y-%m-%d')
        noise = random.uniform(-0.12, 0.12)
        total = round(base_ratio + noise, 3)
        equity = round(total * random.uniform(0.65, 0.85), 3)
        index_ratio = round(total * random.uniform(1.1, 1.5), 3)

        data.append({
            "date": day,
            "equity_put_call_ratio": equity,
            "index_put_call_ratio": index_ratio,
            "total_put_call_ratio": total,
        })

    return data