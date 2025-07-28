#!/bin/bash

#ps aux | grep uvicorn

PORT=8000

echo "🔍 查找占用 $PORT 端口的进程..."
PID=$(lsof -i :$PORT -t)

if [ -n "$PID" ]; then
    echo "⛔ 结束进程 PID: $PID"
    kill $PID
    sleep 1
else
    echo "✅ 没有占用 $PORT 端口的进程"
fi

echo "🚀 启动 uvicorn..."
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload > /tmp/log.txt 2>&1 &
