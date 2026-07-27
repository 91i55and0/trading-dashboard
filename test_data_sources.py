import requests
import json
import re

# Test 1: Sina Finance API for financial data
print("=== Test 1: Sina Finance financial data ===")
try:
    url = "https://finance.sina.com.cn/realstock/company/sh600519/nc.shtml"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    # Try to find PE/PB in the page
    pe_match = re.search(r'市盈率[：:]\s*([\d.]+)', r.text)
    pb_match = re.search(r'市净率[：:]\s*([\d.]+)', r.text)
    print(f"PE found: {pe_match.group(1) if pe_match else 'Not found'}")
    print(f"PB found: {pb_match.group(1) if pb_match else 'Not found'}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 2: Sina quote API for A-share (to check fields)
print("\n=== Test 2: Sina quote for sh600519 ===")
try:
    url = "https://hq.sinajs.cn/list=sh600519"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn/",
    }
    r = requests.get(url, headers=headers, timeout=10)
    content = r.text
    if '"' in content:
        data = content.split('"')[1]
        parts = data.split(",")
        print(f"Total fields: {len(parts)}")
        for i, p in enumerate(parts[:35]):
            print(f"  [{i}] = {p}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 3: Try AKShare spot_em with proxy
print("\n=== Test 3: AKShare spot_em (East Money via proxy) ===")
try:
    import akshare as ak
    import os
    os.environ["AKSHARE_TOKEN"] = "20260718K92YUFOB"
    os.environ["AKSHARE_PROXY"] = "https://ak.cheapproxy.net/dashboard/akshare"
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(ak.stock_zh_a_spot_em)
        try:
            df = future.result(timeout=20)
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            # Find 600519
            row = df[df["代码"] == "600519"]
            if not row.empty:
                r = row.iloc[0]
                print(f"Name: {r['名称']}")
                print(f"Price: {r['最新价']}")
                print(f"PE: {r.get('市盈率-动态', 'N/A')}")
                print(f"PB: {r.get('市净率', 'N/A')}")
                print(f"MarketCap: {r.get('总市值', 'N/A')}")
                print(f"Industry: {r.get('行业', 'N/A')}")
        except concurrent.futures.TimeoutError:
            print("AKShare timeout")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 4: East Money API with shorter timeout
print("\n=== Test 4: East Money datacenter (shorter test) ===")
try:
    url = "https://datacenter.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_DMSK_FN_MAININDICATOR",
        "columns": "SECURITY_CODE,PE_TTM_WEIGHT,PB_WEIGHT,TOTAL_MARKET_CAP,INDUSTRY_NAME",
        "filter": '(SECURITY_TYPE_CODE="058001001")(SECURITY_CODE="600519")',
        "pageNumber": 1,
        "pageSize": 1,
        "sortTypes": -1,
        "sortColumns": "REPORT_DATE",
    }
    r = requests.get(url, params=params, headers=headers, timeout=20)
    print(f"Status: {r.status_code}")
    data = r.json()
    if data.get("success") and data.get("result") and data["result"].get("data"):
        rec = data["result"]["data"][0]
        print(f"PE: {rec.get('PE_TTM_WEIGHT')}")
        print(f"PB: {rec.get('PB_WEIGHT')}")
        print(f"MarketCap: {rec.get('TOTAL_MARKET_CAP')}")
        print(f"Industry: {rec.get('INDUSTRY_NAME')}")
    else:
        print("No data returned")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")