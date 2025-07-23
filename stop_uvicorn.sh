#!/bin/bash

echo "正在查找 uvicorn 进程..."

PIDS=$(ps aux | grep uvicorn | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "未找到 uvicorn 进程。"
else
    echo "找到 uvicorn 进程 PID: $PIDS，准备终止..."
    for PID in $PIDS; do
        kill -9 "$PID" && echo "✅ 已终止 PID: $PID"
    done
fi
