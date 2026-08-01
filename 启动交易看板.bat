@echo off
chcp 65001 >nul 2>&1
title Trading Dashboard
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo   交易看板 - 启动中...
echo ============================================
echo.

REM ===== 1. 检查 Python =====
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 并添加到 PATH
    pause
    exit /b 1
)
for /f "delims=" %%i in ('where python') do set "PYTHON_EXE=%%i"
echo [OK] Python: !PYTHON_EXE!

REM ===== 2. 检查 Python 关键依赖 =====
echo [检查] 验证 Python 依赖...
python -c "import uvicorn, fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] Python 依赖缺失，正在安装...
    pip install uvicorn fastapi pydantic httpx python-multipart aiofiles matplotlib plotly scipy ta backtrader beautifulsoup4 lxml requests -q
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败，请手动运行: pip install -r backend\requirements.txt
        pause
        exit /b 1
    )
    echo [OK] 依赖安装完成
) else (
    echo [OK] Python 依赖已就绪
)

REM ===== 3. 检查 Node.js =====
set NODE_EXE=
set NODE_FOUND=0

where node >nul 2>&1
if %errorlevel% equ 0 (
    for /f "delims=" %%i in ('where node') do set "NODE_EXE=%%i"
    set NODE_FOUND=1
)

REM 如果 PATH 中找不到，尝试 TRAE IDE 内置的 Node.js
if %NODE_FOUND% equ 0 (
    set "TRAE_NODE=%APPDATA%\TRAE SOLO CN\ModularData\ai-agent\vm\tools\node"
    if exist "!TRAE_NODE!\node.exe" (
        set "NODE_EXE=!TRAE_NODE!\node.exe"
        set "PATH=!TRAE_NODE!;!PATH!"
        set NODE_FOUND=1
        echo [OK] 使用 TRAE IDE 内置 Node.js
    )
)

REM 尝试 WorkBuddy 内置 Node.js
if %NODE_FOUND% equ 0 (
    set "WB_NODE=%USERPROFILE%\.workbuddy\binaries\node\versions\22.12.0"
    if exist "!WB_NODE!\node.exe" (
        set "NODE_EXE=!WB_NODE!\node.exe"
        set "PATH=!WB_NODE!;!PATH!"
        set NODE_FOUND=1
        echo [OK] 使用 WorkBuddy 内置 Node.js
    )
)

if %NODE_FOUND% equ 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 并添加到 PATH
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js: !NODE_EXE!

REM ===== 4. 检查前端依赖 =====
if not exist "frontend\node_modules" (
    echo [警告] 前端依赖未安装，正在安装...
    cd frontend
    call "!NODE_EXE!" node_modules\npm\bin\npm-cli.js install 2>&1
    cd ..
    if not exist "frontend\node_modules" (
        echo [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
    echo [OK] 前端依赖安装完成
) else (
    echo [OK] 前端依赖已就绪
)

echo.

REM ===== 5. 清理旧进程 =====
echo [清理] 检查并关闭旧进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    echo [清理] 已关闭端口 8000 上的旧进程 (PID %%a)
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
    echo [清理] 已关闭端口 5173 上的旧进程 (PID %%a)
)
echo.

REM ===== 6. 防火墙放行（首次需管理员权限） =====
netsh advfirewall firewall show rule name="Trading Dashboard 5173" >nul 2>&1
if %errorlevel% neq 0 (
    echo [设置] 配置防火墙放行端口 5173 和 8000...
    netsh advfirewall firewall add rule name="Trading Dashboard 5173" dir=in action=allow protocol=TCP localport=5173 >nul 2>&1
    netsh advfirewall firewall add rule name="Trading Dashboard 8000" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1
)

REM ===== 7. 启动后端（使用绝对路径） =====
echo [1/2] 启动后端服务 (端口 8000)...
start "Backend" cmd /k ""!PYTHON_EXE!" "%~dp0backend\main.py" 2>&1"

REM 等待后端就绪（最多等30秒）
echo 等待后端就绪...
set /a retry=0
:wait_backend
timeout /t 2 /nobreak >nul
set /a retry+=1
python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 后端已就绪 (耗时 !retry!x2秒^)
    goto backend_ready
)
if %retry% lss 15 goto wait_backend
echo [警告] 后端可能启动失败，请检查 Backend 窗口的错误信息
echo 仍将继续启动前端...
:backend_ready

REM ===== 8. 启动前端（切换到 frontend 目录再启动） =====
echo [2/2] 启动前端服务 (端口 5173)...
start "Frontend" cmd /k "cd /d %~dp0frontend && !NODE_EXE! node_modules\vite\bin\vite.js --host 0.0.0.0 2>&1"

REM 等待前端就绪（最多等15秒）
echo 等待前端就绪...
set /a retry=0
:wait_frontend
timeout /t 2 /nobreak >nul
set /a retry+=1
python -c "import urllib.request; urllib.request.urlopen('http://localhost:5173')" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 前端已就绪 (耗时 !retry!x2秒^)
    goto frontend_ready
)
if %retry% lss 8 goto wait_frontend
echo [警告] 前端可能启动失败，请检查 Frontend 窗口的错误信息
:frontend_ready

REM ===== 9. 获取局域网IP =====
for /f "tokens=3 delims=: " %%i in ('netsh int ip show address ^| findstr "IP地址" ^| findstr /v "10.10" ^| findstr /v "169.254"') do set "LAN_IP=%%i"
if "!LAN_IP!"=="" for /f "tokens=3 delims=: " %%i in ('netsh int ip show address ^| findstr "IP地址"') do set "LAN_IP=%%i"

REM ===== 10. 打开浏览器 =====
start http://localhost:5173

echo.
echo ============================================
echo   启动完成！
echo   本机: http://localhost:5173
echo   手机: http://!LAN_IP!:5173
echo   （手机需连接同一WiFi）
echo ============================================
echo.
pause