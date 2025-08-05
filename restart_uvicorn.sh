#!/bin/bash

echo "🔧 正在停止所有 uvicorn 进程..."
pkill -f "uvicorn app.main:app"

sleep 2

# 检查是否还残留有 uvicorn 进程
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "⚠️ 进程未完全退出，强制终止中..."
    pkill -9 -f "uvicorn app.main:app"
fi

echo "🚀 正在重新启动 uvicorn..."

cd /opt/setAImodel || { echo "❌ 目录不存在，退出"; exit 1; }

# 启动虚拟环境
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "❌ 找不到虚拟环境，退出"
    exit 1
fi

# 启动服务
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

