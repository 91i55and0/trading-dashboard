"""
新闻推送服务
- 每日市场重要事件日报
- 硅谷顶级观点推送
- SEC EDGAR 13F 持仓监控报告
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json


def get_daily_market_events(date: str = None) -> Dict[str, Any]:
    """
    获取每日市场重要事件日报
    包括：全球核心经济数据、会议、讲话、央行动态
    """
    today = date or datetime.now().strftime("%Y-%m-%d")

    # 尝试从数据源获取实际数据，当前返回模拟结构
    # 后续可接入财经日历 API (如 investing.com, forexfactory, akshare)
    events = _generate_market_events(today)

    # 分类汇总
    economic_data = [e for e in events if e["category"] == "economic_data"]
    central_bank = [e for e in events if e["category"] == "central_bank"]
    speeches = [e for e in events if e["category"] == "speech"]
    meetings = [e for e in events if e["category"] == "meeting"]

    return {
        "date": today,
        "summary": f"今日共 {len(events)} 项重要事件，其中经济数据 {len(economic_data)} 项，央行动态 {len(central_bank)} 项",
        "events": events,
        "by_category": {
            "economic_data": economic_data,
            "central_bank": central_bank,
            "speeches": speeches,
            "meetings": meetings,
        },
        "high_impact": [e for e in events if e["impact"] == "high"],
        "generated_at": datetime.now().isoformat(),
    }


def get_silicon_valley_insights(days: int = 1) -> Dict[str, Any]:
    """
    获取硅谷顶级观点推送
    追踪知名投资人和科技领袖的公开观点
    """
    insights = _generate_insights(days)

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_insights": len(insights),
        "insights": insights,
        "by_topic": _group_by_topic(insights),
        "generated_at": datetime.now().isoformat(),
    }


def get_13f_monitor(lookback_days: int = 30) -> Dict[str, Any]:
    """
    SEC EDGAR 13F 持仓监控报告
    监控知名机构的最新13F持仓变动
    """
    filings = _generate_13f_filings(lookback_days)

    # 按机构汇总
    institutions = {}
    for f in filings:
        inst = f["institution"]
        if inst not in institutions:
            institutions[inst] = {
                "name": inst,
                "filings": [],
                "total_new_positions": 0,
                "total_closed_positions": 0,
                "total_value_change": 0,
            }
        inst_data = institutions[inst]
        inst_data["filings"].append(f)
        inst_data["total_new_positions"] += len(f.get("new_positions", []))
        inst_data["total_closed_positions"] += len(f.get("closed_positions", []))
        inst_data["total_value_change"] += f.get("portfolio_value_change", 0)

    return {
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "lookback_days": lookback_days,
        "total_filings": len(filings),
        "institutions": list(institutions.values()),
        "filings": filings,
        "generated_at": datetime.now().isoformat(),
    }


def get_news_digest() -> Dict[str, Any]:
    """获取综合新闻摘要"""
    events = get_daily_market_events()
    insights = get_silicon_valley_insights()
    filings_13f = get_13f_monitor()

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "market_events_count": len(events["events"]),
        "high_impact_events": events["high_impact"],
        "insights_count": insights["total_insights"],
        "top_insights": insights["insights"][:3],
        "latest_13f": {
            "total_filings": filings_13f["total_filings"],
            "institutions": [i["name"] for i in filings_13f["institutions"]],
        },
        "generated_at": datetime.now().isoformat(),
    }


# ============================
# 数据生成 (模拟数据，后续替换为真实数据源)
# ============================

def _generate_market_events(date_str: str) -> List[Dict[str, Any]]:
    """生成市场事件数据"""
    return [
        # 经济数据
        {
            "id": "evt_001",
            "time": f"{date_str} 08:30",
            "title": "美国 7月 核心PCE物价指数月率",
            "country": "美国",
            "category": "economic_data",
            "impact": "high",
            "previous": "0.1%",
            "forecast": "0.2%",
            "actual": "待公布",
            "description": "美联储最关注的通胀指标，对利率政策有直接影响",
            "related_assets": ["美元指数", "黄金", "美股期货", "美债收益率"],
        },
        {
            "id": "evt_002",
            "time": f"{date_str} 10:00",
            "title": "美国 7月 密歇根大学消费者信心指数终值",
            "country": "美国",
            "category": "economic_data",
            "impact": "high",
            "previous": "68.2",
            "forecast": "68.5",
            "actual": "待公布",
            "description": "反映消费者对经济前景的信心程度",
            "related_assets": ["美元指数", "美股", "消费类股票"],
        },
        {
            "id": "evt_003",
            "time": f"{date_str} 09:00",
            "title": "中国 7月 官方制造业PMI",
            "country": "中国",
            "category": "economic_data",
            "impact": "high",
            "previous": "49.5",
            "forecast": "49.7",
            "actual": "待公布",
            "description": "中国制造业景气度先行指标，影响A股和商品市场",
            "related_assets": ["A股", "人民币", "铜", "铁矿石"],
        },
        {
            "id": "evt_004",
            "time": f"{date_str} 14:00",
            "title": "欧元区 7月 CPI年率初值",
            "country": "欧元区",
            "category": "economic_data",
            "impact": "high",
            "previous": "2.5%",
            "forecast": "2.4%",
            "actual": "待公布",
            "description": "欧元区通胀数据，影响欧央行利率决策",
            "related_assets": ["欧元/美元", "欧洲股市", "欧债"],
        },
        {
            "id": "evt_005",
            "time": f"{date_str} 16:30",
            "title": "美国 EIA原油库存周报",
            "country": "美国",
            "category": "economic_data",
            "impact": "medium",
            "previous": "-250万桶",
            "forecast": "-180万桶",
            "actual": "待公布",
            "description": "原油库存变化，影响油价走势",
            "related_assets": ["WTI原油", "布伦特原油", "能源股"],
        },
        {
            "id": "evt_006",
            "time": f"{date_str} 20:30",
            "title": "美国 周度初请失业金人数",
            "country": "美国",
            "category": "economic_data",
            "impact": "medium",
            "previous": "23.0万",
            "forecast": "23.5万",
            "actual": "待公布",
            "description": "劳动力市场健康状况的周度指标",
            "related_assets": ["美元指数", "美股", "美债"],
        },
        # 央行动态
        {
            "id": "evt_007",
            "time": f"{date_str} 21:00",
            "title": "美联储 FOMC 利率决议",
            "country": "美国",
            "category": "central_bank",
            "impact": "high",
            "previous": "5.25%-5.50%",
            "forecast": "5.00%-5.25%",
            "actual": "待公布",
            "description": "美联储利率决议，全球金融市场最重要的事件之一",
            "related_assets": ["全球股市", "美元指数", "黄金", "美债", "全球汇率"],
        },
        {
            "id": "evt_008",
            "time": f"{date_str} 09:00",
            "title": "中国人民银行 MLF 操作",
            "country": "中国",
            "category": "central_bank",
            "impact": "medium",
            "previous": "2.50%",
            "forecast": "2.50%",
            "actual": "待公布",
            "description": "中国央行中期借贷便利操作利率",
            "related_assets": ["A股", "人民币", "中国国债"],
        },
        # 讲话
        {
            "id": "evt_009",
            "time": f"{date_str} 22:30",
            "title": "美联储主席鲍威尔 新闻发布会",
            "country": "美国",
            "category": "speech",
            "impact": "high",
            "previous": "-",
            "forecast": "-",
            "actual": "待公布",
            "description": "FOMC会后新闻发布会，关注利率路径指引",
            "related_assets": ["全球股市", "美元指数", "黄金", "美债"],
        },
        # 会议
        {
            "id": "evt_010",
            "time": f"{date_str} 全天",
            "title": "G20 财长和央行行长会议 (第二日)",
            "country": "多国",
            "category": "meeting",
            "impact": "medium",
            "previous": "-",
            "forecast": "-",
            "actual": "-",
            "description": "讨论全球经济形势、金融稳定和数字货币等议题",
            "related_assets": ["全球股市", "外汇市场", "加密货币"],
        },
    ]


def _generate_insights(days: int) -> List[Dict[str, Any]]:
    """生成硅谷顶级观点"""
    from datetime import datetime
    today = datetime.now()

    insights = [
        {
            "id": "ins_001",
            "source": "a16z",
            "author": "Marc Andreessen",
            "role": "a16z 联合创始人",
            "date": today.strftime("%Y-%m-%d"),
            "title": "AI 正在重塑软件业的商业模式",
            "summary": "Andreessen 认为，AI 原生公司将从根本上改变软件行业的单位经济模型。传统 SaaS 公司依赖人力密集的销售和支持，而 AI 原生公司可以实现近乎零边际成本的规模化。",
            "topic": "AI/科技",
            "sentiment": "bullish",
            "tags": ["AI", "SaaS", "商业模式"],
            "url": "https://a16z.com/",
        },
        {
            "id": "ins_002",
            "source": "ARK Invest",
            "author": "Cathie Wood",
            "role": "ARK Invest CEO",
            "date": today.strftime("%Y-%m-%d"),
            "title": "特斯拉自动驾驶出租车将创造万亿市场",
            "summary": "Wood 重申特斯拉 Robotaxi 业务的巨大潜力，预计到 2030 年自动驾驶出租车市场规模将超过 10 万亿美元。她认为市场低估了特斯拉在 AI 和自动驾驶领域的技术领先优势。",
            "topic": "自动驾驶/新能源",
            "sentiment": "bullish",
            "tags": ["特斯拉", "自动驾驶", "Robotaxi"],
            "url": "https://ark-invest.com/",
        },
        {
            "id": "ins_003",
            "source": "Sequoia Capital",
            "author": "Roelof Botha",
            "role": "红杉资本 管理合伙人",
            "date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            "title": "生成式AI 正在从实验阶段进入部署阶段",
            "summary": "Botha 指出，2024-2025 年生成式AI 从概念验证转向大规模部署，企业级应用开始产生实际 ROI。投资重点从基础模型层转向应用层和基础设施层。",
            "topic": "AI/科技",
            "sentiment": "bullish",
            "tags": ["生成式AI", "企业软件", "投资趋势"],
            "url": "https://www.sequoiacap.com/",
        },
        {
            "id": "ins_004",
            "source": "Y Combinator",
            "author": "Garry Tan",
            "role": "Y Combinator CEO",
            "date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            "title": "开源 AI 模型将打破巨头垄断",
            "summary": "Tan 认为开源 AI 模型（如 Llama 3、Mistral）正在快速缩小与闭源模型的差距，这将为创业公司创造前所未有的机会。",
            "topic": "AI/科技",
            "sentiment": "neutral",
            "tags": ["开源AI", "创业", "Llama"],
            "url": "https://www.ycombinator.com/",
        },
        {
            "id": "ins_005",
            "source": "Founders Fund",
            "author": "Peter Thiel",
            "role": "Founders Fund 合伙人",
            "date": (today - timedelta(days=2)).strftime("%Y-%m-%d"),
            "title": "美国国债问题被严重低估",
            "summary": "Thiel 警告美国联邦债务规模已达不可持续水平，利率正常化可能引发财政危机。他建议投资者增加硬资产（黄金、比特币）和抗通胀资产配置。",
            "topic": "宏观经济",
            "sentiment": "bearish",
            "tags": ["美国国债", "通胀", "黄金", "比特币"],
            "url": "https://foundersfund.com/",
        },
        {
            "id": "ins_006",
            "source": "Benchmark",
            "author": "Bill Gurley",
            "role": "Benchmark 合伙人",
            "date": (today - timedelta(days=2)).strftime("%Y-%m-%d"),
            "title": "IPO 市场正在回暖，但估值纪律依然重要",
            "summary": "Gurley 观察到 IPO 市场在经历两年冰封后开始解冻，但强调公司需要展示真正的盈利能力和可持续增长，而不仅仅是增长故事。",
            "topic": "资本市场",
            "sentiment": "neutral",
            "tags": ["IPO", "估值", "盈利能力"],
            "url": "https://www.benchmark.com/",
        },
        {
            "id": "ins_007",
            "source": "Khosla Ventures",
            "author": "Vinod Khosla",
            "role": "Khosla Ventures 创始人",
            "date": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
            "title": "核聚变将在 2030 年代实现商业化",
            "summary": "Khosla 预测核聚变技术将在未来 10-15 年内实现商业化，这将彻底改变全球能源格局。他已经在多家核聚变初创公司中布局。",
            "topic": "能源/科技",
            "sentiment": "bullish",
            "tags": ["核聚变", "清洁能源", "深度科技"],
            "url": "https://www.khoslaventures.com/",
        },
        {
            "id": "ins_008",
            "source": "Altimeter Capital",
            "author": "Brad Gerstner",
            "role": "Altimeter Capital CEO",
            "date": (today - timedelta(days=3)).strftime("%Y-%m-%d"),
            "title": "软件股估值已回归合理区间",
            "summary": "Gerstner 认为经过 2022-2023 年的估值调整，优质 SaaS 公司的估值已经回归合理水平，现在是逐步建仓的好时机。",
            "topic": "资本市场",
            "sentiment": "bullish",
            "tags": ["SaaS", "估值", "软件股"],
            "url": "https://www.altimeter.com/",
        },
    ]

    return insights[: max(1, days * 3)]


def _group_by_topic(insights: List[Dict]) -> Dict[str, List[Dict]]:
    """按主题分组观点"""
    topics = {}
    for ins in insights:
        topic = ins.get("topic", "其他")
        if topic not in topics:
            topics[topic] = []
        topics[topic].append(ins)
    return topics


def _generate_13f_filings(lookback_days: int) -> List[Dict[str, Any]]:
    """生成13F持仓变动数据"""
    today = datetime.now()
    filing_date = (today - timedelta(days=lookback_days // 2)).strftime("%Y-%m-%d")

    return [
        {
            "id": "13f_001",
            "institution": "Berkshire Hathaway",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 312000000000,
            "portfolio_value_change": 8500000000,
            "top_holdings": [
                {"symbol": "AAPL", "name": "Apple Inc.", "shares": 915000000, "value": 175000000000, "change_pct": -1.2},
                {"symbol": "BAC", "name": "Bank of America", "shares": 1030000000, "value": 42000000000, "change_pct": 0},
                {"symbol": "AXP", "name": "American Express", "shares": 151000000, "value": 35000000000, "change_pct": 0},
                {"symbol": "KO", "name": "Coca-Cola", "shares": 400000000, "value": 25000000000, "change_pct": 0},
                {"symbol": "OXY", "name": "Occidental Petroleum", "shares": 255000000, "value": 16000000000, "change_pct": 2.5},
            ],
            "new_positions": [
                {"symbol": "CHTR", "name": "Charter Communications", "shares": 3800000, "value": 1200000000},
            ],
            "increased_positions": [
                {"symbol": "OXY", "name": "Occidental Petroleum", "change_pct": 2.5},
                {"symbol": "SIRI", "name": "Sirius XM", "change_pct": 8.3},
            ],
            "reduced_positions": [
                {"symbol": "AAPL", "name": "Apple Inc.", "change_pct": -1.2},
                {"symbol": "HPQ", "name": "HP Inc.", "change_pct": -5.0},
            ],
            "closed_positions": [
                {"symbol": "STNE", "name": "StoneCo Ltd."},
            ],
            "strategy_note": "巴菲特继续小幅减持苹果，同时加仓西方石油和Sirius XM。新建仓Charter Communications，显示对宽带基础设施的看好。",
        },
        {
            "id": "13f_002",
            "institution": "Scion Asset Management",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 240000000,
            "portfolio_value_change": -35000000,
            "top_holdings": [
                {"symbol": "JD", "name": "京东", "shares": 250000, "value": 85000000, "change_pct": 20.0},
                {"symbol": "BABA", "name": "阿里巴巴", "shares": 150000, "value": 68000000, "change_pct": 15.0},
                {"symbol": "PDD", "name": "拼多多", "shares": 120000, "value": 55000000, "change_pct": 50.0},
            ],
            "new_positions": [
                {"symbol": "PDD", "name": "拼多多", "shares": 120000, "value": 55000000},
            ],
            "increased_positions": [
                {"symbol": "JD", "name": "京东", "change_pct": 20.0},
                {"symbol": "BABA", "name": "阿里巴巴", "change_pct": 15.0},
            ],
            "reduced_positions": [],
            "closed_positions": [
                {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust"},
                {"symbol": "QQQ", "name": "Invesco QQQ Trust"},
            ],
            "strategy_note": "Michael Burry 大幅增持中概股，清仓了标普500和纳斯达克ETF，显示对美股大盘的谨慎和对中国资产的看好。",
        },
        {
            "id": "13f_003",
            "institution": "Renaissance Technologies",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 68000000000,
            "portfolio_value_change": 2100000000,
            "top_holdings": [
                {"symbol": "NVDA", "name": "NVIDIA", "shares": 8500000, "value": 6800000000, "change_pct": -3.0},
                {"symbol": "META", "name": "Meta Platforms", "shares": 5200000, "value": 4800000000, "change_pct": 5.5},
                {"symbol": "AMZN", "name": "Amazon", "shares": 18000000, "value": 4200000000, "change_pct": 2.0},
            ],
            "new_positions": [
                {"symbol": "SMCI", "name": "Super Micro Computer", "shares": 800000, "value": 650000000},
            ],
            "increased_positions": [
                {"symbol": "META", "name": "Meta Platforms", "change_pct": 5.5},
                {"symbol": "AMD", "name": "AMD", "change_pct": 12.0},
            ],
            "reduced_positions": [
                {"symbol": "NVDA", "name": "NVIDIA", "change_pct": -3.0},
                {"symbol": "TSLA", "name": "Tesla", "change_pct": -8.0},
            ],
            "closed_positions": [],
            "strategy_note": "文艺复兴科技小幅减持英伟达，但新建仓了AI服务器厂商超微电脑(SMCI)，加仓AMD和Meta，整体仍看好AI产业链。",
        },
        {
            "id": "13f_004",
            "institution": "Bridgewater Associates",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 19800000000,
            "portfolio_value_change": -500000000,
            "top_holdings": [
                {"symbol": "IEMG", "name": "iShares Core MSCI Emerging Markets ETF", "shares": 18000000, "value": 1200000000, "change_pct": 8.0},
                {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "shares": 2200000, "value": 1100000000, "change_pct": -5.0},
                {"symbol": "GLD", "name": "SPDR Gold Trust", "shares": 5500000, "value": 1050000000, "change_pct": 12.0},
            ],
            "new_positions": [],
            "increased_positions": [
                {"symbol": "GLD", "name": "SPDR Gold Trust", "change_pct": 12.0},
                {"symbol": "IEMG", "name": "新兴市场ETF", "change_pct": 8.0},
            ],
            "reduced_positions": [
                {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "change_pct": -5.0},
                {"symbol": "EEM", "name": "iShares MSCI Emerging Markets ETF", "change_pct": -3.0},
            ],
            "closed_positions": [],
            "strategy_note": "桥水基金继续增持黄金和新兴市场，减持美股大盘ETF，体现其对全球宏观风险的担忧和对多元化配置的重视。",
        },
        {
            "id": "13f_005",
            "institution": "Tiger Global Management",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 14500000000,
            "portfolio_value_change": 1200000000,
            "top_holdings": [
                {"symbol": "MSFT", "name": "Microsoft", "shares": 7500000, "value": 3800000000, "change_pct": 3.0},
                {"symbol": "META", "name": "Meta Platforms", "shares": 4200000, "value": 3200000000, "change_pct": 10.0},
                {"symbol": "NVDA", "name": "NVIDIA", "shares": 2800000, "value": 2500000000, "change_pct": 15.0},
            ],
            "new_positions": [
                {"symbol": "ARM", "name": "ARM Holdings", "shares": 3500000, "value": 850000000},
            ],
            "increased_positions": [
                {"symbol": "NVDA", "name": "NVIDIA", "change_pct": 15.0},
                {"symbol": "META", "name": "Meta Platforms", "change_pct": 10.0},
            ],
            "reduced_positions": [],
            "closed_positions": [],
            "strategy_note": "Tiger Global 大幅加仓AI相关标的，新建仓ARM Holdings，加仓英伟达和Meta，体现对AI革命的坚定看好。",
        },
        {
            "id": "13f_006",
            "institution": "Point72 Asset Management",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 38000000000,
            "portfolio_value_change": 1500000000,
            "top_holdings": [
                {"symbol": "NVDA", "name": "NVIDIA", "shares": 12000000, "value": 9500000000, "change_pct": 5.0},
                {"symbol": "MSFT", "name": "Microsoft", "shares": 18000000, "value": 8200000000, "change_pct": 2.0},
                {"symbol": "AMZN", "name": "Amazon", "shares": 30000000, "value": 6500000000, "change_pct": -3.0},
                {"symbol": "GOOGL", "name": "Alphabet", "shares": 28000000, "value": 5200000000, "change_pct": 8.0},
                {"symbol": "META", "name": "Meta Platforms", "shares": 8500000, "value": 4800000000, "change_pct": 12.0},
            ],
            "new_positions": [
                {"symbol": "ANET", "name": "Arista Networks", "shares": 2200000, "value": 850000000},
                {"symbol": "CRWD", "name": "CrowdStrike Holdings", "shares": 1800000, "value": 620000000},
            ],
            "increased_positions": [
                {"symbol": "META", "name": "Meta Platforms", "change_pct": 12.0},
                {"symbol": "GOOGL", "name": "Alphabet", "change_pct": 8.0},
                {"symbol": "NVDA", "name": "NVIDIA", "change_pct": 5.0},
            ],
            "reduced_positions": [
                {"symbol": "AMZN", "name": "Amazon", "change_pct": -3.0},
                {"symbol": "TSLA", "name": "Tesla", "change_pct": -15.0},
            ],
            "closed_positions": [
                {"symbol": "INTC", "name": "Intel Corporation"},
            ],
            "strategy_note": "Steve Cohen的Point72大幅加仓AI基础设施标的（Arista Networks、CrowdStrike），继续增持Mega-cap科技股，清仓Intel显示对传统半导体的谨慎。",
        },
        {
            "id": "13f_007",
            "institution": "Citadel Advisors",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 62000000000,
            "portfolio_value_change": 3200000000,
            "top_holdings": [
                {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "shares": 35000000, "value": 18500000000, "change_pct": -2.0},
                {"symbol": "QQQ", "name": "Invesco QQQ Trust", "shares": 25000000, "value": 12500000000, "change_pct": 5.0},
                {"symbol": "NVDA", "name": "NVIDIA", "shares": 15000000, "value": 11000000000, "change_pct": 10.0},
                {"symbol": "AAPL", "name": "Apple Inc.", "shares": 45000000, "value": 8500000000, "change_pct": 4.0},
                {"symbol": "IWM", "name": "iShares Russell 2000 ETF", "shares": 30000000, "value": 6500000000, "change_pct": -8.0},
            ],
            "new_positions": [
                {"symbol": "RDDT", "name": "Reddit Inc.", "shares": 3500000, "value": 420000000},
            ],
            "increased_positions": [
                {"symbol": "NVDA", "name": "NVIDIA", "change_pct": 10.0},
                {"symbol": "QQQ", "name": "Invesco QQQ Trust", "change_pct": 5.0},
                {"symbol": "AAPL", "name": "Apple Inc.", "change_pct": 4.0},
            ],
            "reduced_positions": [
                {"symbol": "IWM", "name": "iShares Russell 2000 ETF", "change_pct": -8.0},
                {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "change_pct": -2.0},
            ],
            "closed_positions": [],
            "strategy_note": "Ken Griffin的Citadel减少小盘股暴露（IWM -8%），加仓大型科技股和QQQ，显示对大盘成长风格的偏好。新建仓Reddit，看好社交平台AI变现潜力。",
        },
        {
            "id": "13f_008",
            "institution": "Baupost Group",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 14200000000,
            "portfolio_value_change": -800000000,
            "top_holdings": [
                {"symbol": "GOOGL", "name": "Alphabet", "shares": 22000000, "value": 4200000000, "change_pct": 3.0},
                {"symbol": "LBTYK", "name": "Liberty Global", "shares": 85000000, "value": 2800000000, "change_pct": 5.0},
                {"symbol": "FIS", "name": "Fidelity National Info Services", "shares": 38000000, "value": 2500000000, "change_pct": 0},
                {"symbol": "WFC", "name": "Wells Fargo", "shares": 32000000, "value": 1800000000, "change_pct": -5.0},
                {"symbol": "VRNA", "name": "Verona Pharma", "shares": 45000000, "value": 1100000000, "change_pct": 25.0},
            ],
            "new_positions": [
                {"symbol": "KVUE", "name": "Kenvue Inc.", "shares": 12000000, "value": 280000000},
            ],
            "increased_positions": [
                {"symbol": "VRNA", "name": "Verona Pharma", "change_pct": 25.0},
                {"symbol": "LBTYK", "name": "Liberty Global", "change_pct": 5.0},
                {"symbol": "GOOGL", "name": "Alphabet", "change_pct": 3.0},
            ],
            "reduced_positions": [
                {"symbol": "WFC", "name": "Wells Fargo", "change_pct": -5.0},
            ],
            "closed_positions": [
                {"symbol": "PARA", "name": "Paramount Global"},
            ],
            "strategy_note": "Seth Klarman的Baupost继续深耕价值投资，大幅加仓生物科技（Verona Pharma +25%），新建仓消费健康公司Kenvue，清仓Paramount显示对传统媒体的悲观。",
        },
        {
            "id": "13f_009",
            "institution": "Pershing Square Capital",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 16500000000,
            "portfolio_value_change": 2200000000,
            "top_holdings": [
                {"symbol": "GOOGL", "name": "Alphabet", "shares": 18000000, "value": 3500000000, "change_pct": 0},
                {"symbol": "CMG", "name": "Chipotle Mexican Grill", "shares": 550000, "value": 3200000000, "change_pct": 0},
                {"symbol": "HHC", "name": "Howard Hughes Holdings", "shares": 28000000, "value": 2800000000, "change_pct": 0},
                {"symbol": "QSR", "name": "Restaurant Brands Intl", "shares": 35000000, "value": 2500000000, "change_pct": 5.0},
                {"symbol": "HLT", "name": "Hilton Worldwide", "shares": 10000000, "value": 2200000000, "change_pct": 8.0},
            ],
            "new_positions": [
                {"symbol": "NKE", "name": "Nike Inc.", "shares": 8500000, "value": 950000000},
            ],
            "increased_positions": [
                {"symbol": "HLT", "name": "Hilton Worldwide", "change_pct": 8.0},
                {"symbol": "QSR", "name": "Restaurant Brands Intl", "change_pct": 5.0},
            ],
            "reduced_positions": [],
            "closed_positions": [],
            "strategy_note": "Bill Ackman新建仓Nike（9.5亿美元），押注品牌复苏和CEO更换后的战略转型。继续看好集中持仓策略，前5大持仓占比超80%。",
        },
        {
            "id": "13f_010",
            "institution": "Soros Fund Management",
            "filing_date": filing_date,
            "period": "2025Q2",
            "portfolio_value": 7200000000,
            "portfolio_value_change": 450000000,
            "top_holdings": [
                {"symbol": "RIVN", "name": "Rivian Automotive", "shares": 18000000, "value": 420000000, "change_pct": -12.0},
                {"symbol": "AER", "name": "AerCap Holdings", "shares": 4500000, "value": 380000000, "change_pct": 5.0},
                {"symbol": "CSX", "name": "CSX Corporation", "shares": 8500000, "value": 350000000, "change_pct": 8.0},
                {"symbol": "NEM", "name": "Newmont Corporation", "shares": 5500000, "value": 320000000, "change_pct": 15.0},
                {"symbol": "GDX", "name": "VanEck Gold Miners ETF", "shares": 8000000, "value": 280000000, "change_pct": 20.0},
            ],
            "new_positions": [
                {"symbol": "TLT", "name": "iShares 20+ Year Treasury Bond ETF", "shares": 2500000, "value": 250000000},
                {"symbol": "GLD", "name": "SPDR Gold Trust", "shares": 1200000, "value": 220000000},
            ],
            "increased_positions": [
                {"symbol": "GDX", "name": "VanEck Gold Miners ETF", "change_pct": 20.0},
                {"symbol": "NEM", "name": "Newmont Corporation", "change_pct": 15.0},
                {"symbol": "CSX", "name": "CSX Corporation", "change_pct": 8.0},
            ],
            "reduced_positions": [
                {"symbol": "RIVN", "name": "Rivian Automotive", "change_pct": -12.0},
            ],
            "closed_positions": [
                {"symbol": "QS", "name": "QuantumScape Corporation"},
            ],
            "strategy_note": "Soros基金大幅增持黄金和长期美债（TLT），显示对宏观风险的担忧和对避险资产的偏好。减持Rivian，清仓QuantumScape，减少电动车高风险敞口。",
        },
    ]


# 确保 timedelta 可用
from datetime import timedelta