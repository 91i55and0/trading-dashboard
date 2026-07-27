import requests
import json
import re

# Test 1: Tencent Finance API for stock data
print("=== Test 1: Tencent Finance stock API ===")
try:
    # Tencent stock quote API
    url = "https://qt.gtimg.cn/q=sh600519"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    content = r.text
    # Parse Tencent format: v_sh600519="1~贵州茅台~600519~1297.41~..."
    if "~" in content:
        parts = content.split('"')[1] if '"' in content else content
        fields = parts.split("~")
        print(f"Total fields: {len(fields)}")
        for i, f in enumerate(fields[:50]):
            if f.strip():
                print(f"  [{i}] = {f[:80]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 2: Tencent batch query with PE/PB
print("\n=== Test 2: Tencent batch query ===")
try:
    url = "https://qt.gtimg.cn/q=sh600519,sz000858"
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    for line in r.text.strip().split("\n"):
        if '="' in line:
            parts = line.split('"')[1].split("~")
            name = parts[1] if len(parts) > 1 else ""
            code = parts[2] if len(parts) > 2 else ""
            price = parts[3] if len(parts) > 3 else ""
            pe = parts[39] if len(parts) > 39 else ""
            print(f"  {name}({code}): price={price}, PE field[39]={pe}")
            # Print all non-empty fields
            for i, f in enumerate(parts):
                if f.strip():
                    print(f"    [{i}] = {f[:60]}")
            break
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 3: Sina Finance API for financial indicators
print("\n=== Test 3: Sina Finance financial indicators API ===")
try:
    # Sina Finance financial data API
    url = "https://money.finance.sina.com.cn/corp/go.php/vFD_FinancialGuideLine/stockid/600519/ctrl/2025/displaytype/4/"
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    # Look for PE/PB in the response
    pe_match = re.search(r'市盈率.*?(\d+\.?\d*)', r.text)
    pb_match = re.search(r'市净率.*?(\d+\.?\d*)', r.text)
    roe_match = re.search(r'净资产收益率.*?(\d+\.?\d*)', r.text)
    print(f"PE: {pe_match.group(1) if pe_match else 'Not found'}")
    print(f"PB: {pb_match.group(1) if pb_match else 'Not found'}")
    print(f"ROE: {roe_match.group(1) if roe_match else 'Not found'}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 4: Xueqiu API (often works well)
print("\n=== Test 4: Xueqiu stock API ===")
try:
    url = "https://stock.xueqiu.com/v5/stock/quote.json?symbol=SH600519&extend=detail"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://xueqiu.com/",
    }
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        quote = data.get("data", {}).get("quote", {})
        print(f"Name: {quote.get('name')}")
        print(f"PE_TTM: {quote.get('pe_ttm')}")
        print(f"PE_lyr: {quote.get('pe_lyr')}")
        print(f"PB: {quote.get('pb')}")
        print(f"MarketCap: {quote.get('market_capital')}")
        print(f"ROE: {quote.get('roe_ttm')}")
        print(f"EPS: {quote.get('eps')}")
        print(f"Revenue: {quote.get('total_revenue')}")
        print(f"NetProfit: {quote.get('net_profits')}")
    else:
        print(f"Response: {r.text[:200]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 5: Sina Finance JSON API
print("\n=== Test 5: Sina Finance JSON API ===")
try:
    url = "https://finance.sina.com.cn/api/stock/stock_payload.php?action=getCompanyProfile&symbol=sh600519"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    print(f"Status: {r.status_code}, Content: {r.text[:500]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")