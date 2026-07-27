import requests
import json

url = "https://datacenter.eastmoney.com/api/data/v1/get"
params = {
    "reportName": "RPT_DMSK_FN_MAININDICATOR",
    "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,REPORT_DATE,BASIC_EPS,WEIGHTAVG_ROE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,GROSS_PROFIT_RATIO,NET_PROFIT_RATIO,OPERATE_INCOME_YOY,NETPROFIT_YOY,TOTAL_MARKET_CAP,PE_TTM_WEIGHT,PB_WEIGHT,INDUSTRY_NAME",
    "filter": '(SECURITY_TYPE_CODE="058001001")(SECURITY_CODE="600519")',
    "pageNumber": 1,
    "pageSize": 4,
    "sortTypes": -1,
    "sortColumns": "REPORT_DATE",
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}

try:
    r = requests.get(url, params=params, headers=headers, timeout=15)
    print("Status:", r.status_code)
    data = r.json()
    print("Success:", data.get("success"))
    result = data.get("result")
    if result and result.get("data"):
        records = result["data"]
        print("Record count:", len(records))
        for rec in records[:2]:
            print("  Code:", rec.get("SECURITY_CODE"))
            print("  Name:", rec.get("SECURITY_NAME_ABBR"))
            print("  Date:", rec.get("REPORT_DATE"))
            print("  PE:", rec.get("PE_TTM_WEIGHT"))
            print("  PB:", rec.get("PB_WEIGHT"))
            print("  ROE:", rec.get("WEIGHTAVG_ROE"))
            print("  MarketCap:", rec.get("TOTAL_MARKET_CAP"))
            print("  Revenue YoY:", rec.get("OPERATE_INCOME_YOY"))
            print("  Profit YoY:", rec.get("NETPROFIT_YOY"))
            print("  GrossMargin:", rec.get("GROSS_PROFIT_RATIO"))
            print("  NetMargin:", rec.get("NET_PROFIT_RATIO"))
            print("  Industry:", rec.get("INDUSTRY_NAME"))
            print("---")
    else:
        print("No data or result is None")
        print("Response:", json.dumps(data, ensure_ascii=False)[:500])
except Exception as e:
    print("Error:", type(e).__name__, e)