#!/usr/bin/env python3
"""
丰富的入场信号库

包含多种技术指标组合
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalLibrary:
    """入场信号库"""
    
    @staticmethod
    def calculate_all_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """计算所有技术指标"""
        df = data.copy()
        
        # 1. 移动平均
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma50'] = df['close'].rolling(50).mean()
        
        # 2. RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 3. 布林带
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # BB宽度百分位
        df['bb_width_pct'] = df['bb_width'].rolling(60).apply(
            lambda x: (x.iloc[-1] <= x).sum() / len(x) if len(x) > 0 else 0.5
        )
        
        # 4. MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # 5. 成交量指标
        df['volume_ma20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        # 6. ATR（真实波动幅度）
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # 7. 动量指标
        df['momentum'] = df['close'].pct_change(5)
        df['roc'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10)
        
        # 8. 威廉指标
        highest_high = df['high'].rolling(14).max()
        lowest_low = df['low'].rolling(14).min()
        df['williams_r'] = -100 * (highest_high - df['close']) / (highest_high - lowest_low)
        
        # 9. CCI（顺势指标）
        tp = (df['high'] + df['low'] + df['close']) / 3
        ma_tp = tp.rolling(20).mean()
        mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean())
        df['cci'] = (tp - ma_tp) / (0.015 * mad)
        
        # 10. 价格位置
        df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / \
                               (df['high'].rolling(20).max() - df['low'].rolling(20).min())
        
        return df
    
    @staticmethod
    def get_signal_definitions() -> Dict[str, Dict]:
        """
        获取所有信号定义
        
        Returns:
            信号字典，包含名称、描述和检测函数
        """
        return {
            # 基础信号
            'bb_compression': {
                'name': 'BB压缩',
                'description': 'Bollinger Band宽度压缩 < 30%分位',
                'weight': 0.15,
                'params': {'threshold': 0.3}
            },
            
            'rsi_oversold': {
                'name': 'RSI超卖',
                'description': 'RSI < 30',
                'weight': 0.12,
                'params': {'threshold': 30}
            },
            
            'rsi_overbought': {
                'name': 'RSI超买',
                'description': 'RSI > 70',
                'weight': 0.12,
                'params': {'threshold': 70}
            },
            
            'volume_surge': {
                'name': '成交量激增',
                'description': '成交量 > 20日均量的1.5倍',
                'weight': 0.10,
                'params': {'threshold': 1.5}
            },
            
            # 趋势信号
            'ma_crossover': {
                'name': '均线金叉',
                'description': 'MA5上穿MA20',
                'weight': 0.08,
                'params': {}
            },
            
            'ma_crossunder': {
                'name': '均线死叉',
                'description': 'MA5下穿MA20',
                'weight': 0.08,
                'params': {}
            },
            
            'price_above_ma50': {
                'name': '价格在MA50上方',
                'description': '价格 > MA50（上升趋势）',
                'weight': 0.05,
                'params': {}
            },
            
            # MACD信号
            'macd_crossover': {
                'name': 'MACD金叉',
                'description': 'MACD线上穿信号线',
                'weight': 0.10,
                'params': {}
            },
            
            'macd_divergence': {
                'name': 'MACD背离',
                'description': '价格新低但MACD未新低',
                'weight': 0.08,
                'params': {}
            },
            
            # 波动率信号
            'low_volatility': {
                'name': '低波动率',
                'description': 'ATR处于低位（突破前兆）',
                'weight': 0.06,
                'params': {'threshold': 0.3}
            },
            
            # 威廉指标
            'williams_oversold': {
                'name': 'Williams超卖',
                'description': 'Williams %R < -80',
                'weight': 0.06,
                'params': {'threshold': -80}
            },
            
            'williams_overbought': {
                'name': 'Williams超买',
                'description': 'Williams %R > -20',
                'weight': 0.06,
                'params': {'threshold': -20}
            },
            
            # 综合信号
            'bb_breakout': {
                'name': 'BB突破',
                'description': '价格突破上轨或下轨',
                'weight': 0.08,
                'params': {}
            },
            
            'cci_extreme': {
                'name': 'CCI极值',
                'description': 'CCI < -100 或 > 100',
                'weight': 0.06,
                'params': {'threshold': 100}
            },
            
            'momentum_reversal': {
                'name': '动量反转',
                'description': '动量从负转正或从正转负',
                'weight': 0.07,
                'params': {}
            }
        }
    
    @staticmethod
    def detect_signal(signal_name: str, data: pd.DataFrame, idx: int) -> Tuple[bool, float]:
        """
        检测单个信号
        
        Args:
            signal_name: 信号名称
            data: 数据（已计算指标）
            idx: 当前索引
        
        Returns:
            (是否触发, 信号强度)
        """
        if idx < 50:  # 确保有足够历史数据
            return False, 0.0
        
        row = data.iloc[idx]
        prev_row = data.iloc[idx-1] if idx > 0 else row
        
        # BB压缩
        if signal_name == 'bb_compression':
            triggered = row['bb_width_pct'] < 0.3
            strength = 1.0 - row['bb_width_pct'] if triggered else 0.0
            return triggered, strength
        
        # RSI超卖
        elif signal_name == 'rsi_oversold':
            triggered = row['rsi'] < 30
            strength = (30 - row['rsi']) / 30 if triggered else 0.0
            return triggered, strength
        
        # RSI超买
        elif signal_name == 'rsi_overbought':
            triggered = row['rsi'] > 70
            strength = (row['rsi'] - 70) / 30 if triggered else 0.0
            return triggered, strength
        
        # 成交量激增
        elif signal_name == 'volume_surge':
            triggered = row['volume_ratio'] > 1.5
            strength = min((row['volume_ratio'] - 1.5) / 1.5, 1.0) if triggered else 0.0
            return triggered, strength
        
        # 均线金叉
        elif signal_name == 'ma_crossover':
            triggered = (row['ma5'] > row['ma20']) and (prev_row['ma5'] <= prev_row['ma20'])
            strength = abs(row['ma5'] - row['ma20']) / row['ma20'] if triggered else 0.0
            return triggered, strength
        
        # 均线死叉
        elif signal_name == 'ma_crossunder':
            triggered = (row['ma5'] < row['ma20']) and (prev_row['ma5'] >= prev_row['ma20'])
            strength = abs(row['ma5'] - row['ma20']) / row['ma20'] if triggered else 0.0
            return triggered, strength
        
        # 价格在MA50上方
        elif signal_name == 'price_above_ma50':
            triggered = row['close'] > row['ma50']
            strength = (row['close'] - row['ma50']) / row['ma50'] if triggered else 0.0
            return triggered, min(strength, 1.0)
        
        # MACD金叉
        elif signal_name == 'macd_crossover':
            triggered = (row['macd'] > row['macd_signal']) and \
                       (prev_row['macd'] <= prev_row['macd_signal'])
            strength = abs(row['macd_hist']) / row['close'] * 100 if triggered else 0.0
            return triggered, min(strength, 1.0)
        
        # MACD背离
        elif signal_name == 'macd_divergence':
            if idx < 60:
                return False, 0.0
            recent_prices = data.iloc[idx-10:idx+1]['close']
            recent_macd = data.iloc[idx-10:idx+1]['macd']
            
            price_min_idx = recent_prices.idxmin()
            macd_min_idx = recent_macd.idxmin()
            
            triggered = (price_min_idx != macd_min_idx) and (recent_prices.iloc[-1] < recent_prices.iloc[0])
            strength = 0.7 if triggered else 0.0
            return triggered, strength
        
        # 低波动率
        elif signal_name == 'low_volatility':
            atr_pct = data.iloc[max(0, idx-60):idx+1]['atr'].rank(pct=True).iloc[-1]
            triggered = atr_pct < 0.3
            strength = 1.0 - atr_pct if triggered else 0.0
            return triggered, strength
        
        # Williams超卖
        elif signal_name == 'williams_oversold':
            triggered = row['williams_r'] < -80
            strength = (-80 - row['williams_r']) / 20 if triggered else 0.0
            return triggered, min(strength, 1.0)
        
        # Williams超买
        elif signal_name == 'williams_overbought':
            triggered = row['williams_r'] > -20
            strength = (row['williams_r'] + 20) / 20 if triggered else 0.0
            return triggered, min(strength, 1.0)
        
        # BB突破
        elif signal_name == 'bb_breakout':
            triggered = (row['close'] > row['bb_upper']) or (row['close'] < row['bb_lower'])
            if row['close'] > row['bb_upper']:
                strength = (row['close'] - row['bb_upper']) / row['bb_middle']
            elif row['close'] < row['bb_lower']:
                strength = (row['bb_lower'] - row['close']) / row['bb_middle']
            else:
                strength = 0.0
            return triggered, min(strength, 1.0)
        
        # CCI极值
        elif signal_name == 'cci_extreme':
            triggered = abs(row['cci']) > 100
            strength = min(abs(row['cci']) / 200, 1.0) if triggered else 0.0
            return triggered, strength
        
        # 动量反转
        elif signal_name == 'momentum_reversal':
            triggered = (row['momentum'] * prev_row['momentum'] < 0)  # 符号改变
            strength = abs(row['momentum']) if triggered else 0.0
            return triggered, min(strength, 1.0)
        
        else:
            return False, 0.0
    
    @staticmethod
    def evaluate_signal_combination(
        data: pd.DataFrame,
        idx: int,
        signal_weights: Dict[str, float]
    ) -> Tuple[float, str, Dict]:
        """
        评估信号组合
        
        Args:
            data: 数据
            idx: 当前索引
            signal_weights: 信号权重字典
        
        Returns:
            (综合得分, 推荐方向, 详细信息)
        """
        total_score = 0.0
        active_signals = []
        signal_details = {}
        
        for signal_name, weight in signal_weights.items():
            triggered, strength = SignalLibrary.detect_signal(signal_name, data, idx)
            
            if triggered:
                contribution = weight * strength
                total_score += contribution
                active_signals.append(signal_name)
                signal_details[signal_name] = {
                    'triggered': True,
                    'strength': strength,
                    'contribution': contribution
                }
        
        # 判断方向
        row = data.iloc[idx]
        
        # 看涨信号
        bullish_signals = [
            'rsi_oversold', 'ma_crossover', 'macd_crossover',
            'williams_oversold', 'momentum_reversal'
        ]
        
        # 看跌信号
        bearish_signals = [
            'rsi_overbought', 'ma_crossunder', 'williams_overbought'
        ]
        
        bullish_score = sum(signal_details.get(s, {}).get('contribution', 0) 
                          for s in bullish_signals if s in active_signals)
        bearish_score = sum(signal_details.get(s, {}).get('contribution', 0) 
                          for s in bearish_signals if s in active_signals)
        
        if bullish_score > bearish_score:
            direction = 'long_call'
        elif bearish_score > bullish_score:
            direction = 'long_put'
        else:
            # 根据RSI判断
            direction = 'long_call' if row['rsi'] < 50 else 'long_put'
        
        return total_score, direction, signal_details


if __name__ == '__main__':
    print("Signal Library Module")
    print(f"Total signals: {len(SignalLibrary.get_signal_definitions())}")
    
    for name, info in SignalLibrary.get_signal_definitions().items():
        print(f"  • {info['name']}: {info['description']}")



