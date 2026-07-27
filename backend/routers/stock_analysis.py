"""
个股分析路由
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict

router = APIRouter()


@router.get("/llm-providers")
def get_llm_providers():
    """获取可用的LLM Provider信息"""
    from services.deepseek_service import get_provider_info
    return get_provider_info()


class StockAnalysisRequest(BaseModel):
    """个股分析请求"""
    symbol: str
    market: str = "A"  # A= A股, US= 美股
    analysis_types: List[str] = ["technical", "fundamental", "valuation"]


class TechnicalIndicators(BaseModel):
    """技术指标"""
    ma5: float
    ma10: float
    ma20: float
    ma60: float
    rsi: float
    macd: float
    macd_signal: float
    macd_hist: float
    bollinger_upper: float
    bollinger_middle: float
    bollinger_lower: float
    volume_ratio: float


class FundamentalData(BaseModel):
    """基本面数据"""
    pe_ratio: float
    pb_ratio: float
    market_cap: float
    revenue_growth: float
    profit_growth: float
    roe: float
    debt_ratio: float
    dividend_yield: float


class StockAnalysisResult(BaseModel):
    """个股分析结果"""
    symbol: str
    name: str
    market: str
    latest_price: float
    change_pct: float
    technical: Optional[TechnicalIndicators]
    fundamental: Optional[FundamentalData]
    analysis_summary: str
    signals: List[Dict[str, str]]
    risk_level: str
    charts: Optional[dict]


@router.get("/search")
def search_stock(
    keyword: str = Query(...),
    market: str = Query(default="A", description="市场: A=A股, US=美股"),
):
    """搜索股票"""
    from services.stock_analysis_service import search_stock
    try:
        return search_stock(keyword, market=market)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote")
def get_quote(
    symbol: str = Query(...),
    market: str = Query(default="A"),
):
    """获取实时行情"""
    from services.stock_analysis_service import get_quote
    try:
        return get_quote(symbol, market)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
def analyze_stock(req: StockAnalysisRequest):
    """执行个股分析"""
    from services.stock_analysis_service import analyze_stock_service
    try:
        return analyze_stock_service(
            symbol=req.symbol,
            market=req.market,
            analysis_types=req.analysis_types,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kline")
def get_kline(
    symbol: str = Query(...),
    market: str = Query(default="A"),
    period: str = Query(default="daily"),
    count: int = Query(default=250),
):
    """获取K线数据"""
    from services.stock_analysis_service import get_kline_data
    try:
        return get_kline_data(symbol, market, period, count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ResearchReportRequest(BaseModel):
    """研报生成请求"""
    symbol: str
    market: str = "A"
    deep_analysis: bool = True
    llm_config: Optional["LLMConfig"] = None


class LLMConfig(BaseModel):
    """用户自定义LLM配置"""
    provider: str = "deepseek"  # deepseek / openai / custom
    api_key: str = ""
    base_url: str = ""   # custom时必填
    model: str = ""       # custom时必填


@router.post("/research-report")
def generate_research_report(req: ResearchReportRequest):
    """生成个股深度研报"""
    from services.stock_analysis_service import generate_research_report
    try:
        llm_cfg = req.llm_config.model_dump() if req.llm_config else None
        return generate_research_report(
            symbol=req.symbol,
            market=req.market,
            deep_analysis=req.deep_analysis,
            llm_config=llm_cfg,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))