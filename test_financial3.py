import requests
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://emweb.securities.eastmoney.com/",
}

# Test: Get multiple periods of financial data
print("=== Getting 4 periods of financial data ===")
url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
params = {"code": "SH600519", "type": "0"}
r = requests.get(url, params=params, headers=headers, timeout=15)
data = r.json()
records = data.get("data", [])
print(f"Total records: {len(records)}, Pages: {data.get('pages')}")

# Filter to get annual + quarterly data, take last 4
# Each record has REPORT_DATE, take the most recent 4 distinct dates
annual_records = [r for r in records if r.get("REPORT_DATE", "").endswith("-12-31")]
if not annual_records:
    annual_records = records[-4:] if len(records) >= 4 else records
else:
    annual_records = annual_records[-4:]

for rec in annual_records:
    print(f"\n--- {rec['REPORT_DATE']} ({rec['REPORT_TYPE']}) ---")
    print(f"  Revenue: {rec.get('TOTALOPERATEREVE'):.0f}")
    print(f"  NetProfit: {rec.get('PARENTNETPROFIT'):.0f}")
    print(f"  EPS: {rec.get('EPSJB')}")
    print(f"  ROE: {rec.get('ROEJQ')}%")
    print(f"  GrossMargin: {rec.get('XSMLL')}%")
    print(f"  NetMargin: {rec.get('XSJLL')}%")
    print(f"  RevenueYoY: {rec.get('TOTALOPERATEREVETZ')}%")
    print(f"  ProfitYoY: {rec.get('PARENTNETPROFITTZ')}%")
    print(f"  DebtRatio: {rec.get('ZCFZL')}%")
    print(f"  BPS: {rec.get('BPS')}")

# Test: Get peer data from F10
print("\n\n=== Getting peer comparison data ===")
try:
    # First get the industry code
    url2 = "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax"
    params2 = {"code": "SH600519"}
    r2 = requests.get(url2, params=params2, headers=headers, timeout=15)
    if r2.status_code == 200:
        try:
            data2 = r2.json()
            print("Company survey data:", json.dumps(data2, ensure_ascii=False)[:2000])
        except:
            print("Not JSON:", r2.text[:500])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test: Get industry peers from push2
print("\n\n=== Getting industry peers from push2 ===")
try:
    # Get industry board constituents
    url3 = "https://push2.eastmoney.com/api/qt/clist/get"
    params3 = {
        "pn": "1",
        "pz": "20",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f20",
        "fs": "m:1+t:2,m:1+t:23",
        "fields": "f12,f14,f2,f3,f9,f15,f16,f17,f18,f20,f21,f115",
    }
    r3 = requests.get(url3, params=params3, headers=headers, timeout=10)
    print(f"Status: {r3.status_code}")
    if r3.status_code == 200:
        data3 = r3.json()
        print(json.dumps(data3, ensure_ascii=False)[:2000])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Test: East Money F10 peer comparison
print("\n\n=== Getting peer comparison from F10 ===")
try:
    url4 = "https://emweb.securities.eastmoney.com/PC_HSF10/HyComparison/PageAjax"
    params4 = {"code": "SH600519"}
    r4 = requests.get(url4, params=params4, headers=headers, timeout=15)
    print(f"Status: {r4.status_code}")
    if r4.status_code == 200:
        try:
            data4 = r4.json()
            print(json.dumps(data4, ensure_ascii=False)[:3000])
        except:
            print("Not JSON:", r4.text[:500])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")