"""测试腾讯API同行数据"""
import requests
import json

headers = {"User-Agent": "Mozilla/5.0"}
codes = ["sz002594", "sz300014", "sz002074", "sz300207", "sh688063"]
url = "https://qt.gtimg.cn/q=" + ",".join(codes)
r = requests.get(url, headers=headers, timeout=10)
lines = r.text.strip().split("\n")
print(f"Total lines: {len(lines)}")

for i, line in enumerate(lines):
    if "~" not in line:
        continue
    parts = line.split('"')[1] if '"' in line else line
    fields = parts.split("~")
    print(f"\nLine {i}: {len(fields)} fields")
    print(f"  [1] name: {fields[1] if len(fields) > 1 else 'N/A'}")
    print(f"  [2] code: {fields[2] if len(fields) > 2 else 'N/A'}")
    print(f"  [39] PE: {fields[39] if len(fields) > 39 else 'N/A'}")
    print(f"  [43] EPS?: {fields[43] if len(fields) > 43 else 'N/A'}")
    print(f"  [44] mcap: {fields[44] if len(fields) > 44 else 'N/A'}")
    print(f"  [45] circ_mcap: {fields[45] if len(fields) > 45 else 'N/A'}")
    print(f"  [46] PB: {fields[46] if len(fields) > 46 else 'N/A'}")
    # Print all fields for debugging
    if len(fields) > 44:
        print(f"  [44] raw={fields[44]}, [45] raw={fields[45]}, [46] raw={fields[46]}")