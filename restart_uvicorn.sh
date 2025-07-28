#!/bin/bash
echo "正在停止所有 uvicorn 进程..."
pkill -f "uvicorn app.main:app"

sleep 2

echo "正在重新启动 uvicorn..."
cd /opt/setAImodel
source .venv/bin/activate
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 > uvicorn.log 2>&1 &

echo "完成 ✅"
