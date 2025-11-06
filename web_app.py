#!/usr/bin/env python3
"""
量化交易策略管理 Web 应用

基于 run_iterative_optimization.py 和 strategy_scanner.py 的核心功能
提供可读、可写、可选、可看的完整界面

运行方式:
streamlit run web_app.py
"""

import streamlit as st
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime
import time
import subprocess
import sys
import threading
import queue
from io import StringIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from backtest_engine import OptionBacktest

# 页面配置
st.set_page_config(
    page_title="量化交易策略管理平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapse sidebar by default since we're moving navigation to top
)

# 自定义 CSS - Updated to match RockAlpha design with top navigation
st.markdown("""
<style>
    /* RockAlpha-inspired dark theme with purple gradients */
    body {
        background: linear-gradient(135deg, #0A0A12 0%, #0F0F1A 100%);
        color: #EAEAEA;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    }
    
    /* Top navigation bar - Fixed at top */
    .top-nav {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        padding: 1rem 2rem;
        border-bottom: 1px solid rgba(161, 0, 255, 0.2);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        width: 100%;
        z-index: 999;
        display: flex;
        justify-content: space-between;
        align-items: center;
        backdrop-filter: blur(10px);
    }
    
    /* Add padding to body to account for fixed nav (no Streamlit header) */
    .main .block-container {
        padding-top: 6rem !important;
    }
    
    /* Adjust top padding since Streamlit header is hidden */
    #MainMenu {
        visibility: hidden;
    }
    
    /* Hide Streamlit footer */
    footer[data-testid='stFooter'] {
        display: none !important;
    }
    
    .nav-title {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(to right, #A100FF, #632BFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    
    .nav-links {
        display: flex;
        gap: 1.5rem;
    }
    
    .nav-link {
        color: #B0B0C0 !important;
        text-decoration: none !important;
        font-weight: 500;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        transition: all 0.3s ease;
        font-size: 1rem;
        border: none !important;
        border-bottom: none !important;
        outline: none !important;
        background: transparent !important;
        cursor: pointer !important;
        font-family: inherit !important;
    }
    
    .nav-link:hover {
        color: #FFFFFF !important;
        background: rgba(161, 0, 255, 0.1) !important;
        text-decoration: none !important;
        border-bottom: none !important;
    }
    
    .nav-link.active {
        color: #FFFFFF !important;
        background: linear-gradient(135deg, #A100FF 0%, #632BFF 100%) !important;
        text-decoration: none !important;
        border-bottom: none !important;
    }
    
    /* Remove any underline from nav links */
    .nav-link:visited,
    .nav-link:active,
    .nav-link:focus {
        text-decoration: none !important;
        border-bottom: none !important;
        outline: none !important;
    }
    
    /* Main header with RockAlpha gradient */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(to right, #A100FF, #632BFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 2rem 0;
        text-align: center;
    }
    
    /* Metric cards with dark theme */
    .metric-card {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        border: 1px solid rgba(161, 0, 255, 0.2);
    }
    
    /* Success messages */
    .success-box {
        background: linear-gradient(135deg, #0f3b39 0%, #1a5e5a 100%);
        border-left: 4px solid #38ef7d;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: #38ef7d;
    }
    
    /* Warning messages */
    .warning-box {
        background: linear-gradient(135deg, #3b361f 0%, #5e551a 100%);
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: #ffc107;
    }
    
    /* Error messages */
    .error-box {
        background: linear-gradient(135deg, #3b1f24 0%, #5e2a35 100%);
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: #dc3545;
    }
    
    /* Hide Streamlit default header and deploy button */
    header[data-testid='stHeader'] {
        display: none !important;
    }
    
    /* Hide deploy button */
    .stDeployButton {
        display: none !important;
    }
    
    /* Hide Streamlit menu button */
    button[data-testid='baseButton-header'] {
        display: none !important;
    }
    
    /* Hide Streamlit toolbar */
    [data-testid='stToolbar'] {
        display: none !important;
    }
    
    /* Hide Streamlit header actions */
    [data-testid='stHeader'] > div {
        display: none !important;
    }
    
    /* Sidebar styling - hidden since we moved navigation to top */
    [data-testid='stSidebar'] {
        display: none;
    }
    
    /* Main content area */
    .main {
        background: linear-gradient(135deg, #0A0A12 0%, #0F0F1A 100%);
        padding-top: 1rem;
    }
    
    /* Dataframe styling */
    [data-testid='stDataFrame'] {
        background: #1A1A2E;
        border-radius: 8px;
        border: 1px solid rgba(161, 0, 255, 0.1);
    }
    
    /* Buttons */
    button {
        background: linear-gradient(135deg, #A100FF 0%, #632BFF 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    }
    
    button:hover {
        background: linear-gradient(135deg, #B42AFF 0%, #7A3CFF 100%) !important;
        transform: translateY(-2px);
        transition: all 0.2s ease;
    }
    
    /* Input fields */
    input, select, textarea {
        background: #1A1A2E !important;
        border: 1px solid rgba(161, 0, 255, 0.3) !important;
        border-radius: 8px !important;
        color: #EAEAEA !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif !important;
    }
    
    input:focus, select:focus, textarea:focus {
        border: 1px solid #A100FF !important;
        box-shadow: 0 0 0 2px rgba(161, 0, 255, 0.2) !important;
    }
    
    /* Metrics */
    [data-testid='stMetricValue'] {
        color: #A100FF !important;
        font-weight: bold;
    }
    
    [data-testid='stMetricDelta'] {
        color: #38ef7d !important;
    }
    
    /* Expander */
    [data-testid='stExpander'] {
        background: #1A1A2E;
        border-radius: 8px;
        border: 1px solid rgba(161, 0, 255, 0.1);
    }
    
    [data-testid='stExpander'] div:first-child {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        border-radius: 8px 8px 0 0;
    }
    
    /* Footer */
    footer {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        padding: 1.5rem;
        border-top: 1px solid rgba(161, 0, 255, 0.2);
        margin-top: 2rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 session state
if 'tasks' not in st.session_state:
    st.session_state.tasks = {}
if 'task_counter' not in st.session_state:
    st.session_state.task_counter = 0

# 后台任务管理器
class BackgroundTask:
    """后台任务管理器"""
    
    def __init__(self, task_id, task_name, cmd):
        self.task_id = task_id
        self.task_name = task_name
        self.cmd = cmd
        self.status = "running"  # running, completed, failed
        self.output_queue = queue.Queue()
        self.process = None
        self.thread = None
        self.start_time = datetime.now()
        self.end_time = None
        self.logs = []
        
    def start(self):
        """启动后台任务"""
        # 添加初始日志
        initial_log = f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Starting task: {self.task_name}"
        self.logs.append(initial_log)
        self.output_queue.put(initial_log)
        
        self.thread = threading.Thread(target=self._run_task, daemon=True)
        self.thread.start()
    
    def _run_task(self):
        """在后台线程中运行任务"""
        try:
            # 添加完整命令日志（用于调试）
            cmd_str = ' '.join(self.cmd)
            if len(cmd_str) > 200:
                debug_log = f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Command: {cmd_str[:200]}..."
            else:
                debug_log = f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Command: {cmd_str}"
            self.logs.append(debug_log)
            self.output_queue.put(debug_log)
            
            # 设置环境变量强制无缓冲输出
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # 分别捕获 stderr
                text=True,
                bufsize=0,  # 完全无缓冲
                universal_newlines=True,
                env=env  # 传递环境变量
            )
            
            # 进程启动后的日志
            started_log = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Process started (PID: {self.process.pid})"
            self.logs.append(started_log)
            self.output_queue.put(started_log)
            
            # 使用线程同时读取 stdout 和 stderr，避免阻塞
            def read_stream(stream, is_stderr=False):
                """在单独线程中读取流"""
                try:
                    for line in iter(stream.readline, ''):
                        if line:
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            # 只对真正的错误添加 ERROR 前缀
                            # 排除：包含 INFO/WARNING 的行，或者只是分隔符/空行
                            stripped = line.strip()
                            if is_stderr and stripped:
                                # 检查是否是真正的错误（包含错误关键词）
                                error_keywords = ['error', 'exception', 'traceback', 'failed', 'fatal']
                                is_real_error = (
                                    'INFO' not in line and 
                                    'WARNING' not in line and 
                                    not all(c in '=-_*#' for c in stripped) and  # 不是分隔符
                                    any(keyword in line.lower() for keyword in error_keywords)  # 包含错误关键词
                                )
                                if is_real_error:
                                    log_line = f"[{timestamp}] ❌ ERROR: {line.rstrip()}"
                                else:
                                    log_line = f"[{timestamp}] {line.rstrip()}"
                            else:
                                log_line = f"[{timestamp}] {line.rstrip()}"
                            self.logs.append(log_line)
                            self.output_queue.put(log_line)
                except Exception as e:
                    error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Stream read error: {e}"
                    self.logs.append(error_msg)
                    self.output_queue.put(error_msg)
            
            # 创建两个线程分别读取 stdout 和 stderr
            stdout_thread = threading.Thread(
                target=read_stream, 
                args=(self.process.stdout, False),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_stream, 
                args=(self.process.stderr, True),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 等待进程结束
            self.process.wait()
            
            # 等待读取线程完成（最多等待2秒）
            stdout_thread.join(timeout=2)
            # stderr_thread.join(timeout=2)
            
            self.end_time = datetime.now()
            
            if self.process.returncode == 0:
                self.status = "completed"
                complete_log = f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Task completed successfully"
                self.logs.append(complete_log)
                self.output_queue.put(complete_log)
            else:
                self.status = "failed"
                fail_log = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Task failed (exit code: {self.process.returncode})"
                self.logs.append(fail_log)
                self.output_queue.put(fail_log)
                
                # 如果没有其他日志，添加提示
                if len(self.logs) <= 4:  # 只有启动日志
                    hint_log = f"[{datetime.now().strftime('%H:%M:%S')}] 💡 Hint: Process exited immediately. Check if the script has syntax errors or missing dependencies."
                    self.logs.append(hint_log)
                    self.output_queue.put(hint_log)
                
        except Exception as e:
            self.status = "failed"
            self.end_time = datetime.now()
            error_msg = f"❌ 任务异常: {str(e)}"
            self.logs.append(error_msg)
            self.output_queue.put(error_msg)
    
    def get_logs(self):
        """获取所有日志"""
        # 从队列中读取新日志
        while not self.output_queue.empty():
            try:
                line = self.output_queue.get_nowait()
                if line not in self.logs:
                    self.logs.append(line)
            except queue.Empty:
                break
        return self.logs
    
    def get_duration(self):
        """获取任务运行时长"""
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        else:
            duration = (datetime.now() - self.start_time).total_seconds()
        return duration
    
    def is_running(self):
        """检查任务是否正在运行"""
        return self.status == "running" and self.process and self.process.poll() is None
    
    def stop(self):
        """停止任务"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status = "stopped"
            self.end_time = datetime.now()
            self.output_queue.put("⚠️ 任务已手动停止")

# Top Navigation Bar
def render_top_navigation():
    # Get current page from query params or default to home
    if "page" not in st.query_params:
        current_page = "home"
    else:
        current_page = st.query_params.get("page", ["home"])[0]
    
    # Navigation HTML with JavaScript to handle clicks without page reload
    nav_html = f"""
    <div class="top-nav">
        <h1 class="nav-title">📊 QTSP</h1>
        <div class="nav-links">
            <button class="nav-link {'active' if current_page == 'home' else ''}" onclick="navigateTo('home')">🏠 Home</button>
            <button class="nav-link {'active' if current_page == 'monitor' else ''}" onclick="navigateTo('monitor')">📈 Real-time Monitor</button>
            <button class="nav-link {'active' if current_page == 'optimization' else ''}" onclick="navigateTo('optimization')">🚀 Strategy Optimization</button>
            <button class="nav-link {'active' if current_page == 'management' else ''}" onclick="navigateTo('management')">📁 Strategy Management</button>
        </div>
    </div>
    <script>
    function navigateTo(page) {{
        // Update URL without page reload
        const url = new URL(window.location);
        url.searchParams.set('page', page);
        window.history.pushState({{page: page}}, '', url);
        
        // Trigger Streamlit rerun by updating query params
        // This will be handled by Streamlit's query params system
        window.location.search = '?page=' + page;
    }}
    </script>
    """
    
    st.markdown(nav_html, unsafe_allow_html=True)
    
    return current_page

# Render top navigation and get current page
page = render_top_navigation()

# Sidebar navigation - Hidden since we moved to top
# st.sidebar.markdown("# 📊 Navigation Menu")
# page = st.sidebar.radio(
#     "Select Function",
#     ["🏠 Home", "📈 Real-time Monitor", "🚀 Strategy Optimization", "📁 Strategy Management"],
#     label_visibility="collapsed"
# )

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Quick Info")

# Display strategy statistics
def load_strategies():
    """加载所有策略文件"""
    strategies_dir = Path("strategies")
    if not strategies_dir.exists():
        return []
    
    strategies = []
    for file in strategies_dir.glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            strategies.append({
                'filename': file.name,
                'symbol': file.name.split('_')[0],
                'name': data.get('name', 'Unknown'),
                'signal_weights': data.get('signal_weights', {}),
                'backtest_performance': data.get('backtest_performance', {}),
                'metadata': data.get('metadata', {}),
                'modified': datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'size': file.stat().st_size,
                'path': str(file)
            })
        except Exception as e:
            # Skip files with errors instead of showing error on every page load
            continue
    
    return sorted(strategies, key=lambda x: x['modified'], reverse=True)

strategies = load_strategies()
symbols = list(set([s['symbol'] for s in strategies]))
st.sidebar.metric("Total Strategies", len(strategies))
st.sidebar.metric("Number of Symbols", len(symbols))

if strategies:
    latest = strategies[0]
    st.sidebar.info(f"**Latest Update**\n\n{latest['symbol']} - {latest['name']}\n\n{latest['modified']}")

# Map page names to display names
page_mapping = {
    "home": "🏠 Home",
    "monitor": "📈 Real-time Monitor",
    "optimization": "🚀 Strategy Optimization",
    "management": "📁 Strategy Management"
}

# Get the display name for the current page
display_page = page_mapping.get(page, "🏠 Home")

# ==================== Home ====================
if display_page == "🏠 Home":
    st.markdown('<h1 class="main-header">📊 QTSP - Quantitative Trading Strategy Platform</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    ### AI Powered Option Experimentation Platform！
    """)
    
    # 功能介绍
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🚀 Strategy Optimization</h3>
            <p>DeepSeek AI powered optimization, up to 10 iterations, automatically converges to the best configuration.</p>
            <ul>
                <li>AI-driven optimization</li>
                <li>Automatic version management</li>
                <li>Complete metadata recording</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>🔍 Strategy Scanning</h3>
            <p>Batch backtest multiple strategies across multiple symbols, automatically generate comparison reports and visual charts.</p>
            <ul>
                <li>Multiple symbol comparison</li>
                <li>8 professional charts</li>
                <li>Complete HTML report</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>📁 Strategy Management</h3>
            <p>View, edit, delete strategy files, intelligent version control system.</p>
            <ul>
                <li>Automatic version management</li>
                <li>Online editor</li>
                <li>Backup recovery</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 最近策略列表
    st.markdown("### 📋 Recently updated strategies")
    
    if strategies:
        df = pd.DataFrame([{
            'Symbol': s['symbol'],
            'Strategy Name': s['name'],
            'File Name': s['filename'],
            'Updated Time': s['modified'],
            'File Size': f"{s['size']} bytes"
        } for s in strategies[:10]])
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No strategy files found, please run strategy optimization or manually add strategies.")


# ==================== Real-time Monitor ====================
elif display_page == "📈 Real-time Monitor":
    st.markdown('<h1 class="main-header">📈 Real-time Strategy Monitor</h1>', unsafe_allow_html=True)
    
    # Add custom CSS for the monitoring dashboard
    st.markdown("""
    <style>
        /* RockAlpha-inspired monitor cards */
        .monitor-card {
            background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
            padding: 1.5rem;
            border-radius: 12px;
            color: #EAEAEA;
            margin-bottom: 1rem;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            border: 1px solid rgba(161, 0, 255, 0.2);
            transition: transform 0.2s ease;
        }
        
        .monitor-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.4);
        }
        
        .monitor-card-positive {
            background: linear-gradient(135deg, #0f3b39 0%, #1a5e5a 100%);
            padding: 1.5rem;
            border-radius: 12px;
            color: #38ef7d;
            margin-bottom: 1rem;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            border: 1px solid rgba(56, 239, 125, 0.3);
            transition: transform 0.2s ease;
        }
        
        .monitor-card-positive:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.4);
        }
        
        .monitor-card-negative {
            background: linear-gradient(135deg, #3b1f24 0%, #5e2a35 100%);
            padding: 1.5rem;
            border-radius: 12px;
            color: #ff6b6b;
            margin-bottom: 1rem;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            border: 1px solid rgba(255, 107, 107, 0.3);
            transition: transform 0.2s ease;
        }
        
        .monitor-card-negative:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.4);
        }
        
        .big-number {
            font-size: 3rem;
            font-weight: bold;
            margin: 0.5rem 0;
            text-align: center;
            background: linear-gradient(to right, #A100FF, #632BFF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .subtitle-text {
            font-size: 1.2rem;
            opacity: 0.9;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        
        /* Data source indicator */
        .data-source {
            font-size: 0.9rem;
            opacity: 0.8;
            text-align: center;
            margin: 0.3rem 0;
            font-weight: 500;
        }
        
        /* Metric styling */
        [data-testid='stMetricValue'] {
            color: #A100FF !important;
        }
        
        /* Chart container */
        .chart-container {
            background: #1A1A2E;
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid rgba(161, 0, 255, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Configuration
    monitor_start_date = "2025-04-01"
    
    # Check API key availability
    import os
    has_api_key = bool(os.getenv('POLYGON_API_KEY'))
    
    if has_api_key:
        st.info(f"📅 Monitoring Period: **{monitor_start_date}** to **Today** | 🔴 Live data enabled | Auto-refresh every 30 seconds")
    else:
        st.warning(f"📅 Monitoring Period: **{monitor_start_date}** to **Today** | 💾 Using cached backtest results (POLYGON_API_KEY not set for live data)")
    
    # Auto-refresh toggle
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)
    with col2:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    # Load strategies and run backtests
    strategies = load_strategies()
    
    if not strategies:
        st.warning("⚠️ No strategies found. Please run optimization first.")
    else:
        # Group strategies by symbol and find best performing one
        symbol_best_strategies = {}
        
        for strategy in strategies:
            symbol = strategy['symbol']
            
            # Skip if already have a strategy for this symbol with better performance
            if symbol in symbol_best_strategies:
                existing_return = symbol_best_strategies[symbol].get('backtest_performance', {}).get('total_return', -999)
                current_return = strategy.get('backtest_performance', {}).get('total_return', -999)
                if current_return <= existing_return:
                    continue
            
            symbol_best_strategies[symbol] = strategy
        
        st.markdown(f"### 🎯 Monitoring {len(symbol_best_strategies)} Symbols")
        
        # Run live backtests for each symbol
        monitor_results = []
        
        with st.spinner('🔄 Loading strategy data...'):
            for symbol, strategy in symbol_best_strategies.items():
                try:
                    # Load strategy config
                    with open(strategy['path'], 'r', encoding='utf-8') as f:
                        strategy_config = json.load(f)
                    
                    # Get stored backtest performance from strategy file
                    backtest_perf = strategy.get('backtest_performance', {})
                    
                    # Check if we have existing backtest data
                    if backtest_perf and 'total_return' in backtest_perf:
                        # Use cached backtest results from strategy file
                        total_return = backtest_perf.get('total_return', 0)
                        num_trades = backtest_perf.get('num_trades', 0)
                        win_rate = backtest_perf.get('win_rate', 0)
                        final_value = 10000 * (1 + total_return)
                        
                        # Create a simple equity curve from stored data
                        # Generate synthetic equity curve based on return
                        days = (datetime.now() - pd.to_datetime(monitor_start_date)).days
                        dates = pd.date_range(start=monitor_start_date, periods=days, freq='D')
                        # Simple linear growth assumption
                        equity_values = [10000 + (final_value - 10000) * (i / days) for i in range(days)]
                        equity_curve = pd.Series(equity_values, index=dates)
                        
                        monitor_results.append({
                            'symbol': symbol,
                            'strategy_name': strategy['name'],
                            'total_return': total_return,
                            'final_value': final_value,
                            'num_trades': num_trades,
                            'win_rate': win_rate,
                            'equity_curve': equity_curve,
                            'trades': [],  # No detailed trade history from cache
                            'is_cached': True
                        })
                    else:
                        # Try to run live backtest if API key is available
                        import os
                        if not os.getenv('POLYGON_API_KEY'):
                            st.warning(f"⚠️ {symbol}: No cached data and POLYGON_API_KEY not set. Skipping live backtest.")
                            continue
                        
                        # Run backtest from 2025-04-01 to today
                        backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
                        
                        params = strategy_config.get('params', {})
                        signal_weights = strategy_config.get('signal_weights', {})
                        
                        result = backtest.run_backtest(
                            symbol=symbol,
                            start_date=monitor_start_date,
                            end_date=datetime.now().strftime("%Y-%m-%d"),
                            strategy='auto',
                            entry_signal=signal_weights,
                            profit_target=params.get('profit_target', 5.0),
                            stop_loss=params.get('stop_loss', -0.5),
                            max_holding_days=params.get('max_holding_days', 30),
                            position_size=params.get('position_size', 0.1)
                        )
                        
                        # Calculate metrics
                        final_value = result.equity_curve[-1] if len(result.equity_curve) > 0 else 10000
                        total_return = (final_value - 10000) / 10000
                        num_trades = len(result.trades)
                        winning_trades = sum(1 for t in result.trades if t.pnl and t.pnl > 0)
                        win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0
                        
                        monitor_results.append({
                            'symbol': symbol,
                            'strategy_name': strategy['name'],
                            'total_return': total_return,
                            'final_value': final_value,
                            'num_trades': num_trades,
                            'win_rate': win_rate,
                            'equity_curve': result.equity_curve,
                            'trades': result.trades,
                            'is_cached': False
                        })
                    
                except Exception as e:
                    st.error(f"❌ Error loading {symbol}: {str(e)}")
                    continue
        
        # Sort by return (best first)
        monitor_results.sort(key=lambda x: x['total_return'], reverse=True)
        
        # Display summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_symbols = len(monitor_results)
        avg_return = sum(r['total_return'] for r in monitor_results) / total_symbols if total_symbols > 0 else 0
        positive_symbols = sum(1 for r in monitor_results if r['total_return'] > 0)
        total_trades = sum(r['num_trades'] for r in monitor_results)
        
        with col1:
            st.metric("🎯 Total Symbols", total_symbols)
        with col2:
            st.metric("📈 Avg Return", f"{avg_return:+.2%}")
        with col3:
            st.metric("✅ Positive", f"{positive_symbols}/{total_symbols}")
        with col4:
            st.metric("📊 Total Trades", total_trades)
        
        st.markdown("---")
        
        # Display individual strategy cards
        st.markdown("### 📈 Live Strategy Performance")
        
        for idx, result in enumerate(monitor_results):
            card_class = "monitor-card-positive" if result['total_return'] > 0 else "monitor-card-negative"
            data_source = "💾 Cached" if result.get('is_cached', False) else "🔴 Live"
            data_source_class = "data-source"
            
            col1, col2 = st.columns([2, 3])
            
            with col1:
                st.markdown(f"""
                <div class="{card_class}">
                    <h2 style="margin:0; text-align: center;">📊 {result['symbol']}</h2>
                    <p class="subtitle-text">{result['strategy_name']}</p>
                    <p class="{data_source_class}">{data_source}</p>
                    <div class="big-number">{result['total_return']:+.2%}</div>
                    <p style="font-size: 1.1rem; margin: 0.5rem 0; text-align: center;">
                        💰 ${result['final_value']:,.0f} | 
                        📊 {result['num_trades']} trades | 
                        🎯 {result['win_rate']:.1f}% win rate
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if result['equity_curve']:
                    # Create equity curve chart
                    fig, ax = plt.subplots(figsize=(10, 4))
                    
                    # Set dark theme for matplotlib
                    fig.patch.set_facecolor('#1A1A2E')
                    ax.set_facecolor('#1A1A2E')
                    
                    equity_series = pd.Series(result['equity_curve'])
                    equity_series.index = pd.to_datetime(equity_series.index)
                    
                    line_color = '#38ef7d' if result['total_return'] > 0 else '#ff6b6b'
                    fill_color = '#38ef7d' if result['total_return'] > 0 else '#ff6b6b'
                    
                    ax.plot(equity_series.index, equity_series.values, 
                           linewidth=2.5, color=line_color)
                    ax.axhline(y=10000, color='#A100FF', linestyle='--', alpha=0.5, linewidth=1)
                    ax.fill_between(equity_series.index, 10000, equity_series.values, 
                                   alpha=0.3, color=fill_color)
                    
                    # Style the chart
                    ax.set_title(f'{result["symbol"]} Equity Curve', fontsize=12, fontweight='bold', color='#EAEAEA')
                    ax.set_xlabel('Date', fontsize=10, color='#EAEAEA')
                    ax.set_ylabel('Portfolio Value ($)', fontsize=10, color='#EAEAEA')
                    ax.tick_params(colors='#EAEAEA')
                    ax.grid(True, alpha=0.2, color='#A100FF')
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', color='#EAEAEA')
                    plt.tight_layout()
                    
                    st.pyplot(fig)
                    plt.close(fig)
            
            # Expandable trade details
            with st.expander(f"📝 View {result['num_trades']} Trades for {result['symbol']}"):
                if result['trades']:
                    trades_data = []
                    for i, trade in enumerate(result['trades'], 1):
                        trades_data.append({
                            '#': i,
                            'Entry': trade.entry_date,
                            'Exit': trade.exit_date,
                            'Type': trade.position_type,
                            'Entry Price': f"${trade.entry_price:.2f}",
                            'Exit Price': f"${trade.exit_price:.2f}",
                            'P&L': f"${trade.pnl:+,.2f}",
                            'Return': f"{trade.pnl_pct:+.2%}",
                            'Reason': trade.exit_reason
                        })
                    
                    trades_df = pd.DataFrame(trades_data)
                    st.dataframe(trades_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No trades executed in this period")
        
        # Performance comparison table
        st.markdown("---")
        st.markdown("### 📊 Performance Comparison")
        
        comparison_df = pd.DataFrame([{
            'Symbol': r['symbol'],
            'Strategy': r['strategy_name'],
            'Return': f"{r['total_return']:+.2%}",
            'Final Value': f"${r['final_value']:,.0f}",
            'Trades': r['num_trades'],
            'Win Rate': f"{r['win_rate']:.1f}%"
        } for r in monitor_results])
        
        st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(30)
        st.rerun()


# ==================== 策略优化 ====================
elif display_page == "🚀 Strategy Optimization":
    st.markdown('<h1 class="main-header">🚀 Strategy Optimization</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Use DeepSeek AI to automatically optimize strategy parameters, generate versioned strategy files with timestamps.
    **Background tasks will continue to run, you can switch to other tabs to view progress.**
    """)
    
    # 显示当前运行的优化任务
    running_tasks = {tid: task for tid, task in st.session_state.tasks.items() 
                    if task.status == "running" and tid.startswith("opt_")}
    
    if running_tasks:
        st.info(f"⏳ There are {len(running_tasks)} optimization tasks running")
        for task_id, task in running_tasks.items():
            with st.expander(f"🔄 {task.task_name} (Running {task.get_duration():.0f} seconds)", expanded=False):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**Status:** {task.status}")
                    st.write(f"**Start Time:** {task.start_time.strftime('%H:%M:%S')}")
                with col2:
                    if st.button("⏹️ Stop", key=f"stop_opt_{task_id}"):
                        task.stop()
                        st.rerun()
    
    # 单标的优化表单
    st.markdown("### 📊 Optimize Strategy")
    st.markdown("Generate optimized strategy for a specific symbol.")
    
    with st.form("single_optimization_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("Symbol", value="BABA", help="e.g.: BABA, NVDA, AAPL")
            start_date = st.date_input("Backtest Start Date", value=pd.to_datetime("2025-01-01"), key="single_start")
            max_iter = st.slider("Max Iterations", 1, 20, 10, key="single_iter")
        
        with col2:
            st.write("")  # 占位
            end_date = st.date_input("Backtest End Date", value=pd.to_datetime("2025-12-01"), key="single_end")
            threshold = st.slider("Convergence Threshold", 0.01, 0.2, 0.05, 0.01, key="single_threshold")
        
        submitted = st.form_submit_button("🚀 Start Optimization", use_container_width=True)
    
    if submitted:
        if not symbol:
            st.error("Please enter the symbol code")
        else:
            # 创建后台任务
            st.session_state.task_counter += 1
            task_id = f"opt_{st.session_state.task_counter}"
            
            cmd = [
                sys.executable,
                "-u",  # 无缓冲模式，确保实时输出日志
                "run_iterative_optimization.py",
                "--symbol", symbol,
                "--start", start_date.strftime("%Y-%m-%d"),
                "--end", end_date.strftime("%Y-%m-%d"),
                "--max-iter", str(max_iter),
                "--threshold", str(threshold)
            ]
            
            task = BackgroundTask(
                task_id=task_id,
                task_name=f"Optimize {symbol}",
                cmd=cmd
            )
            
            st.session_state.tasks[task_id] = task
            task.start()
            
            st.success(f"✅ Task started! Task ID: {task_id}")
            st.info("💡 You can switch to other pages, the task will continue to run in the background")
            st.rerun()
    
    # 显示所有优化任务
    st.markdown("---")
    st.markdown("### 📋 Optimization Task List")
    
    # 显示所有优化任务
    opt_tasks = {tid: task for tid, task in st.session_state.tasks.items() 
                 if tid.startswith("opt_")}
    
    if not opt_tasks:
        st.info("No optimization tasks found")
    else:
        # 按状态分组
        for task_id, task in list(opt_tasks.items()):
            status_icon = {
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "stopped": "⏹️"
            }.get(task.status, "❓")
            
            with st.expander(
                f"{status_icon} {task.task_name} | {task.status.upper()} | 开始于 {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                expanded=(task.status == "running")
            ):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**Task ID:** {task_id}")
                    st.write(f"**Status:** {task.status}")
                
                with col2:
                    st.write(f"**Start Time:** {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    if task.end_time:
                        st.write(f"**End Time:** {task.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**Run Time:** {task.get_duration():.1f} seconds")
                
                with col3:
                    if task.status == "running":
                        if st.button("⏹️ Stop Task", key=f"stop_task_{task_id}"):
                            task.stop()
                            st.rerun()
                    else:
                        if st.button("🗑️ Delete", key=f"del_task_{task_id}"):
                            del st.session_state.tasks[task_id]
                            st.rerun()
                
                # 实时日志
                st.markdown("**📜 Real-time Logs:**")
                logs = task.get_logs()
                
                if logs:
                    # 控制选项
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        show_count = st.selectbox(
                            "Show logs",
                            options=[50, 100, 200, 500, "All"],
                            index=1,  # 默认100
                            key=f"opt_log_count_{task_id}"
                        )
                    with col2:
                        st.caption(f"📊 Total: {len(logs)} log entries")
                    with col3:
                        if len(logs) > 50:
                            full_log_text = "\n".join(logs)
                            st.download_button(
                                "📥",
                                data=full_log_text,
                                file_name=f"{task_id}_logs.txt",
                                mime="text/plain",
                                key=f"opt_save_logs_{task_id}",
                                help="Download full logs"
                            )
                    
                    # 显示日志
                    if show_count == "All":
                        display_logs = logs
                    else:
                        display_logs = logs[-show_count:]
                    
                    log_text = "\n".join(display_logs)
                    st.code(log_text, language="log")
                else:
                    # 显示等待信息，但显示任务状态和已运行时间
                    st.info(f"Waiting for logs to output... (Task {task.status}, running {task.get_duration():.1f}s)")
                
                # 自动刷新（运行中的任务始终刷新，无论是否有日志）
                if task.status == "running":
                    time.sleep(0.5)
                    st.rerun()
                
                # 如果任务完成，显示结果
                if task.status == "completed":
                    st.success("🎉 Mission completed successfully!")
                    
                    # 尝试获取生成的策略
                    symbol = task.task_name.split()[-1]  # 从任务名称提取标的
                    latest = get_latest_strategy(symbol)
                    if latest:
                        st.json(latest)
                        st.download_button(
                            "💾 Download Strategy File",
                            data=json.dumps(latest, indent=2, ensure_ascii=False),
                            file_name=f"{symbol}_strategy.json",
                            mime="application/json",
                            key=f"download_{task_id}"
                        )


# ==================== 策略扫描 ====================
elif page == "📁 Strategy Management":
    st.markdown('<h1 class="main-header">📁 Strategy Management</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    Manage your trading strategies: browse, compare, edit, and perform batch scanning with selected strategies.
    """)
    
    # 创建标签页
    mgmt_tab1, mgmt_tab2, mgmt_tab3 = st.tabs(["📋 Strategy List", "⚖️ Strategy Comparison", "🎯 Custom Scan"])
    
    # ==================== Tab 1: Strategy List ====================
    with mgmt_tab1:
        st.markdown("### 📋 Strategy Library")
        
        # 过滤选项
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            filter_symbol = st.selectbox("Select Symbol", ["All"] + symbols, key="filter_symbol_list")
        with col2:
            sort_by = st.selectbox("Sort by", ["Modified Time", "Symbol", "File Name"])
        with col3:
            st.write("")
            st.write("")
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        # Filter strategies
        filtered_strategies = strategies
        if filter_symbol != "All":
            filtered_strategies = [s for s in strategies if s['symbol'] == filter_symbol]
        
        # Sort
        if sort_by == "Symbol":
            filtered_strategies = sorted(filtered_strategies, key=lambda x: x['symbol'])
        elif sort_by == "File Name":
            filtered_strategies = sorted(filtered_strategies, key=lambda x: x['filename'])
        
        st.markdown(f"**Found {len(filtered_strategies)} strategies**")
        
        if not filtered_strategies:
            st.info("No strategy files found")
        else:
            for strategy in filtered_strategies:
                with st.expander(f"**{strategy['symbol']}** - {strategy['name']} ({strategy['filename']})"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"""
                        - **File Name**: {strategy['filename']}
                        - **Symbol**: {strategy['symbol']}
                        - **Strategy Name**: {strategy['name']}
                        - **Updated Time**: {strategy['modified']}
                        - **File Size**: {strategy['size']} bytes
                        """)
                        
                        # Display metadata
                        if strategy['metadata']:
                            st.markdown("**Metadata**:")
                            meta = strategy['metadata']
                            if 'best_return' in meta:
                                st.write(f"- Return: {meta['best_return']:+.2%}" if isinstance(meta['best_return'], (int, float)) else f"- Return: {meta['best_return']}")
                            if 'generated_at' in meta:
                                st.write(f"- Generated At: {meta['generated_at']}")
                            if 'backtest_period' in meta:
                                st.write(f"- Backtest Period: {meta['backtest_period']}")
                        
                        # Display backtest performance
                        if strategy.get('backtest_performance'):
                            st.markdown("**Backtest Performance**:")
                            perf = strategy['backtest_performance']
                            if isinstance(perf, dict):
                                # 单标的性能
                                if 'total_return' in perf:
                                    cols = st.columns(4)
                                    cols[0].metric("Return", f"{perf.get('total_return', 0):+.2%}")
                                    cols[1].metric("Win Rate", f"{perf.get('win_rate', 0):.1%}")
                                    cols[2].metric("Sharpe", f"{perf.get('sharpe_ratio', 0):.2f}")
                                    cols[3].metric("Trades", perf.get('num_trades', 0))
                                else:
                                    # 多标的性能
                                    for sym, p in perf.items():
                                        st.write(f"**{sym}**: Return {p.get('total_return', 0):+.2%}, Win Rate {p.get('win_rate', 0):.1%}, Trades {p.get('num_trades', 0)}")
                    
                    with col2:
                        # Action buttons
                        if st.button("📝 Edit", key=f"edit_{strategy['filename']}", use_container_width=True):
                            st.session_state['editing'] = strategy['path']
                        
                        if st.button("💾 Download", key=f"download_{strategy['filename']}", use_container_width=True):
                            with open(strategy['path'], 'r', encoding='utf-8') as f:
                                content = f.read()
                            st.download_button(
                                "Confirm Download",
                                data=content,
                                file_name=strategy['filename'],
                                mime="application/json",
                                key=f"dl_{strategy['filename']}"
                            )
                        
                        if st.button("🗑️ Delete", key=f"delete_{strategy['filename']}", use_container_width=True, type="secondary"):
                            if delete_strategy(strategy['path']):
                                st.success("Deleted successfully")
                                st.rerun()
                    
                    # JSON content
                    try:
                        with open(strategy['path'], 'r', encoding='utf-8') as f:
                            content = json.load(f)
                        st.json(content)
                    except Exception as e:
                        st.error(f"Failed to read file: {e}")
        
        # Editor
        if 'editing' in st.session_state:
            st.markdown("---")
            st.markdown("### ✏️ Edit Strategy")
            
            filepath = st.session_state['editing']
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                edited = st.text_area(
                    "JSON Content",
                    value=content,
                    height=400,
                    help="Please ensure JSON format is correct"
                )
                
                col1, col2, col3 = st.columns([1, 1, 4])
                with col1:
                    if st.button("💾 Save", use_container_width=True):
                        try:
                            # Validate JSON
                            json.loads(edited)
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(edited)
                            st.success("Saved successfully")
                            del st.session_state['editing']
                            st.rerun()
                        except json.JSONDecodeError as e:
                            st.error(f"JSON format error: {e}")
                
                with col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        del st.session_state['editing']
                        st.rerun()
            
            except Exception as e:
                st.error(f"Failed to read file: {e}")
                del st.session_state['editing']
        
        # Upload new strategy
        st.markdown("---")
        st.markdown("### ➕ Upload New Strategy")
        
        uploaded_file = st.file_uploader("Select JSON file", type=['json'], key="upload_strategy_list")
        if uploaded_file:
            try:
                content = json.loads(uploaded_file.read().decode('utf-8'))
                
                symbol = st.text_input("Symbol", value=content.get('metadata', {}).get('symbol', ''), key="upload_symbol_list")
                
                if st.button("📤 Upload"):
                    if symbol:
                        filename = save_strategy(symbol, content)
                        st.success(f"Uploaded successfully: {filename}")
                        st.rerun()
                    else:
                        st.error("Please enter the symbol")
            except Exception as e:
                st.error(f"File format error: {e}")
    
    # ==================== Tab 2: Strategy Comparison ====================
    with mgmt_tab2:
        st.markdown("### ⚖️ Strategy Comparison")
        st.markdown("Select multiple strategies to compare their performance metrics side by side.")
        
        if not strategies:
            st.info("No strategies available for comparison")
        else:
            # 策略选择
            st.markdown("#### Select Strategies to Compare (2-5 strategies)")
            
            # 创建策略选择列表
            strategy_options = {}
            for s in strategies:
                key = f"{s['symbol']} - {s['name']} ({s['filename']})"
                strategy_options[key] = s
            
            selected_keys = st.multiselect(
                "Choose strategies",
                options=list(strategy_options.keys()),
                max_selections=5,
                help="Select 2 to 5 strategies to compare"
            )
            
            if len(selected_keys) < 2:
                st.info("Please select at least 2 strategies to compare")
            else:
                selected_strategies = [strategy_options[key] for key in selected_keys]
                
                st.markdown(f"**Comparing {len(selected_strategies)} strategies**")
                
                # 创建对比表格
                comparison_data = []
                for strat in selected_strategies:
                    row = {
                        "Strategy": strat['name'],
                        "Symbol": strat['symbol'],
                        "File": strat['filename'],
                        "Modified": strat['modified']
                    }
                    
                    # 添加元数据
                    if strat.get('metadata'):
                        meta = strat['metadata']
                        if 'best_return' in meta and isinstance(meta['best_return'], (int, float)):
                            row["Best Return"] = f"{meta['best_return']:+.2%}"
                        if 'backtest_period' in meta:
                            row["Period"] = meta['backtest_period']
                    
                    # 添加回测性能
                    if strat.get('backtest_performance'):
                        perf = strat['backtest_performance']
                        if isinstance(perf, dict) and 'total_return' in perf:
                            row["Total Return"] = f"{perf.get('total_return', 0):+.2%}"
                            row["Win Rate"] = f"{perf.get('win_rate', 0):.1%}"
                            row["Sharpe Ratio"] = f"{perf.get('sharpe_ratio', 0):.2f}"
                            row["Max Drawdown"] = f"{perf.get('max_drawdown', 0):.2%}"
                            row["Num Trades"] = perf.get('num_trades', 0)
                            row["Avg Win"] = f"${perf.get('avg_win', 0):,.0f}"
                            row["Avg Loss"] = f"${perf.get('avg_loss', 0):,.0f}"
                    
                    comparison_data.append(row)
                
                # 显示对比表格
                df_comparison = pd.DataFrame(comparison_data)
                st.dataframe(df_comparison, use_container_width=True, hide_index=True)
                
                # 显示信号权重对比
                st.markdown("#### Signal Weights Comparison")
                
                signal_comparison = {}
                for strat in selected_strategies:
                    strat_label = f"{strat['symbol']}_{strat['name']}"
                    if strat.get('signal_weights'):
                        for signal, weight in strat['signal_weights'].items():
                            if signal not in signal_comparison:
                                signal_comparison[signal] = {}
                            signal_comparison[signal][strat_label] = weight
                
                if signal_comparison:
                    signal_df = pd.DataFrame(signal_comparison).T
                    signal_df = signal_df.fillna(0)
                    
                    # 使用柱状图显示
                    st.bar_chart(signal_df)
                    
                    # 也显示表格
                    with st.expander("View Signal Weights Table"):
                        st.dataframe(signal_df, use_container_width=True)
                
                # 下载对比报告
                st.markdown("---")
                if st.button("📥 Download Comparison Report", use_container_width=True):
                    report_data = {
                        "comparison_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "strategies": comparison_data,
                        "signal_weights": signal_comparison
                    }
                    report_json = json.dumps(report_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        "Download JSON",
                        data=report_json,
                        file_name=f"strategy_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
    
    # ==================== Tab 3: Custom Scan ====================
    with mgmt_tab3:
        st.markdown("### 🎯 Custom Strategy Scan")
        st.markdown("Select specific strategies and symbols to perform a custom batch backtest scan.")
        
        if not strategies:
            st.info("No strategies available. Please create or upload strategies first.")
        else:
            st.markdown("#### Configure Custom Scan")
            st.markdown("*Select symbols and strategies - all combinations will be tested*")
            
            # 按标的分组策略
            strategies_by_symbol = {}
            for s in strategies:
                sym = s['symbol']
                if sym not in strategies_by_symbol:
                    strategies_by_symbol[sym] = []
                strategies_by_symbol[sym].append(s)
            
            # Step 1: 选择标的
            st.markdown("**Step 1: Select Symbols to Test**")
            test_symbols = st.multiselect(
                "Choose symbols",
                options=symbols,
                default=symbols[:3] if len(symbols) >= 3 else symbols,
                help="Select one or more symbols for backtesting",
                key="custom_scan_symbols"
            )
            
            # Step 2: 选择策略（支持多选）
            st.markdown("**Step 2: Select Strategies to Test**")
            st.caption("💡 You can select multiple strategies - each will be tested against each symbol")
            
            selected_strategies = []
            symbol_strategy_pairs = []
            
            if test_symbols:
                # 为每个标的展示可用策略
                strategy_selection_mode = st.radio(
                    "Strategy Selection Mode",
                    options=["Quick Select (Same strategies for all symbols)", 
                             "Advanced (Different strategies per symbol)"],
                    key="strategy_mode",
                    horizontal=True
                )
                
                if strategy_selection_mode.startswith("Quick Select"):
                    # 快速模式：选择策略，应用到所有标的
                    st.markdown("**Select strategies to test across all symbols:**")
                    
                    # 收集所有可用策略（去重）
                    all_strategies = {}
                    for sym in test_symbols:
                        sym_strategies = strategies_by_symbol.get(sym, [])
                        for s in sym_strategies:
                            key = f"{s['filename']}"
                            if key not in all_strategies:
                                all_strategies[key] = s
                    
                    # 添加通用策略
                    universal_strategies = [s for s in strategies if s.get('metadata', {}).get('type') == 'universal']
                    for s in universal_strategies:
                        key = f"{s['filename']}"
                        if key not in all_strategies:
                            all_strategies[key] = s
                    
                    if all_strategies:
                        strategy_list = list(all_strategies.values())
                        strategy_display = [f"{s['name']} ({s['symbol']}) - {s['filename']}" for s in strategy_list]
                        
                        selected_indices = st.multiselect(
                            "Strategies",
                            options=range(len(strategy_list)),
                            default=[0] if len(strategy_list) > 0 else [],
                            format_func=lambda i: strategy_display[i],
                            key="quick_strategies"
                        )
                        
                        # 生成所有组合
                        for sym in test_symbols:
                            for idx in selected_indices:
                                symbol_strategy_pairs.append({
                                    'symbol': sym,
                                    'strategy': strategy_list[idx]
                                })
                    else:
                        st.warning("No strategies available for the selected symbols")
                
                else:
                    # 高级模式：为每个标的单独选择策略
                    st.markdown("**Select strategies for each symbol:**")
                    
                    for test_sym in test_symbols:
                        with st.expander(f"**{test_sym}** - Select Strategies", expanded=False):
                            # 获取该标的可用的策略
                            available_strategies = strategies_by_symbol.get(test_sym, [])
                            
                            # 添加通用策略
                            universal_strategies = [s for s in strategies if s.get('metadata', {}).get('type') == 'universal']
                            all_available = available_strategies + universal_strategies
                            
                            if not all_available:
                                st.warning(f"No strategies available for {test_sym}")
                                continue
                            
                            # 策略多选
                            strategy_display = [f"{s['name']} - {s['filename']}" for s in all_available]
                            selected_indices = st.multiselect(
                                f"Strategies for {test_sym}",
                                options=range(len(all_available)),
                                default=[0] if len(all_available) > 0 else [],
                                format_func=lambda i: strategy_display[i],
                                key=f"strat_select_{test_sym}",
                                label_visibility="collapsed"
                            )
                            
                            # 显示选中策略的信息
                            if selected_indices:
                                st.caption(f"**{len(selected_indices)} strateg{'ies' if len(selected_indices) > 1 else 'y'} selected:**")
                                for idx in selected_indices:
                                    selected_strategy = all_available[idx]
                                    symbol_strategy_pairs.append({
                                        'symbol': test_sym,
                                        'strategy': selected_strategy
                                    })
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.caption(f"📊 {selected_strategy['name']}")
                                    with col2:
                                        perf = selected_strategy.get('backtest_performance', {})
                                        if perf:
                                            returns = perf.get('total_return', 0) * 100
                                            st.caption(f"💰 {returns:+.1f}%")
                                    with col3:
                                        perf = selected_strategy.get('backtest_performance', {})
                                        if perf:
                                            win_rate = perf.get('win_rate', 0) * 100
                                            st.caption(f"🎯 {win_rate:.1f}%")
            else:
                st.info("👆 Please select at least one symbol to continue")
            
            st.markdown("---")
            st.markdown("#### Scan Configuration")
            
            col1, col2 = st.columns(2)
            with col1:
                scan_start = st.date_input(
                    "Start Date",
                    value=pd.to_datetime("2025-01-01"),
                    key="custom_scan_start"
                )
            with col2:
                scan_end = st.date_input(
                    "End Date",
                    value=pd.to_datetime("2025-12-01"),
                    key="custom_scan_end"
                )
            
            # 显示选择摘要
            st.markdown("**Step 3: Review & Launch**")
            
            if symbol_strategy_pairs:
                # 统计唯一的标的和策略数量
                unique_symbols = set([p['symbol'] for p in symbol_strategy_pairs])
                unique_strategies = set([p['strategy']['filename'] for p in symbol_strategy_pairs])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Symbols", len(unique_symbols))
                col2.metric("Strategies", len(unique_strategies))
                col3.metric("Total Tests", len(symbol_strategy_pairs))
                
                # 显示所有组合
                with st.expander("📋 View All Test Combinations", expanded=False):
                    for i, pair in enumerate(symbol_strategy_pairs, 1):
                        st.caption(f"{i}. **{pair['symbol']}** × {pair['strategy']['name']}")
            
            # 启动扫描按钮
            if st.button("🚀 Start Custom Scan", type="primary", use_container_width=True):
                if not test_symbols:
                    st.error("❌ Please select at least one symbol to test")
                elif not symbol_strategy_pairs:
                    st.error("❌ Please select at least one strategy to test")
                else:
                    # 生成任务ID
                    task_id = f"custom_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    
                    # 构建命令：传递所有 symbol-strategy pairs
                    # 格式：--symbols sym1 sym2 ... --strategies strat1 strat2 ...
                    symbols_list = [p['symbol'] for p in symbol_strategy_pairs]
                    strategies_list = [p['strategy']['path'] for p in symbol_strategy_pairs]
                    
                    cmd = [
                        sys.executable, "-u",
                        "run_strategy_scanner.py",
                        "--symbols"
                    ] + symbols_list + [
                        "--start", str(scan_start),
                        "--end", str(scan_end),
                        "--strategies"
                    ] + strategies_list
                    
                    # 创建后台任务
                    task = BackgroundTask(
                        task_id=task_id,
                        task_name=f"Custom scan: {len(unique_symbols)} symbols × {len(unique_strategies)} strategies = {len(symbol_strategy_pairs)} tests",
                        cmd=cmd
                    )
                    task.start()
                    
                    st.session_state.tasks[task_id] = task
                    
                    st.success(f"✅ Custom scan started! Task ID: {task_id}")
                    st.info("💡 Scroll down to view the task in the task list with real-time logs. You can also switch to other tabs, the task will continue running in the background.")
                    
                    # 自动滚动到任务列表
                    time.sleep(0.5)
                    st.rerun()
        
        # 显示自定义扫描任务列表
        st.markdown("---")
        st.markdown("### 📋 Custom Scan Tasks")
        
        custom_scan_tasks = {tid: task for tid, task in st.session_state.tasks.items() 
                            if tid.startswith("custom_scan_")}
        
        if not custom_scan_tasks:
            st.info("No custom scan tasks found. Start a custom scan above to see tasks here.")
        else:
            # 自动刷新选项
            auto_refresh = st.checkbox("🔄 Auto Refresh (every 2 seconds)", value=True, key="custom_scan_auto_refresh")
            
            for task_id, task in list(custom_scan_tasks.items()):
                status_icon = {
                    "running": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "stopped": "⏹️"
                }.get(task.status, "❓")
                
                with st.expander(
                    f"{status_icon} {task.task_name} | {task.status.upper()} | Duration: {task.get_duration():.1f}s",
                    expanded=(task.status == "running")
                ):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**Task ID:** {task_id}")
                        st.write(f"**Status:** {task.status}")
                    
                    with col2:
                        st.write(f"**Start Time:** {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        if task.end_time:
                            st.write(f"**End Time:** {task.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"**Duration:** {task.get_duration():.1f} seconds")
                    
                    with col3:
                        if task.status == "running":
                            if st.button("⏹️ Stop", key=f"stop_custom_{task_id}"):
                                task.stop()
                                st.rerun()
                        else:
                            if st.button("🗑️ Delete", key=f"del_custom_{task_id}"):
                                del st.session_state.tasks[task_id]
                                st.rerun()
                    
                    # 如果任务完成，显示生成的报告
                    if task.status == "completed":
                        st.markdown("---")
                        
                        # 从日志中提取关键指标
                        logs = task.get_logs()
                        summary_metrics = {}
                        for log in logs:
                            # 查找类似 "BABA: 收益 +177.45%, 夏普 1.54, 胜率 66.7%" 的日志
                            if "收益" in log and "夏普" in log and "胜率" in log:
                                # 提取指标
                                import re
                                match = re.search(r'收益\s+([+-]?\d+\.?\d*)%.*夏普\s+(\d+\.?\d*).*胜率\s+(\d+\.?\d*)%', log)
                                if match:
                                    summary_metrics = {
                                        'return': float(match.group(1)),
                                        'sharpe': float(match.group(2)),
                                        'win_rate': float(match.group(3))
                                    }
                                    break
                        
                        # 显示关键指标卡片
                        if summary_metrics:
                            st.markdown("**📈 Performance Summary:**")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                return_color = "normal" if summary_metrics['return'] >= 0 else "off"
                                st.metric("Total Return", f"{summary_metrics['return']:+.2f}%", delta_color=return_color)
                            with col2:
                                st.metric("Sharpe Ratio", f"{summary_metrics['sharpe']:.2f}")
                            with col3:
                                st.metric("Win Rate", f"{summary_metrics['win_rate']:.1f}%")
                            st.markdown("---")
                        
                        st.markdown("**📊 Generated Reports:**")
                        
                        # 检查报告文件
                        report_html = Path("report_assets/scan_report.html")
                        report_csv = Path("report_assets/scan_results.csv")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if report_html.exists():
                                st.success("✅ HTML Report Generated")
                                with open(report_html, 'r', encoding='utf-8') as f:
                                    html_content = f.read()
                                    st.download_button(
                                        "📥 Download HTML Report",
                                        data=html_content,
                                        file_name=f"custom_scan_report_{task_id}.html",
                                        mime="text/html",
                                        key=f"download_html_{task_id}"
                                    )
                                
                                # 显示报告预览按钮
                                if st.button("👁️ Preview Report", key=f"preview_report_{task_id}"):
                                    st.session_state[f"show_report_{task_id}"] = True
                            else:
                                st.warning("⚠️ HTML report not found")
                        
                        with col2:
                            if report_csv.exists():
                                st.success("✅ CSV Results Generated")
                                with open(report_csv, 'r', encoding='utf-8') as f:
                                    csv_content = f.read()
                                    st.download_button(
                                        "📥 Download CSV Results",
                                        data=csv_content,
                                        file_name=f"custom_scan_results_{task_id}.csv",
                                        mime="text/csv",
                                        key=f"download_csv_{task_id}"
                                    )
                                
                                # 显示 CSV 预览
                                try:
                                    df = pd.read_csv(report_csv)
                                    st.dataframe(df, use_container_width=True)
                                except:
                                    pass
                            else:
                                st.warning("⚠️ CSV results not found")
                        
                        # 显示报告预览
                        if st.session_state.get(f"show_report_{task_id}", False):
                            st.markdown("---")
                            st.markdown("**📈 Report Preview:**")
                            
                            # 查找所有相关的图表文件
                            report_dir = Path("report_assets")
                            
                            # 从 HTML 报告中提取最新的图表文件名
                            latest_charts = {
                                'equity': [],
                                'comparison': None,
                                'details': None
                            }
                            
                            if report_html.exists():
                                try:
                                    with open(report_html, 'r', encoding='utf-8') as f:
                                        html_content = f.read()
                                        
                                        # 提取图片文件名
                                        import re
                                        
                                        # 查找权益曲线图
                                        equity_matches = re.findall(r'scan_equity_[^"]+\.png', html_content)
                                        latest_charts['equity'] = list(set(equity_matches))
                                        
                                        # 查找对比图
                                        comparison_match = re.search(r'scan_comparison_[^"]+\.png', html_content)
                                        if comparison_match:
                                            latest_charts['comparison'] = comparison_match.group(0)
                                        
                                        # 查找详细分析图
                                        details_match = re.search(r'scan_details_[^"]+\.png', html_content)
                                        if details_match:
                                            latest_charts['details'] = details_match.group(0)
                                except Exception as e:
                                    st.warning(f"Could not parse HTML report: {e}")
                            
                            # 显示权益曲线图
                            if latest_charts['equity']:
                                st.markdown("### 📈 Equity Curves")
                                for chart_name in sorted(latest_charts['equity']):
                                    chart_path = report_dir / chart_name
                                    if chart_path.exists():
                                        # 从文件名提取标的符号
                                        symbol = chart_name.split('_')[2]
                                        st.markdown(f"**{symbol}**")
                                        st.image(str(chart_path), use_container_width=True)
                            
                            # 显示对比图表
                            if latest_charts['comparison']:
                                comparison_path = report_dir / latest_charts['comparison']
                                if comparison_path.exists():
                                    st.markdown("### 📊 Performance Comparison")
                                    st.image(str(comparison_path), use_container_width=True)
                            
                            # 显示详细分析图表
                            if latest_charts['details']:
                                details_path = report_dir / latest_charts['details']
                                if details_path.exists():
                                    st.markdown("### 📈 Strategy Details Analysis")
                                    st.image(str(details_path), use_container_width=True)
                            
                            # 显示数据表格
                            if report_csv.exists():
                                st.markdown("### 📋 Scan Results")
                                df = pd.read_csv(report_csv)
                                st.dataframe(df, use_container_width=True)
                            
                            # 显示交易详情表格（使用 iframe 渲染）
                            if report_html.exists():
                                try:
                                    with open(report_html, 'r', encoding='utf-8') as f:
                                        html_content = f.read()
                                        
                                        # 检查是否有交易详情表格
                                        if "Trade Details" in html_content:
                                            st.markdown("### 📝 Trade Details")
                                            
                                            # 提取所有交易详情表格
                                            import re
                                            
                                            # 找到所有交易详情部分（包含完整的表格）
                                            trade_sections = re.findall(
                                                r'<div class="section">\s*<h2>📝 Trade Details - (.*?)</h2>\s*<table class="data-table">(.*?)</table>\s*</div>',
                                                html_content,
                                                re.DOTALL
                                            )
                                            
                                            if trade_sections:
                                                # 构建完整的 HTML（包含样式）
                                                full_html = """
                                                <!DOCTYPE html>
                                                <html>
                                                <head>
                                                    <meta charset="UTF-8">
                                                    <style>
                                                        body {
                                                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                                            margin: 0;
                                                            padding: 20px;
                                                            background: white;
                                                        }
                                                        .section {
                                                            margin: 30px 0;
                                                        }
                                                        h3 {
                                                            color: #2d3748;
                                                            margin-bottom: 15px;
                                                            font-size: 18px;
                                                            border-bottom: 2px solid #667eea;
                                                            padding-bottom: 8px;
                                                        }
                                                        .data-table {
                                                            width: 100%;
                                                            border-collapse: collapse;
                                                            font-size: 13px;
                                                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                                        }
                                                        .data-table thead {
                                                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                                        }
                                                        .data-table th {
                                                            color: white;
                                                            padding: 12px 8px;
                                                            text-align: center;
                                                            font-weight: bold;
                                                            border: 1px solid #5a67d8;
                                                        }
                                                        .data-table td {
                                                            padding: 10px 8px;
                                                            border: 1px solid #e5e7eb;
                                                            text-align: center;
                                                        }
                                                        .data-table tbody tr:nth-child(odd) {
                                                            background-color: #f9fafb;
                                                        }
                                                        .data-table tbody tr:hover {
                                                            background-color: #e5e7eb;
                                                        }
                                                        .positive {
                                                            color: #10b981;
                                                            font-weight: bold;
                                                        }
                                                        .negative {
                                                            color: #ef4444;
                                                            font-weight: bold;
                                                        }
                                                    </style>
                                                </head>
                                                <body>
                                                """
                                                
                                                for symbol_name, table_content in trade_sections:
                                                    full_html += f"""
                                                    <div class="section">
                                                        <h3>{symbol_name}</h3>
                                                        <table class="data-table">
                                                            {table_content}
                                                        </table>
                                                    </div>
                                                    """
                                                
                                                full_html += """
                                                </body>
                                                </html>
                                                """
                                                
                                                # 使用 components 渲染
                                                st.components.v1.html(full_html, height=600, scrolling=True)
                                            else:
                                                st.info("No trade details table found in report")
                                except Exception as e:
                                    st.error(f"Could not extract trade details: {e}")
                                    import traceback
                                    st.code(traceback.format_exc())
                            
                            if st.button("❌ Close Preview", key=f"close_preview_{task_id}"):
                                st.session_state[f"show_report_{task_id}"] = False
                                st.rerun()
                    
                    # 显示实时日志
                    st.markdown("---")
                    st.markdown("**📄 Real-time Logs:**")
                    logs = task.get_logs()
                    
                    if logs:
                        # 控制选项
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            show_count = st.selectbox(
                                "Show logs",
                                options=[50, 100, 200, 500, "All"],
                                index=2,  # 默认200
                                key=f"log_count_{task_id}"
                            )
                        with col2:
                            st.caption(f"📊 Total: {len(logs)} log entries")
                        with col3:
                            if len(logs) > 50:
                                full_log_text = "\n".join(logs)
                                st.download_button(
                                    "📥",
                                    data=full_log_text,
                                    file_name=f"{task_id}_logs.txt",
                                    mime="text/plain",
                                    key=f"save_logs_{task_id}",
                                    help="Download full logs"
                                )
                        
                        # 显示日志
                        if show_count == "All":
                            display_logs = logs
                        else:
                            display_logs = logs[-show_count:]
                        
                        log_text = "\n".join(display_logs)
                        st.text_area(
                            "Logs",
                            value=log_text,
                            height=400,
                            key=f"custom_log_display_{task_id}",
                            label_visibility="collapsed"
                        )
                        
                        # 任务运行中时显示提示
                        if task.status == "running":
                            st.info("🔄 Task is running... Logs auto-refresh every 2 seconds")
                    else:
                        st.info("⏳ Waiting for logs to output...")
            
            # 自动刷新逻辑
            if auto_refresh:
                # 检查是否有运行中的任务
                has_running = any(task.status == "running" for task in custom_scan_tasks.values())
                if has_running:
                    time.sleep(2)
                    st.rerun()


# ==================== Results View ====================
if __name__ == "__main__":
    pass  # Streamlit handles the execution


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>Quantitative Trading Strategy Platform v1.0 | Powered by Streamlit</p>
    <p>© 2025 All Rights Reserved</p>
</div>
""", unsafe_allow_html=True)

