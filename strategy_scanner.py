#!/usr/bin/env python3
"""
策略扫描器：从 JSON 读取策略，对多个标的进行回测（每个标的只用其专属策略）
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest_engine import OptionBacktest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyScanner:
    def __init__(
        self,
        strategy_dir: str = "strategies",
        initial_capital: float = 10000.0,
        output_dir: str = "report_assets"
    ):
        self.strategy_dir = Path(strategy_dir)
        self.initial_capital = initial_capital
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.all_results = []
        self.backtest_results = {}  # 存储详细回测结果

    def load_strategy(self, json_path: Path) -> Dict[str, Any]:
        """从 JSON 加载单个策略"""
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def scan_symbols_with_strategy(
        self,
        strategy_config: Dict[str, Any],
        symbols: List[str],
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """用一个策略扫描多个标的（保持兼容，但实际我们只传一个 symbol）"""
        strategy_name = strategy_config['name']
        signal_weights = strategy_config['signal_weights']
        params = strategy_config.get('params', {})

        profit_target = params.get('profit_target', 5.0)
        stop_loss = params.get('stop_loss', -0.5)
        max_holding_days = params.get('max_holding_days', 30)
        position_size = params.get('position_size', 0.1)

        results = []

        for symbol in symbols:
            logger.info(f"🔍 扫描 {symbol} 使用策略: {strategy_name}")
            try:
                backtest = OptionBacktest(
                    initial_capital=self.initial_capital,
                    use_real_prices=True
                )

                result = backtest.run_backtest(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    strategy='auto',
                    entry_signal=signal_weights,
                    profit_target=profit_target,
                    stop_loss=stop_loss,
                    max_holding_days=max_holding_days,
                    position_size=position_size
                )

                record = {
                    'symbol': symbol,
                    'strategy_name': strategy_name,
                    'total_return': result.total_return,
                    'win_rate': result.win_rate,
                    'sharpe_ratio': result.sharpe_ratio,
                    'max_drawdown': result.max_drawdown,
                    'num_trades': result.num_trades,
                    'avg_win': result.avg_win,
                    'avg_loss': result.avg_loss
                }
                results.append(record)
                self.all_results.append(record)
                
                # 保存完整回测结果（用于生成权益曲线）
                self.backtest_results[f"{symbol}_{strategy_name}"] = result

            except Exception as e:
                logger.error(f"❌ {symbol} 回测失败: {e}")
                self.all_results.append({
                    'symbol': symbol,
                    'strategy_name': strategy_name,
                    'total_return': -1.0,
                    'win_rate': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': -1.0,
                    'num_trades': 0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0
                })

        return results

    def run_scan(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        output_csv: str = None,
        output_html: str = None,
        strategy_files = None  # 可以是 Dict[str, Path] 或 List[Tuple[str, Path]]
    ):
        """
        主扫描流程
        
        参数:
            symbols: 标的列表（用于自动查找策略时）
            start_date: 回测开始日期
            end_date: 回测结束日期
            output_csv: CSV 输出文件路径
            output_html: HTML 输出文件路径
            strategy_files: 可选的策略文件
                - Dict[str, Path]: 字典映射 {symbol: Path}（一个标的一个策略）
                - List[Tuple[str, Path]]: 列表 [(symbol, Path), ...]（支持一个标的多个策略）
                - None: 自动查找每个标的的最新策略
        """
        if not self.strategy_dir.exists():
            raise FileNotFoundError(f"策略目录不存在: {self.strategy_dir}")

        # 构建要扫描的 (symbol, strategy_file) 对列表
        scan_pairs = []
        
        if strategy_files is None:
            # 自动模式：为每个标的查找最新策略
            logger.info(f"🎯 自动模式：为 {len(symbols)} 个标的查找最新策略...")
            for symbol in symbols:
                pattern = f"{symbol}_*.json"
                found_files = list(self.strategy_dir.glob(pattern))
                
                if not found_files:
                    logger.warning(f"⚠️ 未找到 {symbol} 的策略文件（应匹配 {pattern}）")
                    continue

                # 按文件修改时间排序，获取最新的策略文件
                found_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest_file = found_files[0]
                
                logger.info(f"✅ {symbol} 使用最新策略: {latest_file.name}")
                scan_pairs.append((symbol, latest_file))
                
        elif isinstance(strategy_files, list):
            # 列表模式：支持一个标的多个策略
            scan_pairs = strategy_files
            unique_symbols = set([s for s, _ in scan_pairs])
            logger.info(f"🎯 指定模式：{len(unique_symbols)} 个标的 × {len(scan_pairs)} 个测试")
            
        elif isinstance(strategy_files, dict):
            # 字典模式：一个标的一个策略（向后兼容）
            scan_pairs = list(strategy_files.items())
            logger.info(f"🎯 指定模式：{len(scan_pairs)} 个标的扫描...")
        
        else:
            raise ValueError(f"strategy_files 类型不支持: {type(strategy_files)}")

        # 执行扫描
        for symbol, strategy_file in scan_pairs:
            logger.info(f"📋 扫描 {symbol} 使用策略: {strategy_file.name}")
            try:
                strategy = self.load_strategy(strategy_file)
                # 每次只传一个 symbol
                self.scan_symbols_with_strategy(strategy, [symbol], start_date, end_date)
            except Exception as e:
                logger.error(f"❌ 加载或运行策略 {strategy_file.name} 失败: {e}")

        # 转为 DataFrame 并排序
        if not self.all_results:
            logger.warning("⚠️ 无任何回测结果生成")
            df = pd.DataFrame()
        else:
            df = pd.DataFrame(self.all_results)
            df = df.sort_values(['symbol', 'strategy_name', 'total_return'], ascending=[True, True, False])

        # 保存 CSV
        if output_csv and not df.empty:
            df.to_csv(output_csv, index=False, encoding='utf-8-sig')
            logger.info(f"✅ 扫描结果已保存至: {output_csv}")

        # 生成简单 HTML 报告（可选）
        if output_html and not df.empty:
            self._generate_html_report(df, output_html)

        return df

    def _plot_equity_curves(self, timestamp: str) -> List[str]:
        """生成每个标的的权益曲线图"""
        chart_paths = []
        
        for key, result in self.backtest_results.items():
            symbol, strategy_name = key.split('_', 1)
            
            try:
                fig, ax = plt.subplots(figsize=(16, 10))
                
                # 绘制权益曲线
                equity_curve = result.equity_curve
                initial_capital = result.initial_capital
                
                ax.plot(equity_curve.index, equity_curve.values, 
                       linewidth=2.5, color='#2E86AB', label='Portfolio Value', zorder=1)
                ax.axhline(y=initial_capital, color='gray', 
                          linestyle='--', alpha=0.6, linewidth=1.5, label='Initial Capital')
                ax.fill_between(equity_curve.index, initial_capital, 
                               equity_curve.values, alpha=0.2, color='#2E86AB')
                
                # 标注交易点
                if result.trades:
                    for i, trade in enumerate(result.trades):
                        try:
                            entry_date = pd.to_datetime(trade.entry_date)
                            exit_date = pd.to_datetime(trade.exit_date)
                            
                            entry_value = equity_curve.asof(entry_date)
                            exit_value = equity_curve.asof(exit_date)
                            
                            # 入场点（绿色三角）
                            ax.scatter(entry_date, entry_value, 
                                     marker='^', s=200, c='green', 
                                     edgecolors='darkgreen', linewidths=2,
                                     zorder=5, alpha=0.8)
                            
                            # 出场点（红色三角）
                            ax.scatter(exit_date, exit_value, 
                                     marker='v', s=200, c='red', 
                                     edgecolors='darkred', linewidths=2,
                                     zorder=5, alpha=0.8)
                            
                            # 标注收益
                            pnl = trade.pnl
                            pnl_pct = trade.pnl_pct
                            
                            y_offset = (equity_curve.max() - equity_curve.min()) * 0.03
                            if pnl > 0:
                                text_y = exit_value + y_offset
                                color = 'green'
                                va = 'bottom'
                            else:
                                text_y = exit_value - y_offset
                                color = 'red'
                                va = 'top'
                            
                            ax.annotate(
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
                                        linewidth=1.5)
                            )
                        except Exception as e:
                            logger.warning(f"无法标注交易 #{i+1}: {e}")
                
                # 设置标题和标签
                ax.set_title(f'{symbol} - {strategy_name} Equity Curve', 
                           fontsize=16, fontweight='bold', pad=20)
                ax.set_xlabel('Date', fontsize=12, fontweight='bold')
                ax.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
                ax.legend(loc='upper left', fontsize=11)
                ax.grid(True, alpha=0.3, linestyle='--')
                
                # 格式化
                ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
                fig.autofmt_xdate()
                
                plt.tight_layout()
                
                # 保存图表
                chart_path = self.output_dir / f"scan_equity_{symbol}_{timestamp}.png"
                plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                
                chart_paths.append(str(chart_path))
                logger.info(f"📈 权益曲线已生成: {chart_path.name}")
                
            except Exception as e:
                logger.error(f"生成 {symbol} 权益曲线失败: {e}")
        
        return chart_paths
    
    def _plot_performance_comparison(self, df: pd.DataFrame, output_dir: str, timestamp: str) -> str:
        """绘制性能对比图（显示所有策略组合）"""
        if df.empty:
            return None
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle('📊 Strategy Performance Analysis (All Combinations)', 
                    fontsize=20, fontweight='bold', y=0.995)
        
        # 创建组合标签（Symbol - Strategy）
        df['combo_label'] = df['symbol'] + '\n' + df['strategy_name']
        
        # 1. 总收益率对比（所有组合）
        colors = ['#10b981' if r > 0 else '#ef4444' for r in df['total_return']]
        bars1 = ax1.bar(range(len(df)), df['total_return'] * 100, 
                       color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=1.5)
        ax1.set_title('Total Return Comparison', fontweight='bold', fontsize=15)
        ax1.set_ylabel('Total Return (%)', fontweight='bold', fontsize=12)
        ax1.set_xlabel('Symbol - Strategy', fontweight='bold', fontsize=12)
        ax1.set_xticks(range(len(df)))
        ax1.set_xticklabels(df['combo_label'], rotation=45, ha='right', fontsize=9)
        ax1.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # 添加数值标签
        for i, bar in enumerate(bars1):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom' if height > 0 else 'top',
                    fontweight='bold', fontsize=8)
        
        # 2. 夏普比率对比
        colors_sharpe = ['#2E86AB' if s > 1 else '#F5A623' if s > 0 else '#ef4444' 
                        for s in df['sharpe_ratio']]
        bars2 = ax2.bar(range(len(df)), df['sharpe_ratio'],
                       color=colors_sharpe, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax2.axhline(y=1, color='green', linestyle='--', linewidth=2, alpha=0.6, label='Good (>1)')
        ax2.axhline(y=0, color='red', linestyle='--', linewidth=2, alpha=0.6)
        ax2.set_title('Sharpe Ratio Comparison', fontweight='bold', fontsize=15)
        ax2.set_ylabel('Sharpe Ratio', fontweight='bold', fontsize=12)
        ax2.set_xlabel('Symbol - Strategy', fontweight='bold', fontsize=12)
        ax2.set_xticks(range(len(df)))
        ax2.set_xticklabels(df['combo_label'], rotation=45, ha='right', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y', linestyle='--')
        ax2.legend(loc='best')
        
        for i, bar in enumerate(bars2):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}', ha='center', va='bottom' if height > 0 else 'top',
                    fontweight='bold', fontsize=8)
        
        # 3. 胜率对比
        bars3 = ax3.bar(range(len(df)), df['win_rate'] * 100,
                       color='#A23B72', alpha=0.8, edgecolor='black', linewidth=1.5)
        ax3.axhline(y=50, color='orange', linestyle='--', linewidth=2, alpha=0.6, label='Break-even (50%)')
        ax3.set_title('Win Rate Comparison', fontweight='bold', fontsize=15)
        ax3.set_ylabel('Win Rate (%)', fontweight='bold', fontsize=12)
        ax3.set_xlabel('Symbol - Strategy', fontweight='bold', fontsize=12)
        ax3.set_xticks(range(len(df)))
        ax3.set_xticklabels(df['combo_label'], rotation=45, ha='right', fontsize=9)
        ax3.set_ylim(0, 100)
        ax3.grid(True, alpha=0.3, axis='y', linestyle='--')
        ax3.legend(loc='best')
        
        for i, bar in enumerate(bars3):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%', ha='center', va='bottom',
                    fontweight='bold', fontsize=8)
        
        # 4. 风险-收益散点图
        scatter = ax4.scatter(df['max_drawdown'] * 100, df['total_return'] * 100,
                             s=df['num_trades'] * 20, alpha=0.6,
                             c=df['sharpe_ratio'], cmap='RdYlGn', 
                             edgecolors='black', linewidth=2)
        
        # 添加标签（Symbol首字母 + 策略编号）
        for idx, row in df.iterrows():
            label = f"{row['symbol'][:2]}-{row['strategy_name'][:10]}"
            ax4.annotate(label, 
                        (row['max_drawdown'] * 100, row['total_return'] * 100),
                        xytext=(5, 5), textcoords='offset points',
                        fontweight='bold', fontsize=8,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        ax4.axhline(y=0, color='black', linestyle='--', linewidth=1.5, alpha=0.5)
        ax4.axvline(x=0, color='black', linestyle='--', linewidth=1.5, alpha=0.5)
        ax4.set_title('Risk-Return Profile (All Combinations)', fontweight='bold', fontsize=15)
        ax4.set_xlabel('Max Drawdown (%)', fontweight='bold', fontsize=12)
        ax4.set_ylabel('Total Return (%)', fontweight='bold', fontsize=12)
        ax4.grid(True, alpha=0.3, linestyle='--')
        
        # 添加颜色条
        cbar = plt.colorbar(scatter, ax=ax4)
        cbar.set_label('Sharpe Ratio', fontweight='bold', fontsize=11)
        
        # 保存图表
        chart_path = os.path.join(output_dir, f'scan_comparison_{timestamp}.png')
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"📊 对比图表已生成: {chart_path}")
        return chart_path
    
    def _plot_strategy_details(self, df: pd.DataFrame, output_dir: str, timestamp: str) -> str:
        """绘制策略详细分析图（显示所有策略组合）"""
        if df.empty:
            return None
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle('📈 Strategy Performance Details (All Combinations)', 
                    fontsize=20, fontweight='bold', y=0.995)
        
        # 创建组合标签
        df['combo_label'] = df['symbol'] + '\n' + df['strategy_name']
        
        # 1. 所有策略收益率（分组显示）
        symbols = df['symbol'].unique()
        
        if len(symbols) == 1:
            # 单标的：直接显示所有策略
            colors = ['#10b981' if r > 0 else '#ef4444' for r in df['total_return']]
            bars = ax1.bar(range(len(df)), df['total_return'] * 100, 
                          color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
            ax1.set_xticks(range(len(df)))
            ax1.set_xticklabels(df['strategy_name'], rotation=45, ha='right', fontsize=9)
            ax1.set_title(f'{symbols[0]} - All Strategies Return', fontweight='bold', fontsize=15)
        else:
            # 多标的：分组显示
            x = np.arange(len(symbols))
            max_strategies = max(df.groupby('symbol').size())
            width = 0.8 / max_strategies
            
            for i, (symbol, group) in enumerate(df.groupby('symbol')):
                returns = (group['total_return'] * 100).tolist()
                colors = ['#10b981' if r > 0 else '#ef4444' for r in returns]
                positions = x[i] + np.arange(len(returns)) * width - (len(returns) * width / 2)
                ax1.bar(positions, returns, width * 0.9, alpha=0.8, edgecolor='black', linewidth=0.5)
            
            ax1.set_xticks(x)
            ax1.set_xticklabels(symbols)
            ax1.set_title('All Strategies Return by Symbol', fontweight='bold', fontsize=15)
        
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=1.5)
        ax1.set_ylabel('Total Return (%)', fontweight='bold', fontsize=12)
        ax1.set_xlabel('Strategy' if len(symbols) == 1 else 'Symbol', fontweight='bold', fontsize=12)
        ax1.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # 2. 交易次数 vs 收益
        if len(symbols) == 1:
            # 单标的：每个策略一个点
            scatter = ax2.scatter(df['num_trades'], df['total_return'] * 100,
                                s=150, alpha=0.7, c=df['sharpe_ratio'], 
                                cmap='RdYlGn', edgecolors='black', linewidth=1.5)
            # 标注策略名
            for idx, row in df.iterrows():
                ax2.annotate(row['strategy_name'][:15], 
                           (row['num_trades'], row['total_return'] * 100),
                           xytext=(5, 5), textcoords='offset points', fontsize=8)
        else:
            # 多标的：按标的分颜色
            for symbol in symbols:
                symbol_df = df[df['symbol'] == symbol]
                ax2.scatter(symbol_df['num_trades'], symbol_df['total_return'] * 100,
                          label=symbol, s=150, alpha=0.7, edgecolors='black', linewidth=1.5)
            ax2.legend(loc='best', fontsize=10)
        
        ax2.axhline(y=0, color='black', linestyle='--', linewidth=1.5, alpha=0.5)
        ax2.set_title('Number of Trades vs Return', fontweight='bold', fontsize=15)
        ax2.set_xlabel('Number of Trades', fontweight='bold', fontsize=12)
        ax2.set_ylabel('Total Return (%)', fontweight='bold', fontsize=12)
        ax2.grid(True, alpha=0.3, linestyle='--')
        
        # 3. 平均盈亏对比（所有策略）
        x_pos = np.arange(len(df))
        width = 0.35
        
        bars1 = ax3.bar(x_pos - width/2, df['avg_win'], width,
                       label='Avg Win', color='#10b981', alpha=0.8, edgecolor='black', linewidth=1.5)
        bars2 = ax3.bar(x_pos + width/2, df['avg_loss'], width,
                       label='Avg Loss', color='#ef4444', alpha=0.8, edgecolor='black', linewidth=1.5)
        
        ax3.set_title('Average Win vs Loss (All Strategies)', fontweight='bold', fontsize=15)
        ax3.set_ylabel('Amount ($)', fontweight='bold', fontsize=12)
        ax3.set_xlabel('Strategy Combination', fontweight='bold', fontsize=12)
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(df['combo_label'], rotation=45, ha='right', fontsize=7)
        ax3.legend(loc='best', fontsize=11)
        ax3.grid(True, alpha=0.3, axis='y', linestyle='--')
        
        # 添加数值标签（简化）
        for i, (win, loss) in enumerate(zip(df['avg_win'], df['avg_loss'])):
            if i % 2 == 0:  # 只标注部分，避免拥挤
                ax3.text(i - width/2, win, f'${win:.0f}', ha='center', va='bottom', fontsize=7)
                ax3.text(i + width/2, loss, f'${loss:.0f}', ha='center', va='bottom', fontsize=7)
        
        # 4. 最大回撤对比（所有策略）
        combo_labels = [f"{row['symbol'][:3]}-{row['strategy_name'][:8]}" for _, row in df.iterrows()]
        drawdowns = (df['max_drawdown'] * 100).tolist()
        
        colors_dd = plt.cm.RdYlGn_r(np.array(drawdowns) / (max(drawdowns) if max(drawdowns) > 0 else 1))
        bars4 = ax4.barh(combo_labels, drawdowns, color=colors_dd, alpha=0.8, edgecolor='black', linewidth=1.5)
        
        ax4.set_title('Maximum Drawdown (All Strategies)', fontweight='bold', fontsize=15)
        ax4.set_xlabel('Max Drawdown (%)', fontweight='bold', fontsize=12)
        ax4.set_ylabel('Symbol - Strategy', fontweight='bold', fontsize=12)
        ax4.grid(True, alpha=0.3, axis='x', linestyle='--')
        
        for i, (bar, val) in enumerate(zip(bars4, drawdowns)):
            ax4.text(val, bar.get_y() + bar.get_height()/2.,
                    f' {val:.1f}%', ha='left', va='center',
                    fontweight='bold', fontsize=8, color='black')
        
        # 保存图表
        chart_path = os.path.join(output_dir, f'scan_details_{timestamp}.png')
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"📊 详细分析图表已生成: {chart_path}")
        return chart_path

    def _generate_html_report(self, df: pd.DataFrame, output_path: str):
        """生成完整的HTML报告（含图表）"""
        if df.empty:
            logger.warning("数据为空，跳过HTML报告生成")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成权益曲线图
        logger.info("📈 生成权益曲线...")
        equity_charts = self._plot_equity_curves(timestamp)
        
        # 生成对比图表
        logger.info("📊 生成对比图表...")
        comparison_chart = self._plot_performance_comparison(df, str(self.output_dir), timestamp)
        
        logger.info("📊 生成详细分析图表...")
        details_chart = self._plot_strategy_details(df, str(self.output_dir), timestamp)
        
        # 计算汇总统计
        best_strategies = []
        for symbol in df['symbol'].unique():
            symbol_df = df[df['symbol'] == symbol]
            best = symbol_df.loc[symbol_df['total_return'].idxmax()]
            best_strategies.append(best)
        
        best_df = pd.DataFrame(best_strategies)
        
        # 生成交易详情表格（为每个标的）
        trades_tables_html = ""
        for key, result in self.backtest_results.items():
            symbol, strategy_name = key.split('_', 1)
            if result.trades:
                trades_tables_html += f"""
                <div class="section">
                    <h2>📝 Trade Details - {symbol} ({strategy_name})</h2>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Entry Date</th>
                                <th>Exit Date</th>
                                <th>Days</th>
                                <th>Strategy</th>
                                <th>Strike</th>
                                <th>Shares</th>
                                <th>Entry Price</th>
                                <th>Exit Price</th>
                                <th>Stock Entry</th>
                                <th>Stock Exit</th>
                                <th>Stock Change</th>
                                <th>P&L</th>
                                <th>Return</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for i, trade in enumerate(result.trades, 1):
                    # 计算持有天数
                    holding_days = (pd.to_datetime(trade.exit_date) - pd.to_datetime(trade.entry_date)).days
                    
                    # 计算股票价格变化
                    stock_change = ((trade.exit_underlying - trade.entry_underlying) / trade.entry_underlying)
                    
                    # 确定行的样式
                    row_class = 'positive' if trade.pnl > 0 else 'negative'
                    stock_class = 'positive' if stock_change > 0 else 'negative'
                    
                    trades_tables_html += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{trade.entry_date}</td>
                            <td>{trade.exit_date}</td>
                            <td>{holding_days}</td>
                            <td>{trade.strategy.upper()}</td>
                            <td>${trade.strike:.2f}</td>
                            <td>{trade.shares}</td>
                            <td>${trade.entry_price:.2f}</td>
                            <td>${trade.exit_price:.2f}</td>
                            <td>${trade.entry_underlying:.2f}</td>
                            <td>${trade.exit_underlying:.2f}</td>
                            <td><span class="{stock_class}">{stock_change:+.2%}</span></td>
                            <td><span class="{row_class}">${trade.pnl:+,.2f}</span></td>
                            <td><span class="{row_class}">{trade.pnl_pct:+.1%}</span></td>
                        </tr>
                    """
                
                trades_tables_html += """
                        </tbody>
                    </table>
                </div>
                """
        
        # 计算总体统计
        total_strategies = len(df)
        total_symbols = len(df['symbol'].unique())
        avg_return = df['total_return'].mean()
        best_return = df['total_return'].max()
        best_symbol = df.loc[df['total_return'].idxmax(), 'symbol']
        best_strategy = df.loc[df['total_return'].idxmax(), 'strategy_name']
        
        # 生成最佳策略表格
        best_table_html = best_df.to_html(
            index=False,
            classes='data-table',
            escape=False,
            formatters={
                'total_return': lambda x: f'<span class="{"positive" if x > 0 else "negative"}">{x:+.2%}</span>',
                'win_rate': lambda x: f'{x:.1%}',
                'sharpe_ratio': lambda x: f'{x:.2f}',
                'max_drawdown': lambda x: f'<span class="negative">{x:.2%}</span>',
                'avg_win': lambda x: f'${x:.2f}',
                'avg_loss': lambda x: f'${x:.2f}'
            },
            columns=['symbol', 'strategy_name', 'total_return', 'win_rate', 
                    'sharpe_ratio', 'max_drawdown', 'num_trades', 'avg_win', 'avg_loss']
        )
        
        # 生成完整结果表格
        full_table_html = df.to_html(
            index=False,
            classes='data-table',
            escape=False,
            formatters={
                'total_return': lambda x: f'<span class="{"positive" if x > 0 else "negative"}">{x:+.2%}</span>',
                'win_rate': lambda x: f'{x:.1%}',
                'sharpe_ratio': lambda x: f'{x:.2f}',
                'max_drawdown': lambda x: f'<span class="negative">{x:.2%}</span>',
                'avg_win': lambda x: f'${x:.2f}',
                'avg_loss': lambda x: f'${x:.2f}'
            }
        )
        
        # HTML模板
        html_content = f"""
        <!DOCTYPE html>
<html lang="en">
        <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>策略扫描报告 - Multi-Symbol Analysis</title>
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
            max-width: 1600px;
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
        
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
            margin-bottom: 50px;
        }}
        
        .summary-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.2);
        }}
        
        .summary-card.highlight {{
            background: linear-gradient(135deg, #F093FB 0%, #F5576C 100%);
            color: white;
        }}
        
        .card-label {{
            font-size: 1em;
            opacity: 0.85;
            margin-bottom: 10px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        
        .card-value {{
            font-size: 2.5em;
            font-weight: bold;
        }}
        
        .section {{
            margin: 50px 0;
        }}
        
        .section h2 {{
            color: #2E86AB;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 4px solid #2E86AB;
            font-size: 1.8em;
        }}
        
        .chart-container {{
            margin: 30px 0;
            text-align: center;
        }}
        
        .chart-container img {{
            width: 100%;
            max-width: 100%;
            border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            transition: transform 0.3s ease;
        }}
        
        .chart-container img:hover {{
            transform: scale(1.01);
        }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 25px;
            background: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-radius: 12px;
            overflow: hidden;
        }}
        
        .data-table thead tr {{
            background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
            color: white;
        }}
        
        .data-table th {{
            padding: 18px 15px;
            text-align: left;
            font-weight: 700;
            font-size: 0.95em;
            letter-spacing: 0.5px;
        }}
        
        .data-table td {{
            padding: 15px;
            border-bottom: 1px solid #e5e7eb;
            font-size: 0.95em;
        }}
        
        .data-table tbody tr:hover {{
            background-color: #f9fafb;
        }}
        
        .data-table tbody tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        .positive {{
            color: #10b981;
            font-weight: bold;
        }}
        
        .negative {{
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
        
        .best-symbol {{
            display: inline-block;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin: 0 5px;
        }}
            </style>
        </head>
        <body>
    <div class="container">
        <div class="header">
            <h1>📊 策略扫描报告</h1>
            <div class="subtitle">Multi-Symbol Strategy Performance Analysis | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="content">
            <h2 style="color: #2E86AB; margin-bottom: 35px; font-size: 2em;">📈 Summary Statistics</h2>
            
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="card-label">Total Symbols Tested</div>
                    <div class="card-value">{total_symbols}</div>
                </div>
                
                <div class="summary-card">
                    <div class="card-label">Total Strategies</div>
                    <div class="card-value">{total_strategies}</div>
                </div>
                
                <div class="summary-card highlight">
                    <div class="card-label">Best Return</div>
                    <div class="card-value">{best_return:+.1%}</div>
                </div>
                
                <div class="summary-card">
                    <div class="card-label">Average Return</div>
                    <div class="card-value">{avg_return:+.1%}</div>
                </div>
            </div>
            
            <div style="text-align: center; margin: 30px 0; padding: 25px; background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%); border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                <h3 style="font-size: 1.5em; margin-bottom: 10px;">🏆 Best Performance</h3>
                <p style="font-size: 1.2em;">
                    <span class="best-symbol">{best_symbol}</span> with strategy 
                    <span style="font-weight: bold; color: #2d3436;">{best_strategy}</span> 
                    achieved <span style="font-weight: bold; color: #10b981; font-size: 1.3em;">{best_return:+.2%}</span>
                </p>
            </div>
            
            <div class="section">
                <h2>📈 Equity Curves</h2>
                {"".join([f'<div class="chart-container"><img src="{os.path.basename(ec)}" alt="Equity Curve"><p style="text-align:center; font-weight:bold; margin-top:10px;">{Path(ec).stem.replace("scan_equity_", "").replace("_"+timestamp, "")}</p></div>' for ec in equity_charts])}
            </div>
            
            <div class="section">
                <h2>📊 Performance Comparison Charts</h2>
                <div class="chart-container">
                    <img src="{os.path.basename(comparison_chart)}" alt="Performance Comparison">
                </div>
            </div>
            
            <div class="section">
                <h2>📈 Strategy Details Analysis</h2>
                <div class="chart-container">
                    <img src="{os.path.basename(details_chart)}" alt="Strategy Details">
                </div>
            </div>
            
            <div class="section">
                <h2>🏆 Best Strategies by Symbol</h2>
                <p style="margin-bottom: 15px; color: #6b7280; font-size: 1.05em;">
                    以下显示每个标的表现最佳的策略配置
                </p>
                {best_table_html}
            </div>
            
            <div class="section">
                <h2>📋 All Scan Results</h2>
                <p style="margin-bottom: 15px; color: #6b7280; font-size: 1.05em;">
                    完整的扫描结果，包含所有标的和策略组合
                </p>
                {full_table_html}
            </div>
            
            {trades_tables_html}
        </div>
        
        <div class="footer">
            <strong>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong><br>
            Strategy Scanner Report | Total Symbols: {total_symbols} | Total Strategies: {total_strategies}
        </div>
    </div>
        </body>
        </html>
"""

        # 保存HTML报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"✅ 完整HTML报告已生成: {output_path}")


# ======================
# 使用示例
# ======================
if __name__ == "__main__":
    # 示例标的列表
    SYMBOLS = ["BABA", "NVDA"]  # 可扩展为 ["BABA", "NVDA", "PLTR", "AAPL", "TSLA"]

    scanner = StrategyScanner(strategy_dir="strategies")
    
    df_results = scanner.run_scan(
        symbols=SYMBOLS,
        start_date="2025-01-01",
        end_date="2025-11-03",
        output_csv="scan_results.csv",
        output_html="scan_report.html"
    )

    if not df_results.empty:
        print("\n" + "="*80)
        print("🏆 最佳策略汇总")
        print("="*80)
        # 打印每个标的的最佳策略
        for symbol in df_results['symbol'].unique():
            best = df_results[df_results['symbol'] == symbol].sort_values('total_return', ascending=False).iloc[0]
            print(f"\n标的: {symbol}")
            print(f"  策略: {best['strategy_name']}")
            print(f"  收益: {best['total_return']:+.2%}")
            print(f"  夏普比率: {best['sharpe_ratio']:.2f}")
            print(f"  胜率: {best['win_rate']:.1%}")
            print(f"  最大回撤: {best['max_drawdown']:.2%}")
        print("\n" + "="*80)
        print("📄 查看完整报告: open scan_report.html")
        print("="*80 + "\n")
    else:
        print("❌ 无有效回测结果")