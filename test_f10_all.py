"""测试东方财富F10完整字段和同业对比API"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://emweb.securities.eastmoney.com/',
}

# Test 1: F10 full record keys
print('=== F10 Full Record Keys ===')
r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew',
    params={'code': 'SH600519', 'type': '0'},
    headers=headers, timeout=15)
d = r.json()
records = d.get('data', [])
if records:
    latest = records[0]  # newest first
    print('All keys:', json.dumps(list(latest.keys()), ensure_ascii=False))
    print('HY_NAME:', latest.get('HY_NAME'))
    print('HY_CODE:', latest.get('HY_CODE'))
    print('EM2016:', latest.get('EM2016'))

# Test 2: HyComparison API
print('\n=== HyComparison API ===')
try:
    r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/HyComparison/PageAjax',
        params={'code': 'SH600519'},
        headers=headers, timeout=15)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('Keys:', list(d.keys()))
        hy = d.get('hy', [])
        print('hy count:', len(hy))
        if hy:
            for p in hy[:5]:
                print(f"  {p.get('SECUCODE')} | {p.get('SECURITY_NAME_ABBR')} | PE={p.get('PE_TTM')} | ROE={p.get('ROE')} | MC={p.get('TOTAL_MARKET_CAP')}")
except Exception as e:
    print('Error:', e)

# Test 3: Company Survey with longer timeout
print('\n=== Company Survey (longer timeout) ===')
try:
    r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax',
        params={'code': 'SH600519'},
        headers=headers, timeout=20)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        jbzl = d.get('jbzl', [])
        if jbzl:
            c = jbzl[0]
            print('All keys:', list(c.keys())[:30])
            print('EM2016:', c.get('EM2016'))
            print('HY_NAME:', c.get('HY_NAME'))
except Exception as e:
    print('Error:', e)