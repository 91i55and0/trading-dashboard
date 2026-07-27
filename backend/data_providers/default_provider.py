"""
默认 AKShare 代理数据提供者

通过 AKShare 代理网关获取数据，支持：
- 积分消耗感知的 API 选择（优先低消耗）
- 自动故障降级（一个 API 不可用时切换下一个）
- 多线程加速（支持的函数列表）
- Token 认证
"""
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime

import pandas as pd
import numpy as np

from .base import BaseDataProvider

logger = logging.getLogger(__name__)

# ==================== 配置 ====================

# 代理网关配置
PROXY_GATEWAY = "https://ak.cheapproxy.net/dashboard/akshare"
PROXY_HOST = "101.201.173.125"
PROXY_TOKEN = "20260718K92YUFOB"

# 积分消耗表 (API名称 -> 消耗积分)
API_COST_MAP = {
    # 行情快照
    "stock_zh_a_spot_em": 10,
    "stock_sh_a_spot_em": 8,
    # K线
    "stock_zh_a_hist": 2,
    "stock_zh_a_hist_min_em": 1,
    "stock_us_hist": 2,
    # 个股信息
    "stock_individual_info_em": 2,
    # 行业板块
    "stock_board_industry_name_em": 4,
    "stock_board_industry_cons_em": 4,
    # 资金流向
    "stock_individual_fund_flow": 1,
    "stock_individual_fund_flow_rank": 5,
    "stock_sector_fund_flow_rank": 2,
    # 基金
    "fund_money_fund_info_em": 5,
    "fund_graded_fund_info_em": 5,
    "fund_etf_fund_info_em": 5,
    "fund_fh_em": 5,
    "fund_cf_em": 5,
    "fund_fh_rank_em": 5,
    # 美股
    "stock_us_spot_em": 10,
    "stock_us_fundamental": 5,
    "stock_us_profit": 5,
    # 财务数据
    "stock_financial_abstract_ths": 5,
    "stock_board_industry_cons_em": 4,
    "stock_yjbb_em": 3,
}

# 支持多线程加速的函数列表
MULTITHREAD_FUNCTIONS = {
    "stock_zh_a_spot_em",
    "stock_sh_a_spot_em",
    "stock_board_industry_cons_em",
    "stock_individual_fund_flow_rank",
    "stock_sector_fund_flow_rank",
    "fund_money_fund_info_em",
    "fund_graded_fund_info_em",
    "fund_etf_fund_info_em",
    "fund_fh_em",
    "fund_cf_em",
    "fund_fh_rank_em",
}

# 同功能 API 备选方案（按积分消耗从低到高排序）
API_FALLBACK_MAP = {
    "get_spot_quote": [
        ("stock_zh_a_spot_em", 10),
        ("stock_sh_a_spot_em", 8),
    ],
    "get_kline": [
        ("stock_zh_a_hist", 2),
        ("stock_zh_a_hist_min_em", 1),
    ],
    "get_fund_flow_rank": [
        ("stock_individual_fund_flow_rank", 5),
        ("stock_sector_fund_flow_rank", 2),
    ],
}


class DefaultAKShareProvider(BaseDataProvider):
    """默认 AKShare 代理数据提供者"""

    def __init__(self):
        super().__init__(name="akshare_proxy")
        self._token = PROXY_TOKEN
        self._gateway = PROXY_GATEWAY
        self._host = PROXY_HOST
        self._total_cost = 0  # 累计积分消耗
        self._call_count = 0
        self._ak = None
        self._us_stock_cache = None  # 美股全量列表缓存
        self._us_stock_cache_time = 0
        self._a_stock_name_cache = None  # A股全量列表缓存
        self._a_stock_name_cache_time = 0
        self._spot_cache = None  # 行情快照缓存
        self._spot_cache_time = 0
        self._spot_cache_market = None
        self._init_akshare()

    def _init_akshare(self):
        """初始化 AKShare，配置代理"""
        try:
            import akshare as ak

            # 配置代理
            if hasattr(ak, 'set_proxy'):
                ak.set_proxy(self._gateway)

            # 设置 token
            os.environ["AKSHARE_TOKEN"] = self._token
            os.environ["AKSHARE_PROXY"] = self._gateway

            self._ak = ak
            logger.info(f"AKShare 初始化成功，网关: {self._gateway}")
        except ImportError:
            logger.warning("AKShare 未安装，使用模拟数据模式")
            self._ak = None
        except Exception as e:
            logger.error(f"AKShare 初始化失败: {e}")
            self._ak = None

    def _track_cost(self, api_name: str):
        """追踪积分消耗"""
        cost = API_COST_MAP.get(api_name, 1)
        self._total_cost += cost
        self._call_count += 1
        logger.debug(f"API: {api_name}, 消耗: {cost}, 累计: {self._total_cost}")

    def _ak_call_with_timeout(self, func: Callable, timeout: float = 10, *args, **kwargs):
        """带超时的AKShare API调用"""
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                raise TimeoutError(f"AKShare API 超时 ({timeout}s)")
            except Exception:
                raise

    def _call_with_fallback(
        self,
        fallback_key: str,
        default_func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        带降级的 API 调用
        按积分消耗从低到高尝试备选 API
        """
        fallbacks = API_FALLBACK_MAP.get(fallback_key, [])

        if not fallbacks:
            # 没有备选方案，直接调用
            return default_func(*args, **kwargs)

        # 按积分消耗排序
        fallbacks = sorted(fallbacks, key=lambda x: x[1])

        last_error = None
        for api_name, cost in fallbacks:
            try:
                self._track_cost(api_name)
                result = default_func(*args, **kwargs, _api_name=api_name)
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"API {api_name} (cost={cost}) 失败: {e}，尝试下一个...")
                continue

        raise last_error or RuntimeError(f"所有备选 API 均失败: {fallback_key}")

    def _safe_call(self, func: Callable, *args, **kwargs) -> Any:
        """安全调用，捕获异常并返回 None"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"API 调用失败: {e}")
            return None

    # ==================== 行情数据 ====================

    def get_spot_quote(self, market: str = "A") -> pd.DataFrame:
        """获取实时行情快照（东方财富 → 腾讯 → 新浪）"""
        if self._ak is None:
            return self._mock_spot_quote()

        # 30秒缓存，避免短时间内重复拉取全市场行情（如 quote + kline 连续调用）
        now = time.time()
        if self._spot_cache is not None and self._spot_cache_market == market and (now - self._spot_cache_time) < 30:
            return self._spot_cache

        # 美股行情
        if market.upper() == "US":
            return self._get_us_spot_quote(now)

        # 尝试多个数据源: 新浪（无代理）→ 东方财富 → 腾讯
        sources = [
            ("stock_zh_a_spot_sina", "新浪", lambda: self._fetch_spot_from_sina()),
            ("stock_zh_a_spot_em", "东方财富", lambda: self._ak_call_with_timeout(self._ak.stock_zh_a_spot_em, 10)),
            ("stock_zh_a_spot_tx", "腾讯", lambda: self._ak_call_with_timeout(self._ak.stock_zh_a_spot_tx, 10)),
        ]

        for api_name, source_name, fetch_func in sources:
            try:
                self._track_cost(api_name)
                df = fetch_func()
                if df is not None and not df.empty:
                    logger.info(f"行情快照获取成功 via {source_name}")
                    self._spot_cache = df
                    self._spot_cache_time = now
                    self._spot_cache_market = market
                    return df
            except Exception as e:
                logger.warning(f"行情快照 {source_name} ({api_name}) 失败: {e}")
                continue

        logger.warning("所有行情快照数据源均失败，使用模拟数据")
        return self._mock_spot_quote()

    def _fetch_spot_from_sina(self) -> Optional[pd.DataFrame]:
        """从新浪获取行情快照"""
        try:
            import requests
            import re

            # 获取上证指数 + 主要股票
            symbols = [
                "sh000001", "sh600519", "sz000858", "sh601318",
                "sz000333", "sh600036", "sz300750", "sz002594",
                "sh601857", "sh600276", "sz000001", "sh600030",
                "sz000002", "sh601166", "sz002415", "sh600900",
                "sz000651", "sh601398", "sz300059", "sh600809",
            ]
            url = "https://hq.sinajs.cn/list=" + ",".join(symbols)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://finance.sina.com.cn/',
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None

            data = []
            lines = resp.text.strip().split('\n')
            for line in lines:
                match = re.search(r'hq_str_(\w+)="(.+)"', line)
                if not match:
                    continue
                sid, content = match.group(1), match.group(2)
                parts = content.split(',')
                if len(parts) < 32:
                    continue

                # 提取深圳股票代码
                code = sid[2:] if sid.startswith(('sh', 'sz')) else sid
                name = parts[0]
                try:
                    price = float(parts[3])
                    pre_close = float(parts[2])
                    change = price - pre_close
                    change_pct = (change / pre_close * 100) if pre_close else 0
                    volume = int(float(parts[8]))
                    amount = float(parts[9])
                    high = float(parts[4])
                    low = float(parts[5])
                    open_price = float(parts[1])
                except (ValueError, IndexError):
                    continue

                if name and price > 0:
                    data.append({
                        "代码": code, "名称": name,
                        "最新价": price, "涨跌额": round(change, 2),
                        "涨跌幅": round(change_pct, 2),
                        "成交量": volume, "成交额": amount,
                        "最高": high, "最低": low,
                        "今开": open_price, "昨收": pre_close,
                    })

            if data:
                return pd.DataFrame(data)
        except Exception as e:
            logger.warning(f"新浪行情获取失败: {e}")
        return None

    def _get_us_spot_quote(self, cache_time: float) -> Optional[pd.DataFrame]:
        """获取美股实时行情快照（使用新浪财经API，稳定可靠）"""
        try:
            from urllib import request as urllib_request
            import ssl

            # 优先使用已缓存的搜索结果中的美股数据
            if self._us_stock_cache is not None and (time.time() - self._us_stock_cache_time) < 3600:
                df = self._us_stock_cache
                if df is not None and not df.empty:
                    self._spot_cache = df
                    self._spot_cache_time = cache_time
                    self._spot_cache_market = "US"
                    return df

            # 使用新浪财经美股API（hq.sinajs.cn 稳定可用）
            # 先获取知名美股列表作为基础
            symbols = [
                "gb_aapl", "gb_msft", "gb_goog", "gb_amzn", "gb_nvda", "gb_meta", "gb_tsla",
                "gb_brka", "gb_jpm", "gb_v", "gb_jnj", "gb_wmt", "gb_pg", "gb_ma",
                "gb_unh", "gb_hd", "gb_bac", "gb_dis", "gb_nflx", "gb_adbe",
                "gb_crm", "gb_amd", "gb_intc", "gb_qcom", "gb_txn", "gb_avgo",
                "gb_pep", "gb_ko", "gb_cost", "gb_cvx", "gb_xom", "gb_cat",
                "gb_ba", "gb_ge", "gb_gm", "gb_f", "gb_uber", "gb_abnb",
                "gb_snap", "gb_pltr", "gb_sofi", "gb_hood", "gb_coin",
                "gb_vrt", "gb_smci", "gb_arm", "gb_mstr", "gb_shop", "gb_snow",
            ]
            url = "https://hq.sinajs.cn/list=" + ",".join(symbols)
            req = urllib_request.Request(url)
            req.add_header("Referer", "https://finance.sina.com.cn/")
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib_request.urlopen(req, timeout=15, context=ctx) as resp:
                raw = resp.read().decode("gbk", errors="ignore")

            records = []
            for line in raw.strip().split("\n"):
                if not line.strip() or "=" not in line:
                    continue
                try:
                    # 格式: var hq_str_gb_XXXX="名称,最新价,..."
                    content = line.split('"')[1] if '"' in line else line.split("=")[1].strip('";')
                    parts = content.split(",")
                    if len(parts) < 30:
                        continue

                    code = parts[0].strip()  # 名称/代码
                    name = code
                    price = float(parts[1]) if parts[1] else 0
                    pre_close = float(parts[26]) if len(parts) > 26 and parts[26] else 0
                    change = round(price - pre_close, 2) if pre_close else 0
                    change_pct = round(change / pre_close * 100, 2) if pre_close else 0
                    high = float(parts[6]) if len(parts) > 6 and parts[6] else 0
                    low = float(parts[7]) if len(parts) > 7 and parts[7] else 0
                    open_price = float(parts[5]) if len(parts) > 5 and parts[5] else 0
                    volume = int(float(parts[10])) if len(parts) > 10 and parts[10] else 0

                    if price > 0:
                        records.append({
                            "代码": code,
                            "名称": name,
                            "最新价": price,
                            "涨跌幅": change_pct,
                            "涨跌额": change,
                            "成交量": volume,
                            "成交额": 0,
                            "振幅": 0,
                            "最高": high,
                            "最低": low,
                            "今开": open_price,
                            "昨收": pre_close,
                            "量比": 0,
                            "换手率": 0,
                            "市盈率-动态": 0,
                            "总市值": 0,
                            "流通市值": 0,
                        })
                except Exception:
                    continue

            if records:
                df = pd.DataFrame(records)
                self._us_stock_cache = df
                self._us_stock_cache_time = time.time()
                self._spot_cache = df
                self._spot_cache_time = cache_time
                self._spot_cache_market = "US"
                logger.info(f"美股行情快照获取成功（新浪财经），共 {len(df)} 只股票")
                return df

        except Exception as e:
            logger.warning(f"新浪美股API失败: {e}")
            return self._get_us_spot_quote_via_akshare(cache_time)

        return self._mock_spot_quote()

    def _get_us_spot_quote_via_akshare(self, cache_time: float) -> Optional[pd.DataFrame]:
        """通过AKShare代理获取美股行情（回退方案）"""
        try:
            df = None
            for attempt in range(2):
                try:
                    self._track_cost("stock_us_spot_em")
                    df = self._ak.stock_us_spot_em()
                    if df is not None and not df.empty:
                        self._us_stock_cache = df
                        self._us_stock_cache_time = time.time()
                        break
                except Exception as e:
                    if attempt < 1:
                        time.sleep(1)
                    else:
                        logger.warning(f"美股行情AKShare获取失败: {e}")

            if df is None or df.empty:
                try:
                    self._track_cost("stock_us_spot_em")
                    df = self._ak.stock_us_famous_spot_em()
                    if df is not None and not df.empty:
                        self._us_stock_cache = df
                        self._us_stock_cache_time = time.time()
                except Exception as e:
                    logger.warning(f"美股知名股票获取失败: {e}")

            if df is not None and not df.empty:
                self._spot_cache = df
                self._spot_cache_time = cache_time
                self._spot_cache_market = "US"
                logger.info(f"美股行情快照获取成功（AKShare），共 {len(df)} 只股票")
                return df
        except Exception as e:
            logger.warning(f"美股行情AKShare回退失败: {e}")

        return self._mock_spot_quote()

    def _fetch_single_us_stock_from_sina(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从新浪API单独获取单只美股行情"""
        try:
            from urllib import request as urllib_request
            import ssl

            url = f"https://hq.sinajs.cn/list=gb_{symbol.lower()}"
            req = urllib_request.Request(url)
            req.add_header("Referer", "https://finance.sina.com.cn/")
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib_request.urlopen(req, timeout=15, context=ctx) as resp:
                raw = resp.read().decode("gbk", errors="ignore")

            if not raw.strip() or "=" not in raw:
                return None

            content = raw.split('"')[1] if '"' in raw else raw.split("=")[1].strip('";')
            parts = content.split(",")
            if len(parts) < 30:
                return None

            name = parts[0].strip()
            price = float(parts[1]) if parts[1] else 0
            pre_close = float(parts[26]) if len(parts) > 26 and parts[26] else 0
            change = round(price - pre_close, 2) if pre_close else 0
            change_pct = round(change / pre_close * 100, 2) if pre_close else 0
            high = float(parts[6]) if len(parts) > 6 and parts[6] else 0
            low = float(parts[7]) if len(parts) > 7 and parts[7] else 0
            open_price = float(parts[5]) if len(parts) > 5 and parts[5] else 0
            volume = int(float(parts[10])) if len(parts) > 10 and parts[10] else 0

            if price <= 0:
                return None

            logger.info(f"美股单股行情获取成功: {symbol} = ${price}")
            return {
                "symbol": symbol,
                "name": name if name else symbol,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
                "amount": 0,
                "high": high,
                "low": low,
                "open": open_price,
                "pre_close": pre_close,
            }
        except Exception as e:
            logger.warning(f"新浪单股行情获取失败 {symbol}: {e}")
            return None

    def get_stock_quote(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """获取单只股票实时行情"""
        df = self.get_spot_quote(market)
        if df is None or df.empty:
            return self._mock_quote(symbol)

        try:
            # 适配不同数据源的列名和代码格式
            if market.upper() == "US":
                # 美股：代码列名可能是 "代码" 或 "code"
                code_col = None
                for col in df.columns:
                    if str(col).lower() in ("代码", "code", "symbol"):
                        code_col = col
                        break
                if code_col is None:
                    code_col = df.columns[0]

                symbol_upper = symbol.upper().strip()
                row = df[df[code_col].astype(str).str.upper().str.strip() == symbol_upper]
                if row.empty:
                    # 缓存中未找到，尝试单独从新浪获取该股票
                    single = self._fetch_single_us_stock_from_sina(symbol)
                    if single:
                        return single
                    return self._mock_quote(symbol)

                r = row.iloc[0]
                name_col = next((col for col in df.columns if str(col).lower() in ("名称", "name")), code_col)
                return {
                    "symbol": symbol,
                    "name": str(r.get(name_col, symbol)),
                    "price": float(r.get("最新价", r.get("price", 0))),
                    "change": float(r.get("涨跌额", r.get("change", 0))),
                    "change_pct": float(r.get("涨跌幅", r.get("change_pct", 0))),
                    "volume": int(float(r.get("成交量", r.get("volume", 0)))),
                    "amount": float(r.get("成交额", r.get("amount", 0))),
                    "high": float(r.get("最高", r.get("high", 0))),
                    "low": float(r.get("最低", r.get("low", 0))),
                    "open": float(r.get("今开", r.get("open", 0))),
                    "pre_close": float(r.get("昨收", r.get("pre_close", 0))),
                }

            # A股
            if "code" in df.columns:
                # 腾讯数据源: code 格式为 "sz000001" / "sh600519"
                mask = (df["code"] == f"sz{symbol}") | (df["code"] == f"sh{symbol}") | (df["code"] == symbol)
                row = df[mask]
            elif "代码" in df.columns:
                # 新浪/东方财富数据源: 代码列名为 "代码"
                row = df[df["代码"] == symbol]
            elif "symbol" in df.columns:
                row = df[df["symbol"] == symbol]
            else:
                row = pd.DataFrame()

            if row.empty:
                return self._mock_quote(symbol)

            r = row.iloc[0]
            # 腾讯数据源列名映射: zxj→最新价, zd→涨跌额, zdf→涨跌幅
            return {
                "symbol": symbol,
                "name": str(r.get("名称", r.get("name", symbol))),
                "price": float(r.get("最新价", r.get("zxj", r.get("price", 0)))),
                "change": float(r.get("涨跌额", r.get("zd", r.get("change", 0)))),
                "change_pct": float(r.get("涨跌幅", r.get("zdf", r.get("change_pct", 0)))),
                "volume": int(float(r.get("成交量", r.get("volume", 0)))),
                "amount": float(r.get("成交额", r.get("turnover", r.get("amount", 0)))),
                "high": float(r.get("最高", r.get("high", 0))),
                "low": float(r.get("最低", r.get("low", 0))),
                "open": float(r.get("今开", r.get("open", 0))),
                "pre_close": float(r.get("昨收", r.get("pre_close", 0))),
            }
        except Exception as e:
            logger.warning(f"解析行情失败: {e}")
            return self._mock_quote(symbol)

    # ==================== K线数据 ====================

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
        """获取K线数据（支持多数据源降级：东方财富 → 腾讯 → 新浪）"""
        if self._ak is None:
            return self._mock_kline(count)

        if market.upper() == "A":
            s_date = start_date.replace("-", "") if start_date else "20240101"
            e_date = end_date.replace("-", "") if end_date else datetime.now().strftime("%Y%m%d")

            # A股 K线数据源降级链
            kline_sources = [
                # 1. 尝试东方财富（默认）
                ("stock_zh_a_hist", "东方财富", lambda: self._ak.stock_zh_a_hist(
                    symbol=symbol, period=period, start_date=s_date,
                    end_date=e_date, adjust=adjust,
                )),
                # 2. 尝试腾讯数据源
                ("stock_zh_a_hist_tx", "腾讯", lambda: self._ak.stock_zh_a_hist_tx(
                    symbol=self._to_tx_symbol(symbol),
                    start_date=start_date.replace("-", "-") if start_date else "2024-01-01",
                    end_date=end_date.replace("-", "-") if end_date else datetime.now().strftime("%Y-%m-%d"),
                )),
                # 3. 尝试新浪数据源
                ("stock_zh_a_daily", "新浪", lambda: self._ak.stock_zh_a_daily(
                    symbol=self._to_sina_symbol(symbol),
                    start_date=start_date.replace("-", "") if start_date else "20240101",
                    end_date=e_date,
                    adjust=adjust,
                )),
            ]

            last_error = None
            for api_name, source_name, fetch_func in kline_sources:
                try:
                    self._track_cost(api_name)
                    df = fetch_func()
                    if df is not None and not df.empty:
                        logger.info(f"K线数据获取成功: {symbol} via {source_name} ({api_name})")
                        df = self._normalize_kline(df, market)
                        return df.tail(count)
                except Exception as e:
                    last_error = e
                    logger.warning(f"K线 {source_name} ({api_name}) 失败: {e}")
                    continue
        else:
            # 美股
            try:
                s_date = start_date.replace("-", "") if start_date else "20240101"
                e_date = end_date.replace("-", "") if end_date else datetime.now().strftime("%Y%m%d")
                self._track_cost("stock_us_hist")
                df = self._ak.stock_us_hist(
                    symbol=symbol, period=period,
                    start_date=s_date, end_date=e_date, adjust=adjust,
                )
                if df is not None and not df.empty:
                    df = self._normalize_kline(df, market)
                    return df.tail(count)
            except Exception as e:
                last_error = e
                logger.warning(f"美股K线失败: {e}")

        logger.warning(f"所有K线数据源均失败，使用模拟数据: {last_error}")
        return self._mock_kline(count)

    def _to_tx_symbol(self, symbol: str) -> str:
        """转换为腾讯数据源格式 (sz000001 / sh600519)"""
        if symbol.startswith(("sz", "sh", "bj")):
            return symbol
        code = symbol.zfill(6)
        if code.startswith(("6", "9")):
            return f"sh{code}"
        elif code.startswith(("0", "3")):
            return f"sz{code}"
        elif code.startswith(("4", "8")):
            return f"bj{code}"
        return f"sz{code}"

    def _to_sina_symbol(self, symbol: str) -> str:
        """转换为新浪数据源格式 (sz000001 / sh600519)"""
        return self._to_tx_symbol(symbol)

    def _normalize_kline(self, df: pd.DataFrame, market: str) -> pd.DataFrame:
        """标准化K线数据列名"""
        rename_map = {
            "日期": "date", "开盘": "open", "收盘": "close",
            "最高": "high", "最低": "low", "成交量": "volume",
            "成交额": "amount",
        }
        for old, new in rename_map.items():
            if old in df.columns:
                df = df.rename(columns={old: new})

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df

    # ==================== 基本面数据 ====================

    def get_stock_info(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """获取个股基本面信息"""
        if self._ak is None:
            return self._mock_fundamental()

        try:
            self._track_cost("stock_individual_info_em")
            df = self._ak.stock_individual_info_em(symbol=symbol)
            if df is not None and not df.empty:
                info = dict(zip(df["item"], df["value"]))
                return {
                    "pe_ratio": float(info.get("市盈率-动态", 0)),
                    "pb_ratio": float(info.get("市净率", 0)),
                    "market_cap": float(info.get("总市值", 0)),
                    "revenue": float(info.get("营业收入", 0)),
                    "net_profit": float(info.get("净利润", 0)),
                    "roe": float(info.get("净资产收益率", 0)),
                    "total_shares": float(info.get("总股本", 0)),
                }
        except Exception as e:
            logger.warning(f"获取基本面数据失败: {e}")

        return self._mock_fundamental()

    # ==================== 深度财务数据 ====================

    def get_financial_data(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """
        获取个股深度财务数据，用于生成研报
        
        返回：
        {
            "basic": {PE, PB, market_cap, revenue, net_profit, roe, industry, ...},
            "growth": {revenue_growth_yoy, profit_growth_yoy, ...},
            "profitability": {gross_margin, net_margin, roe_trend, ...},
            "cashflow": {fcf, fcf_trend, ...},
            "peers": [{code, name, pe, pb, market_cap}, ...],
            "source": "akshare" | "mock"
        }
        """
        if self._ak is None:
            return self._mock_financial_data(symbol, market)

        if market.upper() == "A":
            return self._get_a_share_financial_data(symbol)
        elif market.upper() == "US":
            return self._get_us_financial_data(symbol)
        else:
            return self._mock_financial_data(symbol, market)

    def _get_a_share_financial_data(self, symbol: str) -> Dict[str, Any]:
        """获取A股深度财务数据（push2报价 + F10财务 + 腾讯行情 + AKShare兜底）"""
        result = {"basic": {}, "growth": {}, "profitability": {}, "cashflow": {}, "peers": [], "source": "mock"}
        has_real = False
        
        # ====== 策略1：东方财富 push2 + F10 API（无需代理，直连） ======
        em_data = self._fetch_financial_from_em_web(symbol)
        if em_data:
            result.update(em_data)
            result["source"] = "eastmoney"
            has_real = True
            logger.info(f"东方财富Web API获取财务数据成功: {symbol}")
        
        # ====== 策略2：腾讯行情获取基础数据（PE/PB/市值） ======
        if not result["basic"] or result["basic"].get("pe", 0) == 0:
            tx_data = self._fetch_basic_from_tencent(symbol)
            if tx_data:
                # 只更新值为0或空的字段，不覆盖已有的行业等信息
                for k, v in tx_data.items():
                    if v and (k not in result["basic"] or result["basic"].get(k, 0) == 0):
                        result["basic"][k] = v
                if not has_real:
                    result["source"] = "tencent"
                    has_real = True
                logger.info(f"腾讯行情数据获取成功: {symbol}, PE={tx_data.get('pe')}, PB={tx_data.get('pb')}")
        
        # ====== 策略3：新浪行情 ======
        if not result["basic"] or result["basic"].get("pe", 0) == 0:
            sina_data = self._fetch_basic_from_sina_enhanced(symbol)
            if sina_data:
                # 只更新值为0或空的字段
                for k, v in sina_data.items():
                    if v and (k not in result["basic"] or result["basic"].get(k, 0) == 0):
                        result["basic"][k] = v
                if not has_real:
                    result["source"] = "sina"
                    has_real = True
                logger.info(f"新浪行情数据获取成功: {symbol}")
        
        # ====== 策略4：AKShare代理（兜底） ======
        if not result["basic"] or result["basic"].get("pe", 0) == 0:
            self._try_akshare_basic_info(symbol, result)
        
        if not result["peers"]:
            self._try_fetch_peers_from_em_web(symbol, result)
        if not result["peers"]:
            self._try_akshare_peers(symbol, result)
        
        if not result.get("forecast"):
            self._try_akshare_forecast(symbol, result)
        
        # ====== 数据增强：同行真实财务数据、分析师预测、机构持仓、北向资金、估值分位 ======
        if result["peers"]:
            self._enrich_peer_financials(symbol, result)
        self._enrich_analyst_forecast(symbol, result)
        self._enrich_institutional_holdings(symbol, result)
        self._enrich_northbound_capital(symbol, result)
        self._enrich_valuation_percentile(symbol, result)
        self._enrich_dividend_info(symbol, result)
        self._enrich_income_statement(symbol, result)
        self._enrich_balance_sheet(symbol, result)
        self._enrich_cashflow_statement(symbol, result)
        self._enrich_revenue_segment(symbol, result)
        self._enrich_operating_efficiency(symbol, result)
        self._enrich_shareholder_structure(symbol, result)
        self._enrich_per_capita_metrics(symbol, result)
        self._enrich_growth_quality(symbol, result)
        self._enrich_financial_anomaly(symbol, result)
        self._enrich_earnings_forecast(symbol, result)
        self._enrich_lockup_shares(symbol, result)
        
        # 标记是否使用了真实数据
        if not has_real and not bool(result["growth"].get("revenue_growth_yoy", [])) and not bool(result["peers"]):
            result["_mock"] = True
        
        return result

    def _fetch_financial_from_em_web(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从东方财富 Web API 获取财务数据（push2 + F10，不经过代理）"""
        try:
            import requests
            
            # 确定市场代码前缀
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
                secid = f"1.{symbol}"
            elif symbol.startswith(("0", "3")):
                em_code = f"SZ{symbol}"
                secid = f"0.{symbol}"
            else:
                em_code = f"SZ{symbol}"
                secid = f"0.{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            result = {"basic": {}, "growth": {}, "profitability": {}, "cashflow": {}, "peers": [], "forecast": {}}
            
            # ----- 1. push2 实时行情（PE/PB/市值/EPS） -----
            push2_ok = False
            for retry in range(2):
                try:
                    push2_url = "https://push2.eastmoney.com/api/qt/stock/get"
                    push2_params = {
                        "secid": secid,
                        "fields": "f43,f44,f45,f46,f55,f57,f58,f116,f117,f162,f167,f170",
                        "invt": "2",
                    }
                    resp = requests.get(push2_url, params=push2_params, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        d = data.get("data", {})
                        if d and d.get("f43"):
                            price = self._safe_float(d.get("f43", 0)) / 100
                            pe = self._safe_float(d.get("f162", 0)) / 100
                            pb = self._safe_float(d.get("f167", 0)) / 100
                            market_cap = self._safe_float(d.get("f116", 0))
                            eps = self._safe_float(d.get("f55", 0))
                            high = self._safe_float(d.get("f44", 0)) / 100
                            low = self._safe_float(d.get("f45", 0)) / 100
                            volume = int(self._safe_float(d.get("f47", 0)))
                            amount = self._safe_float(d.get("f48", 0))
                            
                            if price > 0:
                                result["basic"] = {
                                    "pe": pe,
                                    "pb": pb,
                                    "market_cap": market_cap,
                                    "eps": eps,
                                    "revenue": 0,
                                    "net_profit": 0,
                                    "roe": 0,
                                    "industry": "",
                                    "industry_code": "",
                                    "total_shares": 0,
                                    "circulating_cap": self._safe_float(d.get("f117", 0)),
                                    "listing_date": "",
                                }
                                logger.info(f"push2行情: {symbol}, PE={pe}, PB={pb}, 市值={market_cap}")
                                push2_ok = True
                                break
                except Exception as e:
                    if retry == 0:
                        logger.warning(f"push2行情获取失败(第1次): {e}，重试中...")
                        time.sleep(0.5)
                    else:
                        logger.warning(f"push2行情获取失败(第2次): {e}")
            
            # push2失败时，尝试push2his（历史行情API也提供最新PE/PB）
            if not push2_ok:
                try:
                    push2his_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                    push2his_params = {
                        "secid": secid,
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                        "klt": "101",
                        "fqt": "1",
                        "end": "20500101",
                        "lmt": "1",
                    }
                    resp = requests.get(push2his_url, params=push2his_params, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        logger.info(f"push2his行情获取成功(备用): {symbol}")
                except Exception as e:
                    logger.warning(f"push2his行情也失败: {e}")
            
            # ----- 2. F10 财务指标（营收/利润/增速/毛利率/净利率/ROE/负债率） -----
            try:
                f10_url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
                f10_params = {"code": em_code, "type": "0"}
                resp = requests.get(f10_url, params=f10_params, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get("data", [])
                    if records:
                        # 按日期正序排列
                        records.sort(key=lambda r: r.get("REPORT_DATE", ""))
                        # 取最近4期年报用于基础财务指标
                        annual_records = [r for r in records if "-12-31" in (r.get("REPORT_DATE") or "")]
                        if not annual_records:
                            annual_records = records[-4:] if len(records) >= 4 else records
                        else:
                            annual_records = annual_records[-4:]
                        
                        # 使用所有可用记录（最多8期）用于趋势分析（增长率为同比，跨季度可比）
                        trend_records = records[-8:] if len(records) >= 8 else records
                        
                        if annual_records:
                            latest = annual_records[-1]
                            
                            # F10财务数据（营收/净利润/ROE/负债率/毛利率/净利率）
                            f10_revenue = self._safe_float(latest.get("TOTALOPERATEREVE", 0))
                            f10_profit = self._safe_float(latest.get("PARENTNETPROFIT", 0))
                            f10_roe = self._safe_float(latest.get("ROEJQ", 0))
                            f10_debt = self._safe_float(latest.get("ZCFZL", 0))
                            f10_eps = self._safe_float(latest.get("EPSJB", 0))
                            f10_industry = str(latest.get("HY_NAME", ""))
                            
                            # 更新basic：F10数据优先（比push2的0值更可靠）
                            if not result["basic"]:
                                result["basic"] = {
                                    "revenue": f10_revenue,
                                    "net_profit": f10_profit,
                                    "roe": f10_roe,
                                    "eps": f10_eps,
                                    "industry": f10_industry,
                                    "debt_ratio": f10_debt,
                                    "total_shares": 0,
                                }
                            else:
                                # 强制更新：F10数据比push2默认值(0)更可靠
                                if f10_revenue > 0:
                                    result["basic"]["revenue"] = f10_revenue
                                if f10_profit > 0:
                                    result["basic"]["net_profit"] = f10_profit
                                if f10_roe > 0:
                                    result["basic"]["roe"] = f10_roe
                                if f10_debt > 0:
                                    result["basic"]["debt_ratio"] = f10_debt
                                if f10_eps > 0:
                                    result["basic"]["eps"] = f10_eps
                                if f10_industry and f10_industry != "None":
                                    result["basic"]["industry"] = f10_industry
                            
                            # 提取趋势数据（使用所有可用记录以获得更多数据点）
                            rev_growth = []
                            profit_growth = []
                            gross_margin = []
                            net_margin = []
                            roe_trend = []
                            trend_dates = []
                            
                            for r in trend_records:
                                rg = self._safe_float(r.get("TOTALOPERATEREVETZ", 0))
                                pg = self._safe_float(r.get("PARENTNETPROFITTZ", 0))
                                gm = self._safe_float(r.get("XSMLL", 0))
                                nm = self._safe_float(r.get("XSJLL", 0))
                                roe = self._safe_float(r.get("ROEJQ", 0))
                                dt = r.get("REPORT_DATE", "")
                                
                                rev_growth.append(rg)
                                profit_growth.append(pg)
                                gross_margin.append(gm)
                                net_margin.append(nm)
                                roe_trend.append(roe)
                                trend_dates.append(dt[:10] if dt else "")
                            
                            if rev_growth and any(g != 0 for g in rev_growth):
                                # 使用年报数据计算平均增速（避免季度同比波动）
                                annual_rev_growth = [self._safe_float(r.get("TOTALOPERATEREVETZ", 0)) for r in annual_records]
                                annual_profit_growth = [self._safe_float(r.get("PARENTNETPROFITTZ", 0)) for r in annual_records]
                                # 过滤掉极端值（>200%或<-200%的可能是异常数据）
                                annual_rev_growth = [g for g in annual_rev_growth if -200 < g < 200]
                                annual_profit_growth = [g for g in annual_profit_growth if -200 < g < 200]
                                
                                avg_rev = sum(annual_rev_growth) / len(annual_rev_growth) if annual_rev_growth else 0
                                avg_profit = sum(annual_profit_growth) / len(annual_profit_growth) if annual_profit_growth else 0
                                
                                result["growth"] = {
                                    "revenue_growth_yoy": rev_growth,
                                    "profit_growth_yoy": profit_growth,
                                    "avg_revenue_growth": avg_rev,
                                    "avg_profit_growth": avg_profit,
                                    "trend_dates": trend_dates,
                                }
                            
                            if gross_margin and any(g != 0 for g in gross_margin):
                                result["profitability"] = {
                                    "gross_margin": gross_margin,
                                    "net_margin": net_margin,
                                    "roe_trend": roe_trend,
                                    "avg_gross_margin": sum(gross_margin) / len(gross_margin),
                                    "avg_net_margin": sum(net_margin) / len(net_margin),
                                    "trend_dates": trend_dates,
                                }
                            
                            # 现金流数据（从F10获取）
                            # F10 ZYZB 接口不直接提供FCF数据，需从现金流量表单独获取
                            # 标记为不可用，由研报服务根据净利润估算
                            result["cashflow"] = {
                                "operating_cf": 0,
                                "investing_cf": 0,
                                "fcf": 0,
                                "_fcf_unavailable": True,  # 标记FCF数据不可用
                            }
                            # 尝试从F10数据中提取经营活动现金流
                            if latest.get("JYXJLYYSR"):
                                result["cashflow"]["operating_cf"] = self._safe_float(latest.get("JYXJLYYSR", 0))
                            
                            # 资产负债表指标
                            if latest.get("LD"):
                                result["basic"]["current_ratio"] = self._safe_float(latest.get("LD", 0))
                            if latest.get("SD"):
                                result["basic"]["quick_ratio"] = self._safe_float(latest.get("SD", 0))
                            
                            logger.info(f"F10财务指标: {symbol}, 共{len(annual_records)}期, 营收增速={sum(rev_growth)/len(rev_growth):.1f}%")
            except Exception as e:
                logger.warning(f"F10财务指标获取失败: {e}")
            
            # ----- 3. F10 公司概况（行业信息） -----
            try:
                company_url = "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax"
                company_params = {"code": em_code}
                resp = requests.get(company_url, params=company_params, headers=headers, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    jbzl = data.get("jbzl", [])
                    if jbzl:
                        company = jbzl[0]
                        # 始终更新行业信息（F10 ZYZB的HY_NAME可能为空，公司概况的EM2016更可靠）
                        survey_industry = str(company.get("EM2016", ""))
                        if survey_industry and survey_industry != "" and survey_industry != "None":
                            result["basic"]["industry"] = survey_industry
                        result["basic"]["total_shares"] = self._safe_float(company.get("REG_CAPITAL", 0)) * 10000  # 万股转股
                        result["basic"]["listing_date"] = str(company.get("LISTING_DATE", ""))
                        logger.info(f"公司概况: {symbol}, 行业={survey_industry}")
            except Exception as e:
                logger.warning(f"F10公司概况获取失败: {e}")
            
            if result["basic"] and (result["basic"].get("pe", 0) > 0 or result["basic"].get("roe", 0) > 0):
                return result
            # 即使没有PE，只要有F10财务数据也返回
            if result["growth"].get("revenue_growth_yoy") or result["profitability"].get("gross_margin"):
                logger.info(f"东方财富F10数据获取成功(无push2行情): {symbol}")
                return result
        except Exception as e:
            logger.warning(f"东方财富Web API整体失败: {e}")
        
        return None

    def _fetch_basic_from_tencent(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从腾讯行情API获取PE/PB/市值（备用方案）"""
        try:
            import requests
            # 腾讯行情格式: sh600519
            if symbol.startswith("6"):
                tx_code = f"sh{symbol}"
            elif symbol.startswith(("0", "3")):
                tx_code = f"sz{symbol}"
            else:
                tx_code = f"sh{symbol}"
            
            url = f"https://qt.gtimg.cn/q={tx_code}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                content = resp.text
                if "~" in content:
                    parts = content.split('"')[1] if '"' in content else content
                    fields = parts.split("~")
                    if len(fields) > 44:
                        pe = self._safe_float(fields[39]) if len(fields) > 39 else 0
                        pb = self._safe_float(fields[46]) if len(fields) > 46 else 0
                        market_cap = self._safe_float(fields[44]) * 100000000 if len(fields) > 44 else 0  # 亿转元
                        eps = self._safe_float(fields[43]) if len(fields) > 43 else 0
                        
                        if pe > 0 or market_cap > 0:
                            return {
                                "pe": pe,
                                "pb": pb,
                                "market_cap": market_cap,
                                "eps": eps,
                            }
        except Exception as e:
            logger.warning(f"腾讯行情获取失败: {e}")
        return None

    def _fetch_basic_from_sina_enhanced(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从新浪API获取单只A股行情（增强版，尝试获取PE/PB）"""
        try:
            import requests
            import re
            
            if symbol.startswith("6"):
                sina_code = f"sh{symbol}"
            elif symbol.startswith(("0", "3")):
                sina_code = f"sz{symbol}"
            else:
                sina_code = f"sh{symbol}"
            
            url = f"https://hq.sinajs.cn/list={sina_code}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn/",
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None
            
            match = re.search(r'hq_str_\w+="(.+)"', resp.text)
            if not match:
                return None
            
            parts = match.group(1).split(",")
            if len(parts) < 32:
                return None
            
            try:
                name = parts[0]
                price = float(parts[3]) if parts[3] else 0
                pre_close = float(parts[2]) if parts[2] else 0
                high = float(parts[4]) if parts[4] else 0
                low = float(parts[5]) if parts[5] else 0
                open_price = float(parts[1]) if parts[1] else 0
                volume = int(float(parts[8])) if len(parts) > 8 and parts[8] else 0
                amount = float(parts[9]) if len(parts) > 9 and parts[9] else 0
                
                if price <= 0:
                    return None
                
                return {
                    "name": name,
                    "price": price,
                    "change": price - pre_close,
                    "change_pct": (price - pre_close) / pre_close * 100 if pre_close else 0,
                    "high": high,
                    "low": low,
                    "open": open_price,
                    "pre_close": pre_close,
                    "volume": volume,
                    "amount": amount,
                    "pe": 0,  # Sina不直接提供PE/PB
                    "pb": 0,
                    "market_cap": 0,
                    "industry": "",
                }
            except (ValueError, IndexError):
                return None
        except Exception as e:
            logger.warning(f"新浪单股行情获取失败 {symbol}: {e}")
            return None

    def _try_fetch_peers_from_em_web(self, symbol: str, result: Dict[str, Any]):
        """通过东方财富F10获取同行对比数据（HyComparison返回HTML不可用，改用行业映射+腾讯行情）"""
        industry = result["basic"].get("industry", "")
        if not industry:
            return
        
        try:
            import requests
            
            # 从行业名称提取板块关键词
            # 行业格式: "食品饮料-饮料-白酒" -> 提取 "白酒" 作为板块关键词
            industry_parts = industry.split("-") if industry else []
            sector_keyword = industry_parts[-1] if industry_parts else industry
            
            # 常用行业 -> 同行股票映射（硬编码，保证可靠性）
            INDUSTRY_PEERS = {
                "白酒": ["000858", "000568", "002304", "600809", "000596", "603369", "600559", "600779"],
                "啤酒": ["600600", "000729", "002461", "600132"],
                "乳品": ["600887", "002570", "600882", "002946"],
                "调味品": ["603288", "600305", "002481", "600872"],
                "肉制品": ["000895", "002714", "002330", "002840"],
                "银行": ["601398", "601939", "601288", "600036", "000001", "002142", "600000"],
                "保险": ["601318", "601628", "601601", "601336"],
                "证券": ["600030", "601211", "000776", "600837", "601688"],
                "房地产开发": ["000002", "600048", "001979", "600383"],
                "煤炭开采": ["601088", "600188", "601898", "600348"],
                "石油开采": ["601857", "600028", "600938"],
                "动力煤": ["601088", "600188", "601898"],
                "黄金": ["600489", "600547", "601899", "002155"],
                "铜": ["600362", "000630", "601899", "002203"],
                "锂": ["002460", "002466", "300750", "002074"],
                "光伏": ["601012", "600438", "002459", "688599"],
                "风电": ["601615", "002202", "600416", "300772"],
                "新能源汽车": ["002594", "600104", "601238", "000625"],
                "汽车零部件": ["600741", "000338", "601799", "002920"],
                "半导体": ["688981", "002371", "603986", "600584"],
                "芯片": ["688981", "603986", "002049", "300782"],
                "消费电子": ["002475", "601138", "002241", "300433"],
                "通信设备": ["000063", "600050", "600498", "002396"],
                "计算机": ["000977", "002230", "603019", "600536"],
                "软件": ["002230", "600588", "300033", "688111"],
                "医药": ["600276", "000538", "300015", "002001"],
                "医疗器械": ["300760", "002223", "300003", "688029"],
                "中药": ["600085", "000538", "000423", "600436"],
                "家电": ["000333", "000651", "002032", "600690"],
                "空调": ["000651", "000333", "002032"],
                "化工": ["600309", "600426", "000830", "002601"],
                "钢铁": ["600019", "000932", "000825", "600010"],
                "水泥": ["600585", "000786", "000401", "002271"],
                "电力": ["600900", "600025", "600011", "003816"],
                "航空": ["601111", "600029", "600115", "002928"],
                "铁路": ["601006", "601816", "000008"],
                "港口": ["601880", "600018", "000088", "601872"],
                "电信": ["600050", "601728", "600941"],
                "传媒": ["002027", "300413", "300251", "002555"],
                "游戏": ["300418", "002555", "002624", "300315"],
                "影视": ["002739", "300251", "603103", "300291"],
                "农林牧渔": ["002714", "000876", "002385", "600438"],
                "养殖": ["002714", "000876", "002157", "002100"],
                "饲料": ["000876", "002385", "002311", "603363"],
                "军工": ["600760", "600893", "000768", "600862"],
                "航天": ["600118", "000547", "688568", "600879"],
                "环保": ["300070", "600323", "000826", "002672"],
                "零售": ["601933", "002024", "000564", "601828"],
                "物流": ["002352", "600233", "002120", "603056"],
                "酒店": ["600754", "000428", "600258", "000610"],
                "旅游": ["601888", "300144", "002707", "000430"],
                "教育": ["300559", "002607", "600661", "300089"],
                "造纸": ["000488", "600966", "002078", "000833"],
                "纺织": ["002563", "002832", "603877", "600398"],
                "服装": ["603877", "002832", "002563", "601566"],
                "储能": ["300750", "002594", "300014", "002074", "300207", "688063", "300438", "300068"],
                "电池": ["300750", "002594", "300014", "002074", "300207", "688567", "300438", "002812"],
                "电源": ["300750", "300274", "601877", "002518", "300763", "300124", "002851"],
                "电气": ["300750", "601877", "600406", "300124", "300274", "002851", "300763", "688390"],
                "锂电": ["300750", "002594", "300014", "002074", "002460", "002466", "300438", "688567"],
                "新能源": ["300750", "002594", "601012", "600438", "002459", "300274", "688599", "300763"],
                "汽车": ["002594", "600104", "601238", "000625", "600741", "000338", "601799", "300750"],
                "工程机械": ["600031", "000157", "000425", "600815", "000528", "601100", "002097"],
                "建材": ["600585", "000786", "000401", "002271", "600176", "601636", "000012"],
                "食品": ["600519", "000858", "000568", "002304", "600887", "603288", "600809", "000895"],
                "饮料": ["600519", "000858", "000568", "002304", "600809", "000596", "603369", "600559"],
            }
            
            peer_codes = []
            # 按行业路径逐级匹配（从最细粒度到最粗粒度）
            # 例如: "电气设备-电源设备-储能设备" → 依次尝试 "储能设备"、"电源设备"、"电气设备"
            match_segments = list(reversed(industry_parts)) if industry_parts else [industry]
            for segment in match_segments:
                for key, codes in INDUSTRY_PEERS.items():
                    if key in segment:
                        peer_codes = [c for c in codes if c != symbol]
                        break
                if peer_codes:
                    break
            
            if not peer_codes:
                logger.info(f"未找到{symbol}的行业({industry})同行映射")
                return
            
            # 使用腾讯API获取同行实时PE数据
            tx_codes = []
            for pc in peer_codes[:8]:
                if pc.startswith("6"):
                    tx_codes.append(f"sh{pc}")
                else:
                    tx_codes.append(f"sz{pc}")
            
            tx_url = f"https://qt.gtimg.cn/q={','.join(tx_codes)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(tx_url, headers=headers, timeout=10)
            
            peers = []
            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")
                for line in lines:
                    if "~" not in line:
                        continue
                    try:
                        parts = line.split('"')[1] if '"' in line else line
                        fields = parts.split("~")
                        if len(fields) > 44:
                            p_code = fields[2] if len(fields) > 2 else ""
                            p_name = fields[1] if len(fields) > 1 else ""
                            p_pe = self._safe_float(fields[39]) if len(fields) > 39 else 0
                            p_pb = self._safe_float(fields[46]) if len(fields) > 46 else 0
                            p_mcap = self._safe_float(fields[44]) * 100000000 if len(fields) > 44 else 0
                            if p_code and p_code != symbol:
                                peers.append({
                                    "code": p_code,
                                    "name": p_name,
                                    "pe": p_pe,
                                    "pb": p_pb,
                                    "roe": 0,
                                    "market_cap": p_mcap,
                                    "revenue_growth": 0,
                                })
                    except Exception:
                        continue
            
            if peers:
                result["peers"] = peers[:10]
                logger.info(f"行业映射+腾讯行情获取同行: {symbol}, 行业={industry}, 共{len(peers)}家")
            else:
                # 如果腾讯API失败，至少返回代码和名称
                for pc in peer_codes[:8]:
                    peers.append({
                        "code": pc,
                        "name": pc,
                        "pe": 0,
                        "pb": 0,
                        "roe": 0,
                        "market_cap": 0,
                        "revenue_growth": 0,
                    })
                result["peers"] = peers
                logger.info(f"行业映射同行(无行情): {symbol}, 共{len(peers)}家")
        except Exception as e:
            logger.warning(f"同行对比获取失败: {e}")

    def _fetch_basic_from_sina(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从新浪API获取单只A股的基础数据（PE/PB/市值/行业）"""
        try:
            import requests
            import re
            
            # 确定新浪代码格式
            if symbol.startswith("6"):
                sina_code = f"sh{symbol}"
            elif symbol.startswith(("0", "3")):
                sina_code = f"sz{symbol}"
            else:
                sina_code = f"sh{symbol}"
            
            url = f"https://hq.sinajs.cn/list={sina_code}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn/",
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None
            
            match = re.search(r'hq_str_\w+="(.+)"', resp.text)
            if not match:
                return None
            
            parts = match.group(1).split(",")
            if len(parts) < 32:
                return None
            
            try:
                name = parts[0]
                price = float(parts[3]) if parts[3] else 0
                pre_close = float(parts[2]) if parts[2] else 0
                change = price - pre_close
                change_pct = (change / pre_close * 100) if pre_close else 0
                high = float(parts[4]) if parts[4] else 0
                low = float(parts[5]) if parts[5] else 0
                open_price = float(parts[1]) if parts[1] else 0
                volume = int(float(parts[8])) if len(parts) > 8 and parts[8] else 0
                amount = float(parts[9]) if len(parts) > 9 and parts[9] else 0
                
                if price <= 0:
                    return None
                
                return {
                    "name": name,
                    "price": price,
                    "change": change,
                    "change_pct": change_pct,
                    "high": high,
                    "low": low,
                    "open": open_price,
                    "pre_close": pre_close,
                    "volume": volume,
                    "amount": amount,
                    "pe": 0,  # Sina API 不直接提供PE/PB
                    "pb": 0,
                    "market_cap": 0,
                    "industry": "",
                }
            except (ValueError, IndexError):
                return None
        except Exception as e:
            logger.warning(f"新浪单股行情获取失败 {symbol}: {e}")
            return None

    def _try_akshare_basic_info(self, symbol: str, result: Dict[str, Any]):
        """尝试通过AKShare获取个股基本信息（兜底方案）"""
        try:
            # 先尝试行情快照
            spot_df = self.get_spot_quote(market="A")
            if spot_df is not None and not spot_df.empty:
                code_col = None
                for col in spot_df.columns:
                    if str(col).lower() in ("代码", "code", "symbol"):
                        code_col = col
                        break
                if code_col:
                    stock_row = spot_df[spot_df[code_col].astype(str).str.strip() == symbol.strip()]
                else:
                    stock_row = spot_df[spot_df.iloc[:, 0].astype(str).str.strip() == symbol.strip()]
                
                if not stock_row.empty:
                    row = stock_row.iloc[0]
                    result["basic"] = {
                        "pe": self._safe_float(row.get("市盈率-动态", row.get("pe", 0))),
                        "pb": self._safe_float(row.get("市净率", row.get("pb", 0))),
                        "market_cap": self._safe_float(row.get("总市值", row.get("market_cap", 0))),
                        "circulating_cap": self._safe_float(row.get("流通市值", 0)),
                        "revenue": 0,
                        "net_profit": 0,
                        "roe": 0,
                        "total_shares": 0,
                        "industry": str(row.get("行业", row.get("industry", ""))),
                        "listing_date": "",
                    }
                    result["source"] = "akshare_spot"
                    return
        except Exception as e:
            logger.warning(f"行情快照获取失败: {e}")
        
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._ak.stock_individual_info_em, symbol=symbol)
                try:
                    df_info = future.result(timeout=8)
                    if df_info is not None and not df_info.empty:
                        info = dict(zip(df_info["item"], df_info["value"]))
                        result["basic"] = {
                            "pe": self._safe_float(info.get("市盈率-动态", 0)),
                            "pb": self._safe_float(info.get("市净率", 0)),
                            "market_cap": self._safe_float(info.get("总市值", 0)),
                            "revenue": self._safe_float(info.get("营业收入", 0)),
                            "net_profit": self._safe_float(info.get("净利润", 0)),
                            "roe": self._safe_float(info.get("净资产收益率", 0)),
                            "total_shares": self._safe_float(info.get("总股本", 0)),
                            "industry": str(info.get("行业", "")),
                            "listing_date": str(info.get("上市时间", "")),
                        }
                        result["source"] = "akshare_info"
                except concurrent.futures.TimeoutError:
                    pass
        except Exception as e:
            logger.warning(f"stock_individual_info_em 失败: {e}")

    def _try_akshare_peers(self, symbol: str, result: Dict[str, Any]):
        """尝试通过AKShare获取同行数据"""
        industry_name = result["basic"].get("industry", "")
        if not industry_name:
            return
        try:
            self._track_cost("stock_board_industry_cons_em")
            df_peers = self._ak.stock_board_industry_cons_em(symbol=industry_name)
            if df_peers is not None and not df_peers.empty:
                peers = []
                for _, row in df_peers.head(30).iterrows():
                    peer_code = str(row.get("代码", ""))
                    if peer_code and peer_code != symbol:
                        peers.append({
                            "code": peer_code,
                            "name": str(row.get("名称", "")),
                            "pe": self._safe_float(row.get("市盈率-动态", 0)),
                            "pb": self._safe_float(row.get("市净率", 0)),
                            "roe": 0,
                            "market_cap": self._safe_float(row.get("总市值", 0)),
                            "revenue_growth": 0,
                        })
                result["peers"] = peers[:10]
                logger.info(f"AKShare同行获取: {industry_name}, 共{len(peers)}家")
        except Exception as e:
            logger.warning(f"AKShare同行获取失败: {e}")

    def _try_akshare_forecast(self, symbol: str, result: Dict[str, Any]):
        """尝试通过AKShare获取业绩预告"""
        try:
            self._track_cost("stock_yjbb_em")
            df_yj = self._ak.stock_yjbb_em(date="20260630")
            if df_yj is not None and not df_yj.empty:
                code_col = None
                for col in df_yj.columns:
                    if str(col).lower() in ("代码", "code", "symbol", "股票代码"):
                        code_col = col
                        break
                if code_col:
                    stock_row = df_yj[df_yj[code_col].astype(str).str.strip() == symbol.strip()]
                else:
                    stock_row = df_yj[df_yj.iloc[:, 0].astype(str).str.strip() == symbol.strip()]
                
                if not stock_row.empty:
                    latest = stock_row.iloc[0]
                    result["forecast"] = {
                        "type": str(latest.get("业绩变动类型", latest.get("预告类型", ""))),
                        "net_profit_lower": self._safe_float(latest.get("预告净利润下限", latest.get("净利润下限", 0))),
                        "net_profit_upper": self._safe_float(latest.get("预告净利润上限", latest.get("净利润上限", 0))),
                        "change_lower": self._safe_float(latest.get("预告净利润变动幅度下限", latest.get("净利润变动幅度下限", 0))),
                        "change_upper": self._safe_float(latest.get("预告净利润变动幅度上限", latest.get("净利润变动幅度上限", 0))),
                    }
        except Exception as e:
            logger.warning(f"AKShare业绩预告获取失败: {e}")

    # ==================== 数据增强方法 ====================

    def _enrich_peer_financials(self, symbol: str, result: Dict[str, Any]):
        """并行获取同行的真实ROE和营收增速（从东方财富F10）"""
        peers = result.get("peers", [])
        if not peers:
            return
        
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def fetch_peer_f10(peer_info: dict) -> dict:
            """获取单个同行的F10关键财务指标"""
            code = peer_info.get("code", "")
            if not code:
                return peer_info
            
            try:
                if code.startswith("6"):
                    em_code = f"SH{code}"
                else:
                    em_code = f"SZ{code}"
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://emweb.securities.eastmoney.com/",
                }
                
                f10_url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
                resp = requests.get(f10_url, params={"code": em_code, "type": "0"}, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get("data", [])
                    if records:
                        records.sort(key=lambda r: r.get("REPORT_DATE", ""))
                        # 年报数据
                        annual = [r for r in records if "-12-31" in (r.get("REPORT_DATE") or "")]
                        if not annual:
                            annual = records[-4:] if len(records) >= 4 else records
                        else:
                            annual = annual[-4:]
                        
                        if annual:
                            latest = annual[-1]
                            roe = self._safe_float(latest.get("ROEJQ", 0))
                            # 营收增速：取最近4期平均
                            rev_growth_list = []
                            for r in records[-4:]:
                                rg = self._safe_float(r.get("TOTALOPERATEREVETZ", 0))
                                if rg != 0:
                                    rev_growth_list.append(rg)
                            avg_rev_growth = sum(rev_growth_list) / len(rev_growth_list) if rev_growth_list else 0
                            net_margin = self._safe_float(latest.get("XSJLL", 0))
                            
                            if roe > 0:
                                peer_info["roe"] = roe
                            if avg_rev_growth != 0:
                                peer_info["revenue_growth"] = round(avg_rev_growth, 1)
                            if net_margin > 0:
                                peer_info["net_margin"] = net_margin
            except Exception as e:
                logger.debug(f"同行F10获取失败 {code}: {e}")
            
            return peer_info
        
        # 并行获取（最多8个同行）
        updated_peers = []
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(fetch_peer_f10, p): p for p in peers[:8]}
            for future in as_completed(futures, timeout=15):
                try:
                    updated_peers.append(future.result(timeout=3))
                except Exception:
                    updated_peers.append(futures[future])
        
        if updated_peers:
            result["peers"] = updated_peers
            logger.info(f"同行F10增强完成: {symbol}, 共{len(updated_peers)}家")
    
    def _enrich_analyst_forecast(self, symbol: str, result: Dict[str, Any]):
        """获取分析师一致预期数据（东方财富盈利预测）"""
        try:
            import requests
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/ProfitForecast/PageAjax"
            params = {"code": em_code}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                analyst_data = {}
                
                # 1. 评级统计 (pjtj) - 按时间维度汇总的评级
                pjtj = data.get("pjtj", [])
                if pjtj:
                    # 取最近一个月的数据
                    latest = pjtj[0]
                    buy_num = int(self._safe_float(latest.get("RATING_BUY_NUM", 0)))
                    add_num = int(self._safe_float(latest.get("RATING_ADD_NUM", 0)))
                    neutral_num = int(self._safe_float(latest.get("RATING_NEUTRAL_NUM", 0)))
                    reduce_num = int(self._safe_float(latest.get("RATING_REDUCE_NUM", 0)))
                    sale_num = int(self._safe_float(latest.get("RATING_SALE_NUM", 0)))
                    total_org = int(self._safe_float(latest.get("RATING_ORG_NUM", 0)))
                    compre_rating = str(latest.get("COMPRE_RATING", ""))
                    compre_score = self._safe_float(latest.get("COMPRE_RATING_NUM", 0))
                    
                    rating_count = {}
                    if buy_num > 0:
                        rating_count["买入"] = buy_num
                    if add_num > 0:
                        rating_count["增持"] = add_num
                    if neutral_num > 0:
                        rating_count["中性"] = neutral_num
                    if reduce_num > 0:
                        rating_count["减持"] = reduce_num
                    if sale_num > 0:
                        rating_count["卖出"] = sale_num
                    
                    total_ratings = sum(rating_count.values())
                    buy_pct = (buy_num + add_num) / total_ratings * 100 if total_ratings > 0 else 0
                    
                    analyst_data["total_ratings"] = total_ratings
                    analyst_data["buy_pct"] = round(buy_pct, 1)
                    analyst_data["rating_breakdown"] = rating_count
                    analyst_data["compre_rating"] = compre_rating
                    analyst_data["compre_score"] = round(compre_score, 1)
                    analyst_data["total_org"] = total_org
                
                # 2. 机构盈利预测 (jgyc) - EPS预测
                jgyc = data.get("jgyc", [])
                if jgyc:
                    # 取"近六月平均"那条
                    avg_forecast = None
                    for item in jgyc:
                        if "平均" in str(item.get("ORG_NAME_ABBR", "")):
                            avg_forecast = item
                            break
                    if not avg_forecast and jgyc:
                        avg_forecast = jgyc[0]
                    
                    if avg_forecast:
                        eps_forecasts = []
                        for year_key in ["YEAR1", "YEAR2", "YEAR3", "YEAR4"]:
                            year = avg_forecast.get(year_key)
                            eps_key = f"EPS{year_key[-1]}"
                            eps = self._safe_float(avg_forecast.get(eps_key, 0))
                            if year and eps > 0:
                                eps_forecasts.append({
                                    "year": int(year),
                                    "eps": round(eps, 2),
                                })
                        if eps_forecasts:
                            analyst_data["eps_forecasts"] = eps_forecasts
                
                # 3. 历史一致预期 (yctj_list)
                yctj_list = data.get("yctj_list", [])
                if yctj_list:
                    # 最近一期实际数据
                    latest_actual = yctj_list[-1] if yctj_list else None
                    if latest_actual:
                        actual_eps = self._safe_float(latest_actual.get("EPS", 0))
                        actual_revenue = self._safe_float(latest_actual.get("TOTAL_OPERATE_INCOME", 0))
                        if actual_eps > 0:
                            analyst_data["actual_eps"] = round(actual_eps, 2)
                        if actual_revenue > 0:
                            analyst_data["actual_revenue"] = round(actual_revenue / 100000000, 1)  # 转亿
                
                if analyst_data:
                    result["analyst"] = analyst_data
                    logger.info(f"分析师预测获取成功: {symbol}, 评级{analyst_data.get('total_org', 0)}家, 综合{analyst_data.get('compre_rating', '')}")
                    return
        except Exception as e:
            logger.debug(f"分析师预测获取失败: {e}")
    
    def _enrich_institutional_holdings(self, symbol: str, result: Dict[str, Any]):
        """获取机构持仓数据（东方财富十大股东+机构持仓汇总）"""
        try:
            import requests
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            # 十大股东/机构持仓API
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax"
            params = {"code": em_code}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                
                # 十大流通股东 (sdltgd)
                sdltgd = data.get("sdltgd", [])
                top_holders = []
                for h in sdltgd[:10]:
                    top_holders.append({
                        "name": str(h.get("HOLDER_NAME", "")),
                        "ratio": round(self._safe_float(h.get("FREE_HOLDNUM_RATIO", 0)), 2),
                        "type": str(h.get("HOLDER_TYPE", "")),
                        "change": str(h.get("HOLD_NUM_CHANGE", "不变")),
                    })
                
                # 机构持仓汇总 (jgcc)
                jgcc = data.get("jgcc", [])
                total_inst_num = 0
                total_inst_ratio = 0
                for j in jgcc:
                    total_inst_num = max(total_inst_num, int(self._safe_float(j.get("TOTAL_ORG_NUM", 0))))
                    total_inst_ratio = max(total_inst_ratio, self._safe_float(j.get("TOTAL_SHARES_RATIO", 0)))
                
                # 基金持仓 (jjcg) - 计算基金数量和持股比例
                jjcg = data.get("jjcg", [])
                fund_count = len(jjcg)
                fund_total_ratio = round(sum(self._safe_float(j.get("TOTALSHARES_RATIO", 0)) for j in jjcg), 2)
                
                if top_holders or total_inst_num > 0:
                    result["institutional"] = {
                        "top_holders": top_holders[:5],
                        "total_inst_num": total_inst_num,
                        "total_inst_ratio": round(total_inst_ratio, 2),
                        "fund_count": fund_count,
                        "fund_ratio": fund_total_ratio,
                    }
                    logger.info(f"机构持仓获取成功: {symbol}, 机构{total_inst_num}家({total_inst_ratio:.2f}%), 基金{fund_count}家({fund_total_ratio:.2f}%)")
        except Exception as e:
            logger.debug(f"机构持仓获取失败: {e}")
    
    def _enrich_northbound_capital(self, symbol: str, result: Dict[str, Any]):
        """获取北向资金持股数据（东方财富沪深港通个股持股）"""
        try:
            import requests
            
            if symbol.startswith("6"):
                secid = f"1.{symbol}"
            else:
                secid = f"0.{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/",
            }
            
            # 方式1：东方财富push2北向资金个股持股API
            url = "https://push2.eastmoney.com/api/qt/kamt.kline/get"
            params = {
                "fields1": "f1,f2,f3,f4",
                "fields2": "f51,f52,f53,f54",
                "klt": "101",  # 日线
                "lmt": "10",
                "secid": secid,
                "ut": "b2884a393a59ad640b2e1d104a1a3e0e",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = data["data"]["klines"]
                    # 取最近一条有数据的变化
                    hold_ratio = 0
                    hold_change = 0
                    for kline in reversed(klines):
                        parts = kline.split(",")
                        if len(parts) >= 4:
                            ratio = self._safe_float(parts[1])  # 持股比例
                            change = self._safe_float(parts[3])  # 变化
                            if ratio > 0:
                                hold_ratio = ratio
                                hold_change = change
                                break
                    
                    if hold_ratio > 0:
                        # 持股比例已经是百分比
                        result["northbound"] = {
                            "hold_ratio": round(hold_ratio, 2),
                            "hold_change": round(hold_change, 2),
                            "trade_date": str(klines[-1].split(",")[0] if klines else ""),
                        }
                        logger.info(f"北向资金获取成功: {symbol}, 持股{hold_ratio:.2f}%")
                        return
        except Exception as e:
            logger.debug(f"北向资金push2方式获取失败: {e}")
        
        # 方式2：datacenter API（备用）
        try:
            import requests
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/",
            }
            
            url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
            params = {
                "reportName": "RPT_MUTUAL_HOLDSTOCKNORTHSTA",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{symbol}")',
                "pageNumber": "1",
                "pageSize": "3",
                "sortTypes": "-1",
                "sortColumns": "TRADE_DATE",
                "source": "WEB",
                "client": "WEB",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("result") and data["result"].get("data"):
                    rows = data["result"]["data"]
                    if rows:
                        latest = rows[0]
                        hold_ratio = self._safe_float(latest.get("HOLD_RATIO", 0))
                        hold_market = self._safe_float(latest.get("HOLD_MARKET_CAP", 0))
                        hold_change = self._safe_float(latest.get("HOLD_RATIO_CHANGE", 0))
                        
                        if hold_ratio > 0:
                            result["northbound"] = {
                                "hold_ratio": round(hold_ratio, 2),
                                "hold_market_cap": round(hold_market / 100000000, 1) if hold_market > 100000000 else round(hold_market, 1),
                                "hold_change": round(hold_change, 2),
                                "trade_date": str(latest.get("TRADE_DATE", "")),
                            }
                            logger.info(f"北向资金获取成功: {symbol}, 持股{hold_ratio:.2f}%")
                            return
        except Exception as e:
            logger.debug(f"北向资金datacenter方式获取失败: {e}")
    
    def _enrich_valuation_percentile(self, symbol: str, result: Dict[str, Any]):
        """计算PE/PB历史分位数（基于F10历史财务数据）"""
        try:
            import requests
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            # 使用F10 ZYZB type=1获取历史财务数据，计算历史PE波动区间
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
            params = {"code": em_code, "type": "1"}
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("data", [])
                if records:
                    records.sort(key=lambda r: r.get("REPORT_DATE", ""))
                    annual = [r for r in records if "-12-31" in (r.get("REPORT_DATE") or "")]
                    if not annual:
                        annual = records[-5:]
                    
                    # 获取历史ROE和营收增速
                    roe_values = []
                    rev_growth_values = []
                    profit_growth_values = []
                    
                    for r in annual[-5:]:
                        roe = self._safe_float(r.get("ROEJQ", 0))
                        rev_g = self._safe_float(r.get("TOTALOPERATEREVETZ", 0))
                        profit_g = self._safe_float(r.get("PARENTNETPROFITTZ", 0))
                        if roe > 0:
                            roe_values.append(roe)
                        if rev_g != 0:
                            rev_growth_values.append(rev_g)
                        if profit_g != 0:
                            profit_growth_values.append(profit_g)
                    
                    if roe_values:
                        avg_roe = sum(roe_values) / len(roe_values)
                        min_roe = min(roe_values)
                        max_roe = max(roe_values)
                        
                        # 基于ROE和增速估算PE区间
                        # 高ROE公司合理PE = ROE * 合理PB倍数
                        # 合理PB = 1.0~3.0（取决于增速）
                        avg_growth = sum(rev_growth_values) / len(rev_growth_values) if rev_growth_values else 10
                        
                        # 增速越高，合理PB越高
                        if avg_growth > 30:
                            reasonable_pb_low, reasonable_pb_high = 3.0, 6.0
                        elif avg_growth > 20:
                            reasonable_pb_low, reasonable_pb_high = 2.0, 4.5
                        elif avg_growth > 10:
                            reasonable_pb_low, reasonable_pb_high = 1.5, 3.5
                        elif avg_growth > 5:
                            reasonable_pb_low, reasonable_pb_high = 1.0, 2.5
                        else:
                            reasonable_pb_low, reasonable_pb_high = 0.8, 2.0
                        
                        # PE = PB / ROE * 100
                        pe_low = round(reasonable_pb_low / avg_roe * 100, 0)
                        pe_high = round(reasonable_pb_high / avg_roe * 100, 0)
                        
                        current_pe = result["basic"].get("pe", 0)
                        
                        if current_pe > 0 and pe_high > pe_low:
                            # 计算分位
                            if current_pe <= pe_low:
                                pe_percentile = 5
                            elif current_pe >= pe_high:
                                pe_percentile = 95
                            else:
                                pe_percentile = (current_pe - pe_low) / (pe_high - pe_low) * 90 + 5
                            
                            pe_level = "偏低" if pe_percentile < 30 else "中等" if pe_percentile < 70 else "偏高"
                            
                            result["valuation_percentile"] = {
                                "pe_percentile": round(pe_percentile, 1),
                                "pe_range_low": pe_low,
                                "pe_range_high": pe_high,
                                "method": "roe_growth_based",
                                "note": f"基于{len(annual)}年历史ROE(均值{avg_roe:.1f}%)和增速(均值{avg_growth:.1f}%)的PE估值分位",
                                "roe_range": f"{min_roe:.1f}%~{max_roe:.1f}%",
                                "growth_range": f"{min(rev_growth_values):.1f}%~{max(rev_growth_values):.1f}%" if rev_growth_values else "",
                            }
                            logger.info(f"估值分位(改进): {symbol}, PE={current_pe}处于{pe_percentile:.0f}%分位, 历史ROE={avg_roe:.1f}%, 增速={avg_growth:.1f}%")
                            return
        except Exception as e:
            logger.debug(f"估值分位计算失败: {e}")
        
        # 备用方案：基于ROE估算
        try:
            roe = result["basic"].get("roe", 0)
            pe = result["basic"].get("pe", 0)
            
            if roe > 0 and pe > 0:
                if roe > 25:
                    pe_range = (18, 35)
                elif roe > 15:
                    pe_range = (12, 28)
                elif roe > 8:
                    pe_range = (10, 22)
                else:
                    pe_range = (8, 18)
                
                pe_percentile = max(5, min(95, (pe - pe_range[0]) / (pe_range[1] - pe_range[0]) * 100))
                
                result["valuation_percentile"] = {
                    "pe_percentile": round(pe_percentile, 1),
                    "pe_range_low": pe_range[0],
                    "pe_range_high": pe_range[1],
                    "method": "roe_based_estimate",
                    "note": "基于ROE水平的PE估值分位估算",
                }
                logger.info(f"估值分位估算: {symbol}, PE={pe}处于{pe_percentile:.0f}%分位(ROE={roe}%)")
        except Exception as e:
            logger.debug(f"估值分位估算失败: {e}")
    
    def _enrich_dividend_info(self, symbol: str, result: Dict[str, Any]):
        """获取分红数据（东方财富F10分红融资）"""
        try:
            import requests
            import re
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/BonusFinancing/PageAjax"
            params = {"code": em_code}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                
                # 分红影响 (fhyx) - 包含分红方案和进度
                fhyx = data.get("fhyx", [])
                if fhyx:
                    # 找最近一次已实施的现金分红
                    latest_dividend = None
                    for item in fhyx:
                        progress = str(item.get("ASSIGN_PROGRESS", ""))
                        plan = str(item.get("IMPL_PLAN_PROFILE", ""))
                        if "实施" in progress and "派" in plan:
                            latest_dividend = item
                            break
                    
                    if not latest_dividend:
                        # 取最近一条有分红方案的记录
                        for item in fhyx:
                            plan = str(item.get("IMPL_PLAN_PROFILE", ""))
                            if "派" in plan:
                                latest_dividend = item
                                break
                    
                    if latest_dividend:
                        plan = str(latest_dividend.get("IMPL_PLAN_PROFILE", ""))
                        # 解析 "10派280.2423元" 格式 → 每股分红28.02423元
                        cash_per_share = 0
                        match = re.search(r'10派([\d.]+)元', plan)
                        if match:
                            cash_per_share = float(match.group(1)) / 10.0
                        
                        if cash_per_share > 0:
                            # 获取当前股价计算股息率
                            price = 0
                            basic = result.get("basic", {})
                            price = self._safe_float(basic.get("price", basic.get("latest_price", 0)))
                            if price <= 0:
                                # 尝试从腾讯API获取
                                try:
                                    if symbol.startswith("6"):
                                        tx_code = f"sh{symbol}"
                                    else:
                                        tx_code = f"sz{symbol}"
                                    tx_resp = requests.get(f"https://qt.gtimg.cn/q={tx_code}", 
                                                          headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                                    if tx_resp.status_code == 200:
                                        content = tx_resp.text
                                        if "~" in content:
                                            idx1 = content.find('"')
                                            idx2 = content.find('"', idx1 + 1)
                                            if idx1 >= 0 and idx2 > idx1:
                                                fields = content[idx1+1:idx2].split("~")
                                                if len(fields) > 3:
                                                    price = self._safe_float(fields[3])  # 当前价
                                except Exception:
                                    pass
                            
                            dividend_yield = (cash_per_share / price * 100) if price > 0 else 0
                            
                            result["dividend"] = {
                                "dividend_yield": round(dividend_yield, 2),
                                "cash_per_share": round(cash_per_share, 2),
                                "plan": plan,
                                "ex_date": str(latest_dividend.get("EX_DIVIDEND_DATE", "")),
                                "source": "eastmoney_f10",
                            }
                            logger.info(f"分红数据获取成功: {symbol}, {plan}, 股息率{dividend_yield:.2f}%")
                            return
                
                # 历年分红融资 (lnfhrz) - 提供总额数据
                lnfhrz = data.get("lnfhrz", [])
                if lnfhrz and not result.get("dividend"):
                    latest = lnfhrz[0]
                    total_div = self._safe_float(latest.get("TOTAL_DIVIDEND", 0))
                    if total_div > 0:
                        result["dividend"] = {
                            "total_dividend": round(total_div / 100000000, 1),  # 转亿
                            "year": str(latest.get("STATISTICS_YEAR", "")),
                            "source": "eastmoney_f10_annual",
                        }
                        logger.info(f"分红总额获取成功: {symbol}, {latest.get('STATISTICS_YEAR')}年分红{total_div/100000000:.1f}亿")
        except Exception as e:
            logger.debug(f"东方财富分红数据获取失败: {e}")

    def _enrich_revenue_segment(self, symbol: str, result: Dict[str, Any]):
        """获取主营构成数据（东方财富F10经营分析）"""
        try:
            import requests
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax"
            params = {"code": em_code}
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                zygcfx = data.get("zygcfx", [])
                if zygcfx:
                    # 取最新报告期的数据，按收入占比排序
                    latest_date = zygcfx[0].get("REPORT_DATE", "")
                    latest_items = [item for item in zygcfx if item.get("REPORT_DATE") == latest_date]
                    
                    # 按 MAINOP_TYPE 分类：1=行业, 2=产品, 3=地区
                    segments = {"industry": [], "product": [], "region": []}
                    type_map = {"1": "industry", "2": "product", "3": "region"}
                    
                    for item in latest_items:
                        op_type = str(item.get("MAINOP_TYPE", "2"))
                        key = type_map.get(op_type, "product")
                        segments[key].append({
                            "name": str(item.get("ITEM_NAME", "")),
                            "revenue": self._safe_float(item.get("MAIN_BUSINESS_INCOME", 0)),
                            "ratio": self._safe_float(item.get("MBI_RATIO", 0)) * 100,
                            "cost": self._safe_float(item.get("MAIN_BUSINESS_COST", 0)),
                            "profit": self._safe_float(item.get("MAIN_BUSINESS_PROFIT", 0)),
                            "margin": self._safe_float(item.get("MAIN_BUSINESS_RATIO", 0)),
                        })
                    
                    # 按收入降序排列
                    for key in segments:
                        segments[key].sort(key=lambda x: x["revenue"], reverse=True)
                    
                    if any(segments.values()):
                        result["revenue_segment"] = segments
                        total_items = sum(len(v) for v in segments.values())
                        logger.info(f"主营构成获取成功: {symbol}, {total_items}项, 报告期={latest_date[:10]}")
                        return
        except Exception as e:
            logger.debug(f"主营构成获取失败: {e}")
    
    def _enrich_operating_efficiency(self, symbol: str, result: Dict[str, Any]):
        """获取运营效率指标（从F10 ZYZB type=1提取额外字段）"""
        try:
            # 从F10 ZYZB type=1中提取更多效率指标
            # 这些数据已在 _fetch_financial_from_em_web 中获取过，但 type=1 有更多字段
            import requests
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
            params = {"code": em_code, "type": "1"}
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("data", [])
                if records:
                    latest = records[-1]  # 最新一期
                    
                    efficiency = {}
                    
                    # 资产周转率
                    eff_fields = {
                        "asset_turnover": "CURRENT_ASSET_TR",  # 总资产周转率
                        "fixed_asset_turnover": "FIXED_ASSET_TR",  # 固定资产周转率
                        "inventory_turnover": "INVENTORY_TR",  # 存货周转率
                        "receivable_turnover": "RECEIVABLE_TR",  # 应收账款周转率
                        "cash_ratio": "CASH_RATIO",  # 现金比率
                        "current_ratio": "CURRENT_RATIO",  # 流动比率
                        "quick_ratio": "QUICK_RATIO",  # 速动比率
                        "equity_multiplier": "EQUITY_MULTIPLIER",  # 权益乘数
                        "nco_netprofit_ratio": "NCO_NETPROFIT",  # 经营活动现金流/净利润
                        "interest_debt_ratio": "INTEREST_DEBT_RATIO",  # 带息债务比率
                        "tax_rate": "TAXRATE",  # 实际税率
                        "bps": "BPS",  # 每股净资产
                        "bps_growth": "BPSTZ",  # 每股净资产增长率
                        "sales_cash_ratio": "XSJXLYYSR",  # 销售收现/营收
                        "operate_cash_ratio": "JYXJLYYSR",  # 经营现金流/营收
                    }
                    
                    for key, field in eff_fields.items():
                        val = self._safe_float(latest.get(field, 0))
                        if val != 0:
                            efficiency[key] = round(val, 2)
                    
                    if efficiency:
                        result["operating_efficiency"] = efficiency
                        logger.info(f"运营效率获取成功: {symbol}, {len(efficiency)}项指标")
                        return
        except Exception as e:
            logger.debug(f"运营效率获取失败: {e}")

    def _get_us_financial_data(self, symbol: str) -> Dict[str, Any]:
        """获取美股深度财务数据"""
        result = {"basic": {}, "growth": {}, "profitability": {}, "cashflow": {}, "peers": [], "source": "mock"}
        
        try:
            # 使用AKShare美股基本面
            self._track_cost("stock_us_fundamental")
            df = self._ak.stock_us_fundamental(symbol=symbol)
            if df is not None and not df.empty:
                row = df.iloc[0]
                result["basic"] = {
                    "pe": self._safe_float(row.get("市盈率", row.get("PE", 0))),
                    "pb": self._safe_float(row.get("市净率", row.get("PB", 0))),
                    "market_cap": self._safe_float(row.get("总市值", row.get("marketCap", 0))),
                    "revenue": self._safe_float(row.get("营业收入", row.get("revenue", 0))),
                    "net_profit": self._safe_float(row.get("净利润", row.get("netIncome", 0))),
                    "roe": self._safe_float(row.get("净资产收益率", row.get("ROE", 0))),
                    "industry": str(row.get("行业", row.get("industry", ""))),
                    "eps": self._safe_float(row.get("每股收益", row.get("EPS", 0))),
                    "dividend_yield": self._safe_float(row.get("股息率", row.get("dividendYield", 0))),
                }
                result["source"] = "akshare"
                logger.info(f"美股基本面获取成功: {symbol}")
        except Exception as e:
            logger.warning(f"美股基本面获取失败: {e}")

        # 尝试获取美股利润表数据
        try:
            self._track_cost("stock_us_profit")
            df_profit = self._ak.stock_us_profit(symbol=symbol, indicator="年报")
            if df_profit is not None and not df_profit.empty:
                recent = df_profit.tail(4)
                revenues = []
                profits = []
                for _, row in recent.iterrows():
                    rev = self._safe_float(row.get("营业收入", row.get("revenue", 0)))
                    profit = self._safe_float(row.get("净利润", row.get("netIncome", 0)))
                    if rev > 0:
                        revenues.append(rev)
                    if profit != 0:
                        profits.append(profit)
                
                if len(revenues) >= 2:
                    rev_growth = [(revenues[i] - revenues[i-1]) / abs(revenues[i-1]) * 100 for i in range(1, len(revenues))]
                    result["growth"] = {
                        "revenue_growth_yoy": rev_growth,
                        "avg_revenue_growth": sum(rev_growth) / len(rev_growth) if rev_growth else 0,
                    }
                if len(profits) >= 2:
                    profit_growth = [(profits[i] - profits[i-1]) / abs(profits[i-1]) * 100 for i in range(1, len(profits))]
                    result["growth"]["profit_growth_yoy"] = profit_growth
                    result["growth"]["avg_profit_growth"] = sum(profit_growth) / len(profit_growth) if profit_growth else 0
                
                result["source"] = "akshare"
                logger.info(f"美股利润表获取成功: {symbol}")
        except Exception as e:
            logger.warning(f"美股利润表获取失败: {e}")

        return result

    @staticmethod
    def _safe_float(val) -> float:
        """安全转换为float"""
        if val is None:
            return 0.0
        try:
            v = float(val)
            return v if not np.isnan(v) and not np.isinf(v) else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _enrich_income_statement(self, symbol: str, result: Dict[str, Any]):
        """获取利润表明细（东方财富datacenter）"""
        try:
            import requests
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/",
            }
            
            url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
            params = {
                "reportName": "RPT_DMSK_FN_INCOME",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{symbol}")',
                "pageNumber": "1",
                "pageSize": "5",
                "sortTypes": "-1",
                "sortColumns": "REPORT_DATE",
                "source": "WEB",
                "client": "WEB",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("result") and data["result"].get("data"):
                    rows = data["result"]["data"]
                    # 取最近3期年报
                    annual_rows = [r for r in rows if r.get("REPORT_DATE", "").endswith("-12-31")][:3]
                    if not annual_rows:
                        annual_rows = rows[:3]
                    
                    income_data = []
                    for r in annual_rows:
                        income_data.append({
                            "report_date": str(r.get("REPORT_DATE", ""))[:10],
                            "revenue": self._safe_float(r.get("TOTAL_OPERATE_INCOME", 0)),
                            "operate_cost": self._safe_float(r.get("OPERATE_COST", 0)),
                            "sale_expense": self._safe_float(r.get("SALE_EXPENSE", 0)),
                            "manage_expense": self._safe_float(r.get("MANAGE_EXPENSE", 0)),
                            "finance_expense": self._safe_float(r.get("FINANCE_EXPENSE", 0)),
                            "operate_profit": self._safe_float(r.get("OPERATE_PROFIT", 0)),
                            "total_profit": self._safe_float(r.get("TOTAL_PROFIT", 0)),
                            "income_tax": self._safe_float(r.get("INCOME_TAX", 0)),
                            "net_profit": self._safe_float(r.get("PARENT_NETPROFIT", 0)),
                        })
                    
                    if income_data:
                        result["income_statement"] = income_data
                        logger.info(f"利润表获取成功: {symbol}, {len(income_data)}期")
                        return
        except Exception as e:
            logger.debug(f"利润表获取失败: {e}")

    def _enrich_balance_sheet(self, symbol: str, result: Dict[str, Any]):
        """获取资产负债表（东方财富datacenter）"""
        try:
            import requests
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/",
            }
            
            url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
            params = {
                "reportName": "RPT_DMSK_FN_BALANCE",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{symbol}")',
                "pageNumber": "1",
                "pageSize": "3",
                "sortTypes": "-1",
                "sortColumns": "REPORT_DATE",
                "source": "WEB",
                "client": "WEB",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("result") and data["result"].get("data"):
                    rows = data["result"]["data"]
                    latest = rows[0]
                    
                    bs_data = {
                        "report_date": str(latest.get("REPORT_DATE", ""))[:10],
                        "total_assets": self._safe_float(latest.get("TOTAL_ASSETS", 0)),
                        "total_liabilities": self._safe_float(latest.get("TOTAL_LIABILITIES", 0)),
                        "total_equity": self._safe_float(latest.get("TOTAL_EQUITY", 0)),
                        "monetary_funds": self._safe_float(latest.get("MONETARYFUNDS", 0)),
                        "accounts_receivable": self._safe_float(latest.get("ACCOUNTS_RECE", 0)),
                        "inventory": self._safe_float(latest.get("INVENTORY", 0)),
                        "fixed_asset": self._safe_float(latest.get("FIXED_ASSET", 0)),
                        "accounts_payable": self._safe_float(latest.get("ACCOUNTS_PAYABLE", 0)),
                    }
                    
                    if bs_data["total_assets"] > 0:
                        result["balance_sheet"] = bs_data
                        logger.info(f"资产负债表获取成功: {symbol}, 总资产={bs_data['total_assets']/1e8:.0f}亿")
                        return
        except Exception as e:
            logger.debug(f"资产负债表获取失败: {e}")

    def _enrich_cashflow_statement(self, symbol: str, result: Dict[str, Any]):
        """获取现金流量表（东方财富datacenter）"""
        try:
            import requests
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/",
            }
            
            url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
            params = {
                "reportName": "RPT_DMSK_FN_CASHFLOW",
                "columns": "ALL",
                "filter": f'(SECURITY_CODE="{symbol}")',
                "pageNumber": "1",
                "pageSize": "3",
                "sortTypes": "-1",
                "sortColumns": "REPORT_DATE",
                "source": "WEB",
                "client": "WEB",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("result") and data["result"].get("data"):
                    rows = data["result"]["data"]
                    # 取最近3期年报
                    annual_rows = [r for r in rows if r.get("REPORT_DATE", "").endswith("-12-31")][:3]
                    if not annual_rows:
                        annual_rows = rows[:3]
                    
                    cf_data = []
                    for r in annual_rows:
                        cf_data.append({
                            "report_date": str(r.get("REPORT_DATE", ""))[:10],
                            "operate_cf": self._safe_float(r.get("NETCASH_OPERATE", 0)),
                            "invest_cf": self._safe_float(r.get("NETCASH_INVEST", 0)),
                            "finance_cf": self._safe_float(r.get("NETCASH_FINANCE", 0)),
                            "sales_cash": self._safe_float(r.get("SALES_SERVICES", 0)),
                            "capex": self._safe_float(r.get("CONSTRUCT_LONG_ASSET", 0)),
                        })
                    
                    if cf_data:
                        result["cashflow_statement"] = cf_data
                        # 同时更新cashflow的FCF（使用现金流量表的真实数据）
                        if cf_data and cf_data[0]["operate_cf"] != 0:
                            fcf = cf_data[0]["operate_cf"] + cf_data[0].get("capex", 0)
                            result["cashflow"]["operating_cf"] = cf_data[0]["operate_cf"]
                            result["cashflow"]["fcf"] = fcf
                            result["cashflow"]["_fcf_unavailable"] = False
                        logger.info(f"现金流量表获取成功: {symbol}, {len(cf_data)}期")
                        return
        except Exception as e:
            logger.debug(f"现金流量表获取失败: {e}")

    def _enrich_shareholder_structure(self, symbol: str, result: Dict[str, Any]):
        """获取股东结构数据（筹码集中度、实际控制人）"""
        try:
            import requests
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax"
            params = {"code": em_code}
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                
                shareholder_data = {}
                
                # 股东人数变化（筹码集中度）
                gdrs = data.get("gdrs", [])
                if gdrs:
                    holders = []
                    for item in gdrs[:8]:
                        holders.append({
                            "date": str(item.get("END_DATE", ""))[:10],
                            "total_num": self._safe_float(item.get("HOLDER_TOTAL_NUM", 0)),
                            "change_ratio": self._safe_float(item.get("TOTAL_NUM_RATIO", 0)),
                            "avg_shares": self._safe_float(item.get("AVG_FREE_SHARES", 0)),
                            "focus": str(item.get("HOLD_FOCUS", "")),
                        })
                    if holders:
                        shareholder_data["holders_trend"] = holders
                        
                        # 筹码集中度判断
                        latest = holders[0]
                        if len(holders) >= 2:
                            prev = holders[1]
                            if latest["change_ratio"] < -5:
                                shareholder_data["concentration"] = "筹码高度集中，股东人数大幅减少"
                            elif latest["change_ratio"] < -2:
                                shareholder_data["concentration"] = "筹码趋于集中，股东人数减少"
                            elif latest["change_ratio"] > 5:
                                shareholder_data["concentration"] = "筹码趋于分散，股东人数大幅增加"
                            elif latest["change_ratio"] > 2:
                                shareholder_data["concentration"] = "筹码略有分散，股东人数增加"
                            else:
                                shareholder_data["concentration"] = "筹码分布稳定"
                        shareholder_data["avg_hold_amount"] = self._safe_float(
                            gdrs[0].get("AVG_HOLD_AMT", 0)
                        )
                
                # 实际控制人
                sjkzr = data.get("sjkzr", [])
                if sjkzr and sjkzr[0].get("HOLDER_NAME"):
                    shareholder_data["actual_controller"] = str(sjkzr[0]["HOLDER_NAME"])
                
                if shareholder_data:
                    result["shareholder"] = shareholder_data
                    logger.info(f"股东结构获取成功: {symbol}, {len(shareholder_data.get('holders_trend', []))}期")
                    return
        except Exception as e:
            logger.debug(f"股东结构获取失败: {e}")

    def _enrich_per_capita_metrics(self, symbol: str, result: Dict[str, Any]):
        """获取人均效率指标（从F10 ZYZB type=1提取STAFF_NUM和人均指标）"""
        try:
            # 从已有的F10数据中提取（已在_fetch_financial_from_em_web中获取）
            # 此处重新请求以确保获取到最新数据
            import requests
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
            params = {"code": em_code, "type": "1"}
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("data", [])
                if records:
                    # 按日期正序排列
                    records.sort(key=lambda r: r.get("REPORT_DATE", ""))
                    
                    # 取最近几期年报
                    annual = [r for r in records if "-12-31" in (r.get("REPORT_DATE") or "")]
                    if not annual:
                        annual = records[-3:]
                    
                    latest = annual[-1] if annual else records[-1]
                    
                    staff_num = self._safe_float(latest.get("STAFF_NUM", 0))
                    per_toi = self._safe_float(latest.get("PER_TOI", 0))  # 人均营收
                    per_oi = self._safe_float(latest.get("PER_OI", 0))  # 人均营业利润
                    per_ebit = self._safe_float(latest.get("PER_EBIT", 0))  # 人均EBIT
                    
                    # 历史趋势
                    staff_trend = []
                    per_toi_trend = []
                    per_oi_trend = []
                    for r in annual[-4:]:
                        sn = self._safe_float(r.get("STAFF_NUM", 0))
                        pt = self._safe_float(r.get("PER_TOI", 0))
                        po = self._safe_float(r.get("PER_OI", 0))
                        date = str(r.get("REPORT_DATE", ""))[:4]
                        if sn > 0:
                            staff_trend.append({"year": date, "staff": int(sn)})
                        if pt > 0:
                            per_toi_trend.append({"year": date, "per_toi": round(pt, 2)})
                        if po > 0:
                            per_oi_trend.append({"year": date, "per_oi": round(po, 2)})
                    
                    if staff_num > 0 or per_toi > 0:
                        per_capita = {
                            "staff_num": int(staff_num) if staff_num > 0 else 0,
                            "per_revenue": round(per_toi / 10000, 2) if per_toi > 0 else 0,  # 转换为万元
                            "per_operate_profit": round(per_oi / 10000, 2) if per_oi > 0 else 0,
                            "per_ebit": round(per_ebit / 10000, 2) if per_ebit > 0 else 0,
                            "staff_trend": staff_trend,
                            "per_toi_trend": per_toi_trend,
                            "per_oi_trend": per_oi_trend,
                        }
                        result["per_capita"] = per_capita
                        logger.info(f"人均效率获取成功: {symbol}, 员工={staff_num}, 人均营收={per_toi/10000:.1f}万")
                        return
        except Exception as e:
            logger.debug(f"人均效率获取失败: {e}")

    def _enrich_growth_quality(self, symbol: str, result: Dict[str, Any]):
        """分析增长质量（将营收增长拆解为量价贡献）"""
        try:
            # 从F10 ZYZB type=1获取历史毛利率和营收数据来判断增长质量
            # 毛利率持续上升 → 增长由定价权驱动（质量高）
            # 毛利率下降但营收增长 → 增长由量驱动（质量中等）
            # 毛利率下降且营收增长放缓 → 增长质量差
            
            growth = result.get("growth", {})
            profitability = result.get("profitability", {})
            
            gross_margins = profitability.get("gross_margin", [])
            rev_growth = growth.get("revenue_growth_yoy", [])
            
            if not gross_margins or not rev_growth:
                return
            
            # 取最近3期
            recent_gm = gross_margins[-3:] if len(gross_margins) >= 3 else gross_margins
            recent_rev = rev_growth[-3:] if len(rev_growth) >= 3 else rev_growth
            
            # 毛利率趋势
            gm_trend = 0
            if len(recent_gm) >= 2:
                gm_trend = recent_gm[-1] - recent_gm[0]
            
            # 营收增速趋势
            rev_trend = 0
            if len(recent_rev) >= 2:
                rev_trend = recent_rev[-1] - recent_rev[0]
            
            # 增长质量判断
            if gm_trend > 1 and rev_trend > 0:
                quality = "量价齐升，增长质量优秀"
                detail = "毛利率持续提升叠加营收加速增长，说明公司在量价两端均有优势"
            elif gm_trend > 1 and rev_trend < 0:
                quality = "价格驱动，量的增长放缓"
                detail = "毛利率提升但营收增速放缓，增长由提价驱动，需关注销量是否见顶"
            elif gm_trend < -1 and rev_trend > 0:
                quality = "以价换量，增长质量需关注"
                detail = "毛利率下降但营收增速上升，可能在通过降价抢占市场份额"
            elif gm_trend < -1 and rev_trend < 0:
                quality = "量价齐跌，增长质量恶化"
                detail = "毛利率和营收增速双双下滑，经营面临较大压力"
            elif abs(gm_trend) <= 1 and rev_trend > 0:
                quality = "增长稳健，量价结构良好"
                detail = "毛利率稳定、营收增速上升，增长质量较高"
            elif abs(gm_trend) <= 1 and rev_trend < 0:
                quality = "增长放缓，毛利率稳定"
                detail = "毛利率稳定但营收增速下降，可能面临行业天花板"
            else:
                quality = "增长质量基本稳定"
                detail = "毛利率和营收增速变化不大，经营结构稳定"
            
            result["growth_quality"] = {
                "quality": quality,
                "detail": detail,
                "gm_trend": round(gm_trend, 1),
                "rev_trend": round(rev_trend, 1),
            }
            logger.info(f"增长质量分析: {symbol}, {quality}")
        except Exception as e:
            logger.debug(f"增长质量分析失败: {e}")

    def _enrich_financial_anomaly(self, symbol: str, result: Dict[str, Any]):
        """财务异常检测（应收账款/营收、存货/营收异常）"""
        try:
            import requests
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
            params = {"code": em_code, "type": "1"}
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("data", [])
                if records:
                    records.sort(key=lambda r: r.get("REPORT_DATE", ""))
                    annual = [r for r in records if "-12-31" in (r.get("REPORT_DATE") or "")]
                    if not annual:
                        annual = records[-3:]
                    
                    latest = annual[-1] if annual else records[-1]
                    
                    anomalies = []
                    warnings = []
                    
                    # 应收账款/营收 比例
                    yszk_ratio = self._safe_float(latest.get("YSZKYYSR", 0))
                    if yszk_ratio > 50:
                        anomalies.append(f"应收账款/营收={yszk_ratio:.1f}%，占比过高，存在回款风险")
                    elif yszk_ratio > 30:
                        warnings.append(f"应收账款/营收={yszk_ratio:.1f}%，关注回款周期")
                    
                    # 应收账款周转天数
                    yszk_days = self._safe_float(latest.get("YSZKZZTS", 0))
                    if yszk_days > 180:
                        anomalies.append(f"应收账款周转天数={yszk_days:.0f}天，回款周期过长")
                    elif yszk_days > 90:
                        warnings.append(f"应收账款周转天数={yszk_days:.0f}天，回款周期偏长")
                    
                    # 存货/营收趋势
                    chzzl = self._safe_float(latest.get("CHZZL", 0))
                    if chzzl > 0.5:
                        anomalies.append(f"存货增速({chzzl*100:.1f}%)远超营收增速，可能积压")
                    
                    # 经营现金流/净利润
                    nco_np = self._safe_float(latest.get("NCO_NETPROFIT", 0))
                    if nco_np < 0.3:
                        warnings.append(f"经营现金流/净利润={nco_np:.2f}，盈利含金量偏低")
                    
                    # 利息保障倍数
                    interest_cover = self._safe_float(latest.get("INTEREST_COVERAGE_RATIO", 0))
                    if 0 < interest_cover < 2:
                        anomalies.append(f"利息保障倍数={interest_cover:.1f}x，偿债能力不足")
                    elif 0 < interest_cover < 5:
                        warnings.append(f"利息保障倍数={interest_cover:.1f}x，需关注偿债能力")
                    
                    if anomalies or warnings:
                        result["financial_anomaly"] = {
                            "anomalies": anomalies,
                            "warnings": warnings,
                            "yszk_ratio": round(yszk_ratio, 1),
                            "yszk_days": round(yszk_days, 0),
                            "chzzl": round(chzzl * 100, 1) if chzzl else 0,
                            "nco_np": round(nco_np, 2),
                            "interest_cover": round(interest_cover, 1),
                        }
                        logger.info(f"财务异常检测: {symbol}, {len(anomalies)}异常, {len(warnings)}警告")
                        return
        except Exception as e:
            logger.debug(f"财务异常检测失败: {e}")

    def _enrich_earnings_forecast(self, symbol: str, result: Dict[str, Any]):
        """业绩预告数据（管理层指引 vs 实际）"""
        try:
            import requests
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://data.eastmoney.com/",
            }
            
            url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
            params = {
                "reportName": "RPT_PUBLIC_OP_NEWPREDICT",
                "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,NOTICE_DATE,REPORT_DATE,PREDICT_FINANCE,PREDICT_AMT_LOWER,PREDICT_AMT_UPPER,ADD_AMP_LOWER,ADD_AMP_UPPER,PREDICT_CONTENT,CHANGE_REASON_EXPLAIN",
                "filter": f'(SECURITY_CODE="{symbol}")',
                "pageNumber": 1,
                "pageSize": 5,
                "sortTypes": -1,
                "sortColumns": "NOTICE_DATE",
                "source": "WEB",
                "client": "PC",
                "v": "08996668763638384",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("result"):
                    rows = data["result"].get("data", [])
                    if rows:
                        forecasts = []
                        for row in rows[:3]:
                            forecasts.append({
                                "notice_date": (row.get("NOTICE_DATE") or "")[:10],
                                "report_date": (row.get("REPORT_DATE") or "")[:10],
                                "predict_type": row.get("PREDICT_FINANCE", ""),
                                "amt_lower": self._safe_float(row.get("PREDICT_AMT_LOWER", 0)),
                                "amt_upper": self._safe_float(row.get("PREDICT_AMT_UPPER", 0)),
                                "add_amp_lower": self._safe_float(row.get("ADD_AMP_LOWER", 0)),
                                "add_amp_upper": self._safe_float(row.get("ADD_AMP_UPPER", 0)),
                                "content": row.get("PREDICT_CONTENT", ""),
                                "reason": (row.get("CHANGE_REASON_EXPLAIN") or "")[:200],
                            })
                        if forecasts:
                            result["earnings_forecast"] = forecasts
                            logger.info(f"业绩预告: {symbol}, {len(forecasts)}条")
                            return
        except Exception as e:
            logger.debug(f"业绩预告获取失败: {e}")

    def _enrich_lockup_shares(self, symbol: str, result: Dict[str, Any]):
        """限售股解禁分析"""
        try:
            import requests
            
            if symbol.startswith("6"):
                em_code = f"SH{symbol}"
            else:
                em_code = f"SZ{symbol}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://emweb.securities.eastmoney.com/",
            }
            
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax"
            params = {"code": em_code}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                ltgf = data.get("ltgf", [])
                if ltgf:
                    item = ltgf[0]
                    limited = self._safe_float(item.get("LIMITED_SHARES", 0))
                    total = self._safe_float(item.get("HOLD_NUM_COUNT", 0))
                    limited_ratio = self._safe_float(item.get("LIMITED_SHARES_RATIO", 0))
                    unlimited_ratio = self._safe_float(item.get("UNLIMITED_SHARES_RATIO", 0))
                    
                    lockup_info = {
                        "total_shares": int(total),
                        "limited_shares": int(limited),
                        "limited_ratio": limited_ratio,
                        "unlimited_ratio": unlimited_ratio,
                        "end_date": (item.get("END_DATE") or "")[:10],
                    }
                    
                    if limited > 0:
                        lockup_info["risk"] = "有限售股待解禁，需关注解禁时间表"
                        if limited_ratio > 30:
                            lockup_info["risk_level"] = "高"
                        elif limited_ratio > 10:
                            lockup_info["risk_level"] = "中"
                        else:
                            lockup_info["risk_level"] = "低"
                    else:
                        lockup_info["risk"] = "无限售股，全流通"
                        lockup_info["risk_level"] = "无"
                    
                    result["lockup_shares"] = lockup_info
                    logger.info(f"限售股分析: {symbol}, 限售比例={limited_ratio}%")
                    return
        except Exception as e:
            logger.debug(f"限售股分析失败: {e}")

    def _mock_financial_data(self, symbol: str, market: str) -> Dict[str, Any]:
        """模拟财务数据（用于真实数据不可用时的回退）"""
        return {
            "basic": {},
            "growth": {},
            "profitability": {},
            "cashflow": {},
            "peers": [],
            "source": "mock",
            "_mock": True,
        }

    # ==================== 搜索 ====================

    def search_stocks(self, keyword: str, market: str = "A") -> List[Dict[str, Any]]:
        """搜索股票"""
        if self._ak is None:
            return self._mock_search(keyword, market)

        try:
            import time as time_mod
            # 美股搜索
            if market.upper() == "US":
                # 使用缓存（1小时有效），避免每次都拉取全量美股列表
                cache_ttl = 3600
                if self._us_stock_cache is not None and (time_mod.time() - self._us_stock_cache_time) < cache_ttl:
                    df = self._us_stock_cache
                else:
                    df = None
                    for attempt in range(2):
                        try:
                            self._track_cost("stock_us_spot_em")
                            df = self._ak.stock_us_spot_em()
                            if df is not None and not df.empty:
                                self._us_stock_cache = df
                                self._us_stock_cache_time = time_mod.time()
                                break
                        except Exception as e:
                            if attempt < 1:
                                time_mod.sleep(1)
                            else:
                                logger.warning(f"美股列表获取失败: {e}")
                    # 回退
                    if df is None or df.empty:
                        try:
                            self._track_cost("stock_us_spot_em")
                            df = self._ak.stock_us_famous_spot_em()
                            if df is not None and not df.empty:
                                self._us_stock_cache = df
                                self._us_stock_cache_time = time_mod.time()
                        except Exception as e:
                            logger.warning(f"美股知名股票获取失败: {e}")

                if df is not None and not df.empty:
                    code_col = None
                    name_col = None
                    for col in df.columns:
                        col_lower = str(col).lower()
                        if col_lower in ("code", "代码", "symbol"):
                            code_col = col
                        if col_lower in ("name", "名称", "chinese_name", "cname"):
                            name_col = col
                    if code_col is None:
                        code_col = df.columns[0]
                    if name_col is None:
                        name_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

                    keyword_upper = keyword.upper().strip()
                    results = df[
                        df[code_col].astype(str).str.upper().str.contains(keyword_upper, na=False) |
                        df[name_col].astype(str).str.contains(keyword, case=False, na=False)
                    ]
                    stocks = []
                    for _, row in results.head(20).iterrows():
                        code = str(row[code_col]).strip()
                        name = str(row[name_col]).strip() if pd.notna(row[name_col]) else code
                        stocks.append({
                            "code": code,
                            "name": name,
                            "market": "US",
                        })
                    return stocks

                return self._mock_search(keyword, market)

            # A股搜索（默认）
            # 1小时缓存，避免每次搜索都拉取全量A股列表
            cache_ttl = 3600
            if self._a_stock_name_cache is not None and (time_mod.time() - self._a_stock_name_cache_time) < cache_ttl:
                df = self._a_stock_name_cache
            else:
                df = self._ak.stock_info_a_code_name()
                if df is not None and not df.empty:
                    self._a_stock_name_cache = df
                    self._a_stock_name_cache_time = time_mod.time()
            if df is None or df.empty:
                return self._mock_search(keyword, market)

            results = df[
                df["name"].str.contains(keyword, na=False) |
                df["code"].str.contains(keyword, na=False)
            ]
            stocks = []
            for _, row in results.head(20).iterrows():
                stocks.append({
                    "code": row["code"],
                    "name": row["name"],
                    "market": "A",
                })
            return stocks
        except Exception as e:
            logger.warning(f"搜索股票失败: {e}")
            return self._mock_search(keyword, market)

    # ==================== 行业板块 ====================

    def get_industry_list(self, market: str = "A") -> pd.DataFrame:
        """获取行业板块列表"""
        if self._ak is None:
            return pd.DataFrame()

        try:
            self._track_cost("stock_board_industry_name_em")
            df = self._ak.stock_board_industry_name_em()
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.warning(f"获取行业板块失败: {e}")

            # 降级尝试
            try:
                self._track_cost("stock_board_industry_cons_em")
                df = self._ak.stock_board_industry_cons_em(symbol="BK0477")
                return df if df is not None else pd.DataFrame()
            except Exception:
                pass

            return pd.DataFrame()

    # ==================== 资金流向 ====================

    def get_fund_flow(self, symbol: str, market: str = "A") -> Dict[str, Any]:
        """获取个股资金流向"""
        if self._ak is None:
            return self._mock_fund_flow()

        try:
            self._track_cost("stock_individual_fund_flow")
            df = self._ak.stock_individual_fund_flow(symbol=symbol)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    "date": str(latest.get("日期", "")),
                    "main_net_inflow": float(latest.get("主力净流入", 0)),
                    "super_large_net": float(latest.get("超大单净流入", 0)),
                    "large_net": float(latest.get("大单净流入", 0)),
                    "medium_net": float(latest.get("中单净流入", 0)),
                    "small_net": float(latest.get("小单净流入", 0)),
                }
        except Exception as e:
            logger.warning(f"获取资金流向失败: {e}")

        return self._mock_fund_flow()

    def get_sector_fund_flow_rank(self, market: str = "A") -> pd.DataFrame:
        """获取板块资金流向排名"""
        if self._ak is None:
            return pd.DataFrame()

        try:
            self._track_cost("stock_sector_fund_flow_rank")
            df = self._ak.stock_sector_fund_flow_rank(indicator="今日")
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.warning(f"获取板块资金流向失败: {e}")

            # 降级尝试
            try:
                self._track_cost("stock_individual_fund_flow_rank")
                return self._ak.stock_individual_fund_flow_rank()
            except Exception:
                pass

            return pd.DataFrame()

    def get_individual_fund_flow_rank(self, market: str = "A") -> pd.DataFrame:
        """获取个股资金流向排名"""
        if self._ak is None:
            return pd.DataFrame()

        try:
            self._track_cost("stock_individual_fund_flow_rank")
            df = self._ak.stock_individual_fund_flow_rank()
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            logger.warning(f"获取个股资金流向排名失败: {e}")

            try:
                self._track_cost("stock_sector_fund_flow_rank")
                return self._ak.stock_sector_fund_flow_rank(indicator="今日")
            except Exception:
                pass

            return pd.DataFrame()

    # ==================== 市场数据 ====================

    def get_cftc_report(self) -> Dict[str, Any]:
        """获取CFTC持仓报告"""
        if self._ak is None:
            return self._mock_cftc()

        try:
            df = self._ak.futures_cftc_merchant_holding_analysis()
            if df is not None and not df.empty:
                items = []
                for _, row in df.tail(20).iterrows():
                    items.append({
                        "commodity": str(row.get("品种", "")),
                        "date": str(row.get("日期", "")),
                        "long_positions": int(row.get("多头持仓", 0)),
                        "short_positions": int(row.get("空头持仓", 0)),
                        "net_positions": int(row.get("净持仓", 0)),
                        "change_weekly": int(row.get("周变化", 0)),
                    })
                return {
                    "report_date": str(df.iloc[-1].get("日期", "")),
                    "items": items,
                    "updated_at": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.warning(f"获取CFTC数据失败: {e}")

        return self._mock_cftc()

    def get_cboe_put_call(self, days: int = 30) -> Dict[str, Any]:
        """获取CBOE Put/Call比率"""
        if self._ak is None:
            return self._mock_put_call(days)

        try:
            df = self._ak.index_option_cboe_put_call_ratio()
            if df is not None and not df.empty:
                data = []
                for _, row in df.tail(days).iterrows():
                    data.append({
                        "date": str(row.get("日期", "")),
                        "equity_put_call_ratio": float(row.get("equity_put_call_ratio", 0)),
                        "index_put_call_ratio": float(row.get("index_put_call_ratio", 0)),
                        "total_put_call_ratio": float(row.get("total_put_call_ratio", 0)),
                    })
                return {"data": data, "updated_at": datetime.now().isoformat()}
        except Exception as e:
            logger.warning(f"获取CBOE数据失败: {e}")

        return self._mock_put_call(days)

    # ==================== 健康检查 ====================

    def health_check(self) -> Dict[str, Any]:
        """检查数据源健康状态"""
        status = {
            "name": self.name,
            "status": "ok",
            "gateway": self._gateway,
            "total_cost": self._total_cost,
            "call_count": self._call_count,
            "akshare_available": self._ak is not None,
            "timestamp": datetime.now().isoformat(),
        }

        if self._ak is not None:
            try:
                # 快速测试
                self._ak.__version__
                status["akshare_version"] = self._ak.__version__
            except Exception:
                status["akshare_version"] = "unknown"
        else:
            status["status"] = "degraded"
            status["note"] = "AKShare 未安装，使用模拟数据"

        return status

    # ==================== 模拟数据（AKShare 不可用时的降级方案） ====================

    def _mock_spot_quote(self) -> pd.DataFrame:
        """生成模拟行情快照"""
        stocks = [
            ("600519", "贵州茅台", 1850.00, 15.50, 0.85),
            ("000858", "五粮液", 152.30, -2.10, -1.36),
            ("601318", "中国平安", 48.60, 0.80, 1.67),
            ("000333", "美的集团", 62.50, 1.20, 1.96),
            ("600036", "招商银行", 38.20, -0.50, -1.29),
            ("300750", "宁德时代", 210.00, 5.00, 2.44),
            ("002594", "比亚迪", 268.00, 8.00, 3.08),
            ("601857", "中国石油", 8.50, 0.10, 1.19),
            ("600276", "恒瑞医药", 48.90, -0.80, -1.61),
            ("000001", "平安银行", 11.20, 0.15, 1.36),
        ]
        data = []
        for code, name, price, change, change_pct in stocks:
            data.append({
                "代码": code, "名称": name,
                "最新价": price, "涨跌额": change, "涨跌幅": change_pct,
                "成交量": int(np.random.randint(5000000, 50000000)),
                "成交额": price * np.random.randint(5000000, 50000000),
                "最高": price * 1.02, "最低": price * 0.98,
                "今开": price * 0.995, "昨收": price - change,
            })
        return pd.DataFrame(data)

    def _mock_quote(self, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol, "name": symbol, "price": 100.0,
            "change": 1.5, "change_pct": 1.52,
            "volume": 10000000, "amount": 1000000000,
            "high": 101.0, "low": 99.0, "open": 99.5, "pre_close": 98.5,
        }

    def _mock_kline(self, count: int = 250) -> pd.DataFrame:
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=count, freq="B")
        returns = np.random.normal(0.0005, 0.015, count)
        close = 100 * np.exp(np.cumsum(returns))
        data = []
        for i, d in enumerate(dates):
            c = float(close[i])
            o = c * np.random.uniform(0.98, 1.02)
            data.append({
                "date": d, "open": o, "close": c,
                "high": max(o, c) * np.random.uniform(1.0, 1.03),
                "low": min(o, c) * np.random.uniform(0.97, 1.0),
                "volume": int(np.random.randint(1000000, 10000000)),
            })
        return pd.DataFrame(data)

    def _mock_fundamental(self) -> Dict[str, Any]:
        return {
            "pe_ratio": 25.5, "pb_ratio": 3.2,
            "market_cap": 50000000000, "roe": 18.5,
            "revenue": 10000000000, "net_profit": 2000000000,
            "total_shares": 500000000,
        }

    def _mock_search(self, keyword: str) -> List[Dict[str, Any]]:
        return [
            {"code": "600519", "name": "贵州茅台", "market": "A"},
            {"code": "000858", "name": "五粮液", "market": "A"},
            {"code": "AAPL", "name": "Apple Inc.", "market": "US"},
        ]

    def _mock_fund_flow(self) -> Dict[str, Any]:
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "main_net_inflow": 50000000,
            "super_large_net": 30000000,
            "large_net": 20000000,
            "medium_net": -15000000,
            "small_net": -35000000,
        }

    def _mock_cftc(self) -> Dict[str, Any]:
        import random
        random.seed(42)
        commodities = [
            "黄金", "白银", "铜", "原油", "天然气",
            "大豆", "玉米", "小麦", "棉花", "糖",
            "标普500", "纳斯达克", "10年期美债", "欧元", "日元",
        ]
        items = []
        for c in commodities:
            lp = random.randint(50000, 500000)
            sp = random.randint(30000, 400000)
            items.append({
                "commodity": c, "date": datetime.now().strftime("%Y-%m-%d"),
                "long_positions": lp, "short_positions": sp,
                "net_positions": lp - sp,
                "change_weekly": random.randint(-50000, 50000),
            })
        return {
            "report_date": datetime.now().strftime("%Y-%m-%d"),
            "items": items,
            "updated_at": datetime.now().isoformat(),
        }

    def _mock_put_call(self, days: int) -> Dict[str, Any]:
        import random
        random.seed(42)
        data = []
        base = 0.85
        for i in range(days):
            d = datetime.now() - pd.Timedelta(days=days - 1 - i)
            total = round(base + random.uniform(-0.15, 0.15), 3)
            data.append({
                "date": d.strftime("%Y-%m-%d"),
                "equity_put_call_ratio": round(total * random.uniform(0.6, 0.8), 3),
                "index_put_call_ratio": round(total * random.uniform(1.0, 1.4), 3),
                "total_put_call_ratio": total,
            })
        return {"data": data, "updated_at": datetime.now().isoformat()}