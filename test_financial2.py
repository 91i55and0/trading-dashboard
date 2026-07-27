import requests
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://emweb.securities.eastmoney.com/",
}

# Test 1: East Money F10 financial data API
print("=== Test 1: East Money F10 financial summary API ===")
try:
    url = "https://emweb.securities.eastmoney.com/PC_HSF10/FinanceSummary/PageAjax"
    params = {"code": "SH600519"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        # Navigate to find financial data
        print(json.dumps(data, ensure_ascii=False)[:3000])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 2: East Money financial data new API
print("\n=== Test 2: East Money financial main indicator ===")
try:
    url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
    params = {
        "code": "SH600519",
        "type": "0",  # 按报告期
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, ensure_ascii=False)[:3000])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 3: East Money growth analysis API
print("\n=== Test 3: East Money growth analysis API ===")
try:
    url = "https://emweb.securities.eastmoney.com/PC_HSF10/GrowAnalyze/PageAjax"
    params = {"code": "SH600519"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, ensure_ascii=False)[:3000])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 4: Try the datacenter API with different host
print("\n=== Test 4: East Money datacenter with different host ===")
try:
    # Try the web-facing datacenter API
    url = "https://emweb.securities.eastmoney.com/PC_HSF10/FinanceSummary/FinanceSummary"
    params = {"code": "SH600519", "type": "web"}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    # Check if it returns JSON
    try:
        print(r.json())
    except:
        print("Not JSON:", r.text[:500])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")