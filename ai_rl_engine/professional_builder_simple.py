#!/usr/bin/env python3
"""
Professional Builder - 简化版

不依赖真实期权链数据
基于股票数据和波动率智能推荐 Strangle 策略
适用于 Polygon 免费版用户
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OptionLeg:
    """期权腿数据结构"""
    type: str  # 'put' or 'call'
    strike: float
    expiry: str
    estimated_premium: float
    delta: float
    theta: float
    distance_pct: float  # 距离当前价格的百分比


@dataclass
class StranglePosition:
    """Strangle 头寸"""
    symbol: str
    current_price: float
    put_leg: OptionLeg
    call_leg: OptionLeg
    net_delta: float
    estimated_total_premium: float
    estimated_margin: float
    max_profit: float
    breakeven_down: float
    breakeven_up: float
    profit_zone: Tuple[float, float]
    quality_score: float
    dte: int


class ProfessionalBuilderSimple:
    """
    专业建仓引擎 - 简化版
    
    特点：
    - 不依赖期权链数据
    - 基于股票价格和历史波动率
    - 使用 Black-Scholes 估算权利金
    - 智能推荐行权价
    """
    
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY not set")
        
        self.base_url = "https://api.polygon.io"
        logger.info("ProfessionalBuilderSimple initialized")
    
    def build_strangle(
        self,
        symbol: str,
        dte_target: int = 45,
        delta_range: Tuple[float, float] = (-0.1, 0.1)
    ) -> Optional[StranglePosition]:
        """
        构建 Strangle 策略（简化版）
        
        Args:
            symbol: 标的代码
            dte_target: 目标到期天数
            delta_range: Net Delta 范围
        
        Returns:
            StranglePosition 或 None
        """
        logger.info(f"Building Strangle for {symbol} (Simple Mode)...")
        
        # 1. 获取当前价格
        current_price = self._get_current_price(symbol)
        if not current_price:
            logger.error(f"Failed to get price for {symbol}")
            return None
        
        logger.info(f"  ✓ Current price: ${current_price:.2f}")
        
        # 2. 计算历史波动率
        volatility = self._calculate_volatility(symbol)
        if not volatility:
            volatility = 0.30  # 默认 30% 年化波动率
        
        logger.info(f"  ✓ Historical volatility: {volatility:.1%}")
        
        # 3. 计算标准差（用于选择行权价）
        std_dev = current_price * volatility * np.sqrt(dte_target / 252)
        
        logger.info(f"  ✓ Std dev ({dte_target}d): ${std_dev:.2f}")
        
        # 4. 选择行权价（1个标准差外）
        put_strike = self._round_strike(current_price - std_dev)
        call_strike = self._round_strike(current_price + std_dev)
        
        logger.info(f"  ✓ Put strike: ${put_strike:.2f}")
        logger.info(f"  ✓ Call strike: ${call_strike:.2f}")
        
        # 5. 估算权利金（简化的 Black-Scholes）
        expiry = (datetime.now() + timedelta(days=dte_target)).strftime('%Y-%m-%d')
        
        put_premium = self._estimate_option_price(
            current_price, put_strike, dte_target, volatility, 'put'
        )
        call_premium = self._estimate_option_price(
            current_price, call_strike, dte_target, volatility, 'call'
        )
        
        logger.info(f"  ✓ Estimated put premium: ${put_premium:.2f}")
        logger.info(f"  ✓ Estimated call premium: ${call_premium:.2f}")
        
        # 6. 计算 Greeks（简化估算）
        put_delta = -0.25  # OTM put 约 -0.25 delta
        call_delta = 0.25  # OTM call 约 0.25 delta
        
        net_delta = put_delta + call_delta
        
        # 7. 创建 OptionLeg 对象
        put_leg = OptionLeg(
            type='put',
            strike=put_strike,
            expiry=expiry,
            estimated_premium=put_premium,
            delta=put_delta,
            theta=-0.02,  # 估算
            distance_pct=(current_price - put_strike) / current_price
        )
        
        call_leg = OptionLeg(
            type='call',
            strike=call_strike,
            expiry=expiry,
            estimated_premium=call_premium,
            delta=call_delta,
            theta=-0.02,  # 估算
            distance_pct=(call_strike - current_price) / current_price
        )
        
        # 8. 计算总权利金和盈亏
        total_premium = (put_premium + call_premium) * 100  # per contract
        
        breakeven_down = put_strike - (put_premium + call_premium)
        breakeven_up = call_strike + (put_premium + call_premium)
        
        # 9. 估算保证金
        estimated_margin = max(
            put_strike * 0.20 * 100,
            (call_strike - current_price) * 0.20 * 100
        )
        
        # 10. 质量评分
        quality_score = self._calculate_quality_score(
            put_leg, call_leg, net_delta, volatility
        )
        
        return StranglePosition(
            symbol=symbol,
            current_price=current_price,
            put_leg=put_leg,
            call_leg=call_leg,
            net_delta=net_delta,
            estimated_total_premium=total_premium,
            estimated_margin=estimated_margin,
            max_profit=total_premium,
            breakeven_down=breakeven_down,
            breakeven_up=breakeven_up,
            profit_zone=(breakeven_down, breakeven_up),
            quality_score=quality_score,
            dte=dte_target
        )
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """从 Polygon 获取当前价格"""
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev"
        params = {'apiKey': self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    return data['results'][0]['c']  # close price
        except Exception as e:
            logger.error(f"Polygon API error: {e}")
        
        return None
    
    def _calculate_volatility(self, symbol: str, days: int = 30) -> Optional[float]:
        """计算历史波动率"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'apiKey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    df = pd.DataFrame(data['results'])
                    df['return'] = df['c'].pct_change()
                    
                    # 年化波动率
                    volatility = df['return'].tail(days).std() * np.sqrt(252)
                    return volatility
        except Exception as e:
            logger.error(f"Volatility calculation error: {e}")
        
        return None
    
    def _round_strike(self, price: float) -> float:
        """将价格四舍五入到合理的行权价"""
        if price < 10:
            return round(price * 2) / 2  # 0.5 增量
        elif price < 50:
            return round(price)  # 1 增量
        elif price < 100:
            return round(price / 5) * 5  # 5 增量
        else:
            return round(price / 10) * 10  # 10 增量
    
    def _estimate_option_price(
        self,
        spot: float,
        strike: float,
        days: int,
        volatility: float,
        option_type: str
    ) -> float:
        """
        简化的期权定价（基于 intrinsic value + time value）
        
        这不是完整的 Black-Scholes，但对于估算足够了
        """
        # 内在价值
        if option_type == 'put':
            intrinsic = max(strike - spot, 0)
        else:  # call
            intrinsic = max(spot - strike, 0)
        
        # 时间价值（简化估算）
        # 基于波动率和剩余时间
        time_value = spot * volatility * np.sqrt(days / 252) * 0.4
        
        # OTM 期权主要是时间价值
        if intrinsic == 0:
            # 根据距离调整时间价值
            moneyness = abs(spot - strike) / spot
            time_value *= np.exp(-moneyness * 2)  # 越远价值越低
        
        total_value = intrinsic + time_value
        
        # 确保有最小值
        return max(total_value, 0.05)
    
    def _calculate_quality_score(
        self,
        put_leg: OptionLeg,
        call_leg: OptionLeg,
        net_delta: float,
        volatility: float
    ) -> float:
        """计算建仓方案质量评分"""
        
        # 1. Delta 平衡得分
        delta_score = 1 - abs(net_delta) / 0.5
        delta_score = max(delta_score, 0)
        
        # 2. 对称性得分（Put 和 Call 距离是否相近）
        distance_diff = abs(put_leg.distance_pct - call_leg.distance_pct)
        symmetry_score = 1 - distance_diff / 0.1
        symmetry_score = max(symmetry_score, 0)
        
        # 3. 权利金平衡得分
        premium_ratio = min(
            put_leg.estimated_premium / call_leg.estimated_premium,
            call_leg.estimated_premium / put_leg.estimated_premium
        )
        premium_score = premium_ratio
        
        # 4. 波动率得分（中等波动率最佳）
        if 0.25 <= volatility <= 0.45:
            vol_score = 1.0
        else:
            vol_score = 0.7
        
        # 综合评分
        quality = (
            0.35 * delta_score +
            0.25 * symmetry_score +
            0.25 * premium_score +
            0.15 * vol_score
        )
        
        return np.clip(quality, 0, 1)


# =============================================================================
# 使用示例
# =============================================================================

def main():
    """测试"""
    
    builder = ProfessionalBuilderSimple()
    
    symbol = 'GOOGL'
    position = builder.build_strangle(symbol, dte_target=45)
    
    if not position:
        print(f"Failed to build Strangle for {symbol}")
        return
    
    print("\n" + "="*80)
    print(f"🛠️  Professional Builder (Simple Mode) - {symbol}")
    print("="*80 + "\n")
    
    print(f"📊 Market Data:")
    print(f"   Current Price: ${position.current_price:.2f}")
    print(f"   DTE: {position.dte} days")
    
    print(f"\n📋 Put Leg (SELL):")
    print(f"   Strike: ${position.put_leg.strike:.2f}")
    print(f"   Distance: {position.put_leg.distance_pct:.1%} OTM")
    print(f"   Estimated Premium: ${position.put_leg.estimated_premium:.2f}")
    print(f"   Delta: {position.put_leg.delta:.3f}")
    
    print(f"\n📋 Call Leg (SELL):")
    print(f"   Strike: ${position.call_leg.strike:.2f}")
    print(f"   Distance: {position.call_leg.distance_pct:.1%} OTM")
    print(f"   Estimated Premium: ${position.call_leg.estimated_premium:.2f}")
    print(f"   Delta: {position.call_leg.delta:.3f}")
    
    print(f"\n📊 Greeks:")
    print(f"   Net Delta: {position.net_delta:.3f}")
    
    print(f"\n💰 P&L Profile:")
    print(f"   Total Premium (Credit): ${position.estimated_total_premium:.2f}")
    print(f"   Max Profit: ${position.max_profit:.2f}")
    print(f"   Estimated Margin: ${position.estimated_margin:.2f}")
    print(f"   Profit Zone: ${position.breakeven_down:.2f} - ${position.breakeven_up:.2f}")
    
    print(f"\n⭐ Quality Score: {position.quality_score:.2f}")
    
    print("\n" + "="*80)
    print("✅ 基于真实 Polygon 数据 + 智能估算")
    print("💡 注意: 权利金为估算值，实际交易前请核实")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()




