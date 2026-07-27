"""
AI研报生成服务 - 支持多种LLM Provider（DeepSeek / OpenAI / 自定义OpenAI兼容接口）

优先级：
  1. 用户在前端配置的API Key（每次请求携带）
  2. 服务端环境变量/配置文件中的默认Key
  3. 都不可用时降级到模板生成
"""
import json
import logging
from typing import Dict, Any, Optional
import requests

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

# 预设Provider配置
PROVIDER_PRESETS = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com",
        "default_model": "gpt-4o",
    },
    "custom": {
        "name": "自定义",
        "base_url": "",
        "default_model": "",
    },
}


def generate_research_report_via_ai(
    symbol: str,
    name: str,
    market: str,
    price: float,
    change_pct: float,
    fin: Dict[str, Any],
    debate: Dict[str, Any],
    quote: Dict[str, Any],
    llm_config: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    通过LLM API生成AI驱动的深度研究报告
    
    Args:
        symbol: 股票代码
        name: 股票名称
        market: 市场（A/US）
        price: 最新价格
        change_pct: 涨跌幅
        fin: 财务指标字典
        debate: 红蓝对抗结果
        quote: 行情数据
        llm_config: 用户自定义LLM配置，格式：
            {
                "provider": "deepseek" | "openai" | "custom",
                "api_key": "sk-xxx",
                "base_url": "https://...",      # custom时必填
                "model": "model-name",           # custom时必填
            }
    
    Returns:
        Markdown格式的研究报告，失败时返回None
    """
    # 解析最终使用的配置
    api_key, base_url, model = _resolve_config(llm_config)
    
    if not api_key:
        logger.warning("LLM API Key未配置（服务端和用户端均无），跳过AI报告生成")
        return None
    
    if not base_url or not model:
        logger.warning(f"LLM配置不完整: base_url={base_url}, model={model}")
        return None
    
    try:
        data_summary = _build_data_summary(symbol, name, market, price, change_pct, fin, debate, quote)
        system_prompt = _build_system_prompt()
        
        # 确保base_url末尾没有斜杠
        base_url = base_url.rstrip("/")
        
        logger.info(f"调用LLM API: {base_url}, model={model}, provider={llm_config.get('provider', 'default') if llm_config else 'default'}")
        
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data_summary},
                ],
                "temperature": 0.3,
                "max_tokens": 8192,
                "stream": False,
            },
            timeout=120,
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            logger.info(f"AI报告生成成功: {symbol}, 长度={len(content)}")
            return content
        else:
            logger.error(f"LLM API调用失败: {response.status_code} - {response.text[:500]}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error(f"LLM API调用超时: {symbol}")
        return None
    except Exception as e:
        logger.error(f"LLM API调用异常: {e}")
        return None


def _resolve_config(llm_config: Optional[Dict[str, Any]] = None) -> tuple:
    """
    解析LLM配置，优先级：用户配置 > 服务端默认配置
    
    Returns:
        (api_key, base_url, model)
    """
    # 如果用户提供了配置，优先使用
    if llm_config and llm_config.get("api_key"):
        provider = llm_config.get("provider", "custom")
        api_key = llm_config["api_key"]
        
        if provider in PROVIDER_PRESETS and provider != "custom":
            preset = PROVIDER_PRESETS[provider]
            base_url = llm_config.get("base_url") or preset["base_url"]
            model = llm_config.get("model") or preset["default_model"]
        else:
            # custom provider，必须提供base_url和model
            base_url = llm_config.get("base_url", "")
            model = llm_config.get("model", "")
        
        return api_key, base_url, model
    
    # 回退到服务端默认配置
    if DEEPSEEK_API_KEY:
        return DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
    
    return "", "", ""


def get_provider_info() -> Dict[str, Any]:
    """获取可用的Provider信息（供前端展示）"""
    return {
        "providers": [
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "description": "DeepSeek-V3，性价比极高，¥1/百万tokens",
                "default_model": "deepseek-chat",
                "base_url": "https://api.deepseek.com",
                "register_url": "https://platform.deepseek.com",
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "description": "GPT-4o，能力最强，价格较高",
                "default_model": "gpt-4o",
                "base_url": "https://api.openai.com",
                "register_url": "https://platform.openai.com",
            },
            {
                "id": "custom",
                "name": "自定义接口",
                "description": "任何兼容OpenAI接口的LLM服务（如Ollama本地部署、其他API代理等）",
                "default_model": "",
                "base_url": "",
                "register_url": "",
            },
        ],
        "server_has_default": bool(DEEPSEEK_API_KEY),
        "server_default_provider": "deepseek" if DEEPSEEK_API_KEY else None,
    }


# ==================== 以下为提示词和数据格式化（不变） ====================

def _build_system_prompt() -> str:
    """构建系统提示词"""
    return """你是一位专业的A股/美股证券分析师，拥有CFA和CPA资质。你需要根据提供的真实财务数据，生成一份专业的个股深度研究报告。

## 报告格式要求

报告必须使用Markdown格式，包含以下六个模块，使用"## 一、基本面分析"、"## 二、逻辑验证"等作为标题：

### 一、基本面分析
- 核心财务指标表格（PE、PB、ROE、市值、PEG、资产负债率等）
- 营收增长分析（表格+趋势解读）
- 利润增长分析（表格+趋势解读）
- 毛利率与净利率趋势（表格+解读）
- 财务健康度（资产负债率、自由现金流、商誉风险、EPS）
- 利润表明细（如有数据）
- 资产负债表结构（如有数据）
- 现金流量表（如有数据）
- 主营构成（如有数据）
- 运营效率指标（如有数据）+ 杜邦分析
- 同业估值对比（PE、PB表格+分析）
- 同业盈利能力与成长性对比
- 分析师一致预期（如有数据）
- 机构持仓（如有数据）
- 北向资金（如有数据）
- 估值分位（如有数据）
- 分红回报（如有数据）
- 增长质量分析（如有数据）
- 人均效率指标（如有数据）
- 股东结构（如有数据）
- 财务异常检测（如有数据）
- 业绩预告（如有数据）
- 限售股解禁风险（如有数据）

### 二、逻辑验证（红蓝对抗）
- 多方论点（Red Team）：列出3-5个看多理由，每条引用具体数据支撑
- 空方论点（Blue Team）：列出3-5个看空/风险理由，每条引用具体数据支撑
- 综合评分：给出多空力量对比和综合判断

### 三、行业与宏观视角
- 行业景气度分析（基于行业增速、政策环境、竞争格局）
- 宏观敏感性分析（利率、通胀、汇率等对该公司的影响）
- 公司在行业中的竞争地位

### 四、催化剂观察
- 近期潜在催化剂（财报、政策、产品发布、行业事件等）
- 催化剂时间窗口和影响程度评估
- 上行/下行风险情景分析

### 五、五阶引擎深度推演

#### 5.1 SOTP分部重估
- 基于PE、ROE、净利润等数据，使用成长/稳定/资产三阶段分部估值
- 给出各部分权重、估值倍数和合理估值区间

#### 5.2 隐含预期解码
- 从当前PE反推市场隐含的增长率预期
- 与历史增速和行业增速对比，判断预期是否合理

#### 5.3 期权价值识别
- 识别公司可能存在的期权价值（新业务、新技术、市场拓展等）
- 评估期权价值的实现概率和潜在规模

#### 5.4 博弈论对冲分析
- 分析公司在行业博弈中的位置（领导者/挑战者/追随者）
- 主要竞争对手的策略和可能的博弈演化
- 公司的博弈优势（定价权、成本优势、技术壁垒等）

#### 5.5 时间墙与终值回归
- 判断当前估值中的"时间墙"（需要多长时间消化当前估值）
- 终值回归分析（在保守/中性/乐观情景下的预期回报）

### 六、投资总结
- 综合评级（买入/增持/持有/减持/卖出）
- 置信度（高/中/低）
- 建议持有期（短线/中长线/长期）
- 核心投资逻辑（3-5句话）
- 关键风险提示（3-5条）
- 建议仓位和止损位参考

## 写作要求

1. **严格基于数据**：所有分析必须引用提供的真实数据，不得编造任何数据。如果某项数据缺失，明确标注"数据不足"。
2. **专业简洁**：使用bullet points，语言精炼专业，避免空洞套话。
3. **数据驱动**：每个结论都要有数据支撑，用数字说话。
4. **多空平衡**：红蓝对抗必须真实深入，不能敷衍了事。
5. **Markdown格式**：正确使用表格、列表、加粗等Markdown语法。
6. **报告头部**：标题使用"# {股票名称}（{代码}）深度研究报告"，包含生成时间、市场、行业、最新价格、涨跌幅、数据来源等信息。
7. **不要使用任何占位符或模板标记**：所有内容必须是完整的分析文本。
"""


def _build_data_summary(
    symbol: str,
    name: str,
    market: str,
    price: float,
    change_pct: float,
    fin: Dict[str, Any],
    debate: Dict[str, Any],
    quote: Dict[str, Any],
) -> str:
    """构建数据摘要，作为AI的用户输入"""
    
    market_name = "A股" if market == "A" else "美股"
    
    summary = f"""请根据以下真实数据，为{name}（{symbol}）生成一份{market_name}深度研究报告。

## 基础行情数据
- 股票名称：{name}
- 股票代码：{symbol}
- 市场：{market_name}
- 最新价格：{price}元
- 涨跌幅：{change_pct:+.2f}%
- 今日最高：{quote.get('high', 'N/A')}
- 今日最低：{quote.get('low', 'N/A')}
- 今日开盘：{quote.get('open', 'N/A')}
- 昨收：{quote.get('pre_close', 'N/A')}
- 成交额：{quote.get('amount', 'N/A')}

## 核心财务数据
- 市盈率(PE-TTM)：{fin.get('pe', 'N/A')}x
- 市净率(PB)：{fin.get('pb', 'N/A')}x
- 总市值：{fin.get('market_cap', 'N/A')}亿
- 净资产收益率(ROE)：{fin.get('roe', 'N/A')}%
- 每股收益(EPS)：{fin.get('eps', 'N/A')}元
- 资产负债率：{fin.get('debt_ratio', 'N/A')}%
- PEG：{fin.get('peg', 'N/A')}
- 净利润：{fin.get('net_profit', 'N/A')}亿
- 营收：{fin.get('revenue', 'N/A')}亿
- 自由现金流：{fin.get('fcf', 'N/A')}亿
- 经营现金流：{fin.get('oper_cf', 'N/A')}亿
- 商誉/净资产：{fin.get('goodwill_ratio', 'N/A')}%
- 行业：{fin.get('industry', '未知')}

## 营收增速趋势
{_format_list_with_dates(fin.get('revenue_growth', []), fin.get('trend_dates', []), '%')}
- 近4期平均营收增速：{fin.get('avg_revenue_growth', 'N/A')}%

## 利润增速趋势
{_format_list_with_dates(fin.get('profit_growth', []), fin.get('trend_dates', []), '%')}
- 近4期平均利润增速：{fin.get('avg_profit_growth', 'N/A')}%

## 毛利率与净利率趋势
{_format_list_with_dates(fin.get('gross_margin', []), fin.get('trend_dates', []), '%')}
{_format_list_with_dates(fin.get('net_margin', []), fin.get('trend_dates', []), '%')}
- 平均毛利率：{fin.get('avg_gross_margin', 'N/A')}%
- 平均净利率：{fin.get('avg_net_margin', 'N/A')}%

## 同行对比数据
- 同行公司：{', '.join(fin.get('peer_names', [])) if fin.get('peer_names') else '无'}
- 同行PE列表：{fin.get('peer_pe', [])}
- 同行PB列表：{fin.get('peer_pb', [])}
- 同行ROE列表：{fin.get('peer_roe', [])}
- 同行营收增速列表：{fin.get('peer_growth', [])}
- 同行市值列表(亿)：{fin.get('peer_mcap', [])}
- 行业平均PE：{fin.get('avg_peer_pe', 'N/A')}x
- 行业平均PB：{fin.get('avg_peer_pb', 'N/A')}x
- 行业平均ROE：{fin.get('avg_peer_roe', 'N/A')}%
- 行业平均增速：{fin.get('avg_peer_growth', 'N/A')}%

## 利润表明细
{_format_income_statement(fin.get('income_statement', []))}

## 资产负债表
{_format_balance_sheet(fin.get('balance_sheet', {}))}

## 现金流量表
{_format_cashflow_statement(fin.get('cashflow_statement', []))}

## 主营构成
{_format_revenue_segment(fin.get('revenue_segment', {}))}

## 运营效率指标
{_format_operating_efficiency(fin.get('operating_efficiency', {}))}

## 分析师评级
{_format_analyst(fin.get('analyst', {}), price)}

## 机构持仓
{_format_institutional(fin.get('institutional', {}))}

## 北向资金
{_format_northbound(fin.get('northbound', {}))}

## 估值分位
{_format_valuation_percentile(fin.get('valuation_percentile', {}), fin.get('pe', 0))}

## 分红数据
{_format_dividend(fin.get('dividend', {}))}

## 增长质量
{_format_dict(fin.get('growth_quality', {}))}

## 人均效率
{_format_dict(fin.get('per_capita', {}))}

## 股东结构
{_format_dict(fin.get('shareholder', {}))}

## 财务异常检测
{_format_dict(fin.get('financial_anomaly', {}))}

## 业绩预告
{_format_earnings_forecast(fin.get('earnings_forecast', []))}

## 限售股解禁
{_format_dict(fin.get('lockup_shares', {}))}

## 红蓝对抗预分析
- 多方得分：{debate.get('red_score', 0)}/100
- 空方得分：{debate.get('blue_score', 0)}/100
- 多空差值：{debate.get('score_diff', 0)}
- 综合结论：{debate.get('verdict', '')}
- 多方论点：{json.dumps(debate.get('red_arguments', []), ensure_ascii=False)}
- 空方论点：{json.dumps(debate.get('blue_arguments', []), ensure_ascii=False)}

## 数据来源
- 数据来源标识：{fin.get('source', 'unknown')}
- 是否为模拟数据：{fin.get('is_mock', True)}

请严格按照系统提示词中的六个模块要求，生成完整的深度研究报告。所有分析必须基于以上真实数据，不要编造任何数据。如果某项数据缺失，请明确标注"数据不足"。
"""
    return summary


def _format_list_with_dates(values, dates, suffix=""):
    if not values:
        return "- 数据不足"
    lines = []
    for i, v in enumerate(values):
        dt = dates[i] if dates and i < len(dates) else f"第{i+1}期"
        lines.append(f"  - {dt}: {v:+.1f}{suffix}" if isinstance(v, (int, float)) else f"  - {dt}: {v}{suffix}")
    return "\n".join(lines)


def _format_income_statement(income_stmt):
    if not income_stmt:
        return "- 数据不足"
    lines = []
    for row in income_stmt[:3]:
        date = row.get('report_date', '')[:7]
        rev = row.get('revenue', 0) / 100000000
        cost = row.get('operate_cost', 0) / 100000000
        op = row.get('operate_profit', 0) / 100000000
        np_val = row.get('net_profit', 0) / 100000000
        lines.append(f"  - {date}: 营收{rev:.1f}亿, 营业成本{cost:.1f}亿, 营业利润{op:.1f}亿, 净利润{np_val:.1f}亿")
    return "\n".join(lines) if lines else "- 数据不足"


def _format_balance_sheet(bs):
    if not bs or bs.get('total_assets', 0) <= 0:
        return "- 数据不足"
    ta = bs.get('total_assets', 0) / 100000000
    tl = bs.get('total_liabilities', 0) / 100000000
    te = bs.get('total_equity', 0) / 100000000
    return f"  - 总资产: {ta:.1f}亿, 总负债: {tl:.1f}亿, 净资产: {te:.1f}亿"


def _format_cashflow_statement(cf_stmt):
    if not cf_stmt:
        return "- 数据不足"
    lines = []
    for row in cf_stmt[:3]:
        date = row.get('report_date', '')[:4]
        oc = row.get('operate_cf', 0) / 100000000
        ic = row.get('invest_cf', 0) / 100000000
        fc = row.get('finance_cf', 0) / 100000000
        lines.append(f"  - {date}: 经营CF {oc:.1f}亿, 投资CF {ic:.1f}亿, 筹资CF {fc:.1f}亿")
    return "\n".join(lines) if lines else "- 数据不足"


def _format_revenue_segment(rev_seg):
    if not rev_seg:
        return "- 数据不足"
    seg_to_show = rev_seg.get('product', []) or rev_seg.get('industry', [])
    if not seg_to_show:
        return "- 数据不足"
    lines = []
    for item in seg_to_show[:5]:
        lines.append(f"  - {item['name']}: 营收占比{item['ratio']:.1f}%, 毛利率{item['margin']:.1f}%")
    return "\n".join(lines)


def _format_operating_efficiency(eff):
    if not eff:
        return "- 数据不足"
    items = []
    for k, v in eff.items():
        if isinstance(v, (int, float)):
            items.append(f"  - {k}: {v:.2f}")
        else:
            items.append(f"  - {k}: {v}")
    return "\n".join(items) if items else "- 数据不足"


def _format_analyst(analyst, price):
    if not analyst or analyst.get('total_ratings', 0) <= 0:
        return "- 数据不足"
    lines = [f"  - 综合评级: {analyst.get('compre_rating', 'N/A')}"]
    lines.append(f"  - 评级机构数: {analyst.get('total_ratings', 0)}")
    lines.append(f"  - 买入/增持占比: {analyst.get('buy_pct', 0):.0f}%")
    eps_forecasts = analyst.get('eps_forecasts', [])
    for fc in eps_forecasts[:3]:
        fc_pe = price / fc['eps'] if price > 0 and fc['eps'] > 0 else 0
        lines.append(f"  - {fc['year']}E EPS: {fc['eps']:.2f}元 (对应PE {fc_pe:.1f}x)")
    return "\n".join(lines)


def _format_institutional(inst):
    if not inst:
        return "- 数据不足"
    lines = []
    if inst.get('fund_count', 0) > 0:
        lines.append(f"  - 基金持股家数: {inst['fund_count']}, 持股比例: {inst.get('fund_ratio', 0):.1f}%")
    if inst.get('institutional_ratio', 0) > 0:
        lines.append(f"  - 机构合计持股: {inst['institutional_ratio']:.1f}%")
    for h in inst.get('top_holders', [])[:5]:
        lines.append(f"  - {h['name']} ({h.get('type', '')}): {h['ratio']:.2f}%")
    return "\n".join(lines) if lines else "- 数据不足"


def _format_northbound(nb):
    if not nb or nb.get('hold_ratio', 0) <= 0:
        return "- 数据不足"
    return f"  - 持股比例: {nb['hold_ratio']:.2f}%, 持股市值: {nb.get('hold_market_cap', 0):.1f}亿, 近期变动: {nb.get('hold_change', 0):+.2f}pp"


def _format_valuation_percentile(vp, pe):
    if not vp or vp.get('pe_percentile', 0) <= 0:
        return "- 数据不足"
    return f"  - PE {pe}x 处于 {vp['pe_range_low']:.0f}~{vp['pe_range_high']:.0f}x 的 {vp['pe_percentile']:.0f}% 分位"


def _format_dividend(div):
    if not div or div.get('dividend_yield', 0) <= 0:
        return "- 数据不足"
    lines = [f"  - 股息率: {div.get('dividend_yield', 0):.2f}%"]
    if div.get('cash_per_share', 0) > 0:
        lines.append(f"  - 每股分红: {div['cash_per_share']:.2f}元")
    if div.get('plan'):
        lines.append(f"  - 分红方案: {div['plan']}")
    return "\n".join(lines)


def _format_earnings_forecast(forecasts):
    if not forecasts:
        return "- 数据不足"
    lines = []
    for fc in forecasts[:3]:
        lines.append(f"  - {fc['notice_date']} {fc['report_date']}: {fc['predict_type']}, 净利润 {fc['amt_lower']/100000000:.1f}~{fc['amt_upper']/100000000:.1f}亿, 增速 {fc['add_amp_lower']:+.1f}%~{fc['add_amp_upper']:+.1f}%")
    return "\n".join(lines)


def _format_dict(data):
    if not data:
        return "- 数据不足"
    lines = []
    for k, v in data.items():
        if isinstance(v, (int, float)):
            lines.append(f"  - {k}: {v}")
        elif isinstance(v, list):
            lines.append(f"  - {k}: {v}")
        else:
            lines.append(f"  - {k}: {v}")
    return "\n".join(lines) if lines else "- 数据不足"