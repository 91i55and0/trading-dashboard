"""
双均线交叉策略 (示例策略)
- 当短期均线上穿长期均线时买入
- 当短期均线下穿长期均线时卖出
"""
import pandas as pd
import numpy as np


def generate_signals(df: pd.DataFrame, params: dict = None) -> pd.DataFrame:
    """
    生成交易信号

    Args:
        df: 包含 OHLCV 数据的 DataFrame
            - date, open, high, low, close, volume
        params: 策略参数
            - ma_short: 短期均线周期 (默认 5)
            - ma_long: 长期均线周期 (默认 20)

    Returns:
        添加了 signal 列的 DataFrame
        signal: 1=买入, -1=卖出, 0=持有
    """
    if params is None:
        params = {}

    ma_short = params.get("ma_short", 5)
    ma_long = params.get("ma_long", 20)

    df = df.copy()

    # 计算均线
    df["ma_short"] = df["close"].rolling(window=ma_short).mean()
    df["ma_long"] = df["close"].rolling(window=ma_long).mean()

    # 生成信号：金叉买入，死叉卖出
    df["signal"] = 0
    df["prev_ma_short"] = df["ma_short"].shift(1)
    df["prev_ma_long"] = df["ma_long"].shift(1)

    # 金叉：短期均线从下方上穿长期均线
    golden_cross = (df["prev_ma_short"] <= df["prev_ma_long"]) & (df["ma_short"] > df["ma_long"])
    df.loc[golden_cross, "signal"] = 1

    # 死叉：短期均线从上方下穿长期均线
    death_cross = (df["prev_ma_short"] >= df["prev_ma_long"]) & (df["ma_short"] < df["ma_long"])
    df.loc[death_cross, "signal"] = -1

    # 清理辅助列
    df = df.drop(columns=["prev_ma_short", "prev_ma_long"], errors="ignore")

    return df