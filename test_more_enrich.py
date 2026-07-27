"""测试更多数据增强API"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/',
}

url = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'

# 1. 测试主营构成 (收入构成/分部)
print("=" * 60)
print("1. 主营构成 API")
params = {
    'reportName': 'RPT_DMSK_FN_MAINOPERATE',
    'columns': 'ALL',
    'filter': '(SECURITY_CODE="600519")',
    'pageNumber': '1',
    'pageSize': '5',
    'sortTypes': '-1',
    'sortColumns': 'REPORT_DATE',
    'source': 'WEB',
    'client': 'WEB',
}
r = requests.get(url, params=params, headers=headers, timeout=15)
print(f'Status: {r.status_code}')
try:
    data = r.json()
    if data.get('result') and data['result'].get('data'):
        rows = data['result']['data']
        print(f'Count: {len(rows)}')
        print(f'Keys: {list(rows[0].keys())}')
        # 打印第一行
        for k, v in rows[0].items():
            if v and v != 0 and v != '0':
                print(f'  {k}: {v}')
    else:
        print(f'No data: {json.dumps(data, ensure_ascii=False)[:300]}')
except Exception as e:
    print(f'Error: {e}')
    print(f'Text: {r.text[:200]}')

# 2. 测试研发费用
print("\n" + "=" * 60)
print("2. 研发费用 API")
params2 = {
    'reportName': 'RPT_DMSK_FN_RDEXPENSE',
    'columns': 'ALL',
    'filter': '(SECURITY_CODE="300750")',
    'pageNumber': '1',
    'pageSize': '5',
    'sortTypes': '-1',
    'sortColumns': 'REPORT_DATE',
    'source': 'WEB',
    'client': 'WEB',
}
r2 = requests.get(url, params=params2, headers=headers, timeout=15)
print(f'Status: {r2.status_code}')
try:
    data2 = r2.json()
    if data2.get('result') and data2['result'].get('data'):
        rows2 = data2['result']['data']
        print(f'Count: {len(rows2)}')
        print(f'Keys: {list(rows2[0].keys())}')
        for k, v in rows2[0].items():
            if v and v != 0 and v != '0':
                print(f'  {k}: {v}')
    else:
        print(f'No data: {json.dumps(data2, ensure_ascii=False)[:300]}')
except Exception as e:
    print(f'Error: {e}')
    print(f'Text: {r2.text[:200]}')

# 3. 测试员工/人均指标
print("\n" + "=" * 60)
print("3. 员工数据 API")
params3 = {
    'reportName': 'RPT_DMSK_FN_STAFF',
    'columns': 'ALL',
    'filter': '(SECURITY_CODE="600519")',
    'pageNumber': '1',
    'pageSize': '3',
    'sortTypes': '-1',
    'sortColumns': 'REPORT_DATE',
    'source': 'WEB',
    'client': 'WEB',
}
r3 = requests.get(url, params=params3, headers=headers, timeout=15)
print(f'Status: {r3.status_code}')
try:
    data3 = r3.json()
    if data3.get('result') and data3['result'].get('data'):
        rows3 = data3['result']['data']
        print(f'Count: {len(rows3)}')
        if rows3:
            print(f'Keys: {list(rows3[0].keys())}')
            for k, v in rows3[0].items():
                if v and v != 0 and v != '0':
                    print(f'  {k}: {v}')
    else:
        print(f'No data: {json.dumps(data3, ensure_ascii=False)[:300]}')
except Exception as e:
    print(f'Error: {e}')
    print(f'Text: {r3.text[:200]}')

# 4. 测试历史PE/PB分位
print("\n" + "=" * 60)
print("4. 历史估值分位 API")
params4 = {
    'reportName': 'RPT_VALUE_DAILY_VALUATION',
    'columns': 'ALL',
    'filter': '(SECURITY_CODE="600519")',
    'pageNumber': '1',
    'pageSize': '5',
    'sortTypes': '-1',
    'sortColumns': 'TRADE_DATE',
    'source': 'WEB',
    'client': 'WEB',
}
r4 = requests.get(url, params=params4, headers=headers, timeout=15)
print(f'Status: {r4.status_code}')
try:
    data4 = r4.json()
    if data4.get('result') and data4['result'].get('data'):
        rows4 = data4['result']['data']
        print(f'Count: {len(rows4)}')
        if rows4:
            print(f'Keys: {list(rows4[0].keys())}')
            for k, v in rows4[0].items():
                if v and v != 0 and v != '0':
                    print(f'  {k}: {v}')
    else:
        print(f'No data: {json.dumps(data4, ensure_ascii=False)[:300]}')
except Exception as e:
    print(f'Error: {e}')
    print(f'Text: {r4.text[:200]}')

# 5. 测试杜邦分析
print("\n" + "=" * 60)
print("5. 杜邦分析 API")
params5 = {
    'reportName': 'RPT_DMSK_FN_DUPONT',
    'columns': 'ALL',
    'filter': '(SECURITY_CODE="600519")',
    'pageNumber': '1',
    'pageSize': '3',
    'sortTypes': '-1',
    'sortColumns': 'REPORT_DATE',
    'source': 'WEB',
    'client': 'WEB',
}
r5 = requests.get(url, params=params5, headers=headers, timeout=15)
print(f'Status: {r5.status_code}')
try:
    data5 = r5.json()
    if data5.get('result') and data5['result'].get('data'):
        rows5 = data5['result']['data']
        print(f'Count: {len(rows5)}')
        if rows5:
            print(f'Keys: {list(rows5[0].keys())}')
            for k, v in rows5[0].items():
                if v and v != 0 and v != '0':
                    print(f'  {k}: {v}')
    else:
        print(f'No data: {json.dumps(data5, ensure_ascii=False)[:300]}')
except Exception as e:
    print(f'Error: {e}')
    print(f'Text: {r5.text[:200]}')

# 6. F10 更多字段 - 尝试获取研发费用
print("\n" + "=" * 60)
print("6. F10 报表日期与研发费用相关字段")
url6 = 'https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew'
params6 = {'code': 'SH600519', 'type': '0'}
r6 = requests.get(url6, params=params6, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://emweb.securities.eastmoney.com/'}, timeout=15)
try:
    data6 = r6.json()
    records = data6.get('data', [])
    if records:
        latest = records[-1]
        # 搜索研发相关字段
        rd_fields = [k for k in latest.keys() if 'RD' in k.upper() or 'YF' in k.upper() or 'DEVELOP' in k.upper() or 'RESEARCH' in k.upper()]
        print(f'研发相关字段: {rd_fields}')
        for k in rd_fields:
            print(f'  {k}: {latest[k]}')
except Exception as e:
    print(f'Error: {e}')