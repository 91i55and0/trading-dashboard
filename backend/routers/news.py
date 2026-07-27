"""
新闻推送路由
- 每日市场重要事件日报
- 硅谷顶级观点
- SEC EDGAR 13F 持仓监控
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import date

router = APIRouter()


@router.get("/daily-events")
def get_daily_events(
    date_str: str = Query(default=None, alias="date", description="日期 YYYY-MM-DD"),
):
    """获取每日市场重要事件日报"""
    from services.news_service import get_daily_market_events
    try:
        return get_daily_market_events(date_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
def get_insights(
    days: int = Query(default=3, description="获取最近N天的观点"),
):
    """获取硅谷顶级观点"""
    from services.news_service import get_silicon_valley_insights
    try:
        return get_silicon_valley_insights(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/13f")
def get_13f_monitor(
    lookback_days: int = Query(default=45, description="回溯天数"),
):
    """获取SEC EDGAR 13F持仓监控报告"""
    from services.news_service import get_13f_monitor
    try:
        return get_13f_monitor(lookback_days=lookback_days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/digest")
def get_news_digest():
    """获取综合新闻摘要"""
    from services.news_service import get_news_digest
    try:
        return get_news_digest()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))