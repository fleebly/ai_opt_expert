# 故障排查指南

## Polygon API 403 错误

### 错误信息
```
ERROR:backtest_engine:Polygon API returned status 403
```

### 可能的原因

1. **API Key 权限不足**
   - Polygon 免费版不支持期权历史数据
   - 需要 **Starter+ 订阅** 才能访问期权历史数据
   - 解决方案：升级到 Starter+ 计划，或使用估算价格

2. **API Key 无效或过期**
   - API key 可能已过期或被撤销
   - 解决方案：检查并更新 API key

3. **API 配额已用完**
   - 已达到月度/日度 API 调用限制
   - 解决方案：等待配额重置，或升级计划

4. **API Key 配置错误**
   - 环境变量未正确设置
   - 解决方案：检查环境变量配置

### 解决方案

#### 方案1: 检查 API Key

```bash
# 检查环境变量
echo $POLYGON_API_KEY

# 或在 Python 中检查
python3 -c "import os; print('API Key:', os.getenv('POLYGON_API_KEY', 'NOT SET')[:10] + '...')"
```

#### 方案2: 使用估算价格（降级方案）

系统已经内置了降级机制。当遇到 403 错误时，会自动使用估算价格：

- 代码会自动检测 403 错误
- 回退到 Black-Scholes 模型估算期权价格
- 回测可以继续进行，只是使用估算而非真实价格

**注意**: 估算价格可能不如真实价格准确，但足以用于策略回测。

#### 方案3: 升级 Polygon 订阅

如果需要真实期权历史数据：

1. 访问 https://polygon.io/pricing
2. 升级到 **Starter** 或更高计划
3. 更新 API key

#### 方案4: 检查 API Key 状态

```bash
# 测试 API key 是否有效
curl "https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2024-01-01/2024-01-02?apiKey=YOUR_API_KEY"
```

如果返回 403，说明 key 无效或权限不足。

### 系统行为

当遇到 403 错误时：

1. ✅ **自动降级**: 系统会自动使用估算价格
2. ⚠️ **警告日志**: 会记录警告信息，但不中断回测
3. 📊 **继续运行**: 回测会继续使用估算价格完成

### 验证降级是否生效

查看日志输出，应该看到：

```
⚠️ Using estimated price: $X.XX
```

而不是：

```
✅ Found real option price: $X.XX
```

### 其他常见错误

#### ModuleNotFoundError: No module named 'schedule'

```bash
pip3 install schedule
```

#### POLYGON_API_KEY not set

```bash
# 设置环境变量
export POLYGON_API_KEY=your_api_key_here

# 或使用 .env 文件
echo "POLYGON_API_KEY=your_api_key_here" >> .env
```

### 联系支持

如果问题持续存在：

1. 检查 Polygon.io 账户状态
2. 查看 API 使用统计
3. 联系 Polygon.io 支持团队




