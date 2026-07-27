"""
数据源配置管理 API

管理数据提供者：列出、切换、健康检查、积分消耗统计、第三方注册
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

router = APIRouter()


class ThirdPartyRegisterRequest(BaseModel):
    """第三方数据源注册请求"""
    name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    description: Optional[str] = None


class ActivateProviderRequest(BaseModel):
    """激活提供者请求"""
    name: str


@router.get("/list")
def list_providers():
    """列出所有已注册的数据提供者"""
    from data_providers import registry

    providers = registry.list_providers()
    return {
        "providers": providers,
        "total": len(providers),
    }


@router.get("/status")
def get_provider_status():
    """获取当前数据提供者状态"""
    from data_providers import registry, get_provider

    active = registry.get_active()
    active_name = getattr(active, 'name', None) if active else None

    health = {}
    try:
        provider = get_provider()
        health = provider.health_check()
    except Exception as e:
        health = {"status": "error", "error": str(e)}

    return {
        "active_provider": active_name,
        "providers": registry.list_providers(),
        "health": health,
        "timestamp": datetime.now().isoformat(),
    }


@router.put("/activate")
def activate_provider(req: ActivateProviderRequest):
    """切换激活的数据提供者"""
    from data_providers import registry

    if not registry.set_active(req.name):
        raise HTTPException(
            status_code=404,
            detail=f"数据提供者 '{req.name}' 不存在。可用: {[p['name'] for p in registry.list_providers()]}",
        )

    return {
        "status": "ok",
        "active_provider": req.name,
        "message": f"已切换到 {req.name}",
    }


@router.post("/third-party")
def register_third_party(req: ThirdPartyRegisterRequest):
    """注册第三方数据提供者（基于URL回调）"""
    from data_providers import ThirdPartyProvider, registry
    import httpx

    # 验证 URL 可访问性
    if req.base_url:
        try:
            resp = httpx.get(f"{req.base_url}/health", timeout=5)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"第三方数据源健康检查失败: HTTP {resp.status_code}",
                )
        except httpx.ConnectError:
            raise HTTPException(status_code=400, detail=f"无法连接到 {req.base_url}")
        except httpx.TimeoutException:
            raise HTTPException(status_code=400, detail=f"连接超时: {req.base_url}")

    # 创建第三方提供者
    provider = ThirdPartyProvider(name=req.name)
    provider._config = {
        "base_url": req.base_url,
        "api_key": req.api_key,
        "description": req.description,
        "registered_at": datetime.now().isoformat(),
    }

    # 如果提供了 base_url，注册HTTP回调
    if req.base_url:

        def _http_handler(method, endpoint, **kwargs):
            """通用HTTP调用处理器"""
            headers = {"Content-Type": "application/json"}
            if req.api_key:
                headers["Authorization"] = f"Bearer {req.api_key}"

            try:
                resp = httpx.post(
                    f"{req.base_url}{endpoint}",
                    json=kwargs,
                    headers=headers,
                    timeout=30,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"第三方数据源 {req.name} {method} 失败: {e}"
                )
                return None

        # 注册所有数据获取方法
        provider.register_handler(
            "get_spot_quote",
            lambda market="A": _http_handler("get_spot_quote", "/api/spot", market=market),
        )
        provider.register_handler(
            "get_stock_quote",
            lambda symbol, market="A": _http_handler("get_stock_quote", "/api/quote", symbol=symbol, market=market),
        )
        provider.register_handler(
            "get_kline",
            lambda symbol, market="A", period="daily", start_date="", end_date="", count=250, adjust="qfq": _http_handler(
                "get_kline", "/api/kline",
                symbol=symbol, market=market, period=period,
                start_date=start_date, end_date=end_date, count=count, adjust=adjust,
            ),
        )
        provider.register_handler(
            "get_stock_info",
            lambda symbol, market="A": _http_handler("get_stock_info", "/api/info", symbol=symbol, market=market),
        )
        provider.register_handler(
            "search_stocks",
            lambda keyword, market="A": _http_handler("search_stocks", "/api/search", keyword=keyword, market=market),
        )

    registry.register(provider, priority=200)
    return {
        "status": "ok",
        "name": req.name,
        "message": f"第三方数据提供者 '{req.name}' 注册成功",
    }


@router.get("/health")
def get_health():
    """获取所有数据提供者健康检查汇总"""
    from data_providers import registry

    results = {}
    for info in registry.list_providers():
        provider = registry.get(info["name"])
        if provider:
            try:
                results[info["name"]] = provider.health_check()
            except Exception as e:
                results[info["name"]] = {
                    "status": "error",
                    "error": str(e),
                }

    return {
        "providers": results,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/cost")
def get_cost_stats():
    """获取积分消耗统计"""
    from data_providers import registry

    active = registry.get_active()
    if active and hasattr(active, "_total_cost"):
        return {
            "provider": active.name,
            "total_cost": active._total_cost,
            "call_count": active._call_count,
            "avg_cost_per_call": (
                round(active._total_cost / active._call_count, 2)
                if active._call_count > 0
                else 0
            ),
            "timestamp": datetime.now().isoformat(),
        }

    return {
        "provider": None,
        "total_cost": 0,
        "call_count": 0,
        "message": "当前提供者不支持积分追踪",
    }


@router.delete("/third-party/{name}")
def unregister_third_party(name: str):
    """注销第三方数据提供者"""
    from data_providers import registry

    provider = registry.get(name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"提供者 '{name}' 不存在")

    if name == "akshare_proxy":
        raise HTTPException(status_code=400, detail="不能删除内置默认提供者")

    registry.unregister(name)
    return {"status": "ok", "message": f"提供者 '{name}' 已注销", "name": name}