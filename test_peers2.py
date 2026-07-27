"""测试更多同行数据API"""
import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://emweb.securities.eastmoney.com/',
}

# Test 1: F10 行业对比 - 新接口
print('=== F10 行业对比 (新接口) ===')
try:
    r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/HyComparison/GetHyComparison',
        params={'code': 'SH600519'},
        headers=headers, timeout=15)
    print('Status:', r.status_code)
    print('Content[:500]:', r.text[:500])
except Exception as e:
    print('Error:', e)

# Test 2: Datacenter API for industry stocks
print('\n=== Datacenter 行业个股 ===')
try:
    r = requests.get('https://datacenter.eastmoney.com/api/data/v1/get',
        params={
            'sortColumns': 'SECURITY_CODE',
            'sortTypes': '1',
            'pageSize': '20',
            'pageNumber': '1',
            'reportName': 'RPT_DMSK_FN_MAININDICATOR',
            'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR',
            'filter': '(BOARD_CODE="BK0477")(REPORT_DATE="2025-12-31")',
            'source': 'WEB',
            'client': 'WEB',
        },
        headers=headers, timeout=15)
    print('Status:', r.status_code)
    print('Content[:500]:', r.text[:500])
except Exception as e:
    print('Error:', e)

# Test 3: push2 板块成分股 (different format)
print('\n=== push2 板块成分股 ===')
try:
    r = requests.get('https://push2.eastmoney.com/api/qt/clist/get',
        params={
            'pn': '1', 'pz': '20', 'po': '1', 'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2', 'invt': '2', 'fid': 'f20',
            'fs': 'b:BK0477+f:!50',
            'fields': 'f2,f3,f9,f12,f14,f20,f115',
        },
        headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'},
        timeout=10)
    print('Status:', r.status_code)
    if r.status_code == 200:
        print('Content[:500]:', r.text[:500])
except Exception as e:
    print('Error:', e)

# Test 4: Tencent 板块成分股
print('\n=== Tencent 板块成分股 ===')
try:
    r = requests.get('https://proxy.finance.qq.com/ifzqgtimg/appstock/app/HsBoard/stocklist?code=BK0477',
        headers={'User-Agent': 'Mozilla/5.0'},
        timeout=10)
    print('Status:', r.status_code)
    print('Content[:500]:', r.text[:500])
except Exception as e:
    print('Error:', e)

# Test 5: Sina 板块成分股
print('\n=== Sina 板块成分股 ===')
try:
    r = requests.get('https://vip.stock.finance.sina.com.cn/q/go.php/vIndustryRank/kind/bkhy/num/20/indid/BK0477.phtml',
        headers={'User-Agent': 'Mozilla/5.0'},
        timeout=10)
    print('Status:', r.status_code)
except Exception as e:
    print('Error:', e)