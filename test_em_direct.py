"""测试东方财富 push2 + F10 API 直接调用"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://emweb.securities.eastmoney.com/',
}

# Test 1: push2 API
print('=== Test 1: push2 API ===')
try:
    r = requests.get('https://push2.eastmoney.com/api/qt/stock/get', 
        params={'secid': '1.600519', 'fields': 'f43,f44,f45,f46,f55,f57,f58,f116,f117,f162,f167,f170', 'invt': '2'},
        headers=headers, timeout=10)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('push2 response:', json.dumps(d, ensure_ascii=False, indent=2)[:500])
        dd = d.get('data', {})
        if dd:
            price = float(dd.get('f43', 0)) / 100
            pe = float(dd.get('f162', 0)) / 100
            pb = float(dd.get('f167', 0)) / 100
            mcap = float(dd.get('f116', 0))
            print(f'price={price}, PE={pe}, PB={pb}, market_cap={mcap}')
except Exception as e:
    print('Error:', e)

# Test 2: F10 API
print('\n=== Test 2: F10 Financial API ===')
try:
    r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew',
        params={'code': 'SH600519', 'type': '0'},
        headers=headers, timeout=15)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('F10 keys:', list(d.keys()))
        records = d.get('data', [])
        print('Total records:', len(records))
        if records:
            print('First record keys:', list(records[0].keys())[:20])
            annual = [r for r in records if r.get('REPORT_DATE', '').endswith('-12-31')]
            print('Annual records:', len(annual))
            if annual:
                latest = annual[-1]
                date = latest.get('REPORT_DATE')
                print(f'Latest annual: {date}')
                print(f'  Revenue: {latest.get("TOTALOPERATEREVE")}')
                print(f'  NetProfit: {latest.get("PARENTNETPROFIT")}')
                print(f'  ROE: {latest.get("ROEJQ")}%')
                print(f'  GrossMargin: {latest.get("XSMLL")}%')
                print(f'  NetMargin: {latest.get("XSJLL")}%')
                print(f'  RevenueYoY: {latest.get("TOTALOPERATEREVETZ")}%')
                print(f'  ProfitYoY: {latest.get("PARENTNETPROFITTZ")}%')
                print(f'  DebtRatio: {latest.get("ZCFZL")}%')
                print(f'  HY_NAME: {latest.get("HY_NAME")}')
    else:
        print('Response:', r.text[:300])
except Exception as e:
    import traceback
    traceback.print_exc()

# Test 3: F10 Company Survey
print('\n=== Test 3: F10 Company Survey ===')
try:
    r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax',
        params={'code': 'SH600519'},
        headers=headers, timeout=10)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('Survey keys:', list(d.keys()))
        jbzl = d.get('jbzl', [])
        if jbzl:
            c = jbzl[0]
            print('HY_NAME:', c.get('EM2016'))
            print('REG_CAPITAL:', c.get('REG_CAPITAL'))
            print('LISTING_DATE:', c.get('LISTING_DATE'))
    else:
        print('Response:', r.text[:300])
except Exception as e:
    import traceback
    traceback.print_exc()