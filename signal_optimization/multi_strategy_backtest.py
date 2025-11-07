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
        
        Returns:
            Dict of {strategy_name: signal_weights}
        """
        # 基础策略组合
        strategies = {
            "MACD_RSI_BB": {
                "macd_crossover": 0.3,
                "rsi_oversold": 0.3,
                "bb_compression": 0.4
            },
            "Volume_MA_Momentum": {
                "volume_surge": 0.4,
                "ma_crossover": 0.3,
                "price_above_ma50": 0.3
            },
            "CCI_Williams_Hybrid": {
                "cci_extreme": 0.4,
                "williams_oversold": 0.3,
                "low_volatility": 0.3
            },
            "BB_Volume_Hybrid": {
                "bb_breakout": 0.4,
                "volume_surge": 0.3,
                "macd_crossover": 0.3
            },
            "RSI_MACD_Divergence": {
                "rsi_oversold": 0.4,
                "macd_divergence": 0.3,
                "low_volatility": 0.3
            }
        }
        
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

