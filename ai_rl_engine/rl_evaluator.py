#!/usr/bin/env python3
"""
RL Evaluator - 强化学习评估引擎

功能：
1. 对 AI 筛选的信号进行深度评估
2. 计算风险调整后收益（Sharpe/Sortino）
3. 估算 Expected PnL 和 Max Drawdown
4. 输出 RL Score (0-1)

策略核心：
- 基于历史回测模拟 RL 评估
- 考虑市场状态（VIX, IV Rank）
- 动态调整风险权重
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RLEvaluation:
    """RL 评估结果"""
    symbol: str
    rl_score: float  # 0-1, 越高越好
    expected_pnl: float  # 预期盈亏（美元）
    max_drawdown_risk: float  # 最大回撤风险（%）
    win_rate: float  # 胜率
    sharpe_ratio: float  # 夏普比率
    confidence: str  # 'high', 'medium', 'low'
    recommendation: str  # 'STRONG_BUY', 'BUY', 'WAIT'


class RLEvaluator:
    """
    RL 评估引擎
    
    简化版实现：
    - 使用历史回测数据模拟 RL 评估
    - 真实 RL 需要训练 PPO/DQN 模型
    
    未来升级：
    - 集成 Stable-Baselines3
    - 实时 RL 策略更新
    - 多 Agent 协同
    """
    
    def __init__(self, risk_free_rate: float = 0.045):
        """
        Args:
            risk_free_rate: 无风险利率（用于 Sharpe 计算）
        """
        self.risk_free_rate = risk_free_rate
        
        # 历史回测参数（mock）
        self.historical_stats = self._load_historical_stats()
    
    def evaluate(self, signal: Dict) -> RLEvaluation:
        """
        评估单个信号
        
        Args:
            signal: 信号字典，需包含：
                - symbol
                - bb_percentile
                - iv_rank
                - liquidity_score
                - signal_strength
        
        Returns:
            RLEvaluation 对象
        """
        symbol = signal['symbol']
        logger.info(f"Evaluating {symbol}...")
        
        # 1. 计算历史表现统计
        stats = self._get_symbol_stats(symbol, signal)
        
        # 2. 计算 Expected PnL
        expected_pnl = self._calculate_expected_pnl(signal, stats)
        
        # 3. 计算 Max Drawdown Risk
        max_dd_risk = self._calculate_max_drawdown_risk(signal, stats)
        
        # 4. 计算 Sharpe Ratio
        sharpe = self._calculate_sharpe(stats)
        
        # 5. 计算胜率
        win_rate = stats['win_rate']
        
        # 6. 综合 RL Score
        rl_score = self._calculate_rl_score(
            expected_pnl, max_dd_risk, sharpe, win_rate, signal
        )
        
        # 7. 生成建议
        recommendation = self._generate_recommendation(rl_score, max_dd_risk)
        
        # 8. 置信度
        confidence = 'high' if rl_score > 0.75 else 'medium' if rl_score > 0.5 else 'low'
        
        return RLEvaluation(
            symbol=symbol,
            rl_score=rl_score,
            expected_pnl=expected_pnl,
            max_drawdown_risk=max_dd_risk,
            win_rate=win_rate,
            sharpe_ratio=sharpe,
            confidence=confidence,
            recommendation=recommendation
        )
    
    def evaluate_batch(self, signals: pd.DataFrame) -> pd.DataFrame:
        """
        批量评估
        
        Args:
            signals: AI 生成的信号 DataFrame
        
        Returns:
            增强后的 DataFrame（添加 RL 评估列）
        """
        evaluations = []
        
        for _, signal in signals.iterrows():
            try:
                eval_result = self.evaluate(signal.to_dict())
                evaluations.append(vars(eval_result))
            except Exception as e:
                logger.warning(f"Failed to evaluate {signal['symbol']}: {e}")
                continue
        
        if not evaluations:
            return pd.DataFrame()
        
        eval_df = pd.DataFrame(evaluations)
        
        # 合并原始信号和评估结果
        result = pd.merge(
            signals, 
            eval_df, 
            on='symbol', 
            how='inner'
        )
        
        return result.sort_values('rl_score', ascending=False)
    
    def _load_historical_stats(self) -> Dict:
        """
        加载历史回测统计
        
        实际应用中：
        - 从数据库读取
        - 或运行完整回测引擎
        
        这里 mock 返回
        """
        return {
            'default': {
                'avg_return': 0.08,  # 8% 平均收益
                'std_return': 0.15,  # 15% 标准差
                'win_rate': 0.65,    # 65% 胜率
                'avg_win': 150,      # 平均盈利 $150
                'avg_loss': -80,     # 平均亏损 $80
                'max_dd': 0.20,      # 最大回撤 20%
            }
        }
    
    def _get_symbol_stats(self, symbol: str, signal: Dict) -> Dict:
        """
        获取标的历史统计
        
        根据信号特征调整基准统计
        """
        base_stats = self.historical_stats['default'].copy()
        
        # 根据 BB 百分位调整
        bb_percentile = signal.get('bb_percentile', 0.5)
        if bb_percentile < 0.3:  # 低波动率压缩
            base_stats['avg_return'] *= 1.2
            base_stats['win_rate'] *= 1.1
        
        # 根据流动性调整
        liquidity = signal.get('liquidity_score', 0.5)
        if liquidity < 0.5:  # 低流动性
            base_stats['std_return'] *= 1.3
            base_stats['max_dd'] *= 1.2
        
        # 根据 IV Rank 调整
        iv_rank = signal.get('iv_rank', 50)
        if 30 <= iv_rank <= 70:  # 最佳 IV 区间
            base_stats['avg_return'] *= 1.15
        
        return base_stats
    
    def _calculate_expected_pnl(self, signal: Dict, stats: Dict) -> float:
        """
        计算 Expected PnL
        
        公式：
        E[PnL] = P(win) * Avg_Win + P(loss) * Avg_Loss
        """
        win_rate = stats['win_rate']
        avg_win = stats['avg_win']
        avg_loss = stats['avg_loss']
        
        expected = win_rate * avg_win + (1 - win_rate) * avg_loss
        
        # 根据信号强度调整
        signal_strength = signal.get('signal_strength', 0.5)
        expected *= signal_strength
        
        return expected
    
    def _calculate_max_drawdown_risk(self, signal: Dict, stats: Dict) -> float:
        """
        计算最大回撤风险
        
        考虑：
        - 历史 Max DD
        - 当前市场波动率
        - 信号质量
        """
        base_dd = stats['max_dd']
        
        # 根据流动性调整
        liquidity = signal.get('liquidity_score', 0.5)
        dd_risk = base_dd * (1 + (1 - liquidity) * 0.5)
        
        # 根据信号强度调整
        signal_strength = signal.get('signal_strength', 0.5)
        dd_risk *= (1 - signal_strength * 0.3)
        
        return np.clip(dd_risk, 0.05, 0.50)
    
    def _calculate_sharpe(self, stats: Dict) -> float:
        """
        计算 Sharpe Ratio
        
        Sharpe = (E[R] - Rf) / σ[R]
        """
        avg_return = stats['avg_return']
        std_return = stats['std_return']
        
        if std_return == 0:
            return 0.0
        
        sharpe = (avg_return - self.risk_free_rate) / std_return
        
        return sharpe
    
    def _calculate_rl_score(
        self,
        expected_pnl: float,
        max_dd_risk: float,
        sharpe: float,
        win_rate: float,
        signal: Dict
    ) -> float:
        """
        综合 RL Score
        
        权重：
        - Expected PnL: 30%
        - Sharpe Ratio: 25%
        - Win Rate: 20%
        - Max DD (inverse): 15%
        - Signal Strength: 10%
        """
        # 归一化各指标
        pnl_score = np.clip(expected_pnl / 200, 0, 1)  # $200+ = 满分
        sharpe_score = np.clip(sharpe / 2.0, 0, 1)     # Sharpe 2.0+ = 满分
        wr_score = win_rate                            # 已归一化
        dd_score = 1 - max_dd_risk                     # 反向
        signal_score = signal.get('signal_strength', 0.5)
        
        # 加权求和
        rl_score = (
            0.30 * pnl_score +
            0.25 * sharpe_score +
            0.20 * wr_score +
            0.15 * dd_score +
            0.10 * signal_score
        )
        
        return np.clip(rl_score, 0, 1)
    
    def _generate_recommendation(self, rl_score: float, max_dd: float) -> str:
        """生成交易建议"""
        if rl_score >= 0.75 and max_dd < 0.25:
            return 'STRONG_BUY'
        elif rl_score >= 0.60 and max_dd < 0.35:
            return 'BUY'
        else:
            return 'WAIT'


# =============================================================================
# 使用示例
# =============================================================================

def main():
    """示例：评估 AI 信号"""
    
    # Mock 信号
    signal = {
        'symbol': 'NVDA',
        'bb_percentile': 0.25,
        'iv_rank': 45,
        'liquidity_score': 0.85,
        'signal_strength': 0.78
    }
    
    evaluator = RLEvaluator()
    result = evaluator.evaluate(signal)
    
    print("\n" + "="*80)
    print("🤖 RL Evaluator - Deep Analysis")
    print("="*80 + "\n")
    
    print(f"Symbol: {result.symbol}")
    print(f"RL Score: {result.rl_score:.2f}")
    print(f"Expected PnL: ${result.expected_pnl:.2f}")
    print(f"Max Drawdown Risk: {result.max_drawdown_risk:.1%}")
    print(f"Win Rate: {result.win_rate:.1%}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Confidence: {result.confidence.upper()}")
    print(f"Recommendation: {result.recommendation}")
    
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()




