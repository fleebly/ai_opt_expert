#!/usr/bin/env python3
"""
动态策略方向选择器

根据市场信号自动选择 Long Call 或 Long Put
"""

import logging
from typing import Tuple
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyDirectionSelector:
    """
    动态选择期权方向（Call/Put）
    
    基于多个技术指标综合判断市场方向
    """
    
    @staticmethod
    def select_direction(
        data: pd.DataFrame,
        idx: int,
        signal_weights: dict = None
    ) -> Tuple[str, float]:
        """
        选择策略方向
        
        Args:
            data: 包含技术指标的数据
            idx: 当前索引
            signal_weights: 信号权重字典（可选）
        
        Returns:
            ('long_call' or 'long_put', 方向置信度 0-1)
        """
        
        if idx < 50:
            return 'long_call', 0.5  # 数据不足，默认看涨
        
        row = data.iloc[idx]
        prev_row = data.iloc[idx-1] if idx > 0 else row
        
        # 收集多个方向指标
        bullish_score = 0.0  # 看涨得分
        bearish_score = 0.0  # 看跌得分
        
        # 1. RSI 方向
        rsi = row.get('rsi', 50)
        if rsi < 30:
            bullish_score += 0.20  # 超卖，看涨
        elif rsi > 70:
            bearish_score += 0.20  # 超买，看跌
        elif rsi < 40:
            bullish_score += 0.10  # 偏超卖
        elif rsi > 60:
            bearish_score += 0.10  # 偏超买
        
        # 2. MACD 方向
        macd = row.get('macd', 0)
        macd_signal = row.get('macd_signal', 0)
        prev_macd = prev_row.get('macd', 0)
        prev_macd_signal = prev_row.get('macd_signal', 0)
        
        if macd > macd_signal:
            bullish_score += 0.15  # MACD在信号线上方，看涨
            if prev_macd <= prev_macd_signal:
                bullish_score += 0.10  # 刚金叉，更看涨
        elif macd < macd_signal:
            bearish_score += 0.15  # MACD在信号线下方，看跌
            if prev_macd >= prev_macd_signal:
                bearish_score += 0.10  # 刚死叉，更看跌
        
        # 3. 均线位置
        close = row.get('close', 0)
        ma20 = row.get('ma20', close)
        ma50 = row.get('ma50', close)
        
        if close > ma20 and close > ma50:
            bullish_score += 0.15  # 价格在均线上方，看涨
            if ma20 > ma50:
                bullish_score += 0.10  # 短期均线上穿长期，更看涨
        elif close < ma20 and close < ma50:
            bearish_score += 0.15  # 价格在均线下方，看跌
            if ma20 < ma50:
                bearish_score += 0.10  # 短期均线下穿长期，更看跌
        
        # 4. 均线交叉
        ma5 = row.get('ma5', close)
        prev_ma5 = prev_row.get('ma5', close)
        prev_ma20 = prev_row.get('ma20', ma20)
        
        if ma5 > ma20 and prev_ma5 <= prev_ma20:
            bullish_score += 0.15  # 短期均线金叉，看涨
        elif ma5 < ma20 and prev_ma5 >= prev_ma20:
            bearish_score += 0.15  # 短期均线死叉，看跌
        
        # 5. 价格动量
        if idx >= 5:
            recent_prices = data.iloc[idx-5:idx+1]['close']
            price_change = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]
            
            if price_change > 0.03:
                bullish_score += 0.10  # 近期上涨 > 3%，看涨
            elif price_change < -0.03:
                bearish_score += 0.10  # 近期下跌 > 3%，看跌
        
        # 6. 布林带位置
        bb_upper = row.get('bb_upper', close * 1.02)
        bb_lower = row.get('bb_lower', close * 0.98)
        bb_middle = (bb_upper + bb_lower) / 2
        
        if close < bb_lower:
            bullish_score += 0.10  # 接近下轨，可能反弹
        elif close > bb_upper:
            bearish_score += 0.10  # 接近上轨，可能回落
        elif close < bb_middle:
            bearish_score += 0.05  # 在中轨下方
        else:
            bullish_score += 0.05  # 在中轨上方
        
        # 7. Williams %R
        williams_r = row.get('williams_r', -50)
        if williams_r < -80:
            bullish_score += 0.10  # 超卖，看涨
        elif williams_r > -20:
            bearish_score += 0.10  # 超买，看跌
        
        # 8. 基于信号权重的方向判断（如果提供）
        if signal_weights:
            # 分析信号权重中的方向性
            directional_signals = StrategyDirectionSelector._analyze_signal_direction(
                signal_weights, row, prev_row
            )
            bullish_score += directional_signals['bullish'] * 0.15
            bearish_score += directional_signals['bearish'] * 0.15
        
        # 计算最终方向
        total_score = bullish_score + bearish_score
        
        if total_score == 0:
            # 没有明确信号，默认看涨
            return 'long_call', 0.5
        
        bullish_confidence = bullish_score / total_score
        bearish_confidence = bearish_score / total_score
        
        if bullish_confidence > bearish_confidence:
            direction = 'long_call'
            confidence = bullish_confidence
        else:
            direction = 'long_put'
            confidence = bearish_confidence
        
        logger.debug(
            f"Direction: {direction}, Confidence: {confidence:.2f} "
            f"(Bullish: {bullish_score:.2f}, Bearish: {bearish_score:.2f})"
        )
        
        return direction, confidence
    
    @staticmethod
    def _analyze_signal_direction(
        signal_weights: dict,
        row: pd.Series,
        prev_row: pd.Series
    ) -> dict:
        """分析信号权重中的方向性"""
        
        bullish_indicators = 0.0
        bearish_indicators = 0.0
        
        # 看涨信号
        bullish_signals = [
            'rsi_oversold',
            'ma_crossover',
            'macd_crossover',
            'williams_oversold',
            'bb_breakout'  # 如果突破上轨
        ]
        
        # 看跌信号
        bearish_signals = [
            'rsi_overbought',
            'ma_crossunder',
            'williams_overbought'
        ]
        
        # 中性信号（取决于突破方向）
        neutral_signals = [
            'bb_compression',
            'low_volatility',
            'volume_surge'
        ]
        
        for signal_name, weight in signal_weights.items():
            if signal_name in bullish_signals:
                bullish_indicators += weight
            elif signal_name in bearish_signals:
                bearish_indicators += weight
            elif signal_name in neutral_signals:
                # 中性信号根据其他指标判断
                pass
        
        # 归一化
        total = bullish_indicators + bearish_indicators
        if total > 0:
            return {
                'bullish': bullish_indicators / total,
                'bearish': bearish_indicators / total
            }
        else:
            return {'bullish': 0.5, 'bearish': 0.5}
    
    @staticmethod
    def explain_direction(
        data: pd.DataFrame,
        idx: int,
        direction: str,
        confidence: float
    ) -> str:
        """
        解释方向选择的原因
        
        Returns:
            解释文本
        """
        
        row = data.iloc[idx]
        
        reasons = []
        
        # RSI
        rsi = row.get('rsi', 50)
        if rsi < 30:
            reasons.append(f"RSI超卖 ({rsi:.1f})")
        elif rsi > 70:
            reasons.append(f"RSI超买 ({rsi:.1f})")
        
        # MACD
        macd = row.get('macd', 0)
        macd_signal = row.get('macd_signal', 0)
        if macd > macd_signal:
            reasons.append("MACD金叉")
        elif macd < macd_signal:
            reasons.append("MACD死叉")
        
        # 均线
        close = row.get('close', 0)
        ma20 = row.get('ma20', close)
        ma50 = row.get('ma50', close)
        
        if close > ma20 and close > ma50:
            reasons.append("价格强势（在均线上方）")
        elif close < ma20 and close < ma50:
            reasons.append("价格弱势（在均线下方）")
        
        # 布林带
        bb_upper = row.get('bb_upper', close * 1.02)
        bb_lower = row.get('bb_lower', close * 0.98)
        
        if close < bb_lower:
            reasons.append("接近布林带下轨")
        elif close > bb_upper:
            reasons.append("接近布林带上轨")
        
        direction_str = "看涨" if direction == 'long_call' else "看跌"
        
        if reasons:
            return f"{direction_str} (置信度 {confidence:.1%}): {', '.join(reasons)}"
        else:
            return f"{direction_str} (置信度 {confidence:.1%}): 综合技术指标"


if __name__ == '__main__':
    """测试代码"""
    import numpy as np
    
    print("🎯 策略方向选择器测试\n")
    print("="*80 + "\n")
    
    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=100)
    
    # 场景1: 看涨信号
    print("场景1: 看涨信号（超卖反弹）")
    data_bullish = pd.DataFrame({
        'date': dates,
        'close': np.linspace(100, 110, 100),  # 上涨趋势
        'rsi': [25] * 100,  # 超卖
        'macd': [0.5] * 100,
        'macd_signal': [0.3] * 100,  # MACD > Signal
        'ma5': np.linspace(100, 110, 100),
        'ma20': np.linspace(98, 108, 100),
        'ma50': np.linspace(95, 105, 100),
        'bb_upper': np.linspace(105, 115, 100),
        'bb_lower': np.linspace(95, 105, 100),
        'williams_r': [-85] * 100
    })
    
    selector = StrategyDirectionSelector()
    direction, confidence = selector.select_direction(data_bullish, 60)
    explanation = selector.explain_direction(data_bullish, 60, direction, confidence)
    
    print(f"方向: {direction}")
    print(f"置信度: {confidence:.1%}")
    print(f"原因: {explanation}")
    print()
    
    # 场景2: 看跌信号
    print("场景2: 看跌信号（超买回落）")
    data_bearish = pd.DataFrame({
        'date': dates,
        'close': np.linspace(110, 100, 100),  # 下跌趋势
        'rsi': [75] * 100,  # 超买
        'macd': [-0.5] * 100,
        'macd_signal': [-0.3] * 100,  # MACD < Signal
        'ma5': np.linspace(110, 100, 100),
        'ma20': np.linspace(112, 102, 100),
        'ma50': np.linspace(115, 105, 100),
        'bb_upper': np.linspace(115, 105, 100),
        'bb_lower': np.linspace(105, 95, 100),
        'williams_r': [-15] * 100
    })
    
    direction, confidence = selector.select_direction(data_bearish, 60)
    explanation = selector.explain_direction(data_bearish, 60, direction, confidence)
    
    print(f"方向: {direction}")
    print(f"置信度: {confidence:.1%}")
    print(f"原因: {explanation}")
    print()
    
    # 场景3: 中性信号
    print("场景3: 中性信号（震荡市）")
    data_neutral = pd.DataFrame({
        'date': dates,
        'close': [100] * 100,  # 横盘
        'rsi': [50] * 100,  # 中性
        'macd': [0] * 100,
        'macd_signal': [0] * 100,
        'ma5': [100] * 100,
        'ma20': [100] * 100,
        'ma50': [100] * 100,
        'bb_upper': [102] * 100,
        'bb_lower': [98] * 100,
        'williams_r': [-50] * 100
    })
    
    direction, confidence = selector.select_direction(data_neutral, 60)
    explanation = selector.explain_direction(data_neutral, 60, direction, confidence)
    
    print(f"方向: {direction}")
    print(f"置信度: {confidence:.1%}")
    print(f"原因: {explanation}")
    print()
    
    print("="*80)


