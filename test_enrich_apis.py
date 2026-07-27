"""测试数据增强API"""
import requests
import json

headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://emweb.securities.eastmoney.com/"}

# 1. 测试分析师预测API
print("=" * 50)
print("1. 分析师预测API")
url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
params = {
    "reportName": "RPT_DMSK_FN_MAINPREDICTPROFIT",
    "columns": "ALL",
    "filter": '(SECURITY_CODE="600519")',
    "pageNumber": "1",
    "pageSize": "5",
    "source": "WEB",
    "client": "WEB",
}
resp = requests.get(url, params=params, headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Success: {data.get('success')}")
print(f"Has result: {data.get('result') is not None}")
if data.get("result") and data["result"].get("data"):
    rows = data["result"]["data"]
    print(f"Count: {len(rows)}")
    print(f"Sample keys: {list(rows[0].keys())}")
    print(f"Sample: {json.dumps(rows[0], ensure_ascii=False)[:500]}")
else:
    print(f"Response: {str(data)[:500]}")

# 2. 测试十大股东API
print("\n" + "=" * 50)
print("2. 十大股东API")
url2 = "https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax"
params2 = {"code": "SH600519"}
resp2 = requests.get(url2, params=params2, headers=headers, timeout=10)
print(f"Status: {resp2.status_code}")
data2 = resp2.json()
print(f"Keys: {list(data2.keys())}")
if "sdltgd" in data2:
    print(f"sdltgd count: {len(data2['sdltgd'])}")
    for h in data2["sdltgd"][:3]:
        print(f"  {h.get('HOLDER_NAME', '?')}: {h.get('HOLD_NUM_RATIO', '?')}%")
elif "gdrs" in data2:
    print(f"gdrs count: {len(data2['gdrs'])}")
    for h in data2["gdrs"][:3]:
        print(f"  {h.get('HOLDER_NAME', '?')}: {h.get('HOLD_NUM_RATIO', '?')}%")
else:
    print(f"Response: {str(data2)[:500]}")

# 3. 测试北向资金API
print("\n" + "=" * 50)
print("3. 北向资金API")
url3 = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
params3 = {
    "reportName": "RPT_MUTUAL_HOLDSTOCKNORTHSTA",
    "columns": "ALL",
    "filter": '(SECURITY_CODE="600519")',
    "pageNumber": "1",
    "pageSize": "3",
    "source": "WEB",
    "client": "WEB",
}
resp3 = requests.get(url3, params=params3, headers=headers, timeout=10)
print(f"Status: {resp3.status_code}")
data3 = resp3.json()
print(f"Success: {data3.get('success')}")
print(f"Has result: {data3.get('result') is not None}")
if data3.get("result") and data3["result"].get("data"):
    rows = data3["result"]["data"]
    print(f"Count: {len(rows)}")
    print(f"Sample keys: {list(rows[0].keys())}")
    print(f"Sample: {json.dumps(rows[0], ensure_ascii=False)[:500]}")
else:
    print(f"Response: {str(data3)[:500]}")

# 4. 测试腾讯API股息率
print("\n" + "=" * 50)
print("4. 腾讯API股息率")
url4 = "https://qt.gtimg.cn/q=sh600519"
resp4 = requests.get(url4, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
if resp4.status_code == 200:
    content = resp4.text
    if "~" in content:
        parts = content.split('"')[1] if '"' in content else content
        fields = parts.split("~")
        print(f"Total fields: {len(fields)}")
        for i in range(30, min(60, len(fields))):
            print(f"  [{i}]: {fields[i]}")