#!/bin/bash

cd "$(dirname "$0")"

echo "================================"
echo "   报告核对工具启动脚本"
echo "================================"
echo ""

# 检查Python后端
echo "[1/3] 检查Python环境..."
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 启动Python后端（后台运行）
echo "[2/3] 启动后端服务..."
cd python_backend
uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

sleep 2

# 启动Electron前端
echo "[3/3] 启动前端界面..."
npm run dev:electron &
FRONTEND_PID=$!

echo ""
echo "================================"
echo "   应用已启动！"
echo "================================"
echo "后端PID: $BACKEND_PID"
echo "前端PID: $FRONTEND_PID"
echo ""
echo "按回车键关闭应用..."
read

# 关闭进程
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
echo "应用已关闭"
