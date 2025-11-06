#!/usr/bin/env python3
"""
策略配置模块

动态 OTM 比例选择，基于市场条件和盈利预期
"""

from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np


@dataclass
class OTMConfig:
    """OTM 配置"""
    call_multiplier: float  # Call 倍数
    put_multiplier: float   # Put 倍数
    name: str              # 配置名称
    expected_move: float   # 预期涨跌幅
    win_rate: float        # 预期胜率
    leverage: float        # 预期杠杆
    
    def get_otm_pct(self, is_call: bool = True) -> float:
        """获取 OTM 百分比"""
        if is_call:
            return (self.call_multiplier - 1.0) * 100
        else:
            return (1.0 - self.put_multiplier) * 100


class DynamicOTMSelector:
    """动态 OTM 选择器"""
    
    # 预定义策略配置
    STRATEGIES = {
        'ultra_conservative': OTMConfig(
            call_multiplier=1.02,
            put_multiplier=0.98,
            name='Ultra Conservative (2% OTM)',
            expected_move=0.02,
            win_rate=0.70,
            leverage=15.0
        ),
        'conservative': OTMConfig(
            call_multiplier=1.05,
            put_multiplier=0.95,
            name='Conservative (5% OTM)',
            expected_move=0.05,
            win_rate=0.60,
            leverage=8.0
        ),
        'balanced': OTMConfig(
            call_multiplier=1.08,
            put_multiplier=0.92,
            name='Balanced (8% OTM)',
            expected_move=0.08,
            win_rate=0.50,
            leverage=5.0
        ),
        'moderate': OTMConfig(
            call_multiplier=1.12,
            put_multiplier=0.88,
            name='Moderate (12% OTM)',
            expected_move=0.12,
            win_rate=0.40,
            leverage=4.0
        ),
        'aggressive': OTMConfig(
            call_multiplier=1.15,
            put_multiplier=0.85,
            name='Aggressive (15% OTM)',
            expected_move=0.15,
            win_rate=0.30,
            leverage=3.5
        ),
        'speculative': OTMConfig(
            call_multiplier=1.20,
            put_multiplier=0.80,
            name='Speculative (20% OTM)',
            expected_move=0.20,
            win_rate=0.20,
            leverage=3.0
        )
    }
    
    @classmethod
    def select_otm_strategy(
        cls,
        volatility: float,
        momentum: float,
        bb_percentile: float,
        days_to_expiry: int = 30,
        risk_appetite: str = 'balanced'
    ) -> OTMConfig:
        """
        根据市场条件动态选择 OTM 策略
        
        Args:
            volatility: 波动率 (0-1)
            momentum: 动量指标 (-1 to 1)
            bb_percentile: 布林带百分位 (0-1)
            days_to_expiry: 到期天数
            risk_appetite: 风险偏好
        
        Returns:
            最优 OTM 配置
        """
        
        # 1. 基于波动率调整
        # 高波动 → 更保守（减少 OTM）
        # 低波动 → 可以更激进
        if volatility > 0.7:  # 高波动
            base_strategy = 'conservative'
        elif volatility > 0.5:  # 中等波动
            base_strategy = 'balanced'
        elif volatility > 0.3:  # 低波动
            base_strategy = 'moderate'
        else:  # 极低波动
            base_strategy = 'aggressive'
        
        # 2. 基于动量调整
        # 强势动量 → 可以更激进
        abs_momentum = abs(momentum)
        if abs_momentum > 0.5:  # 强动量
            # 根据方向和当前策略调整
            if base_strategy == 'conservative' and abs_momentum > 0.7:
                base_strategy = 'balanced'
            elif base_strategy == 'balanced' and abs_momentum > 0.8:
                base_strategy = 'moderate'
        
        # 3. 基于布林带位置调整
        # BB 压缩 (< 0.3) → 即将突破，可以更激进
        # BB 扩张 (> 0.7) → 已经过度，更保守
        if bb_percentile < 0.3:  # 压缩，即将突破
            if base_strategy == 'conservative':
                base_strategy = 'balanced'
            elif base_strategy == 'balanced':
                base_strategy = 'moderate'
        elif bb_percentile > 0.7:  # 扩张，趋于收敛
            if base_strategy == 'moderate':
                base_strategy = 'balanced'
            elif base_strategy == 'aggressive':
                base_strategy = 'moderate'
        
        # 4. 基于到期时间调整
        # 离到期越近，越保守（时间衰减风险）
        if days_to_expiry < 15:
            if base_strategy in ['aggressive', 'speculative']:
                base_strategy = 'moderate'
            elif base_strategy == 'moderate':
                base_strategy = 'balanced'
        
        # 5. 基于用户风险偏好调整
        if risk_appetite == 'ultra_conservative':
            if base_strategy != 'ultra_conservative':
                base_strategy = 'conservative'
        elif risk_appetite == 'aggressive':
            shift_map = {
                'conservative': 'balanced',
                'balanced': 'moderate',
                'moderate': 'aggressive'
            }
            base_strategy = shift_map.get(base_strategy, base_strategy)
        
        return cls.STRATEGIES[base_strategy]
    
    @classmethod
    def calculate_expected_profit(
        cls,
        config: OTMConfig,
        stock_price: float,
        predicted_move_pct: float,
        days_to_expiry: int = 30
    ) -> Dict:
        """
        计算给定 OTM 配置的预期盈利
        
        Args:
            config: OTM 配置
            stock_price: 当前股价
            predicted_move_pct: 预测涨跌幅
            days_to_expiry: 到期天数
        
        Returns:
            盈利预期字典
        """
        
        # 简化的期权价格模型
        is_call = predicted_move_pct > 0
        
        if is_call:
            strike = stock_price * config.call_multiplier
            otm_pct = config.get_otm_pct(True)
        else:
            strike = stock_price * config.put_multiplier
            otm_pct = config.get_otm_pct(False)
        
        # 估算入场价格（基于 OTM 程度和时间价值）
        entry_price = cls._estimate_option_price(
            stock_price, strike, is_call, days_to_expiry
        )
        
        # 估算到期价格（假设预测准确）
        exit_stock_price = stock_price * (1 + predicted_move_pct)
        exit_price = cls._estimate_option_price(
            exit_stock_price, strike, is_call, max(days_to_expiry - 15, 5)
        )
        
        # 计算盈亏
        profit_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
        
        # 是否实现盈利
        is_profitable = (is_call and exit_stock_price > strike) or \
                       (not is_call and exit_stock_price < strike)
        
        return {
            'config_name': config.name,
            'otm_pct': otm_pct,
            'strike': strike,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'profit_pct': profit_pct,
            'is_profitable': is_profitable,
            'expected_value': profit_pct * config.win_rate,  # 简单期望值
            'risk_reward_ratio': abs(profit_pct) / (otm_pct / 100) if otm_pct > 0 else 0
        }
    
    @staticmethod
    def _estimate_option_price(
        stock_price: float,
        strike: float,
        is_call: bool,
        days_to_expiry: int
    ) -> float:
        """简化的期权定价"""
        
        # 内在价值
        if is_call:
            intrinsic = max(stock_price - strike, 0)
        else:
            intrinsic = max(strike - stock_price, 0)
        
        # 时间价值
        if days_to_expiry > 0:
            moneyness = abs(stock_price - strike) / stock_price
            base_time = stock_price * 0.015 * (days_to_expiry / 30)
            otm_factor = np.exp(-moneyness * 5)
            time_value = base_time * otm_factor
            time_value = max(time_value, 0.05)
        else:
            time_value = 0
        
        return intrinsic + time_value
    
    @classmethod
    def recommend_best_strategy(
        cls,
        stock_price: float,
        volatility: float,
        momentum: float,
        bb_percentile: float,
        predicted_move_pct: float,
        days_to_expiry: int = 30
    ) -> tuple[OTMConfig, Dict]:
        """
        推荐最佳策略
        
        Returns:
            (最佳配置, 分析结果)
        """
        
        # 1. 基于市场条件选择候选策略
        primary = cls.select_otm_strategy(
            volatility, momentum, bb_percentile, days_to_expiry
        )
        
        # 2. 评估多个候选策略
        candidates = [
            cls.STRATEGIES['conservative'],
            cls.STRATEGIES['balanced'],
            cls.STRATEGIES['moderate'],
            cls.STRATEGIES['aggressive']
        ]
        
        evaluations = []
        for config in candidates:
            result = cls.calculate_expected_profit(
                config, stock_price, predicted_move_pct, days_to_expiry
            )
            evaluations.append((config, result))
        
        # 3. 选择期望值最高的
        best_config, best_result = max(
            evaluations,
            key=lambda x: x[1]['expected_value']
        )
        
        return best_config, {
            'primary_recommendation': primary.name,
            'best_by_expected_value': best_config.name,
            'all_evaluations': evaluations
        }


if __name__ == '__main__':
    # 测试
    selector = DynamicOTMSelector()
    
    print("🎯 动态 OTM 策略选择器")
    print("="*80 + "\n")
    
    # 场景1：低波动 + 强动量 + BB压缩
    print("场景1: 低波动 + 强动量 + BB压缩")
    config = selector.select_otm_strategy(
        volatility=0.25,
        momentum=0.6,
        bb_percentile=0.2,
        days_to_expiry=30
    )
    print(f"推荐: {config.name}")
    print(f"OTM: {config.get_otm_pct(True):.1f}%")
    print()
    
    # 场景2：高波动 + 弱动量
    print("场景2: 高波动 + 弱动量")
    config = selector.select_otm_strategy(
        volatility=0.8,
        momentum=0.1,
        bb_percentile=0.5,
        days_to_expiry=30
    )
    print(f"推荐: {config.name}")
    print(f"OTM: {config.get_otm_pct(True):.1f}%")
    print()
    
    # 场景3：综合推荐
    print("场景3: 综合推荐（预测上涨5%）")
    best_config, analysis = selector.recommend_best_strategy(
        stock_price=138.55,
        volatility=0.4,
        momentum=0.3,
        bb_percentile=0.3,
        predicted_move_pct=0.05,
        days_to_expiry=30
    )
    print(f"最佳策略: {best_config.name}")
    print(f"期望值: {analysis['all_evaluations'][0][1]['expected_value']:.2%}")


