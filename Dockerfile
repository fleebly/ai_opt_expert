# Dockerfile for Option Trading System

FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置 PYTHONPATH 确保能找到所有模块
ENV PYTHONPATH=/app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 先显式复制关键模块目录，确保它们被包含
COPY signal_optimization/ ./signal_optimization/
COPY ai_rl_engine/ ./ai_rl_engine/

# 验证关键模块目录存在
RUN test -d signal_optimization && test -f signal_optimization/__init__.py && test -f signal_optimization/multi_strategy_backtest.py && echo "✅ signal_optimization module found" || (echo "❌ signal_optimization module missing" && exit 1)
RUN test -d ai_rl_engine && test -f ai_rl_engine/__init__.py && echo "✅ ai_rl_engine module found" || (echo "❌ ai_rl_engine module missing" && exit 1)

# 复制应用代码（包括所有其他文件）
COPY . .

# 创建日志目录
RUN mkdir -p logs .pids

# 暴露端口（Railway 会通过 $PORT 环境变量动态分配）
EXPOSE 8080

# 启动脚本
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

# 健康检查使用环境变量 PORT
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/_stcore/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]




