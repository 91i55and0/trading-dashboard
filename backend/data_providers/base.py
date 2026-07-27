"""
数据提供者抽象基类

所有数据提供者（内置/第三方）必须实现此接口。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd


class BaseDataProvider(ABC):
    """数据提供者抽象基类"""

    def __init__(self, name: str = "base"):
        self.name = name
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    # ==================== 行情数据 ====================

    @abstractmethod
    def get_spot_quote(self, market: str = "A") -> pd.DataFrame:
        """获取实时行情快照"""
        ...

    @abstractmethod
    def get_stock_quote(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """获取单只股票实时行情"""
        ...

    # ==================== K线数据 ====================

    @abstractmethod
    def get_kline(
        self,
        symbol: str,
        market: str = "A",
        period: str = "daily",
        start_date: str = "",
        end_date: str = "",
        count: int = 250,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """获取K线数据"""
        ...

    # ==================== 基本面数据 ====================

    @abstractmethod
    def get_stock_info(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """获取个股基本面信息"""
        ...

    @abstractmethod
    def get_financial_data(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """获取个股深度财务数据（用于研报生成）"""
        ...

    # ==================== 搜索 ====================

    @abstractmethod
    def search_stocks(self, keyword: str, market: str = "A") -> List[Dict[str, Any]]:
        """搜索股票"""
        ...

    # ==================== 行业板块 ====================

    @abstractmethod
    def get_industry_list(self, market: str = "A") -> pd.DataFrame:
        """获取行业板块列表"""
        ...

    # ==================== 资金流向 ====================

    @abstractmethod
    def get_fund_flow(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """获取个股资金流向"""
        ...

    @abstractmethod
    def get_sector_fund_flow_rank(self, market: str = "A") -> pd.DataFrame:
        """获取板块资金流向排名"""
        ...

    @abstractmethod
    def get_individual_fund_flow_rank(self, market: str = "A") -> pd.DataFrame:
        """获取个股资金流向排名"""
        ...

    # ==================== 市场数据 ====================

    @abstractmethod
    def get_cftc_report(self) -> Dict[str, Any]:
        """获取CFTC持仓报告"""
        ...

    @abstractmethod
    def get_cboe_put_call(self, days: int = 30) -> Dict[str, Any]:
        """获取CBOE Put/Call比率"""
        ...

    # ==================== 状态检查 ====================

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """检查数据源健康状态"""
        ...

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name})>"