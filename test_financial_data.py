import requests
import json
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Test 1: East Money push2 API (might work when datacenter doesn't)
print("=== Test 1: East Money push2 API ===")
try:
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": "1.600519",
        "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f55,f57,f58,f60,f100,f115,f116,f117,f162,f164,f167,f168,f169,f170,f171",
        "invt": 2,
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        d = data.get("data", {})
        print(f"Price(f43): {d.get('f43')}")
        print(f"PE(f162): {d.get('f162')}")
        print(f"PE_dynamic(f9): {d.get('f9')}")
        print(f"PB(f167): {d.get('f167')}")
        print(f"MarketCap(f116): {d.get('f116')}")
        print(f"ROE(f173): {d.get('f173')}")
        print(f"EPS(f55): {d.get('f55')}")
        print(f"Revenue(f44): {d.get('f44')}")
        print(f"NetProfit(f45): {d.get('f45')}")
        print(f"All keys: {list(d.keys())[:30]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 2: East Money financial data via push2
print("\n=== Test 2: East Money push2 financial data ===")
try:
    url = "https://push2.eastmoney.com/api/qt/slist/get"
    params = {
        "secid": "1.600519",
        "fields": "f43,f44,f45,f46,f48,f49,f50,f51,f52,f55,f57,f58,f60,f100,f115,f116,f117,f162,f164,f167,f168,f169,f170,f171,f173,f183,f184,f185,f186,f187,f188,f189",
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(json.dumps(data, ensure_ascii=False)[:1000])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 3: East Money finance report API
print("\n=== Test 3: East Money financial report API ===")
try:
    url = "https://emweb.securities.eastmoney.com/PC_HSF10/FinanceSummary/FinanceSummary"
    params = {
        "code": "SH600519",
        "type": "web",
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    if r.status_code == 200:
        # Look for growth rate data
        data = r.json() if r.text.startswith("{") else {}
        print(json.dumps(data, ensure_ascii=False)[:2000] if data else r.text[:500])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 4: Try Tencent Finance financial data
print("\n=== Test 4: Tencent Finance financial data ===")
try:
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "param": "sh600519,day,,,10,qfq",
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    if r.status_code == 200:
        data = r.json()
        # Check if there's financial data
        print(json.dumps(data, ensure_ascii=False)[:500])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 5: 同花顺 IFind API
print("\n=== Test 5: 10jqka financial data ===")
try:
    url = "https://basic.10jqka.com.cn/600519/"
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    # Look for PE/PB
    pe_match = re.search(r'市盈率.*?(\d+\.?\d*)', r.text)
    pb_match = re.search(r'市净率.*?(\d+\.?\d*)', r.text)
    roe_match = re.search(r'净资产收益率.*?(\d+\.?\d*)', r.text)
    print(f"PE: {pe_match.group(1) if pe_match else 'Not found'}")
    print(f"PB: {pb_match.group(1) if pb_match else 'Not found'}")
    print(f"ROE: {roe_match.group(1) if roe_match else 'Not found'}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test 6: East Money financial data API (newer endpoint)
print("\n=== Test 6: East Money new finance API ===")
try:
    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    params = {
        "reportName": "RPT_LICO_FN_CPD",
        "columns": "SECURITY_CODE,NOTICE_DATE,REPORT_DATE,BASIC_EPS,WEIGHTAVG_ROE,GROSS_PROFIT_RATIO,NET_PROFIT_RATIO,OPERATE_INCOME_YOY,NETPROFIT_YOY",
        "filter": '(SECURITY_TYPE_CODE="058001001")(SECURITY_CODE="600519")',
        "pageNumber": 1,
        "pageSize": 4,
        "sortTypes": -1,
        "sortColumns": "REPORT_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(r.text[:1000])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")