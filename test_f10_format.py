"""测试F10 API返回数据的实际格式"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://emweb.securities.eastmoney.com/',
}

# Check F10 data format
print('=== F10 Data Format ===')
r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew',
    params={'code': 'SH600519', 'type': '0'},
    headers=headers, timeout=15)

d = r.json()
records = d.get('data', [])
for rec in records:
    print(f"DATE: {rec.get('REPORT_DATE')} | TYPE: {rec.get('REPORT_TYPE')} | REV: {rec.get('TOTALOPERATEREVE')} | NP: {rec.get('PARENTNETPROFIT')} | ROE: {rec.get('ROEJQ')} | GM: {rec.get('XSMLL')} | NM: {rec.get('XSJLL')}")

print(f"\nTotal records: {len(records)}")

# Check if push2 works with different params
print('\n=== push2 alternative test ===')
import urllib3
urllib3.disable_warnings()
try:
    # Try with different User-Agent
    h2 = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://quote.eastmoney.com/',
    }
    r = requests.get('https://push2.eastmoney.com/api/qt/stock/get', 
        params={'secid': '1.600519', 'fields': 'f43,f57,f58,f162,f167,f116,f117', 'invt': '2'},
        headers=h2, timeout=10, verify=False)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('push2:', json.dumps(d, ensure_ascii=False, indent=2)[:500])
except Exception as e:
    print('Error:', e)

# Try push2his (delayed) API
print('\n=== push2his API ===')
try:
    r = requests.get('https://push2his.eastmoney.com/api/qt/stock/kline/get',
        params={'secid': '1.600519', 'fields1': 'f1,f2,f3,f4,f5,f6', 'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61', 'klt': '101', 'fqt': '1', 'end': '20500101', 'lmt': '1'},
        headers=h2, timeout=10)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('push2his:', json.dumps(d, ensure_ascii=False, indent=2)[:500])
except Exception as e:
    print('Error:', e)

# Try East Money quote API (different endpoint)
print('\n=== East Money Quote API ===')
try:
    r = requests.get('https://push2.eastmoney.com/api/qt/stock/get',
        params={'secid': '1.600519', 'fields': 'f43,f57,f58,f162,f167,f116,f117', 'invt': '2'},
        headers=h2, timeout=10)
    print('Status:', r.status_code)
    if r.status_code == 200:
        d = r.json()
        print('quote:', json.dumps(d, ensure_ascii=False, indent=2)[:500])
except Exception as e:
    print('Error:', e)