#!/usr/bin/env python3
"""
AI Signal Generator - 纯 Polygon 版本

完全使用 Polygon API，不依赖 yfinance
适用于中国大陆用户
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass
import requests
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """信号数据结构"""
    symbol: str
    timestamp: str
    bb_percentile: float
    dte_to_event: Optional[int]
    news_sentiment: float
    liquidity_score: float
    iv_rank: float
    signal_strength: float
    status: str


class AISignalGeneratorPolygon:
    """
    AI 信号生成器 - 纯 Polygon 版本
    
    完全使用 Polygon API 获取数据
    """
    
    DEFAULT_WATCHLIST = [
        'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
        'AMD', 'INTC', 'NFLX', 'DIS', 'BA', 'SPY', 'QQQ'
    ]
    
    def __init__(self):
        """初始化"""
        self.api_key = os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY not set in environment")
        
        self.base_url = "https://api.polygon.io"
        logger.info("AISignalGeneratorPolygon initialized with Polygon API")
    
    def scan_market(
        self,
        watchlist: Optional[List[str]] = None,
        lookback_days: int = 60
    ) -> pd.DataFrame:
        """
        扫描市场，生成候选信号
        
        Args:
            watchlist: 标的列表
            lookback_days: 回溯天数
        
        Returns:
            DataFrame with signals
        """
        watchlist = watchlist or self.DEFAULT_WATCHLIST
        logger.info(f"Scanning {len(watchlist)} symbols with Polygon API...")
        
        signals = []
        for i, symbol in enumerate(watchlist, 1):
            logger.info(f"[{i}/{len(watchlist)}] Analyzing {symbol}...")
            
            try:
                signal = self._analyze_symbol(symbol, lookback_days)
                if signal and signal.signal_strength > 0.3:
                    signals.append(signal)
                    logger.info(f"  ✅ {symbol}: signal_strength={signal.signal_strength:.2f}")
                else:
                    logger.info(f"  ⚠️  {symbol}: signal too weak or data insufficient")
            except Exception as e:
                logger.warning(f"  ❌ {symbol}: {e}")
                continue
        
        if not signals:
            logger.warning("No signals found")
            return pd.DataFrame()
        
        df = pd.DataFrame([vars(s) for s in signals])
        df = df.sort_values('signal_strength', ascending=False)
        
        logger.info(f"✅ Found {len(df)} candidates")
        return df
    
    def _analyze_symbol(self, symbol: str, lookback_days: int) -> Optional[Signal]:
        """分析单个标的"""
        
        # 1. 获取历史数据 (Polygon)
        data = self._fetch_polygon_data(symbol, lookback_days)
        if data is None or len(data) < 20:
            return None
        
        # 2. 计算布林带宽度百分位
        bb_percentile = self._calculate_bb_percentile(data)
        
        # 3. 财报事件（mock）
        dte_to_event = self._get_days_to_earnings(symbol)
        
        # 4. 新闻情感（mock）
        news_sentiment = np.random.uniform(-0.5, 0.5)
        
        # 5. 流动性得分
        liquidity_score = self._calculate_liquidity(data)
        
        # 6. IV Rank
        iv_rank = self._calculate_iv_rank(data)
        
        # 综合评分
        signal_strength = self._calculate_signal_strength(
            bb_percentile, dte_to_event, news_sentiment, liquidity_score, iv_rank
        )
        
        # 状态分类
        if signal_strength >= 0.7:
            status = 'strong'
        elif signal_strength >= 0.5:
            status = 'moderate'
        else:
            status = 'weak'
        
        return Signal(
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
            bb_percentile=bb_percentile,
            dte_to_event=dte_to_event,
            news_sentiment=news_sentiment,
            liquidity_score=liquidity_score,
            iv_rank=iv_rank,
            signal_strength=signal_strength,
            status=status
        )
    
    def _fetch_polygon_data(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """从 Polygon 获取历史数据"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 5000,
            'apiKey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('resultsCount', 0) > 0:
                    results = data['results']
                    
                    # 转换为 DataFrame
                    df = pd.DataFrame(results)
                    df = df.rename(columns={
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume',
                        't': 'timestamp'
                    })
                    
                    # 转换时间戳
                    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
                    return df[['date', 'open', 'high', 'low', 'close', 'volume']]
                
            logger.warning(f"Polygon API returned status {response.status_code} for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Polygon API error for {symbol}: {e}")
            return None
    
    def _calculate_bb_percentile(self, data: pd.DataFrame, window: int = 20) -> float:
        """计算布林带宽度百分位"""
        close = data['close'].values
        
        sma = pd.Series(close).rolling(window).mean()
        std = pd.Series(close).rolling(window).std()
        
        upper_band = sma + 2 * std
        lower_band = sma - 2 * std
        
        bb_width = (upper_band - lower_band) / sma
        bb_width = bb_width.dropna()
        
        if len(bb_width) < 2:
            return 0.5
        
        current_width = bb_width.iloc[-1]
        percentile = (bb_width < current_width).sum() / len(bb_width)
        
        return percentile
    
    def _get_days_to_earnings(self, symbol: str) -> Optional[int]:
        """获取距离下次财报的天数（mock）"""
        mock_dte = np.random.randint(7, 60)
        if 7 <= mock_dte <= 21:
            return mock_dte
        return None
    
    def _calculate_liquidity(self, data: pd.DataFrame) -> float:
        """流动性得分"""
        if 'volume' not in data.columns or len(data) < 5:
            return 0.5
        
        avg_volume = data['volume'].tail(20).mean()
        volume_score = min(avg_volume / 10_000_000, 1.0)
        
        returns = data['close'].pct_change().tail(20)
        volatility = returns.std()
        vol_score = 1 - min(volatility / 0.05, 1.0)
        
        return 0.6 * volume_score + 0.4 * vol_score
    
    def _calculate_iv_rank(self, data: pd.DataFrame) -> float:
        """IV Rank 估算"""
        returns = data['close'].pct_change().dropna()
        
        if len(returns) < 20:
            return 50.0
        
        rolling_vol = returns.rolling(20).std() * np.sqrt(252)
        
        if len(rolling_vol) < 2:
            return 50.0
        
        current_vol = rolling_vol.iloc[-1]
        min_vol = rolling_vol.min()
        max_vol = rolling_vol.max()
        
        if max_vol == min_vol:
            return 50.0
        
        iv_rank = ((current_vol - min_vol) / (max_vol - min_vol)) * 100
        
        return iv_rank
    
    def _calculate_signal_strength(
        self,
        bb_percentile: float,
        dte_to_event: Optional[int],
        news_sentiment: float,
        liquidity_score: float,
        iv_rank: float
    ) -> float:
        """综合信号强度评分"""
        
        bb_score = 1 - bb_percentile
        
        if dte_to_event:
            event_score = 1.0 if 7 <= dte_to_event <= 14 else 0.7
        else:
            event_score = 0.3
        
        liq_score = liquidity_score
        
        if 30 <= iv_rank <= 70:
            iv_score = 1.0
        elif iv_rank < 30:
            iv_score = iv_rank / 30
        else:
            iv_score = (100 - iv_rank) / 30
        
        news_score = 1 - abs(news_sentiment)
        
        signal = (
            0.30 * bb_score +
            0.25 * event_score +
            0.20 * liq_score +
            0.15 * iv_score +
            0.10 * news_score
        )
        
        return np.clip(signal, 0, 1)


# =============================================================================
# 使用示例
# =============================================================================

def main():
    """测试"""
    
    generator = AISignalGeneratorPolygon()
    
    watchlist = ['NVDA', 'TSLA', 'AAPL']
    
    print("\n" + "="*80)
    print("🔍 AI Signal Generator (Pure Polygon Version)")
    print("="*80 + "\n")
    
    signals_df = generator.scan_market(watchlist, lookback_days=60)
    
    if not signals_df.empty:
        print("\n✅ Found signals:\n")
        print(signals_df[['symbol', 'bb_percentile', 'signal_strength', 'status']].to_string(index=False))
    else:
        print("\n❌ No signals found")
    
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()




