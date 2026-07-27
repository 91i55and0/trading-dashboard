"""
市场数据路由 - CFTC持仓报告 + CBOE Put/Call比率
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

router = APIRouter()


# ============================================================================
# CFTC 持仓报告
# ============================================================================

@router.get("/cftc/refresh")
def refresh_cftc():
    """强制刷新CFTC数据（跳过缓存，直接请求CFTC Socrata API，需VPN/代理）"""
    from services.cftc_service import get_latest_cftc_report
    try:
        report = get_latest_cftc_report(force_refresh=True)
        return {
            "success": True,
            "message": "CFTC 数据刷新成功",
            "data": report,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"CFTC 数据获取失败: {str(e)}。请确保 VPN/代理已开启，或设置 CFTC_PROXY 环境变量。"
        )


@router.get("/cftc/latest")
def get_cftc_latest():
    """获取最新CFTC持仓报告（完整版：TFF + Disaggregated + 分析报告）"""
    from services.cftc_service import get_latest_cftc_report
    try:
        return get_latest_cftc_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cftc/analysis")
def get_cftc_analysis():
    """获取CFTC持仓分析报告（仅分析部分）"""
    from services.cftc_service import get_latest_cftc_report
    try:
        report = get_latest_cftc_report()
        return {
            "report_date": report.get("report_date"),
            "analysis": report.get("analysis"),
            "source": report.get("source"),
            "updated_at": report.get("updated_at"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cftc/tff")
def get_cftc_tff():
    """获取TFF杠杆基金持仓数据"""
    from services.cftc_service import get_latest_cftc_report
    try:
        report = get_latest_cftc_report()
        return {
            "report_date": report.get("report_date"),
            "items": report.get("tff_items", []),
            "source": report.get("source"),
            "updated_at": report.get("updated_at"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cftc/disagg")
def get_cftc_disagg():
    """获取Disaggregated管理资金持仓数据"""
    from services.cftc_service import get_latest_cftc_report
    try:
        report = get_latest_cftc_report()
        return {
            "report_date": report.get("report_date"),
            "items": report.get("disagg_items", []),
            "source": report.get("source"),
            "updated_at": report.get("updated_at"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cftc/history")
def get_cftc_history(
    commodity: str = Query(default="", description="商品名称"),
    weeks: int = Query(default=12, description="周数"),
):
    """获取CFTC历史持仓数据"""
    from services.cftc_service import get_cftc_history
    try:
        return get_cftc_history(commodity=commodity, weeks=weeks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CBOE Put/Call 比率
# ============================================================================

@router.get("/cboe/putcall")
def get_put_call_ratio(
    days: int = Query(default=30, description="天数"),
):
    """获取CBOE Put/Call比率数据"""
    from services.cboe_service import get_put_call_data
    try:
        return get_put_call_data(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cboe/analysis")
def get_put_call_analysis():
    """获取Put/Call比率每日分析报告（完整版）"""
    from services.cboe_service import get_put_call_analysis
    try:
        return get_put_call_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cboe/latest")
def get_put_call_latest():
    """获取最新Put/Call比率（仅当前值）"""
    from services.cboe_service import get_put_call_analysis
    try:
        analysis = get_put_call_analysis()
        return {
            "current_ratio": analysis.get("current_ratio"),
            "current_equity_ratio": analysis.get("current_equity_ratio"),
            "current_index_ratio": analysis.get("current_index_ratio"),
            "sentiment": analysis.get("sentiment"),
            "trend": analysis.get("trend"),
            "risk_level": analysis.get("risk_level"),
            "source": analysis.get("source"),
            "analysis_time": analysis.get("analysis_time"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CFTC 持续跟踪报告
# ============================================================================

@router.get("/cftc/tracking")
def get_cftc_tracking(force_refresh: bool = Query(default=False)):
    """获取CFTC持续跟踪报告（含周度变化、趋势信号、解读）"""
    from services.cftc_tracking import generate_tracking_report
    try:
        return generate_tracking_report(force_refresh=force_refresh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cftc/tracking/{instrument}")
def get_cftc_instrument_tracking(
    instrument: str,
    weeks: int = Query(default=12, description="追踪周数"),
):
    """获取单个品种的持续跟踪数据"""
    from services.cftc_tracking import get_instrument_tracking
    try:
        return get_instrument_tracking(instrument=instrument, weeks=weeks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CBOE Put/Call 持续跟踪报告
# ============================================================================

@router.get("/cboe/tracking")
def get_cboe_tracking():
    """获取CBOE Put/Call持续跟踪报告（含日度变化、累积信号、解读）"""
    from services.cboe_tracking import generate_tracking_report
    try:
        return generate_tracking_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cboe/tracking/daily")
def get_cboe_daily_comparison(days: int = Query(default=7)):
    """获取CBOE日度对比数据"""
    from services.cboe_tracking import get_daily_comparison
    try:
        return get_daily_comparison(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SSE 上交所ETF期权 Put/Call 比率
# ============================================================================

@router.get("/sse/options/daily")
def get_sse_options_daily(date: str = Query(default="", description="日期，格式YYYYMMDD，默认最新")):
    """获取上交所ETF期权每日统计数据"""
    from services.sse_options_service import get_daily_stats
    try:
        date_str = date if date else None
        return get_daily_stats(date_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sse/options/analysis")
def get_sse_options_analysis():
    """获取SSE Put/Call比率分析报告（完整版）"""
    from services.sse_options_service import get_sse_put_call_analysis
    try:
        return get_sse_put_call_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sse/options/latest")
def get_sse_options_latest():
    """获取最新SSE Put/Call比率（仅当前值）"""
    from services.sse_options_service import get_sse_put_call_analysis
    try:
        analysis = get_sse_put_call_analysis()
        return {
            "date": analysis.get("date"),
            "current_pc_ratio_volume": analysis.get("current_pc_ratio_volume"),
            "current_pc_ratio_oi": analysis.get("current_pc_ratio_oi"),
            "sentiment": analysis.get("sentiment"),
            "trend": analysis.get("trend"),
            "risk_level": analysis.get("risk_level"),
            "signal": analysis.get("signal"),
            "source": analysis.get("source"),
            "analysis_time": analysis.get("analysis_time"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sse/options/history")
def get_sse_options_history(days: int = Query(default=30, description="天数")):
    """获取SSE期权历史数据"""
    from services.sse_options_service import get_sse_history
    try:
        return get_sse_history(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sse/options/tracking")
def get_sse_options_tracking():
    """获取SSE Put/Call持续跟踪报告"""
    from services.sse_options_service import get_sse_tracking
    try:
        return get_sse_tracking()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 市场数据总览
# ============================================================================

@router.get("/overview")
def get_market_overview():
    """获取市场数据总览"""
    from services.cftc_service import get_latest_cftc_report
    from services.cboe_service import get_put_call_analysis
    try:
        cftc = get_latest_cftc_report()
        put_call = get_put_call_analysis()

        # SSE 期权数据（可选，失败不影响总览）
        sse_options = None
        try:
            from services.sse_options_service import get_sse_put_call_analysis
            sse_analysis = get_sse_put_call_analysis()
            sse_options = {
                "date": sse_analysis.get("date"),
                "current_pc_ratio_volume": sse_analysis.get("current_pc_ratio_volume"),
                "current_pc_ratio_oi": sse_analysis.get("current_pc_ratio_oi"),
                "sentiment": sse_analysis.get("sentiment"),
                "trend": sse_analysis.get("trend"),
                "risk_level": sse_analysis.get("risk_level"),
                "signal": sse_analysis.get("signal"),
                "source": sse_analysis.get("source"),
            }
        except Exception:
            pass

        return {
            "cftc": {
                "report_date": cftc.get("report_date"),
                "analysis": cftc.get("analysis"),
                "source": cftc.get("source"),
            },
            "put_call": {
                "current_ratio": put_call.get("current_ratio"),
                "sentiment": put_call.get("sentiment"),
                "trend": put_call.get("trend"),
                "risk_level": put_call.get("risk_level"),
                "signal": put_call.get("signal"),
                "report": put_call.get("report"),
                "source": put_call.get("source"),
            },
            "sse_options": sse_options,
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))