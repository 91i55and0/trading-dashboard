"""
量化回测服务

支持两种模式：
1. 简单信号模式：策略文件提供 generate_signals(df, params) 函数
2. Backtrader 模式：策略文件包含完整的 Backtrader Cerebro 流程
3. 直接代码模式：直接传入代码字符串运行
"""
import os
import sys
import json
import importlib.util
import tempfile
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# 策略目录
STRATEGIES_DIR = os.path.join(os.path.dirname(__file__), "..", "strategies")


def _load_strategy(strategy_name: str):
    """动态加载策略模块"""
    strategy_path = os.path.join(STRATEGIES_DIR, f"{strategy_name}.py")
    if not os.path.exists(strategy_path):
        raise FileNotFoundError(f"策略文件不存在: {strategy_name}.py")

    spec = importlib.util.spec_from_file_location(strategy_name, strategy_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[strategy_name] = module  # 注册到 sys.modules，避免 KeyError
    spec.loader.exec_module(module)
    return module


def _fetch_market_data(symbol: str, market: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取市场数据（通过统一数据提供者）"""
    try:
        from data_providers import get_provider

        provider = get_provider()
        df = provider.get_kline(
            symbol=symbol,
            market=market,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            count=9999,
            adjust="qfq",
        )

        if df is not None and not df.empty:
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            return df

    except Exception as e:
        logger.error(f"获取市场数据失败: {e}")
        raise

    raise RuntimeError(f"无法获取 {symbol} 的市场数据：所有数据源均失败")


def _generate_mock_data(start_date: str, end_date: str) -> pd.DataFrame:
    """生成模拟数据（用于测试）"""
    dates = pd.date_range(start=start_date, end=end_date, freq="B")
    np.random.seed(42)
    n = len(dates)

    returns = np.random.normal(0.0005, 0.015, n)
    price = 100 * np.exp(np.cumsum(returns))
    high = price * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = price * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_price = low + np.random.random(n) * (high - low)
    volume = np.random.randint(1000000, 10000000, n)

    return pd.DataFrame({
        "date": dates,
        "open": open_price,
        "high": high,
        "low": low,
        "close": price,
        "volume": volume,
    })


def run_backtest_service(
    strategy_name: str,
    symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    commission: float = 0.0003,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    执行回测服务（从已保存的策略文件）
    """
    strategy_module = _load_strategy(strategy_name)
    df = _fetch_market_data(symbol, market, start_date, end_date)

    # 检测是否为 Backtrader 策略
    if _is_backtrader_strategy(strategy_module):
        return _run_backtrader_backtest(
            strategy_module, df, symbol, market,
            start_date, end_date, initial_capital, commission, params,
        )

    # 简单信号模式
    if hasattr(strategy_module, "generate_signals"):
        df = strategy_module.generate_signals(df, params or {})
    else:
        raise ValueError(f"策略 {strategy_name} 缺少 generate_signals 函数或 Backtrader 策略类")

    trades, equity_curve = _simulate_trades(df, initial_capital, commission)
    metrics = _calculate_metrics(equity_curve, trades, initial_capital)

    return {
        "strategy": strategy_name,
        "symbol": symbol,
        "market": market,
        "period": f"{start_date} ~ {end_date}",
        **metrics,
        "equity_curve": equity_curve,
        "trades": [
            {k: (str(v) if isinstance(v, (pd.Timestamp, datetime)) else v)
             for k, v in t.items()}
            for t in trades
        ],
        "run_time": datetime.now().isoformat(),
    }


def run_code_backtest(
    code: str,
    symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    commission: float = 0.0003,
) -> Dict[str, Any]:
    """
    直接传入代码字符串执行回测（支持 Backtrader 策略）
    """
    df = _fetch_market_data(symbol, market, start_date, end_date)

    # 将代码写入临时文件并加载
    strategy_name = f"_temp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    tmp_path = os.path.join(STRATEGIES_DIR, f"{strategy_name}.py")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(code)

        module = _load_strategy(strategy_name)

        if _is_backtrader_strategy(module):
            return _run_backtrader_backtest(
                module, df, symbol, market,
                start_date, end_date, initial_capital, commission,
            )

        if hasattr(module, "generate_signals"):
            df = module.generate_signals(df, {})
            trades, equity_curve = _simulate_trades(df, initial_capital, commission)
            metrics = _calculate_metrics(equity_curve, trades, initial_capital)
            return {
                "strategy": "代码运行",
                "symbol": symbol,
                "market": market,
                "period": f"{start_date} ~ {end_date}",
                **metrics,
                "equity_curve": equity_curve,
                "trades": [
                    {k: (str(v) if isinstance(v, (pd.Timestamp, datetime)) else v)
                     for k, v in t.items()}
                    for t in trades
                ],
                "run_time": datetime.now().isoformat(),
            }

        raise ValueError("代码必须包含 generate_signals 函数或 Backtrader Strategy 类")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _is_backtrader_strategy(module) -> bool:
    """检测是否为 Backtrader 策略"""
    # 检查是否有 import backtrader
    source = ""
    try:
        source = open(module.__file__, encoding="utf-8").read()
    except Exception:
        pass

    if "import backtrader" in source or "from backtrader" in source:
        return True

    # 检查是否有继承 bt.Strategy 的类
    import inspect
    for name, obj in inspect.getmembers(module, inspect.isclass):
        try:
            bases = [b.__name__ for b in obj.__mro__]
            if "Strategy" in bases and "backtrader" in str(obj.__module__).lower():
                return True
        except Exception:
            pass

    return False


def _run_backtrader_backtest(
    module,
    df: pd.DataFrame,
    symbol: str,
    market: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    commission: float = 0.0003,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """运行 Backtrader 策略回测"""
    try:
        import backtrader as bt
    except ImportError:
        raise ImportError("Backtrader 未安装，请运行: pip install backtrader")

    # 查找策略类
    import inspect
    strategy_cls = None
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            try:
                if issubclass(obj, bt.Strategy) and obj != bt.Strategy:
                    strategy_cls = obj
                    break
            except TypeError:
                pass

    if strategy_cls is None:
        raise ValueError("未找到 Backtrader Strategy 子类")

    # 校验数据量：根据策略参数确定最小K线数
    has_ma200 = hasattr(strategy_cls.params, 'ma200')
    min_required = 200 if has_ma200 else 50
    if len(df) < min_required:
        raise ValueError(
            f"数据不足：仅 {len(df)} 根K线，策略需要至少 {min_required} 根K线。"
            f"请将起始日期提前约 {'1 年' if has_ma200 else '3 个月'} 以上。"
        )

    # 准备数据
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

    required_cols = {"open", "high", "low", "close", "volume"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"数据缺少必要列: {required_cols - set(df.columns)}")

    data = bt.feeds.PandasData(dataname=df)

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.adddata(data)

    # 策略参数
    if params:
        cerebro.addstrategy(strategy_cls, **params)
    else:
        cerebro.addstrategy(strategy_cls)

    # 经纪商配置
    cerebro.broker.setcash(initial_capital)
    cerebro.broker.setcommission(commission=commission)

    # 分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

    # 添加观察者
    cerebro.addobserver(bt.observers.BuySell)
    cerebro.addobserver(bt.observers.Value)

    # 运行
    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strat = results[0]
    end_value = cerebro.broker.getvalue()

    # 提取交易记录
    trades = []
    equity_curve = []

    # 从 observers 提取净值曲线
    for obs in strat.getobservers():
        if isinstance(obs, bt.observers.Value):
            for i in range(len(obs)):
                try:
                    dt = data.datetime.datetime(i)
                except Exception:
                    dt = datetime.now()
                val = obs.array[i]
                if val and val != float('inf'):
                    equity_curve.append({
                        "date": str(dt.date()) if hasattr(dt, 'date') else str(dt),
                        "equity": round(float(val), 2),
                        "return_pct": round((float(val) / initial_capital - 1) * 100, 2),
                        "cash": round(float(val), 2),
                        "position_value": 0,
                    })

    # 提取交易记录
    if hasattr(strat, 'trade_log'):
        trades = strat.trade_log
    elif hasattr(strat, 'trades'):
        for t in strat.trades:
            trades.append({
                "date": str(t.get("date", "")),
                "type": "buy" if t.get("action") == "BUY" else "sell",
                "price": t.get("price", 0),
                "shares": t.get("size", 0),
                "amount": t.get("value", 0),
                "profit": t.get("pnl"),
                "profit_pct": t.get("pnl_pct"),
                "reason": t.get("rule", ""),
            })

    # 分析器结果
    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    if sharpe is None:
        sharpe = 0

    dd = strat.analyzers.drawdown.get_analysis()
    max_drawdown = dd.get('max', {}).get('drawdown', 0) if dd.get('max') else 0

    trades_analysis = strat.analyzers.trades.get_analysis()
    total_trades = trades_analysis.get('total', {}).get('total', 0)
    won_trades = trades_analysis.get('won', {}).get('total', 0)
    win_rate = won_trades / total_trades * 100 if total_trades > 0 else 0

    ret = strat.analyzers.returns.get_analysis()
    annual_return = ret.get('rnorm100', 0) * 100

    total_return = (end_value - start_value) / start_value * 100

    # 计算盈亏比
    profit_factor = 0
    avg_profit = 0
    avg_loss = 0
    profit_trades = 0
    loss_trades = 0
    if hasattr(strat, 'trade_log') and strat.trade_log:
        sell_trades = [t for t in strat.trade_log if t.get("action") == "SELL"]
        profits = [t.get("pnl", 0) for t in sell_trades if t.get("pnl") is not None]
        profit_list = [p for p in profits if p > 0]
        loss_list = [p for p in profits if p <= 0]
        profit_trades = len(profit_list)
        loss_trades = len(loss_list)
        avg_profit = np.mean(profit_list) if profit_list else 0
        avg_loss = abs(np.mean(loss_list)) if loss_list else 0
        total_profit = sum(profit_list)
        total_loss = abs(sum(loss_list))
        profit_factor = total_profit / total_loss if total_loss > 0 else 999

    return {
        "strategy": strategy_cls.__name__,
        "symbol": symbol,
        "market": market,
        "period": f"{start_date} ~ {end_date}",
        "total_return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "win_rate": round(win_rate, 2),
        "total_trades": total_trades,
        "profit_trades": profit_trades,
        "loss_trades": loss_trades,
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999,
        "final_value": round(end_value, 2),
        "initial_value": round(start_value, 2),
        "equity_curve": equity_curve,
        "trades": trades,
        "engine": "backtrader",
        "run_time": datetime.now().isoformat(),
    }

    # 添加数据不足警告
    if total_trades == 0:
        bar_count = len(data) if data else 0
        if bar_count < 200:
            result["warning"] = (
                f"数据不足：仅获取到 {bar_count} 根K线，策略需要至少 200 根K线（MA200 指标预热）。"
                f"请将起始日期提前至 {(datetime.now() - pd.Timedelta(days=365)).strftime('%Y-%m-%d')} 或更早。"
            )
        else:
            result["warning"] = (
                f"数据充足（{bar_count} 根K线），但策略未产生交易信号。"
                f"可能原因：市场环境不满足入场条件、策略参数过于严格。"
            )

    return result


def _simulate_trades(
    df: pd.DataFrame,
    initial_capital: float,
    commission: float,
) -> tuple:
    """模拟交易执行"""
    trades = []
    equity = []
    cash = initial_capital
    position = 0
    position_price = 0

    for i, row in df.iterrows():
        signal = row.get("signal", 0)
        price = row["close"]
        date = row["date"]

        if signal == 1 and position == 0:
            trade_amount = cash * 0.95
            shares = int(trade_amount / price / 100) * 100
            if shares > 0:
                cost = shares * price * (1 + commission)
                if cost <= cash:
                    cash -= cost
                    position = shares
                    position_price = price
                    trades.append({
                        "date": str(date),
                        "type": "buy",
                        "price": round(price, 2),
                        "shares": shares,
                        "amount": round(cost, 2),
                        "reason": "买入信号",
                    })

        elif signal == -1 and position > 0:
            revenue = position * price * (1 - commission)
            cash += revenue
            profit = revenue - position * position_price
            trades.append({
                "date": str(date),
                "type": "sell",
                "price": round(price, 2),
                "shares": position,
                "amount": round(revenue, 2),
                "profit": round(profit, 2),
                "profit_pct": round(profit / (position * position_price) * 100, 2),
                "reason": "卖出信号",
            })
            position = 0
            position_price = 0

        market_value = position * price
        total_value = cash + market_value
        equity.append({
            "date": str(date),
            "equity": round(total_value, 2),
            "cash": round(cash, 2),
            "position_value": round(market_value, 2),
            "return_pct": round((total_value / initial_capital - 1) * 100, 2),
        })

    if position > 0:
        last_price = df.iloc[-1]["close"]
        revenue = position * last_price * (1 - commission)
        cash += revenue
        trades.append({
            "date": str(df.iloc[-1]["date"]),
            "type": "sell",
            "price": round(last_price, 2),
            "shares": position,
            "amount": round(revenue, 2),
            "profit": round(revenue - position * position_price, 2),
            "reason": "回测结束平仓",
        })

    return trades, equity


def _calculate_metrics(equity_curve: List[dict], trades: List[dict], initial_capital: float) -> dict:
    """计算回测指标"""
    if not equity_curve:
        return {}

    final_value = equity_curve[-1]["equity"]
    total_return = (final_value / initial_capital - 1) * 100

    days = len(equity_curve)
    if days > 0:
        annual_return = ((final_value / initial_capital) ** (252 / days) - 1) * 100
    else:
        annual_return = 0

    equity_values = [e["equity"] for e in equity_curve]
    peak = equity_values[0]
    max_drawdown = 0
    for v in equity_values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_drawdown:
            max_drawdown = dd

    daily_returns = []
    for i in range(1, len(equity_values)):
        ret = (equity_values[i] - equity_values[i - 1]) / equity_values[i - 1]
        daily_returns.append(ret)
    if daily_returns:
        avg_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)
        sharpe = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
    else:
        sharpe = 0

    sell_trades = [t for t in trades if t["type"] == "sell"]
    if sell_trades:
        profits = [t.get("profit", 0) for t in sell_trades]
        profit_trades = [p for p in profits if p > 0]
        loss_trades = [p for p in profits if p <= 0]
        win_rate = len(profit_trades) / len(sell_trades) * 100 if sell_trades else 0
        avg_profit = np.mean(profit_trades) if profit_trades else 0
        avg_loss = np.mean(loss_trades) if loss_trades else 0
        total_profit = sum(p for p in profits if p > 0)
        total_loss = abs(sum(p for p in profits if p <= 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")
    else:
        win_rate = 0
        avg_profit = 0
        avg_loss = 0
        profit_factor = 0
        profit_trades = []
        loss_trades = []

    return {
        "total_return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
        "win_rate": round(win_rate, 2),
        "total_trades": len(sell_trades),
        "profit_trades": len(profit_trades) if sell_trades else 0,
        "loss_trades": len(loss_trades) if sell_trades else 0,
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999,
        "final_value": round(final_value, 2),
    }


def run_multi_symbol_backtest(
    strategy_name: str,
    symbols: list,
    market: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    commission: float = 0.0003,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    多股票组合回测（支持 MultiStockStrategy 等策略）
    """
    strategy_module = _load_strategy(strategy_name)
    df_list = []

    for symbol in symbols:
        df = _fetch_market_data(symbol, market, start_date, end_date)
        if df is not None and not df.empty:
            df_list.append((symbol, df))

    if not df_list:
        raise ValueError("没有获取到任何股票数据")

    return _run_multi_backtrader_backtest(
        strategy_module, df_list, symbols, market,
        start_date, end_date, initial_capital, commission, params,
    )


def run_multi_code_backtest(
    code: str,
    symbols: list,
    market: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    commission: float = 0.0003,
) -> Dict[str, Any]:
    """直接传入代码字符串执行多股票回测"""
    df_list = []
    for symbol in symbols:
        df = _fetch_market_data(symbol, market, start_date, end_date)
        if df is not None and not df.empty:
            df_list.append((symbol, df))

    if not df_list:
        raise ValueError("没有获取到任何股票数据")

    strategy_name = f"_temp_multi_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    tmp_path = os.path.join(STRATEGIES_DIR, f"{strategy_name}.py")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(code)

        module = _load_strategy(strategy_name)
        return _run_multi_backtrader_backtest(
            module, df_list, symbols, market,
            start_date, end_date, initial_capital, commission,
        )
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _run_multi_backtrader_backtest(
    module,
    df_list: list,
    symbols: list,
    market: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    commission: float = 0.0003,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """运行多股票 Backtrader 策略回测"""
    try:
        import backtrader as bt
    except ImportError:
        raise ImportError("Backtrader 未安装，请运行: pip install backtrader")

    import inspect
    strategy_cls = None
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            try:
                if issubclass(obj, bt.Strategy) and obj != bt.Strategy:
                    strategy_cls = obj
                    break
            except TypeError:
                pass

    if strategy_cls is None:
        raise ValueError("未找到 Backtrader Strategy 子类")

    # 校验数据量：根据策略参数确定最小K线数
    has_ma200 = hasattr(strategy_cls.params, 'ma200')
    min_required = 200 if has_ma200 else 50
    min_bars = min(len(df) for _, df in df_list)
    if min_bars < min_required:
        raise ValueError(
            f"数据不足：最短的数据仅 {min_bars} 根K线，策略需要至少 {min_required} 根K线。"
            f"请将起始日期提前约 {'1 年' if has_ma200 else '3 个月'} 以上。"
        )

    cerebro = bt.Cerebro(stdstats=False)

    # 添加多只股票数据
    for symbol, df in df_list:
        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
        required_cols = {"open", "high", "low", "close", "volume"}
        if not required_cols.issubset(df.columns):
            continue
        data = bt.feeds.PandasData(dataname=df, name=symbol)
        cerebro.adddata(data)

    if not cerebro.datas:
        raise ValueError("没有有效的股票数据可用于回测")

    if params:
        cerebro.addstrategy(strategy_cls, **params)
    else:
        cerebro.addstrategy(strategy_cls)

    cerebro.broker.setcash(initial_capital)
    cerebro.broker.setcommission(commission=commission)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.02)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')

    cerebro.addobserver(bt.observers.Value)

    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strat = results[0]
    end_value = cerebro.broker.getvalue()

    # 提取净值曲线
    equity_curve = []
    for obs in strat.getobservers():
        if isinstance(obs, bt.observers.Value):
            first_data = cerebro.datas[0]
            for i in range(len(obs)):
                if i < len(first_data):
                    try:
                        dt = first_data.datetime.datetime(i)
                    except Exception:
                        dt = datetime.now()
                else:
                    continue
                val = obs.array[i]
                if val and val != float('inf'):
                    equity_curve.append({
                        "date": str(dt.date()) if hasattr(dt, 'date') else str(dt),
                        "equity": round(float(val), 2),
                        "return_pct": round((float(val) / initial_capital - 1) * 100, 2),
                        "cash": round(float(val), 2),
                        "position_value": 0,
                    })

    # 提取交易记录
    trades = []
    if hasattr(strat, 'trade_log'):
        for t in strat.trade_log:
            trades.append({
                "date": str(t.get("date", "")),
                "type": "buy" if t.get("action") == "BUY" else "sell",
                "price": t.get("price", 0),
                "shares": t.get("size", 0),
                "amount": t.get("value", 0),
                "profit": t.get("pnl"),
                "profit_pct": t.get("pnl_pct"),
                "reason": str(t.get("rule", "")),
            })

    # 分析器结果
    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    if sharpe is None:
        sharpe = 0

    dd = strat.analyzers.drawdown.get_analysis()
    max_drawdown = dd.get('max', {}).get('drawdown', 0) if dd.get('max') else 0

    trades_analysis = strat.analyzers.trades.get_analysis()
    total_trades = trades_analysis.get('total', {}).get('total', 0)
    won_trades = trades_analysis.get('won', {}).get('total', 0)
    win_rate = won_trades / total_trades * 100 if total_trades > 0 else 0

    ret = strat.analyzers.returns.get_analysis()
    annual_return = ret.get('rnorm100', 0) * 100
    total_return = (end_value - start_value) / start_value * 100

    profit_factor = 0
    avg_profit = 0
    avg_loss = 0
    profit_trades = 0
    loss_trades = 0
    if hasattr(strat, 'trade_log') and strat.trade_log:
        sell_trades = [t for t in strat.trade_log if t.get("action") == "SELL"]
        profits = [t.get("pnl", 0) for t in sell_trades if t.get("pnl") is not None]
        profit_list = [p for p in profits if p > 0]
        loss_list = [p for p in profits if p <= 0]
        profit_trades = len(profit_list)
        loss_trades = len(loss_list)
        avg_profit = np.mean(profit_list) if profit_list else 0
        avg_loss = abs(np.mean(loss_list)) if loss_list else 0
        total_profit = sum(profit_list)
        total_loss = abs(sum(loss_list))
        profit_factor = total_profit / total_loss if total_loss > 0 else 999

    return {
        "strategy": strategy_cls.__name__,
        "symbol": ", ".join(symbols),
        "market": market,
        "period": f"{start_date} ~ {end_date}",
        "total_return": round(total_return, 2),
        "annual_return": round(annual_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "win_rate": round(win_rate, 2),
        "total_trades": total_trades,
        "profit_trades": profit_trades,
        "loss_trades": loss_trades,
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else 999,
        "final_value": round(end_value, 2),
        "initial_value": round(start_value, 2),
        "equity_curve": equity_curve,
        "trades": trades,
        "engine": "backtrader",
        "multi_symbol": True,
        "run_time": datetime.now().isoformat(),
    }

    # 添加数据不足警告
    if total_trades == 0:
        min_bars = min(len(d) for d in cerebro.datas) if cerebro.datas else 0
        if min_bars < 200:
            result["warning"] = (
                f"数据不足：仅获取到 {min_bars} 根K线，策略需要至少 200 根K线（MA200 指标预热）。"
                f"请将起始日期提前至 {(datetime.now() - pd.Timedelta(days=365)).strftime('%Y-%m-%d')} 或更早。"
            )
        else:
            result["warning"] = (
                f"数据充足（{min_bars} 根K线），但策略未产生交易信号。"
                f"可能原因：市场环境不满足入场条件、策略参数过于严格。"
            )

    return result


def format_ai_prompt(description: str, symbol: str = "", market: str = "A") -> str:
    """
    将自然语言描述格式化为 AI 提示词，方便用户复制到 TRAE 中生成策略代码
    """
    market_name = "A股" if market == "A" else "美股"
    prompt = f"""# 量化策略开发请求

## 策略描述
{description}

## 回测参数
- 市场: {market_name}
- 股票代码: {symbol if symbol else '（用户指定）'}
- 起始日期: 用户指定
- 结束日期: 用户指定

## 技术要求
请使用 Backtrader 框架编写策略，遵循以下规范：

### 必须遵守的规则
1. 策略类继承 `bt.Strategy`，定义 `params` 元组
2. 指标在 `__init__` 中声明（向量化计算），严禁在 `next` 中循环计算
3. 下单前检查 `if self.order: return`
4. 必须实现 `notify_order(self, order)` 回调
5. 使用 `self.log()` 记录交易日志
6. 数据访问：`self.data.close[0]` 当前值，`self.data.close[-1]` 前一根

### 标准代码模板
```python
import backtrader as bt

class MyStrategy(bt.Strategy):
    params = (
        ('param1', 10),
        ('param2', 20),
    )

    def __init__(self):
        # 指标声明（向量化）
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.param1)
        self.order = None
        self.entry_price = None

    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print(f'{{dt}} {{txt}}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.log(f'买入成交 @ {{order.executed.price:.2f}}')
            self.order = None
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单失败/取消')
            self.order = None

    def next(self):
        if self.order:
            return
        # 在此编写交易逻辑
        pass
```

请根据以上规范生成完整的策略代码，只输出策略类代码即可（不需要 Cerebro 主程序部分）。
"""
    return prompt