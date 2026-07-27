"""
数据提供者模块

提供统一的数据获取接口，支持：
- 内置默认 AKShare 代理提供者
- 第三方数据源接入
- 自动故障转移和积分消耗优化
"""
from .base import BaseDataProvider
from .registry import ProviderRegistry, registry
from .default_provider import DefaultAKShareProvider
from .third_party import ThirdPartyProvider, register_third_party


def init_default_provider() -> DefaultAKShareProvider:
    """初始化并注册默认数据提供者"""
    provider = DefaultAKShareProvider()
    registry.register(provider, priority=10)
    return provider


def get_provider() -> BaseDataProvider:
    """获取当前可用的数据提供者（自动故障转移）"""
    provider = registry.get_available_provider()
    if provider is None:
        # 回退：尝试初始化默认提供者
        provider = init_default_provider()
    return provider


# 自动初始化默认提供者
try:
    _default = init_default_provider()
except Exception:
    pass