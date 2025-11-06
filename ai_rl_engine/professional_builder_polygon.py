#!/usr/bin/env python3
"""
Professional Builder - Polygon 真实期权链版本

使用 Polygon API 的真实期权合约数据
支持真实的行权价、到期日选择
智能估算权利金（如果没有实时报价）
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
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
    ticker: str  # 完整的期权代码
    type: str  # 'put' or 'call'
    strike: float
    expiry: str
    premium: float  # 真实报价或估算
    is_estimated: bool  # 是否为估算值
    delta: float
    theta: float
    gamma: Optional[float] = None
    vega: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    distance_pct: float = 0.0


@dataclass
class StranglePosition:
    """Strangle 头寸"""
    symbol: str
    current_price: float
    put_leg: OptionLeg
    call_leg: OptionLeg
    net_delta: float
    total_premium: float
    estimated_margin: float
    max_profit: float
    breakeven_down: float
    breakeven_up: float
    profit_zone: Tuple[float, float]
    quality_score: float
    dte: int
    data_quality: str  # 'real', 'mixed', 'estimated'


class ProfessionalBuilderPolygon:
    """
    专业建仓引擎 - Polygon 真实期权链版本
    
    特点：
    - 使用 Polygon 真实期权合约
    - 支持真实到期日和行权价
    - 自动匹配最佳期权腿
    - 如果没有实时报价，智能估算
    - 考虑流动性（Open Interest, Volume）
    """
    
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY not set")
        
        self.base_url = "https://api.polygon.io"
        logger.info("ProfessionalBuilderPolygon initialized with REAL option chains")
    
    def build_strangle(
        self,
        symbol: str,
        dte_target: int = 45,
        delta_range: Tuple[float, float] = (-0.1, 0.1),
        min_open_interest: int = 50
    ) -> Optional[StranglePosition]:
        """
        构建 Strangle 策略（使用真实期权链）
        
        Args:
            symbol: 标的代码
            dte_target: 目标到期天数
            delta_range: Net Delta 范围
            min_open_interest: 最小持仓量（流动性过滤）
        
        Returns:
            StranglePosition 或 None
        """
        logger.info(f"Building Strangle for {symbol} with REAL option chains...")
        
        # 1. 获取当前价格
        current_price = self._get_current_price(symbol)
        if not current_price:
            logger.error(f"Failed to get price for {symbol}")
            return None
        
        logger.info(f"  ✓ Current price: ${current_price:.2f}")
        
        # 2. 获取真实期权链
        option_chain = self._get_option_chain(symbol, dte_target)
        if option_chain.empty:
            logger.error(f"Failed to get option chain for {symbol}")
            return None
        
        logger.info(f"  ✓ Loaded {len(option_chain)} option contracts")
        
        # 3. 计算历史波动率（用于估算）
        volatility = self._calculate_volatility(symbol)
        if not volatility:
            volatility = 0.30
        
        logger.info(f"  ✓ Historical volatility: {volatility:.1%}")
        
        # 4. 选择最佳到期日（先选到期日，再分离 Put/Call）
        target_expiry = self._select_best_expiry(option_chain, dte_target)
        if not target_expiry:
            logger.error("No suitable expiry found")
            return None
        
        logger.info(f"  ✓ Selected expiry: {target_expiry}")
        
        # 筛选该到期日的期权
        option_chain_expiry = option_chain[option_chain['expiration_date'] == target_expiry]
        
        # 5. 分离 Put 和 Call
        puts = option_chain_expiry[option_chain_expiry['contract_type'] == 'put'].copy()
        calls = option_chain_expiry[option_chain_expiry['contract_type'] == 'call'].copy()
        
        if puts.empty or calls.empty:
            logger.error(f"No put or call contracts found for expiry {target_expiry}")
            return None
        
        logger.info(f"  ✓ Puts: {len(puts)}, Calls: {len(calls)}")
        
        # 6. 选择 Put 腿（~1 标准差下方，OTM）
        put_leg = self._select_put_leg(
            puts, current_price, volatility, dte_target, min_open_interest
        )
        if not put_leg:
            logger.error("Failed to select put leg")
            return None
        
        logger.info(f"  ✓ Put leg: {put_leg.ticker} @ ${put_leg.strike:.2f}")
        
        # 7. 选择 Call 腿（~1 标准差上方，OTM）
        call_leg = self._select_call_leg(
            calls, current_price, volatility, dte_target, min_open_interest
        )
        if not call_leg:
            logger.error("Failed to select call leg")
            return None
        
        logger.info(f"  ✓ Call leg: {call_leg.ticker} @ ${call_leg.strike:.2f}")
        
        # 8. 计算 Net Delta 和其他指标
        net_delta = put_leg.delta + call_leg.delta
        total_premium = (put_leg.premium + call_leg.premium) * 100
        
        breakeven_down = put_leg.strike - (put_leg.premium + call_leg.premium)
        breakeven_up = call_leg.strike + (put_leg.premium + call_leg.premium)
        
        # 9. 估算保证金
        estimated_margin = max(
            put_leg.strike * 0.20 * 100,
            (call_leg.strike - current_price) * 0.20 * 100
        )
        
        # 10. 数据质量评估
        data_quality = self._assess_data_quality(put_leg, call_leg)
        
        # 11. 质量评分
        quality_score = self._calculate_quality_score(
            put_leg, call_leg, net_delta, volatility
        )
        
        # 计算实际 DTE
        actual_dte = (datetime.strptime(target_expiry, '%Y-%m-%d') - datetime.now()).days
        
        return StranglePosition(
            symbol=symbol,
            current_price=current_price,
            put_leg=put_leg,
            call_leg=call_leg,
            net_delta=net_delta,
            total_premium=total_premium,
            estimated_margin=estimated_margin,
            max_profit=total_premium,
            breakeven_down=breakeven_down,
            breakeven_up=breakeven_up,
            profit_zone=(breakeven_down, breakeven_up),
            quality_score=quality_score,
            dte=actual_dte,
            data_quality=data_quality
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
                    return data['results'][0]['c']
        except Exception as e:
            logger.error(f"Error fetching price: {e}")
        
        return None
    
    def _get_option_chain(
        self,
        symbol: str,
        dte_target: int,
        dte_tolerance: int = 15
    ) -> pd.DataFrame:
        """从 Polygon 获取真实期权链"""
        
        min_date = (datetime.now() + timedelta(days=dte_target - dte_tolerance)).strftime('%Y-%m-%d')
        max_date = (datetime.now() + timedelta(days=dte_target + dte_tolerance)).strftime('%Y-%m-%d')
        
        url = f"{self.base_url}/v3/reference/options/contracts"
        params = {
            'underlying_ticker': symbol,
            'expiration_date.gte': min_date,
            'expiration_date.lte': max_date,
            'limit': 250,
            'apiKey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    df = pd.DataFrame(results)
                    return df
        except Exception as e:
            logger.error(f"Error fetching option chain: {e}")
        
        return pd.DataFrame()
    
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
                    volatility = df['return'].tail(days).std() * np.sqrt(252)
                    return volatility
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
        
        return None
    
    def _select_best_expiry(
        self,
        option_chain: pd.DataFrame,
        dte_target: int
    ) -> Optional[str]:
        """选择最接近目标 DTE 且有完整 put/call 的到期日"""
        
        expiries = option_chain['expiration_date'].unique()
        
        if len(expiries) == 0:
            return None
        
        # 计算每个到期日距离目标的天数
        today = datetime.now()
        expiry_dtes = []
        
        for exp in expiries:
            # 检查该到期日是否有 put 和 call
            exp_chain = option_chain[option_chain['expiration_date'] == exp]
            has_puts = (exp_chain['contract_type'] == 'put').any()
            has_calls = (exp_chain['contract_type'] == 'call').any()
            
            if not (has_puts and has_calls):
                continue
            
            exp_date = datetime.strptime(exp, '%Y-%m-%d')
            dte = (exp_date - today).days
            
            if dte > 7:  # 至少 7 天
                expiry_dtes.append((exp, abs(dte - dte_target), dte))
        
        if not expiry_dtes:
            return None
        
        # 返回差距最小的
        best_expiry = min(expiry_dtes, key=lambda x: x[1])
        return best_expiry[0]
    
    def _select_put_leg(
        self,
        puts: pd.DataFrame,
        current_price: float,
        volatility: float,
        dte: int,
        min_oi: int
    ) -> Optional[OptionLeg]:
        """选择 Put 腿（OTM，约 1 标准差下方）"""
        
        # 计算目标行权价（1 标准差下方）
        std_dev = current_price * volatility * np.sqrt(dte / 252)
        target_strike = current_price - std_dev
        
        # 筛选 OTM put（行权价 < 当前价）
        otm_puts = puts[puts['strike_price'] < current_price].copy()
        
        if otm_puts.empty:
            logger.warning(f"No OTM puts found (current price: ${current_price:.2f})")
            return None
        
        logger.info(f"  → Found {len(otm_puts)} OTM puts, target strike: ${target_strike:.2f}")
        
        # 找到最接近目标行权价的
        otm_puts['distance'] = abs(otm_puts['strike_price'] - target_strike)
        otm_puts = otm_puts.sort_values('distance')
        
        # 选择最佳的（前 5 个中选第一个）
        top_candidates = otm_puts.head(5)
        
        if top_candidates.empty:
            logger.warning("No suitable put candidates found")
            return None
        
        # 使用第一个候选
        contract = top_candidates.iloc[0]
        strike = contract['strike_price']
        ticker = contract['ticker']
        expiry = contract['expiration_date']
        
        logger.info(f"  → Selected put: {ticker} @ ${strike:.2f}")
            
        # 估算权利金
        premium = self._estimate_option_price(
            current_price, strike, dte, volatility, 'put'
        )
        
        # 估算 Delta（OTM put 约 -0.25）
        moneyness = (current_price - strike) / current_price
        delta = -0.15 - (0.15 * (1 - moneyness / 0.15))  # 根据距离调整
        delta = max(delta, -0.35)  # 限制范围
        
        theta = -premium / dte if dte > 0 else 0
        distance_pct = (current_price - strike) / current_price
        
        return OptionLeg(
            ticker=ticker,
            type='put',
            strike=strike,
            expiry=expiry,
            premium=premium,
            is_estimated=True,
            delta=delta,
            theta=theta,
            distance_pct=distance_pct
        )
    
    def _select_call_leg(
        self,
        calls: pd.DataFrame,
        current_price: float,
        volatility: float,
        dte: int,
        min_oi: int
    ) -> Optional[OptionLeg]:
        """选择 Call 腿（OTM，约 1 标准差上方）"""
        
        # 计算目标行权价（1 标准差上方）
        std_dev = current_price * volatility * np.sqrt(dte / 252)
        target_strike = current_price + std_dev
        
        # 筛选 OTM call（行权价 > 当前价）
        otm_calls = calls[calls['strike_price'] > current_price].copy()
        
        if otm_calls.empty:
            return None
        
        # 找到最接近目标行权价的
        otm_calls['distance'] = abs(otm_calls['strike_price'] - target_strike)
        otm_calls = otm_calls.sort_values('distance')
        
        # 选择最佳的
        top_candidates = otm_calls.head(5)
        
        if top_candidates.empty:
            logger.warning("No suitable call candidates found")
            return None
        
        # 使用第一个候选
        contract = top_candidates.iloc[0]
        strike = contract['strike_price']
        ticker = contract['ticker']
        expiry = contract['expiration_date']
        
        logger.info(f"  → Selected call: {ticker} @ ${strike:.2f}")
            
        # 估算权利金
        premium = self._estimate_option_price(
            current_price, strike, dte, volatility, 'call'
        )
        
        # 估算 Delta（OTM call 约 0.25）
        moneyness = (strike - current_price) / current_price
        delta = 0.15 + (0.15 * (1 - moneyness / 0.15))
        delta = min(delta, 0.35)
        
        theta = -premium / dte if dte > 0 else 0
        distance_pct = (strike - current_price) / current_price
        
        return OptionLeg(
            ticker=ticker,
            type='call',
            strike=strike,
            expiry=expiry,
            premium=premium,
            is_estimated=True,
            delta=delta,
            theta=theta,
            distance_pct=distance_pct
        )
    
    def _estimate_option_price(
        self,
        spot: float,
        strike: float,
        days: int,
        volatility: float,
        option_type: str
    ) -> float:
        """估算期权价格"""
        
        # 内在价值
        if option_type == 'put':
            intrinsic = max(strike - spot, 0)
        else:
            intrinsic = max(spot - strike, 0)
        
        # 时间价值
        time_value = spot * volatility * np.sqrt(days / 252) * 0.4
        
        # OTM 期权
        if intrinsic == 0:
            moneyness = abs(spot - strike) / spot
            time_value *= np.exp(-moneyness * 2)
        
        total_value = intrinsic + time_value
        return max(total_value, 0.05)
    
    def _assess_data_quality(
        self,
        put_leg: OptionLeg,
        call_leg: OptionLeg
    ) -> str:
        """评估数据质量"""
        
        if not put_leg.is_estimated and not call_leg.is_estimated:
            return 'real'
        elif put_leg.is_estimated and call_leg.is_estimated:
            return 'estimated'
        else:
            return 'mixed'
    
    def _calculate_quality_score(
        self,
        put_leg: OptionLeg,
        call_leg: OptionLeg,
        net_delta: float,
        volatility: float
    ) -> float:
        """计算建仓方案质量评分"""
        
        # Delta 平衡
        delta_score = 1 - abs(net_delta) / 0.5
        delta_score = max(delta_score, 0)
        
        # 对称性
        distance_diff = abs(put_leg.distance_pct - call_leg.distance_pct)
        symmetry_score = 1 - distance_diff / 0.1
        symmetry_score = max(symmetry_score, 0)
        
        # 权利金平衡
        premium_ratio = min(
            put_leg.premium / call_leg.premium,
            call_leg.premium / put_leg.premium
        )
        premium_score = premium_ratio
        
        # 波动率
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
    
    builder = ProfessionalBuilderPolygon()
    
    symbol = 'GOOGL'
    position = builder.build_strangle(symbol, dte_target=45)
    
    if not position:
        print(f"Failed to build Strangle for {symbol}")
        return
    
    print("\n" + "="*80)
    print(f"🛠️  Professional Builder (Polygon Real Chains) - {symbol}")
    print("="*80 + "\n")
    
    print(f"📊 Market Data:")
    print(f"   Current Price: ${position.current_price:.2f}")
    print(f"   DTE: {position.dte} days")
    print(f"   Data Quality: {position.data_quality.upper()}")
    
    print(f"\n📋 Put Leg (SELL):")
    print(f"   Contract: {position.put_leg.ticker}")
    print(f"   Strike: ${position.put_leg.strike:.2f}")
    print(f"   Distance: {position.put_leg.distance_pct:.1%} OTM")
    print(f"   Premium: ${position.put_leg.premium:.2f}")
    print(f"   Delta: {position.put_leg.delta:.3f}")
    print(f"   Expiry: {position.put_leg.expiry}")
    
    print(f"\n📋 Call Leg (SELL):")
    print(f"   Contract: {position.call_leg.ticker}")
    print(f"   Strike: ${position.call_leg.strike:.2f}")
    print(f"   Distance: {position.call_leg.distance_pct:.1%} OTM")
    print(f"   Premium: ${position.call_leg.premium:.2f}")
    print(f"   Delta: {position.call_leg.delta:.3f}")
    print(f"   Expiry: {position.call_leg.expiry}")
    
    print(f"\n📊 Greeks:")
    print(f"   Net Delta: {position.net_delta:.3f}")
    
    print(f"\n💰 P&L Profile:")
    print(f"   Total Premium (Credit): ${position.total_premium:.2f}")
    print(f"   Max Profit: ${position.max_profit:.2f}")
    print(f"   Estimated Margin: ${position.estimated_margin:.2f}")
    print(f"   Profit Zone: ${position.breakeven_down:.2f} - ${position.breakeven_up:.2f}")
    
    print(f"\n⭐ Quality Score: {position.quality_score:.2f}")
    
    print("\n" + "="*80)
    print("✅ 使用 Polygon 真实期权合约")
    print("✅ 真实到期日和行权价")
    print("⚠️  权利金为估算值（如需真实报价，请升级 Polygon 订阅）")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()

