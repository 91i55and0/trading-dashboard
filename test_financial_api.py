"""测试东方财富财务数据API"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://data.eastmoney.com/',
}

# 1. 测试datacenter利润表API
print("=" * 60)
print("1. 利润表 (datacenter)")
url = 'https://datacenter.eastmoney.com/securities/api/data/v1/get'
params = {
    'reportName': 'RPT_DMSK_FN_INCOME',
    'columns': 'ALL',
    'filter': '(SECURITY_CODE="600519")',
    'pageNumber': '1',
    'pageSize': '3',
    'sortTypes': '-1',
    'sortColumns': 'REPORT_DATE',
    'source': 'WEB',
    'client': 'WEB',
}
r = requests.get(url, params=params, headers=headers, timeout=15)
print(f'Status: {r.status_code}, len={len(r.text)}')
try:
    data = r.json()
    print(f'Success: {data.get("success")}, code: {data.get("code")}')
    if data.get('result') and data['result'].get('data'):
        rows = data['result']['data']
        print(f'Count: {len(rows)}')
        print(f'Sample keys: {list(rows[0].keys())[:30]}')
        # 打印关键字段
        for k in ['TOTAL_OPERATE_INCOME', 'OPERATE_PROFIT', 'TOTAL_PROFIT', 'NET_PROFIT', 'BASIC_EPS']:
            if k in rows[0]:
                print(f'  {k}: {rows[0][k]}')
except Exception as e:
    print(f'Error: {e}')
    print(f'Text: {r.text[:500]}')

# 2. 测试datacenter资产负债表API
print("\n" + "=" * 60)
print("2. 资产负债表 (datacenter)")
params2 = {
    'reportName': 'RPT_DMSK_FN_BALANCE',
    'columns': 'ALL',
    'filter': '(SECURITY_CODE="600519")',
    'pageNumber': '1',
    'pageSize': '3',
    'sortTypes': '-1',
    'sortColumns': 'REPORT_DATE',
    'source': 'WEB',
    'client': 'WEB',
}
r2 = requests.get(url, params=params2, headers=headers, timeout=15)
print(f'Status: {r2.status_code}, len={len(r2.text)}')
try:
    data2 = r2.json()
    if data2.get('result') and data2['result'].get('data'):
        rows2 = data2['result']['data']
        print(f'Count: {len(rows2)}')
        print(f'Sample keys: {list(rows2[0].keys())[:30]}')
        for k in ['TOTAL_ASSETS', 'TOTAL_LIABILITIES', 'TOTAL_EQUITY', 'CURRENT_ASSETS', 'CURRENT_LIABILITIES']:
            if k in rows2[0]:
                print(f'  {k}: {rows2[0][k]}')
except Exception as e:
    print(f'Error: {e}')

# 3. 测试datacenter现金流量表API
print("\n" + "=" * 60)
print("3. 现金流量表 (datacenter)")
params3 = {
    'reportName': 'RPT_DMSK_FN_CASHFLOW',
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
print(f'Status: {r3.status_code}, len={len(r3.text)}')
try:
    data3 = r3.json()
    if data3.get('result') and data3['result'].get('data'):
        rows3 = data3['result']['data']
        print(f'Count: {len(rows3)}')
        print(f'Sample keys: {list(rows3[0].keys())[:30]}')
        for k in ['NETCASH_OPERATE', 'NETCASH_INVEST', 'NETCASH_FINANCE', 'FREE_CASH_FLOW']:
            if k in rows3[0]:
                print(f'  {k}: {rows3[0][k]}')
except Exception as e:
    print(f'Error: {e}')

# 4. 测试F10 ZYZB更多字段
print("\n" + "=" * 60)
print("4. F10 ZYZB更多字段")
url4 = 'https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew'
params4 = {'code': 'SH600519', 'type': '0'}
r4 = requests.get(url4, params=params4, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://emweb.securities.eastmoney.com/'}, timeout=15)
try:
    data4 = r4.json()
    records = data4.get('data', [])
    if records:
        latest = records[-1]
        print(f'All keys ({len(latest)}): {list(latest.keys())}')
        # 打印所有非零字段
        for k, v in latest.items():
            if v and v != 0 and v != '0' and v != '' and v is not None:
                print(f'  {k}: {v}')
except Exception as e:
    print(f'Error: {e}')