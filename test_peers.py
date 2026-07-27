"""测试同行对比API"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://emweb.securities.eastmoney.com/',
}

# Test HyComparison API with different params
print('=== HyComparison (type=1) ===')
try:
    r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/HyComparison/PageAjax',
        params={'code': 'SH600519', 'type': '1'},
        headers=headers, timeout=15)
    print('Status:', r.status_code)
    print('Content[:500]:', r.text[:500])
except Exception as e:
    print('Error:', e)

# Try the F10 NewFinanceAnalysis 同业对比
print('\n=== F10 同业对比 ===')
try:
    r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/HyComparison/HyComparison',
        params={'code': 'SH600519'},
        headers=headers, timeout=15)
    print('Status:', r.status_code)
    print('Content[:500]:', r.text[:500])
except Exception as e:
    print('Error:', e)

# Try push2 for industry stocks (push2his might work)
print('\n=== push2his 行业 ===')
try:
    r = requests.get('https://push2his.eastmoney.com/api/qt/stock/kline/get',
        params={'secid': '90.BK0477', 'fields1': 'f1,f2,f3,f4,f5,f6', 'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61', 'klt': '101', 'fqt': '1', 'end': '20500101', 'lmt': '1'},
        headers=headers, timeout=10)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('push2his:', json.dumps(d, ensure_ascii=False)[:300])
except Exception as e:
    print('Error:', e)

# Try East Money datacenter API for industry stocks
print('\n=== East Money datacenter for 白酒板块 ===')
try:
    r = requests.get('https://datacenter.eastmoney.com/api/data/v1/get',
        params={
            'sortColumns': 'SECURITY_CODE',
            'sortTypes': '1',
            'pageSize': '20',
            'pageNumber': '1',
            'reportName': 'RPT_DMSK_FN_MAININDICATOR',
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_MARKET_CODE',
            'filter': '(BOARD_CODE="BK0477")(REPORT_DATE="2025-12-31")',
        },
        headers=headers, timeout=15)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('datacenter:', json.dumps(d, ensure_ascii=False)[:500])
except Exception as e:
    print('Error:', e)