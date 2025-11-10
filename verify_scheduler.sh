#!/bin/bash
# 验证调度器功能的脚本

echo "🔍 Verifying scheduler setup..."
echo ""

# 1. 检查 Python 模块
echo "1️⃣  Checking Python dependencies..."
python3 -c "import schedule" 2>/dev/null && echo "   ✅ schedule module available" || echo "   ❌ schedule module missing"

# 2. 检查调度器脚本
echo ""
echo "2️⃣  Checking scheduler script..."
if [ -f "monitor_realtime_updater.py" ]; then
    echo "   ✅ monitor_realtime_updater.py exists"
    python3 -c "import monitor_realtime_updater" 2>/dev/null && echo "   ✅ Script can be imported" || echo "   ❌ Script has import errors"
else
    echo "   ❌ monitor_realtime_updater.py not found"
fi

# 3. 检查环境变量
echo ""
echo "3️⃣  Checking environment variables..."
if [ -n "$POLYGON_API_KEY" ]; then
    echo "   ✅ POLYGON_API_KEY is set"
else
    echo "   ⚠️  POLYGON_API_KEY is not set (scheduler will skip updates)"
fi

if [ -n "$ENABLE_SCHEDULER" ]; then
    echo "   📋 ENABLE_SCHEDULER=$ENABLE_SCHEDULER"
else
    echo "   📋 ENABLE_SCHEDULER not set (will default to true)"
fi

# 4. 检查是否有运行中的调度器进程
echo ""
echo "4️⃣  Checking for running scheduler processes..."
SCHEDULER_PIDS=$(ps aux | grep -i "monitor_realtime_updater" | grep -v grep | awk '{print $2}')
if [ -n "$SCHEDULER_PIDS" ]; then
    echo "   ✅ Scheduler is running (PIDs: $SCHEDULER_PIDS)"
    for pid in $SCHEDULER_PIDS; do
        echo "      - PID $pid: $(ps -p $pid -o command= | head -1)"
    done
else
    echo "   ⚠️  No scheduler process found (not running or not started yet)"
fi

# 5. 检查调度器日志
echo ""
echo "5️⃣  Checking scheduler logs..."
if [ -f "/tmp/scheduler.log" ]; then
    echo "   ✅ Scheduler log file exists"
    echo "   📋 Last 10 lines of log:"
    tail -10 /tmp/scheduler.log | sed 's/^/      /'
else
    echo "   ⚠️  Scheduler log file not found (scheduler may not have run yet)"
fi

# 6. 测试调度器功能
echo ""
echo "6️⃣  Testing scheduler functionality..."
python3 test_scheduler.py > /tmp/scheduler_test.log 2>&1 &
TEST_PID=$!
sleep 15
if ps -p $TEST_PID > /dev/null 2>&1; then
    echo "   ✅ Scheduler test is running (PID: $TEST_PID)"
    echo "   📋 Test output (first 20 lines):"
    head -20 /tmp/scheduler_test.log | sed 's/^/      /'
    kill $TEST_PID 2>/dev/null
    wait $TEST_PID 2>/dev/null
else
    echo "   ⚠️  Scheduler test completed or failed"
    if [ -f "/tmp/scheduler_test.log" ]; then
        echo "   📋 Test output:"
        cat /tmp/scheduler_test.log | sed 's/^/      /'
    fi
fi

echo ""
echo "✅ Verification complete!"
echo ""
echo "💡 To start the scheduler manually:"
echo "   python3 monitor_realtime_updater.py"
echo ""
echo "💡 To test scheduler with a short interval:"
echo "   python3 test_monitor_scheduler.py"


