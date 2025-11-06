#!/bin/bash
set -e

# 设置默认端口（Railway 会通过 $PORT 环境变量提供）
PORT=${PORT:-8501}

# 创建必要的目录
mkdir -p logs .pids report_assets strategies signal_optimization

# 启动 Streamlit 应用
echo "🚀 Starting Streamlit application on port $PORT..."
exec streamlit run web_app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false

