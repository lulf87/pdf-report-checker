#!/bin/bash

cd "$(dirname "$0")"

echo "================================"
echo "   报告核对工具启动脚本"
echo "================================"
echo ""

# 检查Python后端
echo "[1/4] 检查Python环境..."
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 启动Python后端（后台运行）
echo "[2/4] 启动后端服务..."
cd python_backend
uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

sleep 2

# 启动React开发服务器
echo "[3/4] 启动前端渲染服务..."
cd src/renderer
npm run dev &
RENDERER_PID=$!
cd ../..

sleep 3

# 等待服务就绪
echo "[4/4] 等待服务就绪并启动Electron..."
npx wait-on tcp:127.0.0.1:8000 tcp:127.0.0.1:5173 --timeout 30000

# 启动Electron（macOS上确保前台显示）
NODE_ENV=development npx electron . &
ELECTRON_PID=$!

# 给 Electron 一点时间来显示窗口
sleep 2

# 在 macOS 上，尝试将应用带到前台
if [ "$(uname)" = "Darwin" ]; then
    osascript -e 'tell application "报告审核工具" to activate' 2>/dev/null || true
fi

echo ""
echo "================================"
echo "   应用已启动！"
echo "================================"
echo "后端PID: $BACKEND_PID"
echo "渲染器PID: $RENDERER_PID"
echo "Electron PID: $ELECTRON_PID"
echo ""
echo "按回车键关闭应用..."
read

# 关闭进程
echo "正在关闭应用..."
kill $ELECTRON_PID 2>/dev/null
kill $RENDERER_PID 2>/dev/null
kill $BACKEND_PID 2>/dev/null
echo "应用已关闭"
