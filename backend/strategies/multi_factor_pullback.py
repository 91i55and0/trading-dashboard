"""
多因子回踩策略（test_v2 适配版）
- 多标的、动态调仓、最多持仓5只、多因子打分
- 固定止盈15%，固定止损8%
- 规则一：站稳MA20 买入，连续跌破MA20卖出
- 规则二：回踩MA60 买入，触及MA20卖出
- 规则三：回踩MA200 买入，触及MA60卖出
"""
import backtrader as bt
import datetime


class MultiFactorPullbackStrategy(bt.Strategy):
    params = (
        ('ma20', 20),
        ('ma60', 60),
        ('ma200', 200),
        ('confirm_days', 3),
        ('limit_premium', 0.010),
        ('observe_days', 5),
        ('use_macd_filter', True),
        ('macd_max_days', 3),
        ('max_positions', 5),
        ('stop_loss', 0.08),
        ('take_profit', 0.15),
        ('stake_pct', 0.95),
    )

    def __init__(self):
        self.inds = {}
        self.cross_days = {}
        self.break_counts = {}
        self.entry_prices = {}
        self.active_rules = {}
        self.trade_log = []

        for data in self.datas:
            sma20 = bt.indicators.SMA(data.close, period=self.p.ma20)
            sma60 = bt.indicators.SMA(data.close, period=self.p.ma60)
            sma200 = bt.indicators.SMA(data.close, period=self.p.ma200)
            macd = bt.indicators.MACD(data.close)
            macd_cross = bt.indicators.CrossOver(macd.macd, macd.signal)
            rsi = bt.indicators.RSI(data.close, period=14)
            atr = bt.indicators.ATR(data, period=14)
            vol_ma = bt.indicators.SMA(data.volume, period=20)

            self.inds[data] = {
                'sma20': sma20,
                'sma60': sma60,
                'sma200': sma200,
                'macd': macd,
                'macd_cross': macd_cross,
                'rsi': rsi,
                'atr': atr,
                'vol_ma': vol_ma,
            }
            self.cross_days[data] = 999
            self.break_counts[data] = 0
            self.entry_prices[data] = None
            self.active_rules[data] = 0

    def log(self, txt, dt=None):
        if dt is None:
            try:
                dt = self.datas[0].datetime.date(0)
            except:
                dt = datetime.date.today()
        print(f'{dt} {txt}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            data = order.data
            current_date = self.datas[0].datetime.date(0)
            if order.isbuy():
                self.entry_prices[data] = order.executed.price
                self.trade_log.append({
                    'date': str(current_date),
                    'action': 'BUY',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.price * order.executed.size,
                    'pnl': None,
                    'pnl_pct': None,
                    'rule': self.active_rules.get(data, 0),
                })
            else:
                entry = self.entry_prices.get(data)
                pnl = None
                pnl_pct = None
                if entry is not None and entry > 0:
                    pnl = (order.executed.price - entry) * order.executed.size
                    pnl_pct = (order.executed.price / entry - 1) * 100
                self.trade_log.append({
                    'date': str(current_date),
                    'action': 'SELL',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.price * order.executed.size,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'rule': self.active_rules.get(data, 0),
                })
                self.entry_prices[data] = None
                self.active_rules[data] = 0
                self.break_counts[data] = 0

    def get_score(self, data, rule, target_ma):
        ind = self.inds[data]
        close = data.close[0]
        deviation = (close - target_ma) / target_ma
        if 0 <= deviation <= 0.05:
            bias_score = 1 - deviation / 0.05
        else:
            bias_score = 0

        days = self.cross_days.get(data, 999)
        if days == 0:
            macd_score = 1.0
        elif days == 1:
            macd_score = 0.5
        else:
            macd_score = 0

        vol = data.volume[0]
        vol_ma = ind['vol_ma'][0]
        if vol_ma > 0:
            vol_ratio = vol / vol_ma
            vol_score = min(1.0, vol_ratio / 1.5)
        else:
            vol_score = 0

        rsi = ind['rsi'][0]
        rsi_score = 1 - abs(rsi - 50) / 50
        rsi_score = max(0, min(1, rsi_score))

        atr = ind['atr'][0]
        if close > 0 and atr > 0:
            atr_ratio = atr / close
            if atr_ratio <= 0.05:
                atr_score = 1 - atr_ratio / 0.05
            else:
                atr_score = 0
        else:
            atr_score = 0

        total_score = (
            bias_score * 0.35 +
            macd_score * 0.25 +
            vol_score * 0.20 +
            rsi_score * 0.10 +
            atr_score * 0.10
        )
        return total_score

    def next(self):
        if len(self.datas[0]) < self.p.ma200:
            return

        for data in self.datas:
            ind = self.inds[data]
            cross = ind['macd_cross'][0]
            if cross == 1:
                self.cross_days[data] = 0
            else:
                self.cross_days[data] = self.cross_days.get(data, 999) + 1

        # ---- 卖出逻辑 ----
        sell_candidates = []
        for data in self.datas:
            pos = self.getposition(data)
            if pos.size == 0:
                continue
            close = data.close[0]
            ind = self.inds[data]
            sma20 = ind['sma20'][0]
            sma60 = ind['sma60'][0]
            entry_price = self.entry_prices.get(data)
            rule = self.active_rules.get(data, 0)

            if entry_price is not None:
                if close < entry_price * (1 - self.p.stop_loss):
                    sell_candidates.append((data, '止损卖出'))
                    continue
                if close > entry_price * (1 + self.p.take_profit):
                    sell_candidates.append((data, '止盈卖出'))
                    continue

            if rule == 1:
                if close < sma20:
                    self.break_counts[data] = self.break_counts.get(data, 0) + 1
                    if self.break_counts[data] >= self.p.observe_days:
                        sell_candidates.append((data, '规则一卖出'))
                        continue
                else:
                    self.break_counts[data] = 0
            elif rule == 2:
                if close >= sma20:
                    sell_candidates.append((data, '规则二卖出'))
                    continue
            elif rule == 3:
                if close >= sma60:
                    sell_candidates.append((data, '规则三卖出'))
                    continue

        for data, reason in sell_candidates:
            pos = self.getposition(data)
            if pos.size > 0:
                self.close(data=data)
                self.entry_prices[data] = None
                self.active_rules[data] = 0
                self.break_counts[data] = 0

        # ---- 买入逻辑 ----
        buy_candidates = []
        for data in self.datas:
            pos = self.getposition(data)
            if pos.size > 0:
                continue
            close = data.close[0]
            ind = self.inds[data]
            sma20 = ind['sma20'][0]
            sma60 = ind['sma60'][0]
            sma200 = ind['sma200'][0]

            if self.p.use_macd_filter:
                days = self.cross_days.get(data, 999)
                if days > self.p.macd_max_days:
                    continue

            rule = 0
            target_ma = 0

            if close >= sma20:
                rule = 1
                target_ma = sma20
                confirm = True
                for i in range(1, self.p.confirm_days + 1):
                    if data.close[-i] < sma20:
                        confirm = False
                        break
                if confirm:
                    buy_candidates.append((data, rule, target_ma))
            elif close < sma20 and close >= sma60 and close >= sma200:
                rule = 2
                target_ma = sma60
                confirm = True
                for i in range(1, self.p.confirm_days + 1):
                    if data.close[-i] < sma60:
                        confirm = False
                        break
                if confirm:
                    buy_candidates.append((data, rule, target_ma))
            elif close < sma60 and close >= sma200:
                rule = 3
                target_ma = sma200
                confirm = True
                for i in range(1, self.p.confirm_days + 1):
                    if data.close[-i] < sma200:
                        confirm = False
                        break
                if confirm:
                    buy_candidates.append((data, rule, target_ma))

        if buy_candidates:
            scored = []
            for data, rule, target_ma in buy_candidates:
                score = self.get_score(data, rule, target_ma)
                scored.append((data, rule, target_ma, score))
            scored.sort(key=lambda x: x[3], reverse=True)

            current_positions = sum(1 for d in self.datas if self.getposition(d).size > 0)
            available_slots = self.p.max_positions - current_positions

            if available_slots > 0:
                selected = scored[:available_slots]
                cash = self.broker.getcash()
                target_cash_per_stock = cash * self.p.stake_pct / len(selected) if selected else 0

                for data, rule, target_ma, score in selected:
                    limit_price = target_ma * (1 + self.p.limit_premium)
                    size = int(target_cash_per_stock / limit_price)
                    if size > 0 and cash > limit_price * size:
                        self.buy(data=data, size=size,
                                 exectype=bt.Order.Limit,
                                 price=limit_price,
                                 valid=datetime.timedelta(days=1))
                        self.active_rules[data] = rule
                        self.break_counts[data] = 0