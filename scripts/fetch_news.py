"""
新闻/市场事件数据采集脚本
从 AKShare 东方财富全球财经新闻获取实时数据，提取经济事件和观点
适用于 GitHub Actions 每日定时运行
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "news"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def extract_economic_event(title, summary, pub_time):
    """从新闻标题中提取经济事件"""
    text = (title + " " + summary).lower()

    economic_keywords = [
        "cpi", "ppi", "pmi", "gdp", "通胀", "物价指数", "失业", "就业",
        "零售", "工业产出", "贸易", "进出口", "外汇储备", "社融", "m2",
        "消费者信心", "制造业", "服务业", "采购经理人", "非农", "初请",
        "eia", "原油库存", "利率决议", "降息", "加息", "存款准备金",
        "lpr", "mlf", "逆回购", "国债", "央行", "美联储", "欧央行",
        "货币政策", "财政", "关税", "制裁", "经济数据", "景气",
    ]

    if not any(kw in text for kw in economic_keywords):
        return None

    # 类别
    if any(kw in text for kw in ["利率", "央行", "fed", "fomc", "ecb", "mlf", "lpr", "存款准备金", "降息", "加息", "货币政策", "逆回购"]):
        category = "central_bank"
    elif any(kw in text for kw in ["讲话", "演讲", "新闻发布会", "证词", "表态"]):
        category = "speech"
    elif any(kw in text for kw in ["会议", "峰会", "论坛", "g20", "g7", "opec"]):
        category = "meeting"
    else:
        category = "economic_data"

    # 影响等级
    if any(kw in text for kw in ["cpi", "ppi", "非农", "利率决议", "降息", "加息", "gdp", "央行", "美联储", "fomc", "货币政策"]):
        impact = "high"
    elif any(kw in text for kw in ["pmi", "就业", "失业", "零售", "贸易", "eia", "lpr", "mlf"]):
        impact = "medium"
    else:
        impact = "low"

    # 国家
    if any(kw in text for kw in ["美国", "美联储", "美元", "fomc", "fed"]):
        country = "美国"
    elif any(kw in text for kw in ["中国", "央行", "人民币", "mlf", "lpr", "逆回购"]):
        country = "中国"
    elif any(kw in text for kw in ["欧元区", "欧洲", "欧央行", "ecb", "欧元"]):
        country = "欧元区"
    elif any(kw in text for kw in ["日本", "日元", "日央行"]):
        country = "日本"
    elif any(kw in text for kw in ["英国", "英镑", "英央行"]):
        country = "英国"
    elif any(kw in text for kw in ["韩国", "韩元"]):
        country = "韩国"
    else:
        country = "国际"

    event_time = pub_time if pub_time else datetime.now().strftime("%Y-%m-%d %H:%M")

    return {
        "id": f"evt_{hash(title) % 100000:05d}",
        "time": event_time,
        "title": title,
        "country": country,
        "category": category,
        "impact": impact,
        "previous": "-",
        "forecast": "-",
        "actual": "待公布",
        "description": (summary[:200] if len(summary) > 200 else summary) or title,
        "related_assets": [],
    }


def classify_topic(title, summary):
    """分类话题"""
    text = (title + " " + summary).lower()
    if any(kw in text for kw in ["ai", "人工智能", "大模型", "gpt", "智能体", "模型", "算法", "机器学"]):
        return "AI/科技"
    if any(kw in text for kw in ["芯片", "半导体", "光刻", "英伟达", "nvidia", "amd", "英特尔"]):
        return "芯片/半导体"
    if any(kw in text for kw in ["新能源", "光伏", "锂电", "储能", "电动车", "特斯拉", "固态电池"]):
        return "新能源"
    if any(kw in text for kw in ["机器人", "自动驾驶", "低空", "无人机", "脑机"]):
        return "前沿科技"
    if any(kw in text for kw in ["央行", "利率", "降息", "加息", "通胀", "cpi", "ppi", "gdp", "美联储", "货币政策"]):
        return "宏观经济"
    if any(kw in text for kw in ["a股", "港股", "美股", "ipo", "上市", "回购", "减持", "涨停", "跌停"]):
        return "资本市场"
    if any(kw in text for kw in ["医药", "医疗", "创新药", "生物"]):
        return "医药健康"
    if any(kw in text for kw in ["消费", "零售", "电商", "品牌"]):
        return "消费"
    if any(kw in text for kw in ["深圳", "北京", "上海", "政策", "国务院", "发改委", "工信部"]):
        return "政策/产业"
    return "综合财经"


def classify_sentiment(title, summary):
    """判断情感倾向"""
    text = (title + " " + summary).lower()
    bullish = ["增长", "利好", "突破", "上涨", "反弹", "创新高", "扩产", "增持", "回购", "投资", "合作", "获批", "量产", "落地", "加速", "提升", "超预期"]
    bearish = ["下跌", "亏损", "风险", "警告", "制裁", "限制", "调查", "处罚", "暴雷", "违约", "退市", "减持", "裁员", "下滑", "衰退", "低于预期"]
    bc = sum(1 for k in bullish if k in text)
    sc = sum(1 for k in bearish if k in text)
    if bc > sc:
        return "bullish"
    elif sc > bc:
        return "bearish"
    return "neutral"


def fetch_news_data():
    """从 AKShare 获取东方财富全球财经新闻"""
    try:
        import akshare as ak
        df = ak.stock_info_global_em()
        if df is None or df.empty:
            print("警告: 东方财富新闻返回空数据")
            return None, None

        events = []
        insights = []
        for _, row in df.iterrows():
            try:
                title = str(row.get("标题", ""))
                summary = str(row.get("摘要", ""))
                pub_time = str(row.get("发布时间", ""))
                url = str(row.get("链接", ""))

                # 提取经济事件
                evt = extract_economic_event(title, summary, pub_time)
                if evt:
                    events.append(evt)

                # 提取观点/新闻
                topic = classify_topic(title, summary)
                sentiment = classify_sentiment(title, summary)
                tags = []
                tag_kws = ["AI", "人工智能", "芯片", "半导体", "新能源", "机器人", "自动驾驶",
                          "央行", "美联储", "利率", "A股", "港股", "美股", "回购", "IPO",
                          "政策", "大模型", "智能体", "低空经济", "特斯拉"]
                for kw in tag_kws:
                    if kw in (title + summary):
                        tags.append(kw)

                for kw in tag_kws:
                    if kw in (title + summary):
                        tags.append(kw)

                insights.append({
                    "id": f"ins_{len(insights)+1:03d}",
                    "source": "东方财富",
                    "author": "财经快讯",
                    "role": "实时资讯",
                    "date": pub_time[:10] if len(pub_time) >= 10 else datetime.now().strftime("%Y-%m-%d"),
                    "title": title,
                    "summary": summary[:200] if len(summary) > 200 else summary,
                    "topic": topic,
                    "sentiment": sentiment,
                    "tags": list(set(tags))[:5],
                    "url": url,
                })
            except Exception:
                continue

        print(f"OK: 获取到 {len(events)} 个经济事件, {len(insights)} 条新闻")
        return events, insights

    except ImportError:
        print("错误: AKShare 未安装")
        return None, None
    except Exception as e:
        print(f"错误: 获取新闻失败: {e}")
        return None, None


def save_data(events, insights):
    """保存新闻数据为 JSON"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 每日事件
    if events:
        events.sort(key=lambda e: e["time"])
        high_impact = [e for e in events if e.get("impact") == "high"]
        by_category = {
            "economic_data": [e for e in events if e.get("category") == "economic_data"],
            "central_bank": [e for e in events if e.get("category") == "central_bank"],
            "speeches": [e for e in events if e.get("category") == "speech"],
            "meetings": [e for e in events if e.get("category") == "meeting"],
        }
        daily_events = {
            "date": today,
            "summary": f"今日共有 {len(events)} 个重要事件，其中 {len(high_impact)} 个高影响事件",
            "total_events": len(events),
            "high_impact": high_impact,
            "events": events[:50],
            "by_category": by_category,
            "source": "东方财富实时财经新闻（实时）",
        }
        with open(DATA_DIR / "daily_events.json", "w", encoding="utf-8") as f:
            json.dump(daily_events, f, ensure_ascii=False, indent=2)
        print(f"OK: 已保存每日事件 ({len(events)} 个)")
    else:
        print("跳过: 无经济事件数据")

    # 新闻观点
    if insights:
        topics = {}
        for ins in insights:
            topic = ins.get("topic", "其他")
            topics.setdefault(topic, []).append(ins)

        news_data = {
            "total_insights": len(insights),
            "insights": insights[:20],
            "by_topic": topics,
            "period": f"最近 1 天",
            "source": "东方财富实时财经新闻（实时）",
        }
        with open(DATA_DIR / "insights.json", "w", encoding="utf-8") as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        print(f"OK: 已保存新闻观点 ({len(insights)} 条)")
    else:
        print("跳过: 无新闻数据")


def main():
    print("=" * 50)
    print("新闻/市场事件数据采集")
    print("=" * 50)

    events, insights = fetch_news_data()
    save_data(events, insights)

    return 0


if __name__ == "__main__":
    sys.exit(main())