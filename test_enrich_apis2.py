"""测试十大股东字段"""
import requests
import json

headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://emweb.securities.eastmoney.com/"}

# 十大股东API
url = "https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax"
params = {"code": "SH600519"}
resp = requests.get(url, params=params, headers=headers, timeout=10)
data = resp.json()

# 查看sdltgd字段
sdltgd = data.get("sdltgd", [])
print(f"sdltgd count: {len(sdltgd)}")
for i, h in enumerate(sdltgd[:3]):
    print(f"\n[{i}] Keys: {list(h.keys())}")
    print(f"  Sample: {json.dumps(h, ensure_ascii=False)[:500]}")

# 查看jgcc字段
jgcc = data.get("jgcc", [])
print(f"\njgcc count: {len(jgcc)}")
for i, h in enumerate(jgcc[:3]):
    print(f"\n[{i}] Keys: {list(h.keys())}")
    print(f"  Sample: {json.dumps(h, ensure_ascii=False)[:500]}")

# 查看jjcg字段
jjcg = data.get("jjcg", [])
print(f"\njjcg count: {len(jjcg)}")
for i, h in enumerate(jjcg[:3]):
    print(f"\n[{i}] Keys: {list(h.keys())}")
    print(f"  Sample: {json.dumps(h, ensure_ascii=False)[:500]}")

# Test analyst forecast with different API
print("\n\n=== 分析师预测 - 尝试不同API ===")
# Try East Money push2 API
url2 = "https://push2.eastmoney.com/api/qt/stock/get"
params2 = {
    "secid": "1.600519",
    "fields": "f43,f162,f167,f116,f117,f55,f57,f58,f170,f171,f172,f173,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f193,f194",
    "invt": "2",
}
resp2 = requests.get(url2, params=params2, headers=headers, timeout=10)
data2 = resp2.json()
d = data2.get("data", {})
if d:
    print(f"Keys present: {[k for k, v in d.items() if v and v != '-']}")
    # Check for dividend yield
    for k, v in d.items():
        if k.startswith("f") and v and v != "-":
            print(f"  {k}: {v}")

# Test northbound from push2
print("\n\n=== 北向资金 - push2 API ===")
url3 = "https://push2.eastmoney.com/api/qt/stock/get"
params3 = {
    "secid": "1.600519",
    "fields": "f43,f162,f167,f116,f117,f55,f57,f58,f170,f171,f172,f173,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f193,f194",
    "invt": "2",
}
resp3 = requests.get(url3, params=params3, headers=headers, timeout=10)
data3 = resp3.json()
d3 = data3.get("data", {})
if d3:
    # Look for northbound related fields
    for k, v in sorted(d3.items()):
        if v and v != "-" and k.startswith("f"):
            print(f"  {k}: {v}")