@echo off
echo 正在设置环境并启动服务...

:: 检查 Python 虚拟环境
if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

:: 激活虚拟环境
call venv\Scripts\activate

:: 升级 pip
python -m pip install --upgrade pip

:: 尝试使用预编译的 wheel 安装 aiohttp
echo 安装 aiohttp...
pip install aiohttp --only-binary :all:

:: 安装其他依赖
echo 安装其他依赖...
pip install fastapi uvicorn python-multipart tencentcloud-sdk-python cos-python-sdk-v5 requests

:: 如果 aiohttp 安装失败，提供说明
pip show aiohttp > nul 2>&1
if errorlevel 1 (
    echo.
    echo ======================================================
    echo aiohttp 安装失败。请按以下步骤操作：
    echo 1. 下载并安装 Visual Studio Build Tools：
    echo    https://aka.ms/vs/17/release/vs_BuildTools.exe
    echo 2. 在安装程序中选择"使用 C++ 的桌面开发"
    echo 3. 安装完成后重新运行此脚本
    echo ======================================================
    echo.
    pause
    exit /b 1
)

:: 启动服务
echo 启动服务...
python -m uvicorn sse_server:app --host 127.0.0.1 --port 8000 --reload

pause
