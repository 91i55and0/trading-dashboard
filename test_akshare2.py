"""测试 AKShare 不同数据源和配置"""
import requests
import json

# 1. 测试东方财富 API 直接访问
print("=== 1. 东方财富 API ===")
em_urls = [
    # 实时行情
    "https://push2.eastmoney.com/api/qt/stock/get",
    # 历史行情
    "https://push2his.eastmoney.com/api/qt/stock/kline/get",
    # 数据中心
    "https://datacenter.eastmoney.com/api/data/v1/get",
]
for url in em_urls:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/',
        }
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  {url}: Status={r.status_code}, Len={len(r.text)}")
    except Exception as e:
        print(f"  {url}: Error={type(e).__name__}: {str(e)[:100]}")

# 2. 测试东方财富历史K线 API
print("\n=== 2. 东方财富 K线 API ===")
try:
    params = {
        "secid": "0.000001",
        "ut": "fa5fd1943c7b386f172d6893dbfb1d6f",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "beg": "20260101",
        "end": "20260725",
        "lmt": "100",
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/',
    }
    r = requests.get(
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        params=params,
        headers=headers,
        timeout=15
    )
    print(f"  Status: {r.status_code}, Len: {len(r.text)}")
    if r.status_code == 200:
        data = r.json()
        if data.get('data') and data['data'].get('klines'):
            print(f"  Klines: {len(data['data']['klines'])} rows")
            print(f"  Last: {data['data']['klines'][-1]}")
        else:
            print(f"  Response: {json.dumps(data, ensure_ascii=False)[:500]}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {str(e)[:100]}")

# 3. 测试新浪财经 API
print("\n=== 3. 新浪财经 API ===")
sina_urls = [
    "https://hq.sinajs.cn/list=sh000001",
    "https://hq.sinajs.cn/list=sz000001",
]
for url in sina_urls:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn/',
        }
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  {url}: Status={r.status_code}, Len={len(r.text)}")
        if r.status_code == 200:
            print(f"    Content: {r.text[:200]}")
    except Exception as e:
        print(f"  {url}: Error={type(e).__name__}: {str(e)[:100]}")

# 4. 尝试 AKShare 使用不同的数据源
print("\n=== 4. AKShare 不同数据源 ===")
try:
    import akshare as ak
    
    # 尝试使用腾讯数据源
    try:
        df = ak.stock_zh_a_hist_tx(symbol="sz000001", start_date="20260701", end_date="20260725")
        print(f"  Tencent source: {len(df)} rows")
    except Exception as e:
        print(f"  Tencent source error: {type(e).__name__}: {str(e)[:100]}")
    
    # 尝试使用新浪数据源
    try:
        df = ak.stock_zh_a_daily(symbol="sz000001", start_date="20260701", end_date="20260725", adjust="qfq")
        print(f"  Sina source: {len(df)} rows")
    except Exception as e:
        print(f"  Sina source error: {type(e).__name__}: {str(e)[:100]}")
    
    # 尝试获取指数数据
    try:
        df = ak.stock_zh_index_daily(symbol="sh000001")
        print(f"  Index daily: {len(df)} rows")
    except Exception as e:
        print(f"  Index daily error: {type(e).__name__}: {str(e)[:100]}")
        
except ImportError:
    print("  AKShare not installed")

# 5. 测试通达信数据接口
print("\n=== 5. 通达信/同花顺/其他数据源 ===")
# 测试腾讯行情
try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    r = requests.get(
        "https://qt.gtimg.cn/q=sz000001",
        headers=headers,
        timeout=10
    )
    print(f"  腾讯行情: Status={r.status_code}, Len={len(r.text)}")
    if r.status_code == 200:
        print(f"    Content: {r.text[:200]}")
except Exception as e:
    print(f"  腾讯行情 error: {type(e).__name__}: {str(e)[:100]}")

# 6. 测试 efinance
print("\n=== 6. efinance ===")
try:
    import efinance as ef
    print(f"  efinance available")
    try:
        df = ef.stock.get_quote_history('000001', beg='20260701', end='20260725')
        print(f"  efinance quote: {len(df)} rows")
    except Exception as e:
        print(f"  efinance error: {type(e).__name__}: {str(e)[:100]}")
except ImportError:
    print("  efinance not installed")