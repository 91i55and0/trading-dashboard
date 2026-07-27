"""测试研报生成"""
import requests
import json
import time

symbol = "600519"
market = "A"

print(f"Testing research report for {symbol}...")
start = time.time()
r = requests.post(
    "http://localhost:8000/api/stock/research-report",
    json={"symbol": symbol, "market": market, "deep_analysis": True},
    timeout=120
)
elapsed = time.time() - start
print(f"Status: {r.status_code}, Time: {elapsed:.1f}s")

if r.status_code == 200:
    data = r.json()
    print(f"Name: {data.get('name', '')}")
    report = data.get("report_markdown", "")
    print(f"Report length: {len(report)} chars")
    
    sections = data.get("sections", {})
    fund = sections.get("fundamental", {})
    print(f"\nFundamental keys: {list(fund.keys())}")
    print(f"Has shareholder: {bool(fund.get('shareholder'))}")
    print(f"Has per_capita: {bool(fund.get('per_capita'))}")
    print(f"Has growth_quality: {bool(fund.get('growth_quality'))}")
    print(f"Has financial_anomaly: {bool(fund.get('financial_anomaly'))}")
    
    # Check for new sections
    sections_found = []
    for keyword in ["增长质量", "人均效率", "股东结构", "财务异常", "估值分位"]:
        if keyword in report:
            sections_found.append(keyword)
    print(f"\nNew sections found: {sections_found}")
    
    # Print the report structure (all ### headers)
    for line in report.split("\n"):
        if line.startswith("### "):
            print(f"  {line}")
else:
    print(f"Error: {r.text[:500]}")