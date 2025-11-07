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
mkdir -p logs .pids report_assets strategies signal_optimization monitor_cache

# 检查是否启用调度器
ENABLE_SCHEDULER=${ENABLE_SCHEDULER:-true}

if [ "$ENABLE_SCHEDULER" = "true" ]; then
    echo "🔄 Starting background scheduler (monitor_realtime_updater.py)..."
    echo "📋 Environment: ENABLE_SCHEDULER=$ENABLE_SCHEDULER"
    
    # 在后台启动调度器
    nohup python3 monitor_realtime_updater.py > /tmp/scheduler.log 2>&1 &
    SCHEDULER_PID=$!
    echo "✅ Scheduler started with PID: $SCHEDULER_PID"
    echo "📋 Scheduler logs: /tmp/scheduler.log"
    
    # 等待一下确保进程启动
    sleep 2
    
    # 检查进程是否还在运行
    if kill -0 $SCHEDULER_PID 2>/dev/null; then
        echo "✅ Scheduler is running (PID: $SCHEDULER_PID)"
    else
        echo "⚠️  Warning: Scheduler may have failed to start, check logs:"
        tail -20 /tmp/scheduler.log 2>/dev/null || echo "   (log file not found)"
    fi
    
    # 设置清理函数
    cleanup() {
        echo "🛑 Shutting down scheduler (PID: $SCHEDULER_PID)..."
        kill $SCHEDULER_PID 2>/dev/null || true
        wait $SCHEDULER_PID 2>/dev/null || true
        echo "✅ Scheduler stopped"
    }
    
    # 注册清理函数
    trap cleanup EXIT TERM INT
else
    echo "⏭️  Scheduler disabled (ENABLE_SCHEDULER=false)"
fi

# 启动 Streamlit 应用
echo "🚀 Starting Streamlit application on port $PORT..."
echo "📋 Environment: PORT=$PORT, ENABLE_SCHEDULER=$ENABLE_SCHEDULER"

# 使用 exec 确保 streamlit 成为主进程
exec streamlit run web_app.py \
    --server.port "$PORT" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false

