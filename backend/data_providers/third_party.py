"""
第三方数据提供者接口

允许用户注册自定义数据源，只需实现 BaseDataProvider 抽象方法即可。
"""
from typing import Dict, Any, List, Optional, Callable
import pandas as pd

from .base import BaseDataProvider
from .registry import registry


class ThirdPartyProvider(BaseDataProvider):
    """
    第三方数据提供者

    用户可以通过注册回调函数来接入自定义数据源。
    支持两种方式：
    1. 继承 BaseDataProvider 实现完整接口
    2. 使用此 ThirdPartyProvider 注册单个回调函数
    """

    def __init__(self, name: str = "third_party"):
        super().__init__(name=name)
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, method: str, handler: Callable):
        """
        注册单个数据获取处理器

        Args:
            method: 方法名，如 'get_kline', 'get_spot_quote' 等
            handler: 回调函数，接收与原方法相同的参数
        """
        self._handlers[method] = handler

    def _call_handler(self, method: str, *args, **kwargs):
        """调用注册的处理器，未注册则返回 None"""
        handler = self._handlers.get(method)
        if handler:
            return handler(*args, **kwargs)
        return None

    # ==================== 行情数据 ====================

    def get_spot_quote(self, market: str = "A") -> pd.DataFrame:
        result = self._call_handler("get_spot_quote", market=market)
        if result is not None:
            return result
        return pd.DataFrame()

    def get_stock_quote(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        result = self._call_handler("get_stock_quote", symbol=symbol, market=market)
        if result is not None:
            return result
        return {"symbol": symbol, "name": symbol, "price": 0}

    # ==================== K线数据 ====================

    def get_kline(
        self, symbol: str, market: str = "A", period: str = "daily",
        start_date: str = "", end_date: str = "", count: int = 250,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        result = self._call_handler(
            "get_kline", symbol=symbol, market=market, period=period,
            start_date=start_date, end_date=end_date, count=count, adjust=adjust,
        )
        if result is not None:
            return result
        return pd.DataFrame()

    # ==================== 基本面数据 ====================

    def get_stock_info(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        result = self._call_handler("get_stock_info", symbol=symbol, market=market)
        if result is not None:
            return result
        return {}

    def get_financial_data(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """获取个股深度财务数据"""
        result = self._call_handler("get_financial_data", symbol=symbol, market=market)
        if result is not None:
            return result
        return {"basic": {}, "growth": {}, "profitability": {}, "peers": [], "source": "mock", "_mock": True}

    # ==================== 搜索 ====================

    def search_stocks(self, keyword: str, market: str = "A") -> List[Dict[str, Any]]:
        result = self._call_handler("search_stocks", keyword=keyword, market=market)
        if result is not None:
            return result
        return []

    # ==================== 行业板块 ====================

    def get_industry_list(self, market: str = "A") -> pd.DataFrame:
        result = self._call_handler("get_industry_list", market=market)
        if result is not None:
            return result
        return pd.DataFrame()

    # ==================== 资金流向 ====================

    def get_fund_flow(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        result = self._call_handler("get_fund_flow", symbol=symbol, market=market)
        if result is not None:
            return result
        return {}

    def get_sector_fund_flow_rank(self, market: str = "A") -> pd.DataFrame:
        result = self._call_handler("get_sector_fund_flow_rank", market=market)
        if result is not None:
            return result
        return pd.DataFrame()

    def get_individual_fund_flow_rank(self, market: str = "A") -> pd.DataFrame:
        result = self._call_handler("get_individual_fund_flow_rank", market=market)
        if result is not None:
            return result
        return pd.DataFrame()

    # ==================== 市场数据 ====================

    def get_cftc_report(self) -> Dict[str, Any]:
        result = self._call_handler("get_cftc_report")
        if result is not None:
            return result
        return {"items": []}

    def get_cboe_put_call(self, days: int = 30) -> Dict[str, Any]:
        result = self._call_handler("get_cboe_put_call", days=days)
        if result is not None:
            return result
        return {"data": []}

    # ==================== 健康检查 ====================

    def health_check(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": "ok" if self._handlers else "unconfigured",
            "handlers": list(self._handlers.keys()),
            "type": "third_party",
        }


def register_third_party(name: str, **handlers: Callable) -> ThirdPartyProvider:
    """
    便捷函数：注册第三方数据提供者

    Usage:
        provider = register_third_party(
            name="my_provider",
            get_kline=my_kline_func,
            get_stock_quote=my_quote_func,
        )
    """
    provider = ThirdPartyProvider(name=name)
    for method, handler in handlers.items():
        provider.register_handler(method, handler)
    registry.register(provider, priority=200)  # 第三方默认低优先级
    return provider