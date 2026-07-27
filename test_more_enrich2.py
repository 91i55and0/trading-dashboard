"""测试更多数据增强API - 第二轮"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://emweb.securities.eastmoney.com/',
}

# 1. F10 经营分析 - 主营构成
print("=" * 60)
print("1. F10 经营分析 (BusinessAnalysis) - 主营构成")
url1 = 'https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax'
params1 = {'code': 'SH600519'}
r1 = requests.get(url1, params=params1, headers=headers, timeout=15)
print(f'Status: {r1.status_code}, len={len(r1.text)}')
try:
    data1 = r1.json()
    print(f'Top keys: {list(data1.keys())}')
    for k, v in data1.items():
        if v and isinstance(v, list) and len(v) > 0:
            print(f'  {k}: list[{len(v)}], first={json.dumps(v[0], ensure_ascii=False)[:200]}')
        elif v and isinstance(v, dict):
            print(f'  {k}: dict keys={list(v.keys())[:10]}')
        elif v:
            print(f'  {k}: {str(v)[:200]}')
except Exception as e:
    print(f'Error: {e}')
    print(f'Text: {r1.text[:300]}')

# 2. F10 财务分析 - 更多type参数
print("\n" + "=" * 60)
print("2. F10 ZYZB type=1 (按报告期)")
url2 = 'https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew'
params2 = {'code': 'SH600519', 'type': '1'}
r2 = requests.get(url2, params=params2, headers=headers, timeout=15)
print(f'Status: {r2.status_code}')
try:
    data2 = r2.json()
    records = data2.get('data', [])
    if records:
        print(f'Count: {len(records)}')
        latest = records[-1]
        # 列出所有非零、非空字段
        important = {}
        for k, v in latest.items():
            if v and v != 0 and v != '0' and v != '' and v is not None and v != 'None':
                important[k] = v
        print(f'Non-empty fields count: {len(important)}')
        # 分类打印
        for prefix in ['TOTAL', 'OPERATE', 'PARENT', 'ROE', 'GROSS', 'NET', 'DEBT', 'ASSET', 'INVENTORY', 'RECEIVABLE', 'CASH', 'GOODWILL', 'R&D', 'YF', 'YYS', 'XS', 'MGMT', 'FINANCE', 'TAX', 'EPS', 'BPS', 'NAV']:
            matches = {k: v for k, v in important.items() if any(p in k.upper() for p in [prefix])}
            if matches:
                print(f'\n  [{prefix}相关]:')
                for k, v in list(matches.items())[:10]:
                    print(f'    {k}: {v}')
    else:
        print('No records')
except Exception as e:
    print(f'Error: {e}')

# 3. 尝试获取历史PE/PB via push2 K线 
print("\n" + "=" * 60)
print("3. push2his 日线 (含PE/PB)")
url3 = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
params3 = {
    'secid': '1.600519',
    'fields1': 'f1,f2,f3,f4,f5,f6',
    'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90,f91,f92,f93,f94,f95,f96,f97,f98,f99,f100',
    'klt': '101',
    'fqt': '1',
    'end': '20500101',
    'lmt': '3',
}
r3 = requests.get(url3, params=params3, headers=headers, timeout=10)
print(f'Status: {r3.status_code}')
try:
    data3 = r3.json()
    if data3.get('data') and data3['data'].get('klines'):
        klines = data3['data']['klines']
        print(f'Kline count: {len(klines)}')
        print(f'Sample kline: {klines[-1]}')
        # 计算字段数
        parts = klines[-1].split(',')
        print(f'Fields count: {len(parts)}')
        # 通常push2的日线字段: 0日期,1开盘,2收盘,3最高,4最低,5成交量,6成交额,7振幅,8涨跌幅,9涨跌额,10换手率
        # 更多字段可能需要不同的fields2
        for i, p in enumerate(parts):
            if p and p != '0' and p != '0.00':
                print(f'  [{i}]: {p}')
except Exception as e:
    print(f'Error: {e}')

# 4. F10 核心题材/概念
print("\n" + "=" * 60)
print("4. F10 核心题材")
url4 = 'https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax'
params4 = {'code': 'SH600519'}
r4 = requests.get(url4, params=params4, headers=headers, timeout=10)
print(f'Status: {r4.status_code}')
try:
    data4 = r4.json()
    print(f'Top keys: {list(data4.keys())}')
    for k, v in data4.items():
        if isinstance(v, list) and len(v) > 0:
            print(f'  {k}: list[{len(v)}]')
            if len(v) > 0 and isinstance(v[0], dict):
                print(f'    first keys: {list(v[0].keys())[:10]}')
                for fk, fv in list(v[0].items())[:5]:
                    print(f'    {fk}: {fv}')
        elif isinstance(v, dict):
            print(f'  {k}: dict keys={list(v.keys())[:10]}')
        elif v:
            print(f'  {k}: {str(v)[:200]}')
except Exception as e:
    print(f'Error: {e}')

# 5. 测试互动易/问董秘
print("\n" + "=" * 60)
print("5. F10 行业对比 (HyComparison)")
url5 = 'https://emweb.securities.eastmoney.com/PC_HSF10/IndustryAnalysis/PageAjax'
params5 = {'code': 'SH600519'}
r5 = requests.get(url5, params=params5, headers=headers, timeout=10)
print(f'Status: {r5.status_code}, len={len(r5.text)}')
try:
    data5 = r5.json()
    print(f'Top keys: {list(data5.keys())}')
    for k, v in data5.items():
        if isinstance(v, list) and len(v) > 0:
            print(f'  {k}: list[{len(v)}]')
            if len(v) > 0 and isinstance(v[0], dict):
                print(f'    first: {json.dumps(v[0], ensure_ascii=False)[:300]}')
        elif isinstance(v, dict):
            print(f'  {k}: dict keys={list(v.keys())[:10]}')
        elif v:
            print(f'  {k}: {str(v)[:200]}')
except Exception as e:
    print(f'Error: {e}')
    print(f'Text: {r5.text[:300]}')