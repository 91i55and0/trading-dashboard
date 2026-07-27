"""
量化回测路由
"""
import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
import json

router = APIRouter()


class BacktestRequest(BaseModel):
    """回测请求"""
    strategy_name: str
    symbol: str
    market: str = "A"
    start_date: str = "2024-01-01"
    end_date: str = "2025-12-31"
    initial_capital: float = 100000.0
    commission: float = 0.0003
    params: Optional[dict] = None


class CodeSaveRequest(BaseModel):
    """保存策略代码请求"""
    name: str
    code: str
    overwrite: bool = False


class CodeRunRequest(BaseModel):
    """直接运行代码回测请求"""
    code: str
    symbol: str
    market: str = "A"
    start_date: str = "2024-01-01"
    end_date: str = "2025-12-31"
    initial_capital: float = 100000.0
    commission: float = 0.0003


class MultiSymbolRunRequest(BaseModel):
    """多股票回测请求"""
    strategy_name: str
    symbols: list  # 股票代码列表
    market: str = "A"
    start_date: str = "2024-01-01"
    end_date: str = "2025-12-31"
    initial_capital: float = 100000.0
    commission: float = 0.0003
    params: Optional[dict] = None


class MultiSymbolCodeRunRequest(BaseModel):
    """多股票代码直接运行请求"""
    code: str
    symbols: list
    market: str = "A"
    start_date: str = "2024-01-01"
    end_date: str = "2025-12-31"
    initial_capital: float = 100000.0
    commission: float = 0.0003


class AIRequest(BaseModel):
    """AI 生成策略提示词请求"""
    description: str
    symbol: str = ""
    market: str = "A"


@router.get("/strategies")
def list_strategies():
    """获取可用的回测策略列表（含代码预览）"""
    from services.backtest_service import STRATEGIES_DIR

    strategies = []
    if os.path.exists(STRATEGIES_DIR):
        for f in os.listdir(STRATEGIES_DIR):
            if f.endswith(".py") and not f.startswith("_"):
                name = f.replace(".py", "")
                file_path = os.path.join(STRATEGIES_DIR, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as fh:
                        code = fh.read()
                    preview = code[:200] + ("..." if len(code) > 200 else "")
                    is_backtrader = "import backtrader" in code or "from backtrader" in code
                except Exception:
                    preview = ""
                    is_backtrader = False

                strategies.append({
                    "name": name,
                    "file": f,
                    "preview": preview,
                    "engine": "backtrader" if is_backtrader else "signal",
                    "size": len(code) if preview else 0,
                })
    return {"strategies": strategies}


@router.get("/strategies/{strategy_name}/code")
def get_strategy_code(strategy_name: str):
    """获取策略源代码"""
    from services.backtest_service import STRATEGIES_DIR

    file_path = os.path.join(STRATEGIES_DIR, f"{strategy_name}.py")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="策略文件不存在")

    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()

    return {"name": strategy_name, "code": code}


@router.post("/strategies/save")
def save_strategy_code(req: CodeSaveRequest):
    """保存策略代码（文本方式）"""
    from services.backtest_service import STRATEGIES_DIR

    os.makedirs(STRATEGIES_DIR, exist_ok=True)

    safe_name = req.name.replace(".py", "").replace("/", "_").replace("\\", "_")
    file_path = os.path.join(STRATEGIES_DIR, f"{safe_name}.py")

    if os.path.exists(file_path) and not req.overwrite:
        raise HTTPException(status_code=409, detail=f"策略 '{safe_name}' 已存在，设置 overwrite=true 覆盖")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(req.code)

    return {"status": "ok", "name": safe_name, "message": f"策略 '{safe_name}' 已保存"}


@router.post("/run")
def run_backtest(req: BacktestRequest):
    """执行回测（从已保存的策略）"""
    from services.backtest_service import run_backtest_service
    try:
        result = run_backtest_service(
            strategy_name=req.strategy_name,
            symbol=req.symbol,
            market=req.market,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            commission=req.commission,
            params=req.params,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-code")
def run_code_backtest(req: CodeRunRequest):
    """直接传入代码字符串执行回测"""
    from services.backtest_service import run_code_backtest
    try:
        result = run_code_backtest(
            code=req.code,
            symbol=req.symbol,
            market=req.market,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            commission=req.commission,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-multi")
def run_multi_symbol_backtest(req: MultiSymbolRunRequest):
    """多股票组合回测（从已保存的策略）"""
    from services.backtest_service import run_multi_symbol_backtest
    try:
        result = run_multi_symbol_backtest(
            strategy_name=req.strategy_name,
            symbols=req.symbols,
            market=req.market,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            commission=req.commission,
            params=req.params,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-multi-code")
def run_multi_code_backtest(req: MultiSymbolCodeRunRequest):
    """直接传入代码字符串执行多股票回测"""
    from services.backtest_service import run_multi_code_backtest
    try:
        result = run_multi_code_backtest(
            code=req.code,
            symbols=req.symbols,
            market=req.market,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            commission=req.commission,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-prompt")
def generate_ai_prompt(req: AIRequest):
    """生成 AI 策略开发提示词（用于复制到 TRAE）"""
    from services.backtest_service import format_ai_prompt

    prompt = format_ai_prompt(
        description=req.description,
        symbol=req.symbol,
        market=req.market,
    )

    return {
        "prompt": prompt,
        "description": req.description,
        "market": req.market,
        "symbol": req.symbol,
    }


@router.post("/strategies/upload")
async def upload_strategy(file: UploadFile = File(...)):
    """上传自定义回测策略（文件方式）"""
    from services.backtest_service import STRATEGIES_DIR

    os.makedirs(STRATEGIES_DIR, exist_ok=True)

    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="只支持 .py 文件")

    file_path = os.path.join(STRATEGIES_DIR, file.filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {"status": "ok", "filename": file.filename, "message": "策略上传成功"}


@router.delete("/strategies/{strategy_name}")
def delete_strategy(strategy_name: str):
    """删除策略文件"""
    from services.backtest_service import STRATEGIES_DIR

    file_path = os.path.join(STRATEGIES_DIR, f"{strategy_name}.py")
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "ok", "message": f"策略 {strategy_name} 已删除"}
    raise HTTPException(status_code=404, detail="策略不存在")