"""
MACD 金叉死叉策略
- 金叉（DIF 上穿 DEA）买入
- 死叉（DIF 下穿 DEA）卖出
- 止损：买入价下方 5%
"""
import backtrader as bt


class MACDCrossStrategy(bt.Strategy):
    params = (
        ('fast', 12),
        ('slow', 26),
        ('signal', 9),
        ('stop_loss_pct', 0.05),
    )

    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.p.fast,
            period_me2=self.p.slow,
            period_signal=self.p.signal,
        )
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
        self.order = None
        self.entry_price = None

    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print(f'{dt} {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            if order.isbuy():
                self.entry_price = order.executed.price
                self.log(f'买入成交 @ {order.executed.price:.2f}')
            else:
                self.log(f'卖出成交 @ {order.executed.price:.2f}')
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('订单失败/取消')
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            if self.crossover > 0:
                self.order = self.buy()
        else:
            # 止损
            if self.entry_price and self.data.close[0] < self.entry_price * (1 - self.p.stop_loss_pct):
                self.order = self.sell()
                self.log(f'止损卖出')
            # 死叉卖出
            elif self.crossover < 0:
                self.order = self.sell()