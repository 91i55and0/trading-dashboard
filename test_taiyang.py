"""测试太阳纸业(002078)数据可用性"""
import sys
sys.path.insert(0, "backend")

from data_providers import get_provider

provider = get_provider()
symbol = "002078"

# 获取财务数据
data = provider.get_financial_data(symbol, "A")
print("=" * 60)
print("1. 财务数据概览")
print(f"Source: {data.get('source', 'unknown')}")
print(f"Is mock: {data.get('_mock', False)}")

basic = data.get("basic", {})
print(f"\nBasic keys: {list(basic.keys())}")
print(f"PE: {basic.get('pe')}, PB: {basic.get('pb')}")
print(f"Market cap: {basic.get('market_cap')}")
print(f"Industry: {basic.get('industry')}")
print(f"ROE: {basic.get('roe')}")
print(f"Net profit: {basic.get('net_profit')}")
print(f"Revenue: {basic.get('revenue')}")
print(f"EPS: {basic.get('eps')}")
print(f"Debt ratio: {basic.get('debt_ratio')}")

growth = data.get("growth", {})
print(f"\nGrowth keys: {list(growth.keys())}")
print(f"Revenue growth: {growth.get('revenue_growth_yoy', [])}")
print(f"Profit growth: {growth.get('profit_growth_yoy', [])}")

profitability = data.get("profitability", {})
print(f"\nProfitability keys: {list(profitability.keys())}")
print(f"Gross margin: {profitability.get('gross_margin', [])}")
print(f"Net margin: {profitability.get('net_margin', [])}")

peers = data.get("peers", [])
print(f"\nPeers: {len(peers)}")
for p in peers[:5]:
    print(f"  {p.get('code')} {p.get('name')}: PE={p.get('pe')}, PB={p.get('pb')}, ROE={p.get('roe')}")

# 检查新增数据
print(f"\n2. 新增数据维度")
print(f"Analyst: {bool(data.get('analyst'))}")
print(f"Institutional: {bool(data.get('institutional'))}")
print(f"Northbound: {bool(data.get('northbound'))}")
print(f"Revenue segment: {bool(data.get('revenue_segment'))}")
print(f"Operating efficiency: {bool(data.get('operating_efficiency'))}")
print(f"Shareholder: {bool(data.get('shareholder'))}")
print(f"Per capita: {bool(data.get('per_capita'))}")
print(f"Growth quality: {bool(data.get('growth_quality'))}")
print(f"Financial anomaly: {bool(data.get('financial_anomaly'))}")
print(f"Earnings forecast: {bool(data.get('earnings_forecast'))}")
print(f"Lockup shares: {bool(data.get('lockup_shares'))}")

# 获取行情
print(f"\n3. 行情数据")
quote = provider.get_stock_quote(symbol, "A")
print(f"Price: {quote.get('price')}")
print(f"Name: {quote.get('name')}")
print(f"Change: {quote.get('change_pct')}%")

print("\nDone!")