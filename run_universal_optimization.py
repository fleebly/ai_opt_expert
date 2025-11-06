#!/usr/bin/env python3
"""
一揽子标的通用策略优化

通过 DeepSeek AI 优化出适用于多个标的的通用策略
核心思路：找到在所有标的上都表现良好的信号组合

使用方法:
python run_universal_optimization.py --symbols BABA NVDA PLTR --start 2023-01-01 --end 2025-01-01

特点：
✅ 支持多个标的同时优化
✅ 生成通用策略（而非单独策略）
✅ 综合评估所有标的的表现
✅ 自动保存到 strategies/UNIVERSAL_ST_{timestamp}.json
✅ 详细日志记录
"""

import sys
import os
import argparse
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import OptionBacktest
from ai_rl_engine.deepseek_client import DeepSeekClient
from report_generator import ReportGenerator


@dataclass
class UniversalStrategyResult:
    """通用策略优化结果"""
    strategy_name: str
    signal_weights: Dict[str, float]
    symbol_results: Dict[str, float]  # 每个标的的收益率
    symbol_performance: Dict[str, Dict]  # 每个标的的详细回测性能
    avg_return: float  # 平均收益率
    min_return: float  # 最差标的收益率
    sharpe_ratio: float  # 综合夏普比率
    total_iterations: int
    final_report: str


class UniversalStrategyOptimizer:
    """通用策略优化器 - 针对多个标的生成单一策略"""
    
    def __init__(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        initial_capital: float = 10000.0,
        max_iterations: int = 15,
        convergence_threshold: float = 0.03
    ):
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        
        self.ai_client = DeepSeekClient()
        self.report_gen = ReportGenerator()
        
        # 日志
        self.logger = logging.getLogger(__name__)
    
    def _get_initial_strategies(self) -> Dict[str, Dict[str, float]]:
        """获取初始策略组合"""
        return {
            "Balanced_Multi_Signal": {
                "rsi_oversold": 0.25,
                "macd_crossover": 0.20,
                "bb_compression": 0.15,
                "volume_surge": 0.15,
                "momentum_reversal": 0.15,
                "cci_extreme": 0.10
            },
            "Momentum_Focus": {
                "momentum_reversal": 0.30,
                "rsi_oversold": 0.25,
                "volume_surge": 0.20,
                "macd_crossover": 0.15,
                "bb_compression": 0.10
            },
            "Mean_Reversion": {
                "bb_compression": 0.30,
                "rsi_oversold": 0.25,
                "cci_extreme": 0.20,
                "williams_oversold": 0.15,
                "macd_crossover": 0.10
            },
            "Volatility_Breakout": {
                "bb_compression": 0.25,
                "volume_surge": 0.25,
                "momentum_reversal": 0.20,
                "macd_crossover": 0.15,
                "rsi_oversold": 0.15
            },
            "Conservative_Multi": {
                "rsi_oversold": 0.20,
                "macd_crossover": 0.20,
                "bb_compression": 0.20,
                "cci_extreme": 0.15,
                "volume_surge": 0.15,
                "momentum_reversal": 0.10
            }
        }
    
    def backtest_strategy_on_symbols(
        self, 
        signal_weights: Dict[str, float],
        params: Dict[str, float]
    ) -> Dict[str, Dict]:
        """
        在所有标的上回测同一策略
        
        Returns:
            Dict[symbol, result_dict]
        """
        results = {}
        
        for symbol in self.symbols:
            try:
                self.logger.info(f"📊 回测 {symbol}...")
                
                backtest = OptionBacktest(
                    initial_capital=self.initial_capital,
                    use_real_prices=True
                )
                
                result = backtest.run_backtest(
                    symbol=symbol,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    strategy='auto',
                    entry_signal=signal_weights,
                    profit_target=params.get('profit_target', 5.0),
                    stop_loss=params.get('stop_loss', -0.5),
                    max_holding_days=params.get('max_holding_days', 30),
                    position_size=params.get('position_size', 0.1)
                )
                
                results[symbol] = {
                    'total_return': result.total_return,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate,
                    'max_drawdown': result.max_drawdown,
                    'num_trades': result.num_trades
                }
                
                self.logger.info(
                    f"  ✅ {symbol}: {result.total_return:+.2%} | "
                    f"夏普 {result.sharpe_ratio:.2f} | "
                    f"胜率 {result.win_rate:.1%}"
                )
                
            except Exception as e:
                self.logger.error(f"  ❌ {symbol} 回测失败: {e}")
                results[symbol] = {
                    'total_return': -1.0,
                    'sharpe_ratio': 0.0,
                    'win_rate': 0.0,
                    'max_drawdown': 0.0,
                    'num_trades': 0
                }
        
        return results
    
    def calculate_composite_score(self, results: Dict[str, Dict]) -> Tuple[float, float, float]:
        """
        计算综合评分
        
        考虑因素：
        1. 平均收益率
        2. 最差标的收益率（鲁棒性）
        3. 综合夏普比率
        
        Returns:
            (composite_score, avg_return, min_return)
        """
        returns = [r['total_return'] for r in results.values()]
        sharpes = [r['sharpe_ratio'] for r in results.values()]
        
        avg_return = sum(returns) / len(returns)
        min_return = min(returns)
        avg_sharpe = sum(sharpes) / len(sharpes)
        
        # 综合评分 = 50% 平均收益 + 30% 最差收益 + 20% 夏普比率
        # 确保策略在所有标的上都有良好表现
        composite_score = (
            0.5 * avg_return +
            0.3 * min_return +
            0.2 * (avg_sharpe / 3.0)  # 归一化夏普比率
        )
        
        return composite_score, avg_return, min_return
    
    def optimize(self) -> UniversalStrategyResult:
        """
        执行通用策略优化
        """
        self.logger.info(f"🚀 开始优化通用策略（适用于 {len(self.symbols)} 个标的）")
        self.logger.info(f"   标的列表: {', '.join(self.symbols)}")
        
        best_score = -999
        best_strategy = None
        best_signal_weights = None
        best_symbol_results = None
        
        # 初始策略
        current_strategies = self._get_initial_strategies()
        
        for iteration in range(1, self.max_iterations + 1):
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"🔄 第 {iteration}/{self.max_iterations} 轮优化")
            self.logger.info(f"{'='*80}")
            
            iteration_best_score = -999
            iteration_best_strategy = None
            iteration_best_weights = None
            iteration_best_results = None
            
            # 测试每个策略
            for strategy_name, signal_weights in current_strategies.items():
                self.logger.info(f"\n📋 测试策略: {strategy_name}")
                
                # 默认参数
                params = {
                    'profit_target': 5.0,
                    'stop_loss': -0.5,
                    'max_holding_days': 30,
                    'position_size': 0.1
                }
                
                # 在所有标的上回测
                symbol_results = self.backtest_strategy_on_symbols(signal_weights, params)
                
                # 计算综合评分
                score, avg_ret, min_ret = self.calculate_composite_score(symbol_results)
                
                self.logger.info(f"  📊 综合评分: {score:+.4f}")
                self.logger.info(f"     平均收益: {avg_ret:+.2%}")
                self.logger.info(f"     最差收益: {min_ret:+.2%}")
                
                # 更新本轮最佳
                if score > iteration_best_score:
                    iteration_best_score = score
                    iteration_best_strategy = strategy_name
                    iteration_best_weights = signal_weights
                    iteration_best_results = symbol_results
            
            # 检查是否有改进
            improvement = iteration_best_score - best_score
            self.logger.info(f"\n🏆 第 {iteration} 轮最佳策略: {iteration_best_strategy}")
            self.logger.info(f"   综合评分: {iteration_best_score:+.4f} (改进: {improvement:+.4f})")
            
            if iteration_best_score > best_score:
                best_score = iteration_best_score
                best_strategy = iteration_best_strategy
                best_signal_weights = iteration_best_weights
                best_symbol_results = iteration_best_results
                self.logger.info("   ✅ 找到更好的策略！")
            else:
                self.logger.info("   ⚠️ 未改进")
            
            # 检查收敛
            if iteration > 1 and abs(improvement) < self.convergence_threshold:
                self.logger.info(f"\n✅ 策略已收敛（改进 < {self.convergence_threshold:.2%}）")
                break
            
            # 如果是最后一轮，跳过AI生成
            if iteration == self.max_iterations:
                self.logger.info("\n✅ 达到最大迭代次数")
                break
            
            # 使用 AI 生成下一轮策略
            self.logger.info("\n🤖 AI 正在分析并生成新策略...")
            
            # 构建提示词
            prompt = self._build_ai_prompt(
                iteration_best_strategy,
                iteration_best_weights,
                iteration_best_results,
                iteration_best_score
            )
            
            try:
                response = self.ai_client.generate_strategy_suggestions(
                    prompt=prompt,
                    current_strategies=current_strategies,
                    backtest_results={
                        'symbols': self.symbols,
                        'results': iteration_best_results,
                        'composite_score': iteration_best_score
                    }
                )
                
                # 解析AI响应并生成新策略
                new_strategies = self._parse_ai_response(response)
                if new_strategies:
                    current_strategies = new_strategies
                    self.logger.info(f"   ✅ 生成 {len(new_strategies)} 个新策略")
                else:
                    self.logger.warning("   ⚠️ AI 未生成有效策略，使用现有策略")
                    
            except Exception as e:
                self.logger.error(f"   ❌ AI 生成失败: {e}")
                self.logger.info("   ℹ️ 继续使用现有策略")
        
        # 计算最终指标
        _, avg_return, min_return = self.calculate_composite_score(best_symbol_results)
        avg_sharpe = sum([r['sharpe_ratio'] for r in best_symbol_results.values()]) / len(best_symbol_results)
        symbol_returns = {s: r['total_return'] for s, r in best_symbol_results.items()}
        
        # 生成报告
        report_path = self._generate_report(
            best_strategy,
            best_signal_weights,
            best_symbol_results,
            iteration
        )
        
        return UniversalStrategyResult(
            strategy_name=best_strategy,
            signal_weights=best_signal_weights,
            symbol_results=symbol_returns,
            symbol_performance=best_symbol_results,  # 包含每个标的的详细性能
            avg_return=avg_return,
            min_return=min_return,
            sharpe_ratio=avg_sharpe,
            total_iterations=iteration,
            final_report=report_path
        )
    
    def _build_ai_prompt(
        self,
        strategy_name: str,
        signal_weights: Dict[str, float],
        results: Dict[str, Dict],
        score: float
    ) -> str:
        """构建给AI的提示词"""
        
        prompt = f"""
你是一个专业的量化交易策略优化专家。

任务：优化通用期权交易策略，使其在多个标的上都表现良好。

当前最佳策略：
名称: {strategy_name}
信号权重: {json.dumps(signal_weights, indent=2)}

在各个标的上的表现：
"""
        for symbol, res in results.items():
            prompt += f"\n{symbol}:"
            prompt += f"\n  - 收益率: {res['total_return']:+.2%}"
            prompt += f"\n  - 夏普比率: {res['sharpe_ratio']:.2f}"
            prompt += f"\n  - 胜率: {res['win_rate']:.1%}"
            prompt += f"\n  - 最大回撤: {res['max_drawdown']:.2%}"
        
        prompt += f"""

综合评分: {score:+.4f}

请分析：
1. 哪些信号在所有标的上都表现稳定？
2. 哪些信号可能导致某些标的表现不佳？
3. 如何调整权重使策略更具普适性？

请提供 3-5 个改进后的通用策略配置，要求：
- 增强在所有标的上的稳定性
- 避免过度拟合某个标的
- 保持信号权重合理性（和为1.0左右）

格式要求：JSON格式，包含策略名称和信号权重字典。
"""
        return prompt
    
    def _parse_ai_response(self, response: str) -> Dict[str, Dict[str, float]]:
        """解析AI响应，提取新策略"""
        try:
            # 尝试从响应中提取JSON
            import re
            
            # 查找JSON块
            json_matches = re.findall(r'\{[^{}]*"[^"]*":[^{}]*\}', response, re.DOTALL)
            
            new_strategies = {}
            for i, json_str in enumerate(json_matches[:5], 1):
                try:
                    strategy_data = json.loads(json_str)
                    strategy_name = strategy_data.get('name', f'AI_Universal_Strategy_{i}')
                    signal_weights = strategy_data.get('signal_weights', {})
                    
                    if signal_weights:
                        new_strategies[strategy_name] = signal_weights
                except:
                    continue
            
            return new_strategies if new_strategies else {}
            
        except Exception as e:
            self.logger.error(f"解析AI响应失败: {e}")
            return {}
    
    def _generate_report(
        self,
        strategy_name: str,
        signal_weights: Dict[str, float],
        symbol_results: Dict[str, Dict],
        iterations: int
    ) -> str:
        """生成优化报告"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = Path("signal_optimization")
        report_dir.mkdir(exist_ok=True)
        
        report_path = report_dir / f"UNIVERSAL_optimization_{timestamp}.html"
        
        # 构建HTML报告
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>通用策略优化报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .summary {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .symbol-results {{ background: white; padding: 20px; border-radius: 10px; 
                          box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #667eea; color: white; }}
        .positive {{ color: green; font-weight: bold; }}
        .negative {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 通用策略优化报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>优化标的: {', '.join(self.symbols)}</p>
        <p>迭代轮数: {iterations}</p>
    </div>
    
    <div class="summary">
        <h2>📊 最佳策略</h2>
        <h3>{strategy_name}</h3>
        <h4>信号权重配置：</h4>
        <table>
            <tr><th>信号</th><th>权重</th></tr>
"""
        
        for signal, weight in sorted(signal_weights.items(), key=lambda x: x[1], reverse=True):
            html_content += f"<tr><td>{signal}</td><td>{weight:.3f}</td></tr>"
        
        html_content += """
        </table>
    </div>
    
    <div class="symbol-results">
        <h2>📈 各标的回测结果</h2>
        <table>
            <tr>
                <th>标的</th>
                <th>收益率</th>
                <th>夏普比率</th>
                <th>胜率</th>
                <th>最大回撤</th>
                <th>交易次数</th>
            </tr>
"""
        
        for symbol, res in symbol_results.items():
            return_class = 'positive' if res['total_return'] > 0 else 'negative'
            html_content += f"""
            <tr>
                <td><strong>{symbol}</strong></td>
                <td class="{return_class}">{res['total_return']:+.2%}</td>
                <td>{res['sharpe_ratio']:.2f}</td>
                <td>{res['win_rate']:.1%}</td>
                <td>{res['max_drawdown']:.2%}</td>
                <td>{res['num_trades']}</td>
            </tr>
"""
        
        # 计算平均值
        avg_return = sum([r['total_return'] for r in symbol_results.values()]) / len(symbol_results)
        avg_sharpe = sum([r['sharpe_ratio'] for r in symbol_results.values()]) / len(symbol_results)
        avg_winrate = sum([r['win_rate'] for r in symbol_results.values()]) / len(symbol_results)
        
        html_content += f"""
            <tr style="background-color: #f0f0f0; font-weight: bold;">
                <td>平均值</td>
                <td class="{'positive' if avg_return > 0 else 'negative'}">{avg_return:+.2%}</td>
                <td>{avg_sharpe:.2f}</td>
                <td>{avg_winrate:.1%}</td>
                <td>-</td>
                <td>-</td>
            </tr>
        </table>
    </div>
</body>
</html>
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"📄 报告已生成: {report_path}")
        return str(report_path)


def setup_logger() -> logging.Logger:
    """配置日志"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"universal_optimizer_{timestamp}.log"
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # 清除现有handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # 文件handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"日志文件: {log_file}")
    return logger


def main():
    parser = argparse.ArgumentParser(
        description="🌐 通用策略优化器 - 生成适用于多个标的的策略",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--symbols",
        type=str,
        nargs='+',
        required=True,
        help="标的代码列表，如: BABA NVDA PLTR"
    )
    parser.add_argument("--start", type=str, default="2023-01-01", help="回测开始日期")
    parser.add_argument("--end", type=str, default="2025-01-01", help="回测结束日期")
    parser.add_argument("--max-iter", type=int, default=15, help="最大迭代次数")
    parser.add_argument("--threshold", type=float, default=0.03, help="收敛阈值")
    parser.add_argument("--capital", type=float, default=10000.0, help="初始资金")
    
    args = parser.parse_args()
    
    # 初始化日志
    logger = setup_logger()
    
    banner = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║              🌐 通用策略优化系统                                          ║
║              标的: {', '.join(args.symbols):<50}  ║
║              周期: {args.start} → {args.end}                        ║
║              DeepSeek AI 驱动 - 生成通用策略                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)
    logger.info(f"开始优化通用策略（标的: {', '.join(args.symbols)}）")
    
    try:
        optimizer = UniversalStrategyOptimizer(
            symbols=args.symbols,
            start_date=args.start,
            end_date=args.end,
            initial_capital=args.capital,
            max_iterations=args.max_iter,
            convergence_threshold=args.threshold
        )
        
        result = optimizer.optimize()
        
        logger.info(f"优化完成 | 平均收益: {result.avg_return:+.2%} | 迭代: {result.total_iterations}")
        
        print("\n" + "=" * 80)
        print("🎉 优化完成！")
        print("=" * 80)
        print(f"\n🏆 最佳通用策略: {result.strategy_name}")
        print(f"🔄 总迭代轮数: {result.total_iterations}")
        print(f"\n📊 综合表现:")
        print(f"   平均收益率: {result.avg_return:+.2%}")
        print(f"   最差收益率: {result.min_return:+.2%}")
        print(f"   平均夏普比率: {result.sharpe_ratio:.2f}")
        
        print(f"\n📈 各标的表现:")
        for symbol, ret in result.symbol_results.items():
            print(f"   {symbol}: {ret:+.2%}")
        
        print(f"\n📋 信号权重:")
        for signal, weight in sorted(result.signal_weights.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {signal:<25} {weight:.3f}")
        
        # 保存通用策略 JSON
        strategies_dir = Path("strategies")
        strategies_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_json = strategies_dir / f"UNIVERSAL_ST_{timestamp}.json"
        
        # 构建回测性能数据
        backtest_performance = {}
        for symbol, perf in result.symbol_performance.items():
            backtest_performance[symbol] = {
                "total_return": perf.get('total_return', 0),
                "win_rate": perf.get('win_rate', 0),
                "sharpe_ratio": perf.get('sharpe_ratio', 0),
                "max_drawdown": perf.get('max_drawdown', 0),
                "num_trades": perf.get('num_trades', 0)
            }
        
        json_data = {
            "name": result.strategy_name,
            "signal_weights": result.signal_weights,
            "params": {
                "profit_target": 5.0,
                "stop_loss": -0.5,
                "max_holding_days": 30,
                "position_size": 0.1
            },
            "backtest_performance": backtest_performance,
            "metadata": {
                "type": "universal",
                "symbols": args.symbols,
                "avg_return": result.avg_return,
                "min_return": result.min_return,
                "sharpe_ratio": result.sharpe_ratio,
                "symbol_results": result.symbol_results,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "backtest_period": f"{args.start} to {args.end}"
            }
        }
        
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"通用策略已保存: {output_json}")
        print(f"\n💾 通用策略已保存至: {output_json}")
        print(f"\n📄 查看详细报告:")
        print(f"   open {result.final_report}")
        print("\n" + "=" * 80 + "\n")
        
    except Exception as e:
        logger.exception("优化过程发生错误")
        print(f"\n❌ 错误: {e}\n")
        raise


if __name__ == '__main__':
    main()

