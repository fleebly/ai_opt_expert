# Real-time Strategy Monitor 实时功能说明

## 功能概述

实现了类似 RockAlpha (https://rockalpha.rockflow.ai/ai-stock) 的实时监控功能，包括：

1. **后台定时任务**：每15分钟自动从POLYGON获取最新数据并更新收益
2. **前端实时刷新**：自动检测数据更新并刷新显示
3. **气泡闪烁效果**：数值变化时的视觉反馈动画
4. **实时状态指示器**：LIVE徽章和脉冲动画

## 使用方法

### 1. 启动后台定时任务

```bash
# 方式1: 持续运行（每15分钟自动更新）
python3 monitor_realtime_updater.py

# 方式2: 只运行一次（测试用）
python3 monitor_realtime_updater.py --once
```

后台任务会：
- 每15分钟从POLYGON API获取最新15分钟数据
- 运行回测更新策略收益
- 将结果写入 `monitor_results.json` 文件
- 同时更新缓存系统

### 2. 启动前端服务

```bash
streamlit run web_app.py
```

前端会自动：
- 检测 `monitor_results.json` 文件的更新
- 每15秒检查一次（如果文件最近更新过）
- 自动刷新页面显示最新数据
- 显示实时状态指示器和动画效果

### 3. 前端功能

#### 实时刷新开关
- 页面顶部有 "🔄 Auto Refresh" 复选框
- 开启后会自动检测数据更新并刷新
- 关闭后停止自动刷新

#### 实时状态指示
- **LIVE徽章**：绿色渐变背景，带脉冲动画
- **脉冲圆点**：每个策略卡片上的绿色圆点，持续闪烁
- **数值变化动画**：数值更新时会有绿色/红色闪烁效果

#### 总资产显示
- 显示所有策略的总资产价值
- 实时显示变化金额和百分比
- 绿色表示上涨，红色表示下跌

## 技术实现

### 后台任务 (`monitor_realtime_updater.py`)

- 使用 `schedule` 库实现定时任务
- 每15分钟执行一次数据更新
- 读取策略文件，运行回测，更新缓存和结果文件

### 前端实时刷新 (`web_app.py`)

- 使用 `st.rerun()` 和 `time.sleep()` 实现自动刷新
- 检测文件修改时间判断是否有新数据
- 使用CSS动画实现气泡闪烁效果

### CSS动画效果

1. **脉冲动画** (`.realtime-indicator`): 绿色圆点持续缩放和阴影扩散
2. **数值变化动画** (`.value-updated`): 数值更新时的背景闪烁
3. **LIVE徽章动画** (`.live-badge .pulse-dot`): 徽章内小点的脉冲效果

## 部署建议

### 本地开发

1. 在一个终端运行后台任务：
   ```bash
   python3 monitor_realtime_updater.py
   ```

2. 在另一个终端运行前端：
   ```bash
   streamlit run web_app.py
   ```

### 生产环境

可以使用 `systemd` 或 `supervisor` 管理后台任务：

```ini
[program:monitor_updater]
command=/usr/bin/python3 /path/to/monitor_realtime_updater.py
directory=/path/to/ai_opt_expert
autostart=true
autorestart=true
stderr_logfile=/var/log/monitor_updater.err.log
stdout_logfile=/var/log/monitor_updater.out.log
```

或者使用 `cron`：

```bash
# 每15分钟运行一次
*/15 * * * * cd /path/to/ai_opt_expert && /usr/bin/python3 monitor_realtime_updater.py --once
```

## 注意事项

1. **API限制**：确保POLYGON API有足够的调用配额
2. **性能**：回测可能需要一些时间，建议在非交易时间进行完整回测
3. **数据准确性**：15分钟数据可能不是实时的，取决于POLYGON数据更新频率
4. **资源消耗**：持续运行会消耗计算资源，建议监控服务器负载

## 故障排查

### 后台任务不更新

1. 检查POLYGON_API_KEY环境变量
2. 查看任务日志输出
3. 确认策略文件存在且格式正确

### 前端不刷新

1. 检查 `monitor_results.json` 文件是否存在
2. 确认文件权限可读
3. 检查浏览器控制台是否有错误
4. 确认 "Auto Refresh" 开关已开启



