#!/bin/bash

# 报告核对工具启动脚本
# 可用于 Raycast、Alfred、Terminal 等

APP_PATH="/Users/lulingfeng/Documents/工作/开发/报告核对工具2026.2.9"
cd "$APP_PATH" || exit 1

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "正在安装前端依赖..."
    npm install
fi

if [ ! -d "src/renderer/node_modules" ]; then
    echo "正在安装渲染进程依赖..."
    cd src/renderer && npm install && cd ../..
fi

# 启动应用
echo "启动报告核对工具..."
npm run dev
