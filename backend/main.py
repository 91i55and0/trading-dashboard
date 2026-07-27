"""
交易看板 - FastAPI 主入口
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import SERVER_HOST, SERVER_PORT, CORS_ORIGINS, BASE_DIR
from routers import backtest, market, stock_analysis, news, provider

app = FastAPI(
    title="交易看板 API",
    description="量化回测、市场数据看板、个股分析、新闻推送",
    version="1.0.0",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(backtest.router, prefix="/api/backtest", tags=["量化回测"])
app.include_router(market.router, prefix="/api/market", tags=["市场数据"])
app.include_router(stock_analysis.router, prefix="/api/stock", tags=["个股分析"])
app.include_router(news.router, prefix="/api/news", tags=["新闻推送"])
app.include_router(provider.router, prefix="/api/provider", tags=["数据源管理"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "交易看板"}


# 前端静态文件 (SPA fallback)
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback: 所有非API请求返回 index.html"""
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "Frontend not built"}


if __name__ == "__main__":
    import os
    is_dev = os.environ.get("ENV", "dev") == "dev"
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=is_dev,
        log_level="info",
    )