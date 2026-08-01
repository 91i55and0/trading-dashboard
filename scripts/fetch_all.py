"""
综合数据采集脚本
依次运行所有数据采集脚本，将结果保存为 JSON 文件
适用于 GitHub Actions 每日定时运行
"""
import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def run_fetch_cboe():
    """运行 CBOE 数据采集"""
    print("\n>>> [1/3] CBOE Put/Call 比率数据采集")
    try:
        import importlib
        spec = importlib.util.spec_from_file_location(
            "fetch_cboe", Path(__file__).parent / "fetch_cboe.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.main()
    except Exception as e:
        print(f"  CBOE 采集失败: {e}")
        return 1


def run_fetch_news():
    """运行新闻数据采集"""
    print("\n>>> [2/3] 新闻/市场事件数据采集")
    try:
        import importlib
        spec = importlib.util.spec_from_file_location(
            "fetch_news", Path(__file__).parent / "fetch_news.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.main()
    except Exception as e:
        print(f"  新闻采集失败: {e}")
        return 1


def generate_manifest():
    """生成数据清单文件"""
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "files": [],
    }

    for f in sorted(DATA_DIR.rglob("*.json")):
        rel = f.relative_to(DATA_DIR.parent)
        manifest["files"].append({
            "path": str(rel.as_posix()),
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })

    with open(DATA_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nOK: 数据清单已生成 ({len(manifest['files'])} 个文件)")


def main():
    print("=" * 50)
    print("综合数据采集")
    print(f"运行时间: {datetime.now().isoformat()}")
    print("=" * 50)

    results = {}
    results["cboe"] = run_fetch_cboe()
    results["news"] = run_fetch_news()

    generate_manifest()

    print("\n" + "=" * 50)
    print("采集结果汇总:")
    for name, code in results.items():
        status = "成功" if code == 0 else "失败"
        print(f"  {name}: {status}")
    print("=" * 50)

    return 0 if all(c == 0 for c in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())