#!/bin/bash

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或使用：
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务器
uvicorn sse_server:app --host 0.0.0.0 --port 8000 --reload
