#!/usr/bin/env python3
"""
Professional Builder - 专业建仓模块

功能：
1. 自动选择最优 Strangle 腿
2. Greeks 平衡（Delta 中性）
3. 流动性验证（Bid-Ask Spread, Open Interest）
4. 成本优化
5. 保证金计算

策略核心：
- Put/Call Strike 基于标准差选择
- Net Delta ≈ 0 (Delta Neutral)
- Put/Call 权利金比例 ≈ 1:1
- Open Interest > 100
- Bid-Ask Spread < 5%
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from strategy_system.data_fetcher import PolygonDataFetcher
except ImportError:
    PolygonDataFetcher = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class OptionLeg:
    """期权腿数据结构"""
    type: str  # 'put' or 'call'
    strike: float
    expiry: str
    bid: float
    ask: float
    mid_price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    implied_vol: float
    open_interest: int
    volume: int
    bid_ask_spread_pct: float


@dataclass
class StranglePosition:
    """Strangle 头寸"""
    symbol: str
    put_leg: OptionLeg
    call_leg: OptionLeg
    net_delta: float
    net_gamma: float
    net_theta: float
    net_vega: float
    total_premium: float  # 收入
    margin_required: float
    max_profit: float
    breakeven_down: float
    breakeven_up: float
    profit_zone: Tuple[float, float]
    quality_score: float  # 0-1


class ProfessionalBuilder:
    """
    专业建仓引擎
    
    工作流：
    1. 获取期权链
    2. 计算标的波动率和标准差
    3. 选择 Put Strike（1.0~1.2σ 下方）
    4. 选择 Call Strike（1.0~1.2σ 上方）
    5. 验证 Greeks 平衡
    6. 验证流动性
    7. 输出完整建仓方案
    """
    
    def __init__(self, data_fetcher: Optional[PolygonDataFetcher] = None):
        self.data_fetcher = data_fetcher or (
            PolygonDataFetcher() if PolygonDataFetcher else None
        )
    
    def build_strangle(
        self,
        symbol: str,
        dte_target: int = 45,  # 目标到期天数
        delta_range: Tuple[float, float] = (-0.1, 0.1),  # Net Delta 范围
        min_open_interest: int = 100,
        max_spread_pct: float = 0.05  # 最大 Bid-Ask Spread 5%
    ) -> Optional[StranglePosition]:
        """
        构建 Strangle 策略
        
        Args:
            symbol: 标的代码
            dte_target: 目标到期天数（默认 45 天）
            delta_range: Net Delta 允许范围
            min_open_interest: 最小持仓量
            max_spread_pct: 最大 Bid-Ask Spread 百分比
        
        Returns:
            StranglePosition 或 None（如果没有合适腿）
        """
        logger.info(f"Building Strangle for {symbol}, DTE target: {dte_target}...")
        
        # 1. 获取当前价格
        current_price = self._get_current_price(symbol)
        if not current_price:
            logger.error(f"Failed to get price for {symbol}")
            return None
        
        # 2. 计算历史波动率和标准差
        std_dev = self._calculate_std_dev(symbol)
        if not std_dev:
            logger.warning(f"Using default std_dev for {symbol}")
            std_dev = current_price * 0.15  # 默认 15% 年化波动率
        
        # 3. 获取期权链
        option_chain = self._get_option_chain(symbol, dte_target)
        if not option_chain:
            logger.error(f"Failed to get option chain for {symbol}")
            return None
        
        # 4. 选择 Put Leg
        put_candidates = [
            opt for opt in option_chain 
            if opt['right'] == 'PUT' 
            and opt['strike'] < current_price
            and opt['open_interest'] >= min_open_interest
        ]
        
        put_leg = self._select_best_put(
            put_candidates, current_price, std_dev, max_spread_pct
        )
        
        if not put_leg:
            logger.error("No suitable Put leg found")
            return None
        
        # 5. 选择 Call Leg
        call_candidates = [
            opt for opt in option_chain 
            if opt['right'] == 'CALL' 
            and opt['strike'] > current_price
            and opt['open_interest'] >= min_open_interest
        ]
        
        call_leg = self._select_best_call(
            call_candidates, current_price, std_dev, max_spread_pct, put_leg
        )
        
        if not call_leg:
            logger.error("No suitable Call leg found")
            return None
        
        # 6. 验证 Net Delta
        net_delta = put_leg.delta + call_leg.delta
        if not (delta_range[0] <= net_delta <= delta_range[1]):
            logger.warning(f"Net Delta {net_delta:.3f} outside range {delta_range}")
            # 继续，但标记质量分数较低
        
        # 7. 计算 Greeks 和盈亏
        net_gamma = put_leg.gamma + call_leg.gamma
        net_theta = put_leg.theta + call_leg.theta
        net_vega = put_leg.vega + call_leg.vega
        
        total_premium = (put_leg.mid_price + call_leg.mid_price) * 100  # per contract
        
        # 8. 计算盈亏点
        breakeven_down = put_leg.strike - (put_leg.mid_price + call_leg.mid_price)
        breakeven_up = call_leg.strike + (put_leg.mid_price + call_leg.mid_price)
        
        # 9. 计算保证金（简化）
        margin_required = self._estimate_margin(
            current_price, put_leg.strike, call_leg.strike
        )
        
        # 10. 质量评分
        quality_score = self._calculate_quality_score(
            put_leg, call_leg, net_delta, delta_range
        )
        
        return StranglePosition(
            symbol=symbol,
            put_leg=put_leg,
            call_leg=call_leg,
            net_delta=net_delta,
            net_gamma=net_gamma,
            net_theta=net_theta,
            net_vega=net_vega,
            total_premium=total_premium,
            margin_required=margin_required,
            max_profit=total_premium,
            breakeven_down=breakeven_down,
            breakeven_up=breakeven_up,
            profit_zone=(breakeven_down, breakeven_up),
            quality_score=quality_score
        )
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        if self.data_fetcher:
            try:
                quote = self.data_fetcher.get_stock_quote(symbol)
                return quote.get('price')
            except:
                pass
        
        # Fallback: yfinance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            return ticker.info.get('currentPrice') or ticker.info.get('regularMarketPrice')
        except:
            return None
    
    def _calculate_std_dev(self, symbol: str, window: int = 30) -> Optional[float]:
        """
        计算标的的标准差（用于选择行权价）
        
        使用 30 日历史波动率
        """
        if self.data_fetcher:
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)
                
                data = self.data_fetcher.get_historical_data(
                    symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if data is not None and len(data) >= window:
                    returns = data['close'].pct_change().dropna()
                    daily_std = returns.tail(window).std()
                    
                    # 年化标准差
                    annual_std = daily_std * np.sqrt(252)
                    
                    # 转为价格标准差（假设持有 45 天）
                    current_price = data['close'].iloc[-1]
                    std_dev = current_price * annual_std * np.sqrt(45/252)
                    
                    return std_dev
            except:
                pass
        
        # Fallback: yfinance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='2mo')
            
            if len(hist) >= window:
                returns = hist['Close'].pct_change().dropna()
                daily_std = returns.tail(window).std()
                annual_std = daily_std * np.sqrt(252)
                
                current_price = hist['Close'].iloc[-1]
                std_dev = current_price * annual_std * np.sqrt(45/252)
                
                return std_dev
        except:
            pass
        
        return None
    
    def _get_option_chain(self, symbol: str, dte_target: int) -> Optional[List[Dict]]:
        """
        获取期权链
        
        尝试选择最接近 dte_target 的到期日
        """
        if self.data_fetcher:
            try:
                # Polygon 方式（需要付费计划）
                target_date = (datetime.now() + timedelta(days=dte_target)).strftime('%Y-%m-%d')
                contracts = self.data_fetcher.get_option_contracts(symbol, expiration_date=target_date)
                
                if contracts:
                    return contracts
            except:
                pass
        
        # Fallback: yfinance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            
            if not expirations:
                return None
            
            # 找最接近 dte_target 的到期日
            target_date = datetime.now() + timedelta(days=dte_target)
            closest_exp = min(
                expirations,
                key=lambda x: abs((datetime.strptime(x, '%Y-%m-%d') - target_date).days)
            )
            
            # 获取该到期日的期权链
            chain = ticker.option_chain(closest_exp)
            
            # 转为标准格式
            options = []
            
            for _, row in chain.puts.iterrows():
                options.append({
                    'symbol': symbol,
                    'strike': row['strike'],
                    'expiry': closest_exp,
                    'right': 'PUT',
                    'bid': row['bid'],
                    'ask': row['ask'],
                    'last': row['lastPrice'],
                    'volume': row['volume'],
                    'open_interest': row['openInterest'],
                    'implied_volatility': row.get('impliedVolatility', 0),
                    'delta': row.get('delta', 0),
                    'gamma': row.get('gamma', 0),
                    'theta': row.get('theta', 0),
                    'vega': row.get('vega', 0)
                })
            
            for _, row in chain.calls.iterrows():
                options.append({
                    'symbol': symbol,
                    'strike': row['strike'],
                    'expiry': closest_exp,
                    'right': 'CALL',
                    'bid': row['bid'],
                    'ask': row['ask'],
                    'last': row['lastPrice'],
                    'volume': row['volume'],
                    'open_interest': row['openInterest'],
                    'implied_volatility': row.get('impliedVolatility', 0),
                    'delta': row.get('delta', 0),
                    'gamma': row.get('gamma', 0),
                    'theta': row.get('theta', 0),
                    'vega': row.get('vega', 0)
                })
            
            return options
            
        except Exception as e:
            logger.error(f"Failed to get option chain: {e}")
            return None
    
    def _select_best_put(
        self,
        candidates: List[Dict],
        current_price: float,
        std_dev: float,
        max_spread_pct: float
    ) -> Optional[OptionLeg]:
        """
        选择最优 Put Leg
        
        目标：
        1. Strike ≈ Current Price - 1.0~1.2σ
        2. Bid-Ask Spread < 5%
        3. Delta ≈ -0.30 到 -0.20
        """
        target_strike = current_price - 1.1 * std_dev
        
        # 过滤和评分
        scored_candidates = []
        for opt in candidates:
            # 检查流动性
            if opt['bid'] == 0 or opt['ask'] == 0:
                continue
            
            spread_pct = (opt['ask'] - opt['bid']) / opt['ask']
            if spread_pct > max_spread_pct:
                continue
            
            # 计算得分
            strike_distance = abs(opt['strike'] - target_strike) / target_strike
            delta_score = 1 - abs(opt.get('delta', -0.25) + 0.25) / 0.25  # 目标 -0.25
            spread_score = 1 - spread_pct / max_spread_pct
            
            total_score = (
                0.5 * (1 - strike_distance) +
                0.3 * max(delta_score, 0) +
                0.2 * spread_score
            )
            
            scored_candidates.append((total_score, opt))
        
        if not scored_candidates:
            return None
        
        # 选择最高分
        best_opt = max(scored_candidates, key=lambda x: x[0])[1]
        
        return self._create_option_leg(best_opt)
    
    def _select_best_call(
        self,
        candidates: List[Dict],
        current_price: float,
        std_dev: float,
        max_spread_pct: float,
        put_leg: OptionLeg
    ) -> Optional[OptionLeg]:
        """
        选择最优 Call Leg
        
        目标：
        1. Strike ≈ Current Price + 1.0~1.2σ
        2. 权利金与 Put Leg 接近（1:1 比例）
        3. 使 Net Delta ≈ 0
        """
        target_strike = current_price + 1.1 * std_dev
        
        scored_candidates = []
        for opt in candidates:
            if opt['bid'] == 0 or opt['ask'] == 0:
                continue
            
            spread_pct = (opt['ask'] - opt['bid']) / opt['ask']
            if spread_pct > max_spread_pct:
                continue
            
            # 计算得分
            strike_distance = abs(opt['strike'] - target_strike) / target_strike
            
            # Delta 平衡得分（希望 Net Delta ≈ 0）
            net_delta = put_leg.delta + opt.get('delta', 0.25)
            delta_balance_score = 1 - abs(net_delta) / 0.5
            
            # 权利金平衡
            call_premium = (opt['bid'] + opt['ask']) / 2
            premium_ratio = call_premium / put_leg.mid_price if put_leg.mid_price > 0 else 1
            premium_score = 1 - abs(premium_ratio - 1.0) / 1.0
            
            spread_score = 1 - spread_pct / max_spread_pct
            
            total_score = (
                0.3 * (1 - strike_distance) +
                0.4 * max(delta_balance_score, 0) +
                0.2 * max(premium_score, 0) +
                0.1 * spread_score
            )
            
            scored_candidates.append((total_score, opt))
        
        if not scored_candidates:
            return None
        
        best_opt = max(scored_candidates, key=lambda x: x[0])[1]
        
        return self._create_option_leg(best_opt)
    
    def _create_option_leg(self, opt: Dict) -> OptionLeg:
        """从期权数据创建 OptionLeg 对象"""
        mid_price = (opt['bid'] + opt['ask']) / 2
        spread_pct = (opt['ask'] - opt['bid']) / opt['ask'] if opt['ask'] > 0 else 0
        
        return OptionLeg(
            type='put' if opt['right'] == 'PUT' else 'call',
            strike=opt['strike'],
            expiry=opt['expiry'],
            bid=opt['bid'],
            ask=opt['ask'],
            mid_price=mid_price,
            delta=opt.get('delta', 0),
            gamma=opt.get('gamma', 0),
            theta=opt.get('theta', 0),
            vega=opt.get('vega', 0),
            implied_vol=opt.get('implied_volatility', 0),
            open_interest=opt.get('open_interest', 0),
            volume=opt.get('volume', 0),
            bid_ask_spread_pct=spread_pct
        )
    
    def _estimate_margin(
        self,
        current_price: float,
        put_strike: float,
        call_strike: float
    ) -> float:
        """
        估算 Strangle 保证金需求
        
        简化计算：
        - Short Strangle 保证金 ≈ 较大腿的保证金
        - 保证金 ≈ Strike × 0.2 (20% 裸卖保证金)
        """
        put_margin = put_strike * 100 * 0.2
        call_margin = (call_strike - current_price) * 100 * 0.2
        
        # 取较大值，加上对方腿的权利金
        margin = max(put_margin, call_margin)
        
        return margin
    
    def _calculate_quality_score(
        self,
        put_leg: OptionLeg,
        call_leg: OptionLeg,
        net_delta: float,
        delta_range: Tuple[float, float]
    ) -> float:
        """
        计算建仓方案质量评分
        
        考虑：
        1. Net Delta 接近 0
        2. 流动性（Spread, OI）
        3. 权利金平衡
        """
        # Delta 得分
        if delta_range[0] <= net_delta <= delta_range[1]:
            delta_score = 1.0
        else:
            delta_score = max(0, 1 - abs(net_delta) / 0.5)
        
        # 流动性得分
        put_liquidity = 1 - put_leg.bid_ask_spread_pct / 0.05
        call_liquidity = 1 - call_leg.bid_ask_spread_pct / 0.05
        liquidity_score = (put_liquidity + call_liquidity) / 2
        
        # 权利金平衡得分
        premium_ratio = call_leg.mid_price / put_leg.mid_price if put_leg.mid_price > 0 else 1
        balance_score = 1 - abs(premium_ratio - 1.0) / 1.0
        
        # 综合得分
        quality = (
            0.4 * delta_score +
            0.3 * liquidity_score +
            0.3 * max(balance_score, 0)
        )
        
        return np.clip(quality, 0, 1)


# =============================================================================
# 使用示例
# =============================================================================

def main():
    """示例：构建 Strangle 策略"""
    
    builder = ProfessionalBuilder()
    
    symbol = 'NVDA'
    position = builder.build_strangle(symbol, dte_target=45)
    
    if not position:
        print(f"Failed to build Strangle for {symbol}")
        return
    
    print("\n" + "="*80)
    print(f"🛠️  Professional Builder - Strangle Strategy for {symbol}")
    print("="*80 + "\n")
    
    print(f"Put Leg:")
    print(f"  Strike: ${position.put_leg.strike:.2f}")
    print(f"  Premium: ${position.put_leg.mid_price:.2f}")
    print(f"  Delta: {position.put_leg.delta:.3f}")
    print(f"  Open Interest: {position.put_leg.open_interest}")
    
    print(f"\nCall Leg:")
    print(f"  Strike: ${position.call_leg.strike:.2f}")
    print(f"  Premium: ${position.call_leg.mid_price:.2f}")
    print(f"  Delta: {position.call_leg.delta:.3f}")
    print(f"  Open Interest: {position.call_leg.open_interest}")
    
    print(f"\nGreeks:")
    print(f"  Net Delta: {position.net_delta:.3f}")
    print(f"  Net Theta: {position.net_theta:.3f}")
    print(f"  Net Vega: {position.net_vega:.2f}")
    
    print(f"\nP&L Profile:")
    print(f"  Total Premium (收入): ${position.total_premium:.2f}")
    print(f"  Max Profit: ${position.max_profit:.2f}")
    print(f"  Margin Required: ${position.margin_required:.2f}")
    print(f"  Profit Zone: ${position.breakeven_down:.2f} - ${position.breakeven_up:.2f}")
    
    print(f"\nQuality Score: {position.quality_score:.2f}")
    
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()




