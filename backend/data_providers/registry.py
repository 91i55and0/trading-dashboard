"""
数据提供者注册中心

管理多个数据提供者，支持优先级排序和自动故障转移。
"""
from typing import Dict, List, Optional, Type
from .base import BaseDataProvider


class ProviderRegistry:
    """数据提供者注册中心（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers: Dict[str, BaseDataProvider] = {}
            cls._instance._priority: List[str] = []  # 优先级排序的提供者名称列表
            cls._instance._active_provider: Optional[str] = None
        return cls._instance

    def register(self, provider: BaseDataProvider, priority: int = 100) -> None:
        """
        注册数据提供者

        Args:
            provider: 数据提供者实例
            priority: 优先级（越小越高，默认100）
        """
        self._providers[provider.name] = provider

        # 按优先级插入
        inserted = False
        for i, name in enumerate(self._priority):
            existing = self._providers.get(name)
            if existing and getattr(existing, '_priority', 100) > priority:
                self._priority.insert(i, provider.name)
                inserted = True
                break
        if not inserted:
            self._priority.append(provider.name)

        # 存储优先级
        provider._priority = priority

        # 自动激活第一个
        if self._active_provider is None:
            self._active_provider = provider.name

    def unregister(self, name: str) -> None:
        """注销数据提供者"""
        if name in self._providers:
            del self._providers[name]
        if name in self._priority:
            self._priority.remove(name)
        if self._active_provider == name:
            self._active_provider = self._priority[0] if self._priority else None

    def get(self, name: str) -> Optional[BaseDataProvider]:
        """获取指定名称的提供者"""
        return self._providers.get(name)

    def get_active(self) -> Optional[BaseDataProvider]:
        """获取当前激活的提供者"""
        if self._active_provider:
            return self._providers.get(self._active_provider)
        return None

    def set_active(self, name: str) -> bool:
        """设置激活的提供者"""
        if name in self._providers:
            self._active_provider = name
            return True
        return False

    def get_available_provider(self) -> Optional[BaseDataProvider]:
        """
        获取可用的提供者（自动故障转移）
        按优先级顺序尝试，返回第一个健康可用的
        """
        # 先尝试当前激活的
        active = self.get_active()
        if active and active.enabled:
            try:
                health = active.health_check()
                if health.get("status") == "ok":
                    return active
            except Exception:
                pass

        # 按优先级尝试其他提供者
        for name in self._priority:
            provider = self._providers.get(name)
            if not provider or not provider.enabled:
                continue
            try:
                health = provider.health_check()
                if health.get("status") == "ok":
                    self._active_provider = name
                    return provider
            except Exception:
                continue

        return None

    def list_providers(self) -> List[Dict]:
        """列出所有提供者"""
        result = []
        for name in self._priority:
            provider = self._providers.get(name)
            if provider:
                result.append({
                    "name": name,
                    "type": provider.__class__.__name__,
                    "enabled": provider.enabled,
                    "active": name == self._active_provider,
                    "priority": getattr(provider, '_priority', 100),
                })
        return result

    def __len__(self):
        return len(self._providers)


# 全局注册中心实例
registry = ProviderRegistry()