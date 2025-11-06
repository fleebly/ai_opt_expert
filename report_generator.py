#!/usr/bin/env python3
"""
回测报告生成器

生成精美的HTML报告和图表
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # 使用非GUI后端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = 'backtest_reports'):
        """初始化"""
        self.output_dir = output_dir
        Path(output_dir).mkdir(exist_ok=True)
    
    def generate_report(
        self,
        result: Dict,
        symbol: str,
        strategy: str = 'long_call'
    ) -> str:
        """
        生成完整报告
        
        Args:
            result: BacktestResult 对象
            symbol: 股票代码
            strategy: 策略名称
        
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 生成回测报告: {symbol}")
        logger.info(f"{'='*70}\n")
        
        # 1. 绘制收益曲线
        logger.info("📈 绘制收益曲线...")
        equity_chart = self._plot_equity_curve(
            result.equity_curve,
            result.initial_capital,
            result.trades,
            symbol,
            timestamp
        )
        
        # 2. 绘制交易分布
        logger.info("📊 绘制交易分布...")
        trade_chart = self._plot_trade_distribution(
            result.trades,
            symbol,
            timestamp
        )
        
        # 3. 生成HTML报告
        logger.info("📄 生成HTML报告...")
        report_path = self._generate_html_report(
            result,
            symbol,
            strategy,
            equity_chart,
            trade_chart,
            timestamp
        )
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ 报告已生成: {report_path}")
        logger.info(f"{'='*70}\n")
        
        return report_path
    
    def _plot_equity_curve(
        self,
        equity_curve: pd.Series,
        initial_capital: float,
        trades: List,
        symbol: str,
        timestamp: str
    ) -> str:
        """绘制收益曲线（带交易标注）"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
        
        # 1. 资金曲线
        ax1.plot(equity_curve.index, equity_curve.values, 
                linewidth=2.5, color='#2E86AB', label='Portfolio Value', zorder=1)
        ax1.axhline(y=initial_capital, color='gray', 
                   linestyle='--', alpha=0.6, linewidth=1.5, label='Initial Capital')
        ax1.fill_between(equity_curve.index, initial_capital, 
                         equity_curve.values, alpha=0.2, color='#2E86AB')
        
        # 标注交易入场和离场点
        if trades:
            for i, trade in enumerate(trades):
                try:
                    # 解析日期
                    entry_date = pd.to_datetime(trade.entry_date)
                    exit_date = pd.to_datetime(trade.exit_date)
                    
                    # 获取对应时间点的资金值
                    if entry_date in equity_curve.index:
                        entry_value = equity_curve.loc[entry_date]
                    else:
                        # 找到最接近的日期
                        entry_value = equity_curve.asof(entry_date)
                    
                    if exit_date in equity_curve.index:
                        exit_value = equity_curve.loc[exit_date]
                    else:
                        exit_value = equity_curve.asof(exit_date)
                    
                    # 入场标注（绿色向上三角）
                    ax1.scatter(entry_date, entry_value, 
                               marker='^', s=200, c='green', 
                               edgecolors='darkgreen', linewidths=2,
                               zorder=5, alpha=0.8)
                    
                    # 离场标注（红色向下三角）
                    ax1.scatter(exit_date, exit_value, 
                               marker='v', s=200, c='red', 
                               edgecolors='darkred', linewidths=2,
                               zorder=5, alpha=0.8)
                    
                    # 标注收益
                    pnl = trade.pnl
                    pnl_pct = trade.pnl_pct
                    
                    # 在离场点上方/下方显示收益
                    y_offset = (equity_curve.max() - equity_curve.min()) * 0.03
                    if pnl > 0:
                        text_y = exit_value + y_offset
                        color = 'green'
                        va = 'bottom'
                    else:
                        text_y = exit_value - y_offset
                        color = 'red'
                        va = 'top'
                    
                    # 添加文本标注
                    ax1.annotate(
                        f'#{i+1}\n${pnl:+,.0f}\n({pnl_pct:+.1%})',
                        xy=(exit_date, exit_value),
                        xytext=(exit_date, text_y),
                        fontsize=9,
                        fontweight='bold',
                        color=color,
                        ha='center',
                        va=va,
                        bbox=dict(boxstyle='round,pad=0.5', 
                                facecolor='white', 
                                edgecolor=color, 
                                alpha=0.9,
                                linewidth=1.5),
                        zorder=10
                    )
                    
                    # 连线（从入场到离场）
                    line_color = 'green' if pnl > 0 else 'red'
                    ax1.plot([entry_date, exit_date], [entry_value, exit_value],
                            color=line_color, linestyle=':', linewidth=1.5, 
                            alpha=0.5, zorder=2)
                    
                except Exception as e:
                    logger.warning(f"无法标注交易 #{i+1}: {e}")
                    continue
        
        ax1.set_title(f'{symbol} - Portfolio Equity Curve with Trade Markers', 
                     fontsize=18, fontweight='bold', pad=20)
        ax1.set_ylabel('Portfolio Value ($)', fontsize=13, fontweight='bold')
        ax1.legend(loc='upper left', fontsize=11)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 添加统计信息
        final_value = equity_curve.iloc[-1]
        total_return = (final_value - initial_capital) / initial_capital
        total_pnl = sum([t.pnl for t in trades]) if trades else 0
        
        textstr = f'Initial: ${initial_capital:,.0f}\n'
        textstr += f'Final: ${final_value:,.0f}\n'
        textstr += f'Return: {total_return:+.2%}\n'
        textstr += f'Total P&L: ${total_pnl:+,.0f}'
        
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.95, pad=0.8)
        ax1.text(0.02, 0.98, textstr, transform=ax1.transAxes,
                fontsize=12, verticalalignment='top', bbox=props, 
                fontweight='bold')
        
        # 添加图例说明
        legend_text = '△ Entry (入场)  ▽ Exit (离场)'
        ax1.text(0.98, 0.02, legend_text, transform=ax1.transAxes,
                fontsize=10, ha='right', va='bottom',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # 2. 回撤曲线
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max
        
        ax2.fill_between(drawdown.index, 0, drawdown.values * 100,
                        color='#A23B72', alpha=0.6)
        ax2.plot(drawdown.index, drawdown.values * 100,
                color='#A23B72', linewidth=2.5, label='Drawdown')
        
        ax2.set_title('Drawdown', fontsize=16, fontweight='bold', pad=15)
        ax2.set_xlabel('Date', fontsize=13, fontweight='bold')
        ax2.set_ylabel('Drawdown (%)', fontsize=13, fontweight='bold')
        ax2.legend(loc='best', fontsize=11)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 保存图表
        chart_path = os.path.join(self.output_dir, f'{symbol}_equity_{timestamp}.png')
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return chart_path
    
    def _plot_trade_distribution(
        self,
        trades: List,
        symbol: str,
        timestamp: str
    ) -> str:
        """绘制交易分布"""
        if not trades:
            return None
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 11))
        fig.suptitle(f'{symbol} - Trade Analysis', 
                    fontsize=18, fontweight='bold', y=0.995)
        
        # 准备数据
        pnls = [t.pnl for t in trades]
        returns = [t.pnl_pct * 100 for t in trades]  # 转换为百分比
        hold_days = [(datetime.strptime(t.exit_date, '%Y-%m-%d') - 
                     datetime.strptime(t.entry_date, '%Y-%m-%d')).days 
                     for t in trades]
        
        # 1. P&L分布
        colors = ['#10b981' if p > 0 else '#ef4444' for p in pnls]
        bars = ax1.bar(range(len(pnls)), pnls, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=1.2)
        ax1.set_title('P&L per Trade', fontweight='bold', fontsize=14)
        ax1.set_xlabel('Trade #', fontweight='bold')
        ax1.set_ylabel('P&L ($)', fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # 2. 收益率分布
        n, bins, patches = ax2.hist(returns, bins=20, color='steelblue', alpha=0.7, edgecolor='black', linewidth=1)
        # 颜色编码
        for i, patch in enumerate(patches):
            if bins[i] < 0:
                patch.set_facecolor('#ef4444')
            else:
                patch.set_facecolor('#10b981')
        
        ax2.axvline(x=0, color='black', linestyle='--', linewidth=2)
        ax2.set_title('Return Distribution', fontweight='bold', fontsize=14)
        ax2.set_xlabel('Return (%)', fontweight='bold')
        ax2.set_ylabel('Frequency', fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # 3. 持有时间分布
        ax3.hist(hold_days, bins=15, color='coral', alpha=0.8, edgecolor='black', linewidth=1)
        ax3.set_title('Holding Period Distribution', fontweight='bold', fontsize=14)
        ax3.set_xlabel('Days Held', fontweight='bold')
        ax3.set_ylabel('Frequency', fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # 添加平均线
        avg_hold = np.mean(hold_days)
        ax3.axvline(x=avg_hold, color='red', linestyle='--', linewidth=2, label=f'Avg: {avg_hold:.0f} days')
        ax3.legend()
        
        # 4. 累计收益
        cumulative_pnl = np.cumsum(pnls)
        ax4.plot(cumulative_pnl, linewidth=2.5, color='darkgreen', marker='o', markersize=5, markeredgecolor='black', markeredgewidth=0.5)
        ax4.axhline(y=0, color='black', linestyle='--', linewidth=1.2)
        ax4.fill_between(range(len(cumulative_pnl)), 0, cumulative_pnl, 
                        alpha=0.3, color='darkgreen')
        ax4.set_title('Cumulative P&L', fontweight='bold', fontsize=14)
        ax4.set_xlabel('Trade #', fontweight='bold')
        ax4.set_ylabel('Cumulative P&L ($)', fontweight='bold')
        ax4.grid(True, alpha=0.3, linestyle='--')
        
        # 保存图表
        chart_path = os.path.join(self.output_dir, f'{symbol}_trades_{timestamp}.png')
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return chart_path
    
    def _generate_html_report(
        self,
        result,
        symbol: str,
        strategy: str,
        equity_chart: str,
        trade_chart: str,
        timestamp: str
    ) -> str:
        """生成HTML报告"""
        
        # 准备交易详情表格
        trades_html = ""
        if result.trades:
            trades_html = "<h2>📝 Trade Details</h2>\n<table>\n"
            trades_html += "<tr><th>#</th><th>Entry Date</th><th>Exit Date</th>"
            trades_html += "<th>Strategy</th><th>Entry Stock</th><th>Exit Stock</th>"
            trades_html += "<th>Stock Change</th><th>Option Entry</th><th>Option Exit</th>"
            trades_html += "<th>P&L</th><th>Return</th></tr>\n"
            
            for i, trade in enumerate(result.trades, 1):
                stock_change = ((trade.exit_underlying - trade.entry_underlying) / 
                              trade.entry_underlying)
                row_class = 'profit' if trade.pnl > 0 else 'loss'
                
                trades_html += f"<tr class='{row_class}'>"
                trades_html += f"<td>{i}</td>"
                trades_html += f"<td>{trade.entry_date}</td>"
                trades_html += f"<td>{trade.exit_date}</td>"
                trades_html += f"<td>{trade.strategy.upper()}</td>"
                trades_html += f"<td>${trade.entry_underlying:.2f}</td>"
                trades_html += f"<td>${trade.exit_underlying:.2f}</td>"
                trades_html += f"<td class='{'profit' if stock_change > 0 else 'loss'}'>{stock_change:+.2%}</td>"
                trades_html += f"<td>${trade.entry_price:.2f}</td>"
                trades_html += f"<td>${trade.exit_price:.2f}</td>"
                trades_html += f"<td>${trade.pnl:+,.2f}</td>"
                trades_html += f"<td>{trade.pnl_pct:+.1%}</td>"
                trades_html += "</tr>\n"
            
            trades_html += "</table>\n"
        
        # HTML模板
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Report - {symbol}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
            color: white;
            padding: 50px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 3em;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header .subtitle {{
            font-size: 1.3em;
            opacity: 0.95;
            font-weight: 500;
        }}
        
        .content {{
            padding: 50px;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 50px;
        }}
        
        .metric-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.2);
        }}
        
        .metric-card.highlight {{
            background: linear-gradient(135deg, #F093FB 0%, #F5576C 100%);
            color: white;
        }}
        
        .metric-label {{
            font-size: 1em;
            opacity: 0.85;
            margin-bottom: 10px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        
        .metric-value.positive {{
            color: #10b981;
        }}
        
        .metric-value.negative {{
            color: #ef4444;
        }}
        
        .chart-section {{
            margin: 50px 0;
        }}
        
        .chart-section h2 {{
            color: #2E86AB;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 4px solid #2E86AB;
            font-size: 1.8em;
        }}
        
        .chart-section img {{
            width: 100%;
            border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            margin-bottom: 25px;
            transition: transform 0.3s ease;
        }}
        
        .chart-section img:hover {{
            transform: scale(1.02);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 25px;
            background: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-radius: 12px;
            overflow: hidden;
        }}
        
        th {{
            background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
            color: white;
            padding: 18px 15px;
            text-align: left;
            font-weight: 700;
            font-size: 0.95em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 15px;
            border-bottom: 1px solid #e5e7eb;
            font-size: 0.95em;
        }}
        
        tr:hover {{
            background-color: #f9fafb;
        }}
        
        tr.profit {{
            background-color: #ecfdf5;
        }}
        
        tr.loss {{
            background-color: #fef2f2;
        }}
        
        .profit {{
            color: #10b981;
            font-weight: bold;
        }}
        
        .loss {{
            color: #ef4444;
            font-weight: bold;
        }}
        
        .footer {{
            background: #f9fafb;
            padding: 30px;
            text-align: center;
            color: #6b7280;
            font-size: 0.95em;
            border-top: 3px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Backtest Report</h1>
            <div class="subtitle">{symbol} | {strategy.upper()} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="content">
            <h2 style="color: #2E86AB; margin-bottom: 35px; font-size: 2em;">📈 Performance Metrics</h2>
            
            <div class="metrics">
                <div class="metric-card highlight">
                    <div class="metric-label">Total Return</div>
                    <div class="metric-value">{result.total_return:+.2%}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value">{result.sharpe_ratio:.2f}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value negative">{result.max_drawdown:.2%}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value {'positive' if result.win_rate > 0.5 else ''}">{result.win_rate:.1%}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value">{result.num_trades}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Avg Win</div>
                    <div class="metric-value positive">${result.avg_win:.2f}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Avg Loss</div>
                    <div class="metric-value negative">${result.avg_loss:.2f}</div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Profit Factor</div>
                    <div class="metric-value {'positive' if abs(result.avg_win/result.avg_loss) > 1 else 'negative' if result.avg_loss != 0 else ''}">{abs(result.avg_win/result.avg_loss) if result.avg_loss != 0 else 0:.2f}</div>
                </div>
            </div>
            
            <div class="chart-section">
                <h2>📊 Equity Curve & Drawdown</h2>
                <img src="{os.path.basename(equity_chart)}" alt="Equity Curve">
            </div>
            
            {f'<div class="chart-section"><h2>📊 Trade Analysis</h2><img src="{os.path.basename(trade_chart)}" alt="Trade Analysis"></div>' if trade_chart else ''}
            
            {trades_html}
        </div>
        
        <div class="footer">
            <strong>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong><br>
            Backtest Period: {result.equity_curve.index[0].strftime('%Y-%m-%d')} to {result.equity_curve.index[-1].strftime('%Y-%m-%d')}
        </div>
    </div>
</body>
</html>
"""
        
        # 保存HTML报告
        report_path = os.path.join(self.output_dir, f'{symbol}_report_{timestamp}.html')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return report_path


if __name__ == '__main__':
    print("Report Generator Module")



