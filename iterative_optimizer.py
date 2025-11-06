#!/usr/bin/env python3
"""
迭代策略优化器

通过 DeepSeek AI 不断优化策略组合，直到收敛
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from signal_optimization.multi_strategy_backtest import MultiStrategyBacktester
from ai_rl_engine.deepseek_client import DeepSeekClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IterativeOptimizer:
    """迭代策略优化器"""
    
    def __init__(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 10000,
        max_iterations: int = 10,
        convergence_threshold: float = 0.05,  # 5% 改进视为收敛
        logger: logging.Logger = None  # 新增：可选的自定义 logger
    ):
        """
        初始化
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            max_iterations: 最大迭代次数
            convergence_threshold: 收敛阈值
            logger: 自定义 logger（可选）
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        
        # 使用传入的 logger 或默认 logger
        self.logger = logger if logger else logging.getLogger(__name__)
        
        self.deepseek = DeepSeekClient()
        self.iteration_history = []
        self.best_return = -float('inf')
        self.best_strategies = None
        self.best_backtest_results = None  # 保存最佳策略的完整回测结果
    
    def optimize(self, initial_strategies: Dict[str, Dict[str, float]] = None) -> Dict:
        """
        运行迭代优化
        
        Args:
            initial_strategies: 初始策略组合（如果为None，使用默认）
        
        Returns:
            优化结果字典
        """
        self.logger.info("\n" + "="*80)
        self.logger.info("🚀 迭代策略优化器")
        self.logger.info("="*80)
        self.logger.info(f"标的: {self.symbol}")
        self.logger.info(f"期间: {self.start_date} to {self.end_date}")
        self.logger.info(f"最大迭代: {self.max_iterations} 轮")
        self.logger.info(f"收敛阈值: {self.convergence_threshold:.1%}")
        self.logger.info("="*80 + "\n")
        
        current_strategies = initial_strategies
        
        for iteration in range(1, self.max_iterations + 1):
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"🔄 第 {iteration}/{self.max_iterations} 轮迭代")
            self.logger.info(f"{'='*80}\n")
            
            # 1. 运行回测
            backtest_results = self._run_backtest(current_strategies, iteration)
            
            # 2. 检查是否改进
            current_best_return = backtest_results[0]['total_return']
            improvement = current_best_return - self.best_return
            
            self.logger.info(f"\n📊 当前最佳收益: {current_best_return:+.2%}")
            
            if current_best_return > self.best_return:
                self.logger.info(f"✅ 改进: {improvement:+.2%}")
                self.best_return = current_best_return
                
                # 从回测结果中提取策略（确保有完整的策略信息）
                if current_strategies:
                    self.best_strategies = current_strategies
                else:
                    # 如果 current_strategies 为空，从回测结果中重建
                    self.best_strategies = {}
                    for result in backtest_results[:3]:  # 保存前3个最佳策略
                        if 'signal_weights' in result:
                            self.best_strategies[result['strategy_name']] = result['signal_weights']
                    self.logger.info(f"   从回测结果中提取了 {len(self.best_strategies)} 个策略")
                
                # 保存最佳策略的回测结果（用于生成详细指标）
                self.best_backtest_results = backtest_results[0] if backtest_results else None
            else:
                self.logger.info(f"⚠️  未改进 (差距: {improvement:+.2%})")
                self.logger.info(f"   保留历史最优策略")
            
            # 3. 记录历史
            self.iteration_history.append({
                'iteration': iteration,
                'best_return': current_best_return,
                'strategies': current_strategies,
                'results': backtest_results
            })
            
            # 4. 检查收敛
            if iteration > 1:
                prev_best = self.iteration_history[-2]['best_return']
                if abs(current_best_return - prev_best) < self.convergence_threshold:
                    self.logger.info(f"\n✅ 收敛！改进小于 {self.convergence_threshold:.1%}")
                    self.logger.info(f"在第 {iteration} 轮停止")
                    break
            
            # 5. 如果不是最后一轮，请求 DeepSeek 优化
            if iteration < self.max_iterations:
                self.logger.info(f"\n🤖 请求 DeepSeek AI 优化建议...")
                current_strategies = self._get_deepseek_optimization(
                    backtest_results,
                    current_strategies,
                    iteration
                )
            
            # 保存中间结果
            self._save_iteration_report(iteration)
        
        # 生成最终报告
        final_report = self._generate_final_report()
        
        # 兜底检查：如果仍然没有策略，尝试从历史中获取
        if self.best_strategies is None or not self.best_strategies:
            self.logger.warning("⚠️  最优策略为空，尝试从迭代历史中恢复...")
            
            # 找到收益最高的迭代
            if self.iteration_history:
                best_iter = max(self.iteration_history, key=lambda x: x['best_return'])
                self.logger.info(f"   找到第 {best_iter['iteration']} 轮的策略（收益: {best_iter['best_return']:+.2%}）")
                
                # 从该迭代的回测结果中提取策略
                if best_iter.get('results'):
                    self.best_strategies = {}
                    for result in best_iter['results'][:3]:
                        if 'signal_weights' in result:
                            self.best_strategies[result['strategy_name']] = result['signal_weights']
                    
                    if self.best_strategies:
                        self.logger.info(f"   ✅ 成功恢复 {len(self.best_strategies)} 个策略")
                        self.best_return = best_iter['best_return']
                        # 恢复回测结果
                        self.best_backtest_results = best_iter['results'][0] if best_iter.get('results') else None
                    else:
                        self.logger.error("   ❌ 无法从历史中提取策略")
        
        return {
            'best_return': self.best_return,
            'best_strategies': self.best_strategies,
            'best_backtest_results': self.best_backtest_results,
            'total_iterations': len(self.iteration_history),
            'final_report': final_report
        }
    
    def _run_backtest(
        self,
        strategies: Dict[str, Dict[str, float]],
        iteration: int
    ) -> List[Dict]:
        """运行回测"""
        
        self.logger.info(f"📊 运行回测 (策略数: {len(strategies) if strategies else '默认'})")
        
        backtester = MultiStrategyBacktester(initial_capital=self.initial_capital)
        
        # 如果提供了自定义策略，临时替换
        if strategies:
            # 备份原方法
            original_method = backtester._generate_strategy_combinations
            
            # 临时替换
            def custom_combinations(signal_defs):
                return strategies
            
            backtester._generate_strategy_combinations = custom_combinations
        
        # 运行回测
        results = backtester.run_all_strategies(
            self.symbol,
            self.start_date,
            self.end_date
        )
        
        # 恢复原方法
        if strategies:
            backtester._generate_strategy_combinations = original_method
        
        # 生成对比报告
        backtester.generate_comparison_report(self.symbol)
        
        self.logger.info(f"\n前3名策略:")
        for i, r in enumerate(results[:3], 1):
            self.logger.info(f"  {i}. {r['strategy_name']:<20} | "
                       f"收益: {r['total_return']:>+7.2%} | "
                       f"胜率: {r['win_rate']:>5.1%} | "
                       f"交易: {r['num_trades']:>3}")
        
        return results
    
    def _get_deepseek_optimization(
        self,
        backtest_results: List[Dict],
        current_strategies: Dict[str, Dict[str, float]],
        iteration: int
    ) -> Dict[str, Dict[str, float]]:
        """
        获取 DeepSeek AI 的优化建议
        
        Returns:
            优化后的策略组合
        """
        
        # 准备发送给 AI 的数据
        top_5 = backtest_results[:5]
        bottom_5 = backtest_results[-5:]
        
        prompt = f"""你是一个量化交易策略优化专家。我需要你分析以下期权回测结果，并提出改进建议。

## 当前迭代: 第 {iteration} 轮

## 前5名策略表现:
"""
        
        for i, r in enumerate(top_5, 1):
            prompt += f"\n{i}. {r['strategy_name']}\n"
            prompt += f"   - 总收益: {r['total_return']:+.2%}\n"
            prompt += f"   - 胜率: {r['win_rate']:.1%}\n"
            prompt += f"   - 夏普比率: {r['sharpe_ratio']:.2f}\n"
            prompt += f"   - 交易次数: {r['num_trades']}\n"
            prompt += f"   - 信号权重: {json.dumps(r['signal_weights'], indent=6)}\n"
        
        prompt += f"\n## 后5名策略表现:\n"
        
        for i, r in enumerate(bottom_5, 1):
            prompt += f"\n{i}. {r['strategy_name']}\n"
            prompt += f"   - 总收益: {r['total_return']:+.2%}\n"
            prompt += f"   - 胜率: {r['win_rate']:.1%}\n"
            prompt += f"   - 交易次数: {r['num_trades']}\n"
        
        prompt += f"""

## 可用的信号类型:
- bb_compression: 布林带压缩
- bb_breakout: 布林带突破
- rsi_oversold: RSI超卖
- rsi_overbought: RSI超买
- volume_surge: 成交量激增
- ma_crossover: 均线金叉
- ma_crossunder: 均线死叉
- price_above_ma50: 价格在MA50上方
- macd_crossover: MACD金叉
- macd_divergence: MACD背离
- low_volatility: 低波动率
- williams_oversold: Williams超卖
- williams_overbought: Williams超买
- cci_extreme: CCI极值
- momentum_reversal: 动量反转

## 优化目标:
1. 提高总收益率
2. 提高胜率
3. 增加夏普比率
4. 保持足够的交易次数（至少3-5笔）

## 优化建议要求:
1. 分析表现好的策略的共同特征
2. 分析表现差的策略的问题
3. 提出 5-8 个新的策略组合
4. 每个策略的权重总和应该在 0.8 - 1.2 之间
5. 可以创新组合，不必局限于现有策略

## 输出格式:
请用JSON格式输出新的策略组合，格式如下:
```json
{{
    "analysis": "你的分析...",
    "strategies": {{
        "策略名称1": {{
            "signal1": 0.3,
            "signal2": 0.4,
            "signal3": 0.3
        }},
        "策略名称2": {{
            "signal1": 0.5,
            "signal2": 0.5
        }}
    }}
}}
```

请给出你的分析和优化建议：
"""
        
        try:
            # 调用 DeepSeek
            messages = [
                {"role": "system", "content": "You are a quantitative trading strategy optimizer. Analyze backtest results and provide optimization suggestions in JSON format."},
                {"role": "user", "content": prompt}
            ]
            
            result = self.deepseek.chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            response = result['choices'][0]['message']['content']
            
            self.logger.info(f"\n📝 DeepSeek AI 分析:\n")
            self.logger.info(response[:500] + "..." if len(response) > 500 else response)
            
            # 解析 JSON 响应
            optimized_strategies = self._parse_deepseek_response(response)
            
            if optimized_strategies:
                self.logger.info(f"\n✅ 成功解析 {len(optimized_strategies)} 个优化策略")
                return optimized_strategies
            else:
                self.logger.warning("⚠️  AI响应解析失败，使用当前策略")
                return current_strategies or self._get_default_strategies()
        
        except Exception as e:
            self.logger.error(f"❌ DeepSeek 优化失败: {e}")
            return current_strategies or self._get_default_strategies()
    
    def _parse_deepseek_response(self, response: str) -> Dict[str, Dict[str, float]]:
        """解析 DeepSeek 的 JSON 响应"""
        
        try:
            # 尝试提取 JSON
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                
                if 'strategies' in data:
                    return data['strategies']
                else:
                    return data
            
            return None
        
        except Exception as e:
            self.logger.error(f"JSON解析错误: {e}")
            return None
    
    def _get_default_strategies(self) -> Dict[str, Dict[str, float]]:
        """获取默认策略（回退方案）"""
        return {
            'BB_Specialist': {
                'bb_compression': 0.50,
                'bb_breakout': 0.30,
                'volume_surge': 0.20
            },
            'Volatility_Breakout': {
                'bb_compression': 0.35,
                'bb_breakout': 0.30,
                'low_volatility': 0.20,
                'volume_surge': 0.15
            },
            'Conservative': {
                'bb_compression': 0.20,
                'rsi_oversold': 0.15,
                'volume_surge': 0.15,
                'ma_crossover': 0.15,
                'low_volatility': 0.10
            }
        }
    
    def _save_iteration_report(self, iteration: int):
        """保存每轮迭代报告"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'signal_optimization/iteration_{iteration}_{timestamp}.json'
        
        report = {
            'iteration': iteration,
            'timestamp': timestamp,
            'best_return': self.best_return,
            'history': self.iteration_history
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.debug(f"📄 迭代报告已保存: {filename}")
    
    def _generate_final_report(self) -> str:
        """生成最终优化报告"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'signal_optimization/optimization_final_{self.symbol}_{timestamp}.html'
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>迭代优化最终报告 - {self.symbol}</title>
    <style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #2E86AB;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .summary {{
            background: #f0f9ff;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .iteration {{
            background: #fafafa;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #2E86AB;
        }}
        .best {{
            background: #d1fae5;
            border-left-color: #10b981;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #2E86AB;
            color: white;
        }}
        .positive {{ color: #10b981; font-weight: bold; }}
        .negative {{ color: #ef4444; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 迭代优化最终报告</h1>
        <p style="text-align: center; color: #666; font-size: 1.2em;">
            {self.symbol} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
        
        <div class="summary">
            <h2>📊 优化总结</h2>
            <p><strong>总迭代轮数:</strong> {len(self.iteration_history)}</p>
            <p><strong>最佳收益:</strong> <span class="{'positive' if self.best_return > 0 else 'negative'}">{self.best_return:+.2%}</span></p>
            <p><strong>收敛阈值:</strong> {self.convergence_threshold:.1%}</p>
        </div>
        
        <h2>📈 迭代历史</h2>
"""
        
        for i, hist in enumerate(self.iteration_history, 1):
            is_best = hist['best_return'] == self.best_return
            html += f"""
        <div class="iteration {'best' if is_best else ''}">
            <h3>第 {i} 轮 {'🏆' if is_best else ''}</h3>
            <p><strong>最佳收益:</strong> <span class="{'positive' if hist['best_return'] > 0 else 'negative'}">{hist['best_return']:+.2%}</span></p>
            <p><strong>测试策略数:</strong> {len(hist['strategies']) if hist['strategies'] else '默认'}</p>
        </div>
"""
        
        if self.best_strategies:
            html += f"""
        <h2>🏆 最佳策略组合</h2>
        <table>
            <tr>
                <th>策略名称</th>
                <th>信号权重</th>
            </tr>
"""
            for name, weights in self.best_strategies.items():
                weights_str = '<br>'.join([f"{k}: {v:.2f}" for k, v in weights.items()])
                html += f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{weights_str}</td>
            </tr>
"""
            html += """
        </table>
"""
        
        html += """
        <div style="text-align: center; margin-top: 40px; color: #666;">
            <p><strong>Generated by Option Expert Iterative Optimizer</strong></p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        self.logger.info(f"\n📄 最终报告已生成: {filename}")
        
        return filename


def main():
    """主函数"""
    
    optimizer = IterativeOptimizer(
        symbol='BABA',
        start_date='2024-01-01',
        end_date='2025-11-01',
        max_iterations=10,
        convergence_threshold=0.05
    )
    
    result = optimizer.optimize()
    
    print("\n" + "="*80)
    print("✅ 优化完成！")
    print("="*80)
    print(f"\n最佳收益: {result['best_return']:+.2%}")
    print(f"总迭代轮数: {result['total_iterations']}")
    print(f"最终报告: {result['final_report']}")
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()

