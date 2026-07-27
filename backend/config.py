"""
交易看板 - 全局配置
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 数据存储目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 回测策略存放目录
STRATEGIES_DIR = BASE_DIR / "strategies"

# AKShare 配置
AKSHARE_CACHE_ENABLED = True
AKSHARE_CACHE_TTL = 300  # 缓存有效期（秒）

# 服务端口
SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.environ.get("PORT", 8000))

# CORS 配置
CORS_ORIGINS = ["*"]

# 市场数据配置
CFTC_REPORT_URL = "https://www.cftc.gov/dea/futures/deacmesf.htm"
CBOE_PUT_CALL_URL = "https://www.cboe.com/us/options/market_statistics/daily/"

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek-V3

# 日志配置
LOG_LEVEL = "INFO"