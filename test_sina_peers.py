"""测试 Sina 板块成分股API"""
import requests
import re

# Test Sina industry board API
print('=== Sina 板块成分股 ===')
try:
    # Sina API for industry board stocks
    r = requests.get('https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData',
        params={
            'page': '1',
            'num': '20',
            'sort': 'symbol',
            'asc': '1',
            'node': 'sw2_340100',  # 白酒行业代码
            'symbol': '',
            '_s_r_a': 'init',
        },
        headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://vip.stock.finance.sina.com.cn/'},
        timeout=15)
    print('Status:', r.status_code)
    print('Content[:1000]:', r.text[:1000])
except Exception as e:
    import traceback
    traceback.print_exc()

# Try another Sina API
print('\n=== Sina 行业排名 ===')
try:
    r = requests.get('https://vip.stock.finance.sina.com.cn/q/go.php/vIndustryRank/kind/bkhy/num/20/indid/BK0477.phtml',
        headers={'User-Agent': 'Mozilla/5.0'},
        timeout=15)
    print('Status:', r.status_code)
    print('Content[:1000]:', r.text[:1000])
except Exception as e:
    print('Error:', e)

# Try East Money 行业板块 成分股 (non-push2 API)
print('\n=== East Money 板块成分股 (EM web) ===')
try:
    r = requests.get('https://emweb.securities.eastmoney.com/PC_HSF10/IndustryAnalysis/Index',
        params={'code': 'SH600519'},
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://emweb.securities.eastmoney.com/',
        },
        timeout=15)
    print('Status:', r.status_code)
    print('Content[:500]:', r.text[:500])
except Exception as e:
    print('Error:', e)