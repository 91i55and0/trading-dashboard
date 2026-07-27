"""测试可用的数据增强API"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://emweb.securities.eastmoney.com/',
}

symbol = "600519"
em_code = f"SH{symbol}"
secid = f"1.{symbol}"

# 1. 测试 push2 API 单股行情 (验证push2可用)
print("=" * 60)
print("1. push2 API 行情快照")
url_p2 = "https://push2.eastmoney.com/api/qt/stock/get"
params_p2 = {
    "secid": secid,
    "fields": "f43,f44,f45,f46,f57,f58,f162,f167,f116,f117,f168,f169,f170",
    "invt": "2",
}
try:
    r = requests.get(url_p2, params=params_p2, headers=headers, timeout=10)
    print(f"Status: {r.status_code}, len={len(r.text)}")
    if r.status_code == 200:
        data = r.json()
        d = data.get("data", {})
        if d:
            for k in ["f43", "f44", "f45", "f57", "f58", "f162", "f167", "f116", "f168", "f169", "f170"]:
                print(f"  {k}: {d.get(k, 'N/A')}")
except Exception as e:
    print(f"Error: {e}")

# 2. 测试 F10 ZYZB type=1 - 获取历史PE/PB和更多指标
print("\n" + "=" * 60)
print("2. F10 ZYZB type=1 - 历史PE/PB")
url2 = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew"
params2 = {"code": em_code, "type": "1"}
r2 = requests.get(url2, params=params2, headers=headers, timeout=10)
print(f"Status: {r2.status_code}")
try:
    data2 = r2.json()
    records = data2.get("data", [])
    if records:
        print(f"Record count: {len(records)}")
        print(f"Keys: {sorted(records[0].keys())}")
        # 查找PE/PB相关字段
        pe_pb_fields = [k for k in records[0].keys() if any(x in k.upper() for x in ['PE', 'PB', 'TTM', 'PRICE', 'EARN', 'BOOK'])]
        print(f"PE/PB related fields: {pe_pb_fields}")
        # 打印最近3条
        for r in records[-3:]:
            print(f"\n  Date: {r.get('REPORT_DATE', '')}")
            for f in pe_pb_fields[:8]:
                print(f"    {f}: {r.get(f, 'N/A')}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Response: {r2.text[:300]}")

# 2b. 测试 F10 ZYZB type=0 更多字段
print("\n" + "=" * 60)
print("2b. F10 ZYZB type=0 - 更多字段")
params2b = {"code": em_code, "type": "0"}
r2b = requests.get(url2, params=params2b, headers=headers, timeout=10)
print(f"Status: {r2b.status_code}")
try:
    data2b = r2b.json()
    records = data2b.get("data", [])
    if records:
        print(f"Record count: {len(records)}")
        print(f"Keys: {sorted(records[0].keys())}")
        # 查找研发相关字段
        rd_fields = [k for k in records[0].keys() if any(x in k.upper() for x in ['RD', 'RESEARCH', 'DEVELOP', '研发', 'TECHNOLOGY', 'PATENT'])]
        print(f"R&D related fields: {rd_fields}")
        # 查找员工相关字段
        emp_fields = [k for k in records[0].keys() if any(x in k.upper() for x in ['EMPLOYEE', 'STAFF', 'PER_CAP', '人均', 'WORKER'])]
        print(f"Employee related fields: {emp_fields}")
        # 打印最近1条的所有非零字段
        latest = records[-1]
        print(f"\nLatest ({latest.get('REPORT_DATE', '')}) non-zero fields:")
        for k, v in latest.items():
            if v and v != 0 and v != '0' and k not in ['REPORT_DATE', 'SECURITY_CODE', 'SECURITY_NAME_ABBR', 'ORG_CODE', 'SECURITY_TYPE_CODE']:
                print(f"  {k}: {v}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Response: {r2b.text[:300]}")

# 3. 测试 datacenter 研发费用
print("\n" + "=" * 60)
print("3. datacenter - 研发费用 API")
url3 = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
headers3 = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/',
}
params3 = {
    'reportName': 'RPT_DMSK_FN_INCOME',
    'columns': 'ALL',
    'filter': f'(SECURITY_CODE="{symbol}")',
    'pageNumber': '1',
    'pageSize': '3',
    'sortTypes': '-1',
    'sortColumns': 'REPORT_DATE',
    'source': 'WEB',
    'client': 'WEB',
}
r3 = requests.get(url3, params=params3, headers=headers3, timeout=15)
print(f"Status: {r3.status_code}")
try:
    data3 = r3.json()
    if data3.get("result") and data3["result"].get("data"):
        rows = data3["result"]["data"]
        print(f"Record count: {len(rows)}")
        # 查找研发相关字段
        rd_fields = [k for k in rows[0].keys() if any(x in k.upper() for x in ['RD', 'RESEARCH', 'DEVELOP', '研发'])]
        print(f"R&D related fields: {rd_fields}")
        if rd_fields:
            for k in rd_fields[:5]:
                print(f"  {k}: {rows[0].get(k)}")
        # 打印所有字段名
        print(f"All keys: {sorted(rows[0].keys())[:50]}...")
except Exception as e:
    print(f"Error: {e}")
    print(f"Response: {r3.text[:300]}")

# 4. 测试 F10 员工人数 API
print("\n" + "=" * 60)
print("4. F10 StaffInfo - 员工人数")
url4 = "https://emweb.securities.eastmoney.com/PC_HSF10/StaffInfo/PageAjax"
params4 = {"code": em_code}
r4 = requests.get(url4, params=params4, headers=headers, timeout=10)
print(f"Status: {r4.status_code}")
try:
    data4 = r4.json()
    print(f"Top keys: {list(data4.keys())}")
    for k, v in data4.items():
        if v and isinstance(v, list) and len(v) > 0:
            print(f"  {k}: list[{len(v)}], sample={json.dumps(v[0], ensure_ascii=False)[:300]}")
        elif v and isinstance(v, dict):
            print(f"  {k}: dict keys={list(v.keys())[:10]}")
        elif v:
            print(f"  {k}: {str(v)[:200]}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Response: {r4.text[:300]}")

# 5. 测试 F10 ShareholderResearch - 股东人数
print("\n" + "=" * 60)
print("5. F10 ShareholderResearch - 股东信息")
url5 = "https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/PageAjax"
params5 = {"code": em_code}
r5 = requests.get(url5, params=params5, headers=headers, timeout=10)
print(f"Status: {r5.status_code}")
try:
    data5 = r5.json()
    print(f"Top keys: {list(data5.keys())}")
    for k, v in data5.items():
        if v and isinstance(v, list) and len(v) > 0:
            print(f"  {k}: list[{len(v)}], sample={json.dumps(v[0], ensure_ascii=False)[:300]}")
        elif v and isinstance(v, dict):
            print(f"  {k}: dict keys={list(v.keys())[:10]}")
        elif v:
            print(f"  {k}: {str(v)[:200]}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Response: {r5.text[:300]}")

# 6. 测试 F10 OrganizationStructure - 公司治理
print("\n" + "=" * 60)
print("6. F10 OrganizationStructure - 公司治理")
url6 = "https://emweb.securities.eastmoney.com/PC_HSF10/OrganizationStructure/PageAjax"
params6 = {"code": em_code}
r6 = requests.get(url6, params=params6, headers=headers, timeout=10)
print(f"Status: {r6.status_code}")
try:
    data6 = r6.json()
    print(f"Top keys: {list(data6.keys())}")
    for k, v in data6.items():
        if v and isinstance(v, list) and len(v) > 0:
            print(f"  {k}: list[{len(v)}], sample={json.dumps(v[0], ensure_ascii=False)[:300]}")
        elif v and isinstance(v, dict):
            print(f"  {k}: dict keys={list(v.keys())[:10]}")
        elif v:
            print(f"  {k}: {str(v)[:200]}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Response: {r6.text[:300]}")

# 7. 跳过push2his（已知不可用），直接测试其他API

# 8. 测试 datacenter 质押数据
print("\n" + "=" * 60)
print("8. datacenter - 股东质押")
params8 = {
    'reportName': 'RPT_DMSK_FN_PLEDGE',
    'columns': 'ALL',
    'filter': f'(SECURITY_CODE="{symbol}")',
    'pageNumber': '1',
    'pageSize': '3',
    'sortTypes': '-1',
    'sortColumns': 'REPORT_DATE',
    'source': 'WEB',
    'client': 'WEB',
}
r8 = requests.get(url3, params=params8, headers=headers3, timeout=15)
print(f"Status: {r8.status_code}")
try:
    data8 = r8.json()
    if data8.get("result") and data8["result"].get("data"):
        rows = data8["result"]["data"]
        print(f"Record count: {len(rows)}")
        if rows:
            print(f"Keys: {sorted(rows[0].keys())[:30]}")
            for k, v in rows[0].items():
                if v and v != 0 and v != '0':
                    print(f"  {k}: {v}")
    else:
        print(f"No data: {data8.get('message', 'unknown')}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Response: {r8.text[:200]}")