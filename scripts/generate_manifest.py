"""生成数据清单文件 manifest.json"""
import json
import datetime
from pathlib import Path

data_dir = Path('data')
manifest = {
    'generated_at': datetime.datetime.now().isoformat(),
    'date': datetime.datetime.now().strftime('%Y-%m-%d'),
    'files': [],
}
for f in sorted(data_dir.rglob('*.json')):
    manifest['files'].append({
        'path': str(f.as_posix()),
        'size': f.stat().st_size,
        'modified': datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
    })
with open(data_dir / 'manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)
print(f'数据清单已生成: {len(manifest["files"])} 个文件')