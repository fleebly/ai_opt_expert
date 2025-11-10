"""
Multi-Strategy Backtester for Signal Optimization
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from typing import Dict, List
from datetime import datetime
from pathlib import Path
import pandas as pd

from backtest_engine import OptionBacktest
from signal_library import SignalLibrary

logger = logging.getLogger(__name__)


class MultiStrategyBacktester:
    """
    多策略回测器
    用于批量测试多个信号组合策略
    """
    
    def __init__(self, initial_capital: float = 10000.0):
        """初始化"""
        self.initial_capital = initial_capital
        # Don't create backtest_engine here - create a new one for each strategy
        # to ensure complete isolation between backtests
        self.signal_library = SignalLibrary
    
    def _generate_strategy_combinations(self, signal_defs: Dict) -> Dict[str, Dict[str, float]]:
        """
        生成策略组合
        
        使用随机组合进行宽泛测试，避免过早收敛到局部最优
        
        Returns:
            Dict of {strategy_name: signal_weights}
        """
        import random
        import numpy as np
        
        # 所有可用的信号
        available_signals = [
            "bb_compression",
            "rsi_oversold",
            "rsi_overbought",
            "volume_surge",
            "ma_crossover",
            "ma_crossunder",
            "price_above_ma50",
            "macd_crossover",
            "macd_divergence",
            "low_volatility",
            "williams_oversold",
            "williams_overbought",
            "bb_breakout",
            "cci_extreme",
            "momentum_reversal"
        ]
        
        # 生成8个随机策略组合进行宽泛测试，每个组合包含2-5个信号
        # 这样可以探索更多的策略空间，避免过早收敛到局部最优
        strategies = {}
        random.seed()  # 使用当前时间作为随机种子，确保每次运行都不同
        
        for i in range(8):
            # 随机选择2-5个信号
            num_signals = random.randint(2, 5)
            selected_signals = random.sample(available_signals, num_signals)
            
            # 生成随机权重（归一化到1.0）
            weights = np.random.dirichlet(np.ones(num_signals), size=1)[0]
            
            # 创建信号权重字典
            signal_weights = {signal: float(weight) for signal, weight in zip(selected_signals, weights)}
            
            # 生成策略名称
            strategy_name = "_".join([s.replace("_", "")[:4].upper() for s in selected_signals[:3]])
            if len(selected_signals) > 3:
                strategy_name += f"_Plus{len(selected_signals)-3}"
            
            strategies[strategy_name] = signal_weights
        
        logger.info(f"Generated {len(strategies)} random strategy combinations for broad exploration")
        for name, weights in strategies.items():
            logger.debug(f"  {name}: {list(weights.keys())}")
        
        return strategies
    
    def run_all_strategies(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        运行所有策略组合的回测
        
        Returns:
            List of results sorted by total_return
        """
        strategies = self._generate_strategy_combinations({})
        results = []
        
        logger.info(f"Running {len(strategies)} strategies for {symbol}")
        
        for strategy_name, signal_weights in strategies.items():
            try:
                # Create a new backtest engine instance for each strategy
                # This ensures each strategy starts with fresh initial capital
                backtest_engine = OptionBacktest(
                    initial_capital=self.initial_capital,
                    use_real_prices=True
                )
                
                # 运行回测
                backtest_result = backtest_engine.run_backtest(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    strategy='auto',
                    entry_signal=signal_weights,  # 传入信号权重字典
                    profit_target=5.0,  # 500% profit target
                    stop_loss=-0.5,  # -50% stop loss
                    max_holding_days=30,
                    position_size=0.1
                )
                
                # 整理结果
                result = {
                    'strategy_name': strategy_name,
                    'signal_weights': signal_weights,
                    'total_return': backtest_result.total_return,
                    'sharpe_ratio': backtest_result.sharpe_ratio,
                    'win_rate': backtest_result.win_rate,
                    'num_trades': backtest_result.num_trades,
                    'max_drawdown': backtest_result.max_drawdown,
                    'avg_win': backtest_result.avg_win,
                    'avg_loss': backtest_result.avg_loss
                }
                
                results.append(result)
                
                logger.info(f"  ✓ {strategy_name}: Return={backtest_result.total_return:+.2%}, "
                          f"WinRate={backtest_result.win_rate:.1%}, "
                          f"Trades={backtest_result.num_trades}")
                
            except Exception as e:
                logger.error(f"  ✗ {strategy_name} failed: {e}")
                continue
        
        # 按总收益率排序
        results.sort(key=lambda x: x['total_return'], reverse=True)
        
        return results
    
    def generate_comparison_report(self, symbol: str):
        """生成对比报告（占位符）"""
        logger.info(f"Report generation skipped for {symbol}")
        pass

