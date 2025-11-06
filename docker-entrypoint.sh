#!/bin/bash
set -e

# 设置默认端口（Railway 会通过 $PORT 环境变量提供）
PORT=${PORT:-8501}

# 验证端口是数字
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "❌ Error: PORT must be a number, got: $PORT"
    exit 1
fi

# 创建必要的目录
mkdir -p logs .pids report_assets strategies signal_optimization

# 启动 Streamlit 应用
echo "🚀 Starting Streamlit application on port $PORT..."
echo "📋 Environment: PORT=$PORT"

# 使用 exec 确保 streamlit 成为主进程
exec streamlit run web_app.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false

