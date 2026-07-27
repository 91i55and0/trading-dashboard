# -*- coding: utf-8 -*-
"""
最终归档版本：原版策略（固定止盈15%，无移动止损/加仓/分批止盈）
阶段一+二：多因子选股 + 组合回测（最多持仓5只）
- 包含缓存机制
- 导出CSV
- 使用备用股票列表（16只）
"""

import akshare_proxy_patch
akshare_proxy_patch.install_patch(
    auth_ip="101.201.173.125",
    auth_token="20260718K92YUFOB",
    retry=30,
    fast=True,
    hook_domains=[
        "push2his.eastmoney.com",   # 只对历史数据接口走代理，其他直连
    ]
)

import backtrader as bt
import akshare as ak
import pandas as pd
import datetime
import time
import warnings
import numpy as np
import os
import pickle

warnings.filterwarnings('ignore')


class MultiStockStrategy(bt.Strategy):
    """
    多标的、动态调仓、最多持仓5只、多因子打分
    固定止盈15%，固定止损8%，无移动止损，无加仓，无分批止盈
    """
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
        ('take_profit', 0.15),           # 固定止盈15%（原版）
        ('stake_pct', 0.95),
    )

    def __init__(self):
        self.inds = {}
        self.cross_days = {}
        self.break_counts = {}
        self.entry_prices = {}
        self.active_rules = {}
        
        # 记录每日持仓和交易明细（用于CSV导出）
        self.daily_portfolio = []
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
        
        self.log('组合策略初始化完成（最多持仓5只）')

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
                self.log(f'【买入成交】{data._name} @ {order.executed.price:.2f}, 数量: {order.executed.size}')
                self.entry_prices[data] = order.executed.price
                
                # 记录买入交易
                self.trade_log.append({
                    'date': current_date,
                    'code': data._name,
                    'action': 'BUY',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.price * order.executed.size,
                    'pnl': None,
                    'pnl_pct': None,
                    'rule': self.active_rules.get(data, 0),
                })
            else:
                # 卖出成交
                entry = self.entry_prices.get(data)
                pnl = None
                pnl_pct = None
                
                if entry is not None and entry > 0:
                    pnl = (order.executed.price - entry) * order.executed.size
                    pnl_pct = (order.executed.price / entry - 1) * 100
                    self.log(f'【卖出成交】{data._name} @ {order.executed.price:.2f}, 数量: {order.executed.size}, 盈亏: {pnl:.2f} ({pnl_pct:.2f}%)')
                else:
                    self.log(f'【卖出成交】{data._name} @ {order.executed.price:.2f}, 数量: {order.executed.size} (买入价丢失，盈亏不计)')
                
                # 记录卖出交易
                self.trade_log.append({
                    'date': current_date,
                    'code': data._name,
                    'action': 'SELL',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.price * order.executed.size,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'rule': self.active_rules.get(data, 0),
                })
                
                # 重置状态
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
        
        # 记录每日总资产
        self.daily_portfolio.append({
            'date': self.datas[0].datetime.date(0),
            'total_value': self.broker.getvalue(),
            'cash': self.broker.getcash(),
        })
        
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
                # ---- 固定止损 ----
                if close < entry_price * (1 - self.p.stop_loss):
                    sell_candidates.append((data, '止损卖出'))
                    continue
                # ---- 固定止盈 ----
                if close > entry_price * (1 + self.p.take_profit):
                    sell_candidates.append((data, '止盈卖出'))
                    continue
            
            # ---- 规则卖出 ----
            if rule == 1:
                if close < sma20:
                    self.break_counts[data] = self.break_counts.get(data, 0) + 1
                    if self.break_counts[data] >= self.p.observe_days:
                        sell_candidates.append((data, f'规则一卖出（连续{self.p.observe_days}日跌破MA20）'))
                        continue
                else:
                    self.break_counts[data] = 0
            elif rule == 2:
                if close >= sma20:
                    sell_candidates.append((data, '规则二卖出（收盘触及MA20）'))
                    continue
            elif rule == 3:
                if close >= sma60:
                    sell_candidates.append((data, '规则三卖出（收盘触及MA60）'))
                    continue
        
        for data, reason in sell_candidates:
            pos = self.getposition(data)
            if pos.size > 0:
                self.log(f'【卖出】{data._name} - {reason} @ {data.close[0]:.2f}')
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
            
            macd_ok = True
            if self.p.use_macd_filter:
                days = self.cross_days.get(data, 999)
                macd_ok = (days <= self.p.macd_max_days)
            if not macd_ok:
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
                    buy_candidates.append((data, rule, target_ma, '规则一'))
            elif close < sma20 and close >= sma60 and close >= sma200:
                rule = 2
                target_ma = sma60
                confirm = True
                for i in range(1, self.p.confirm_days + 1):
                    if data.close[-i] < sma60:
                        confirm = False
                        break
                if confirm:
                    buy_candidates.append((data, rule, target_ma, '规则二'))
            elif close < sma60 and close >= sma200:
                rule = 3
                target_ma = sma200
                confirm = True
                for i in range(1, self.p.confirm_days + 1):
                    if data.close[-i] < sma200:
                        confirm = False
                        break
                if confirm:
                    buy_candidates.append((data, rule, target_ma, '规则三'))
        
        if buy_candidates:
            scored = []
            for data, rule, target_ma, rule_name in buy_candidates:
                score = self.get_score(data, rule, target_ma)
                scored.append((data, rule, target_ma, rule_name, score))
            
            scored.sort(key=lambda x: x[4], reverse=True)
            
            current_positions = sum(1 for d in self.datas if self.getposition(d).size > 0)
            available_slots = self.p.max_positions - current_positions
            
            if available_slots > 0:
                selected = scored[:available_slots]
                self.log(f'今日触发信号 {len(scored)} 个，选中 {len(selected)} 个买入')
                
                cash = self.broker.getcash()
                target_cash_per_stock = cash * self.p.stake_pct / len(selected) if selected else 0
                
                for data, rule, target_ma, rule_name, score in selected:
                    limit_price = target_ma * (1 + self.p.limit_premium)
                    size = int(target_cash_per_stock / limit_price)
                    if size > 0 and cash > limit_price * size:
                        self.log(f'【买入挂单】{data._name} - {rule_name} 得分:{score:.3f} 限价:{limit_price:.2f} 数量:{size}')
                        self.buy(data=data, size=size,
                                 exectype=bt.Order.Limit,
                                 price=limit_price,
                                 valid=datetime.timedelta(days=1))
                        self.active_rules[data] = rule
                        self.break_counts[data] = 0


# ==========================================
# 数据获取函数（加入缓存机制）
# ==========================================
def fetch_stock_data(code, start_date='2020-01-01', end_date='2024-12-31'):
    cache_dir = 'stock_cache'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    cache_file = f'{cache_dir}/{code}_{start_date}_{end_date}.pkl'
    
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            df = pickle.load(f)
        print(f"✅ {code} 从缓存加载 ({len(df)} 行)")
        return df
    
    try:
        start = start_date.replace('-', '')
        end = end_date.replace('-', '')
        df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=start, end_date=end, adjust='qfq')
        if df.empty:
            return None
        
        df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        if len(df) > 60:
            df = df.iloc[60:]
        if len(df) < 200:
            return None
        
        with open(cache_file, 'wb') as f:
            pickle.dump(df, f)
        print(f"✅ {code} 从网络获取并缓存 ({len(df)} 行)")
        return df
    except Exception as e:
        print(f"❌ {code} 获取失败: {e}")
        return None


# ==========================================
# 主程序
# ==========================================
if __name__ == '__main__':
    print("="*70)
    print("🚀 阶段一+二：多因子选股 + 组合回测（最多5只）")
    print("="*70)
    
    # ==========================================
    # 股票池：可以使用备用列表，也可以改为沪深300全量
    # 建议：网络稳定时用 get_hs300_stocks()，否则用备用列表
    # ==========================================
    # 备用列表（16只，快速测试）
    stock_list = ['600519', '000858', '600036', '000333', '601318', '000651', '600276', '002415',
                  '601166', '600900', '601398', '600030', '000001', '601288', '601328', '600000']
    print(f"使用备用股票池: {len(stock_list)} 只")
    
    # 如果要使用沪深300全量，取消下面注释，并注释掉上面备用列表
    # stock_list = get_hs300_stocks()
    
    start_date = '2020-01-01'
    end_date = '2024-12-31'
    
    cerebro = bt.Cerebro()
    
    print(f"\n开始加载 {len(stock_list)} 只股票数据...")
    success_count = 0
    for i, code in enumerate(stock_list):
        df = fetch_stock_data(code, start_date, end_date)
        if df is not None and len(df) > 200:
            data = bt.feeds.PandasData(dataname=df, name=code)
            cerebro.adddata(data)
            success_count += 1
            if (i + 1) % 20 == 0:
                print(f"  已加载 {success_count} 只...")
            if (i + 1) % 10 == 0:
                time.sleep(0.5)
    
    print(f"✅ 成功加载 {success_count} 只股票数据")
    
    if success_count < 10:
        print("❌ 数据太少，无法进行有意义的回测")
        exit()
    
    cerebro.addstrategy(MultiStockStrategy)
    cerebro.broker.setcash(1000000)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.broker.set_slippage_perc(perc=0.001)
    
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    print("\n" + "="*70)
    print("开始回测...")
    print("="*70)
    
    start_value = cerebro.broker.getvalue()
    results = cerebro.run()
    strat = results[0]
    end_value = cerebro.broker.getvalue()
    
    # ====== 导出CSV ======
    daily_df = pd.DataFrame(strat.daily_portfolio)
    if not daily_df.empty:
        daily_df.to_csv('daily_portfolio.csv', index=False)
        print("✅ 每日持仓数据已保存: daily_portfolio.csv")
    
    trade_df = pd.DataFrame(strat.trade_log)
    if not trade_df.empty:
        trade_df.to_csv('trade_log.csv', index=False)
        print("✅ 交易明细已保存: trade_log.csv")
    
    # ====== 汇总结果 ======
    total_return = (end_value - start_value) / start_value * 100
    sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    if sharpe is None or not isinstance(sharpe, (int, float)):
        sharpe = 0
    
    dd = strat.analyzers.drawdown.get_analysis()
    max_drawdown = dd.get('max', {}).get('drawdown', 0)
    
    trades = strat.analyzers.trades.get_analysis()
    total_trades = trades.get('total', {}).get('total', 0)
    won_trades = trades.get('won', {}).get('total', 0)
    win_rate = won_trades / total_trades if total_trades > 0 else 0
    
    ret = strat.analyzers.returns.get_analysis()
    annual_return = ret.get('rnorm100', 0) * 100
    
    summary_data = {
        '初始资金': start_value,
        '最终资金': end_value,
        '总收益率(%)': total_return,
        '年化收益率(%)': annual_return,
        '最大回撤(%)': max_drawdown,
        '夏普比率': sharpe,
        '总交易次数': total_trades,
        '盈利次数': won_trades,
        '胜率(%)': win_rate * 100,
        '股票池数量': len(stock_list),
        '实际加载数量': success_count,
        '回测开始': start_date,
        '回测结束': end_date,
    }
    summary_df = pd.DataFrame([summary_data])
    summary_df.to_csv('summary.csv', index=False)
    print("✅ 汇总指标已保存: summary.csv")
    
    print("\n" + "="*70)
    print("📊 回测结果汇总")
    print("="*70)
    print(f"初始资金: {start_value:,.2f}")
    print(f"最终资金: {end_value:,.2f}")
    print(f"总收益率: {total_return:.2f}%")
    print(f"年化收益率: {annual_return:.2f}%")
    print(f"最大回撤: {max_drawdown:.2f}%")
    print(f"夏普比率: {sharpe:.4f}")
    print(f"总交易次数: {total_trades}")
    print(f"盈利次数: {won_trades}")
    print(f"胜率: {win_rate:.2%}")
    print("="*70)
    print("\n✅ CSV文件已导出:")
    print("   - summary.csv        (汇总指标)")
    print("   - daily_portfolio.csv (每日持仓)")
    print("   - trade_log.csv      (交易明细)")
    print("="*70)
    
    # cerebro.plot(style='candle', numfigs=1, volume=False)   # 禁用绘图