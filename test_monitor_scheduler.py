#!/usr/bin/env python3
"""
测试 monitor_realtime_updater.py 调度器
使用短期调度来验证功能
"""
import sys
import os
import time
import schedule
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入实际的更新函数
from monitor_realtime_updater import update_monitor_data

def test_monitor_scheduler():
    """测试监控调度器"""
    print("🧪 Testing monitor_realtime_updater scheduler...")
    print(f"🆔 Process ID: {os.getpid()}")
    print(f"📂 Working directory: {os.getcwd()}")
    print(f"🔑 POLYGON_API_KEY: {'✅ Set' if os.getenv('POLYGON_API_KEY') else '❌ Not set'}")
    
    # 测试：1分钟后运行一次（而不是等到早上6点）
    print("\n📋 Scheduling test run in 1 minute...")
    schedule.every(1).minutes.do(lambda: print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Would run update_monitor_data() here"))
    
    # 也测试实际的更新函数（如果API key存在）
    if os.getenv('POLYGON_API_KEY'):
        print("📋 Scheduling actual update_monitor_data() in 2 minutes...")
        schedule.every(2).minutes.do(update_monitor_data)
    else:
        print("⚠️  POLYGON_API_KEY not set, skipping actual update test")
    
    # 显示所有已调度的任务
    print("\n📅 Scheduled jobs:")
    for job in schedule.jobs:
        print(f"   - {job}")
    
    print("\n🔄 Starting scheduler loop (will run for 3 minutes, then exit)...")
    print("   Press Ctrl+C to stop early\n")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(minutes=3)
    last_heartbeat = start_time
    
    try:
        while datetime.now() < end_time:
            schedule.run_pending()
            
            # 每30秒输出一次心跳
            current_time = datetime.now()
            if (current_time - last_heartbeat).total_seconds() >= 30:
                remaining = (end_time - current_time).total_seconds() / 60
                print(f"[{current_time.strftime('%H:%M:%S')}] 💓 Heartbeat - {remaining:.1f} minutes remaining, {len(schedule.jobs)} jobs scheduled")
                last_heartbeat = current_time
            
            time.sleep(1)  # 每秒检查一次
        
        print(f"\n✅ Test completed successfully!")
        print(f"   Duration: {(datetime.now() - start_time).total_seconds() / 60:.1f} minutes")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_monitor_scheduler()


