import requests

url = 'https://qt.gtimg.cn/q=sh600519,sz000858'
headers = {'User-Agent': 'Mozilla/5.0'}
resp = requests.get(url, headers=headers, timeout=10)
lines = resp.text.strip().split('\n')
for line in lines:
    if '~' not in line:
        continue
    # Extract content between quotes
    idx1 = line.find('"')
    idx2 = line.find('"', idx1 + 1)
    if idx1 >= 0 and idx2 > idx1:
        content = line[idx1+1:idx2]
    else:
        content = line
    fields = content.split('~')
    name = fields[1] if len(fields) > 1 else 'N/A'
    print(f'Name: {name}')
    for i in range(38, 55):
        val = fields[i] if len(fields) > i else 'N/A'
        print(f'  [{i}]: {val}')
    print()