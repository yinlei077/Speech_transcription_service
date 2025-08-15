@echo off
echo 正在启动语音识别服务...

:: 激活虚拟环境
call venv\Scripts\activate

:: 检查是否需要安装依赖
pip show uvicorn > nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install fastapi uvicorn python-multipart aiohttp tencentcloud-sdk-python cos-python-sdk-v5 requests
)

:: 启动服务
python -m uvicorn sse_server:app --host 127.0.0.1 --port 8000 --reload

pause
