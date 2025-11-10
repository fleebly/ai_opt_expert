#!/usr/bin/env python3
"""
测试调度器功能
"""
import sys
import os
import time
import schedule
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_job():
    """测试任务"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Test job executed successfully!")
    return True

def test_scheduler():
    """测试调度器"""
    print("🧪 Testing scheduler functionality...")
    print(f"🆔 Process ID: {os.getpid()}")
    print(f"📂 Working directory: {os.getcwd()}")
    
    # 测试1: 立即运行一次
    print("\n📋 Test 1: Schedule a job to run in 10 seconds...")
    schedule.every(10).seconds.do(test_job)
    
    # 测试2: 每分钟运行（用于验证）
    print("📋 Test 2: Schedule a job to run every minute...")
    schedule.every(1).minutes.do(test_job)
    
    # 显示所有已调度的任务
    print("\n📅 Scheduled jobs:")
    for job in schedule.jobs:
        print(f"   - {job}")
    
    print("\n🔄 Starting scheduler loop (will run for 90 seconds, then exit)...")
    print("   Press Ctrl+C to stop early\n")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=90)
    last_heartbeat = start_time
    
    try:
        while datetime.now() < end_time:
            schedule.run_pending()
            
            # 每30秒输出一次心跳
            current_time = datetime.now()
            if (current_time - last_heartbeat).total_seconds() >= 30:
                remaining = (end_time - current_time).total_seconds()
                print(f"[{current_time.strftime('%H:%M:%S')}] 💓 Heartbeat - {remaining:.0f}s remaining, {len(schedule.jobs)} jobs scheduled")
                last_heartbeat = current_time
            
            time.sleep(1)  # 每秒检查一次
        
        print(f"\n✅ Test completed successfully!")
        print(f"   Duration: {(datetime.now() - start_time).total_seconds():.0f} seconds")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_scheduler()

