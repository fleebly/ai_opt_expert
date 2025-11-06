#!/usr/bin/env python3
"""
AI Signal Generator - 全市场广度扫描

功能：
1. 扫描多标的，识别波动率压缩机会
2. 结合财报事件、新闻情绪
3. 过滤流动性差的标的
4. 输出候选信号池

策略核心：
- 布林带宽度百分位 < 30% → 波动率压缩
- 距离财报 7~21 天 → 事件驱动
- 期权流动性充足 → Bid-Ask Spread < 5%
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass

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
class Signal:
    """信号数据结构"""
    symbol: str
    timestamp: str
    bb_percentile: float  # 布林带宽度百分位 (0-1)
    dte_to_event: Optional[int]  # 距离下次事件天数
    news_sentiment: float  # 新闻情感 (-1 to 1)
    liquidity_score: float  # 流动性得分 (0-1)
    iv_rank: float  # IV Rank (0-100)
    signal_strength: float  # 综合信号强度 (0-1)
    status: str  # 'strong', 'moderate', 'weak'


class AISignalGenerator:
    """
    AI 信号生成器
    
    工作流：
    1. 输入 watchlist（如 ['NVDA', 'TSLA', 'AAPL']）
    2. 对每个标的计算特征
    3. 输出候选信号 DataFrame
    """
    
    # 美股热门标的池（可自定义）
    DEFAULT_WATCHLIST = [
        'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
        'AMD', 'INTC', 'NFLX', 'DIS', 'BA', 'SPY', 'QQQ'
    ]
    
    def __init__(self, data_fetcher: Optional[PolygonDataFetcher] = None):
        """
        Args:
            data_fetcher: Polygon 数据获取器，可选
        """
        self.data_fetcher = data_fetcher or (
            PolygonDataFetcher() if PolygonDataFetcher else None
        )
    
    def scan_market(
        self,
        watchlist: Optional[List[str]] = None,
        lookback_days: int = 60
    ) -> pd.DataFrame:
        """
        扫描市场，生成候选信号
        
        Args:
            watchlist: 标的列表，默认用热门股
            lookback_days: 回溯天数
        
        Returns:
            DataFrame with columns: symbol, bb_percentile, dte_to_event, 
                                    news_sentiment, signal_strength, status
        """
        watchlist = watchlist or self.DEFAULT_WATCHLIST
        logger.info(f"Scanning {len(watchlist)} symbols...")
        
        signals = []
        for symbol in watchlist:
            try:
                signal = self._analyze_symbol(symbol, lookback_days)
                if signal and signal.signal_strength > 0.3:  # 过滤弱信号
                    signals.append(signal)
            except Exception as e:
                logger.warning(f"Failed to analyze {symbol}: {e}")
                continue
        
        # 转为 DataFrame
        if not signals:
            return pd.DataFrame()
        
        df = pd.DataFrame([vars(s) for s in signals])
        df = df.sort_values('signal_strength', ascending=False)
        
        logger.info(f"Found {len(df)} candidate signals")
        return df
    
    def _analyze_symbol(self, symbol: str, lookback_days: int) -> Optional[Signal]:
        """
        分析单个标的
        
        计算：
        1. 布林带宽度百分位
        2. 距离财报天数
        3. 新闻情感（mock）
        4. 流动性得分
        5. IV Rank
        """
        # 获取历史数据
        data = self._fetch_historical_data(symbol, lookback_days)
        if data is None or len(data) < 20:
            return None
        
        # 1. 计算布林带宽度百分位
        bb_percentile = self._calculate_bb_percentile(data)
        
        # 2. 财报事件（mock，实际可用 Polygon Calendar API）
        dte_to_event = self._get_days_to_earnings(symbol)
        
        # 3. 新闻情感（mock，实际可用 NewsAPI + BERT）
        news_sentiment = self._get_news_sentiment(symbol)
        
        # 4. 流动性得分
        liquidity_score = self._calculate_liquidity(data)
        
        # 5. IV Rank（需要期权数据，这里简化用价格波动率）
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
    
    def _fetch_historical_data(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """获取历史 OHLCV 数据"""
        if self.data_fetcher:
            try:
                # 使用 Polygon
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                data = self.data_fetcher.get_historical_data(
                    symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                return data
            except:
                pass
        
        # Fallback: yfinance
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=f"{days}d")
            if data.empty:
                return None
            data = data.reset_index()
            data.columns = [c.lower() for c in data.columns]
            return data
        except:
            return None
    
    def _calculate_bb_percentile(self, data: pd.DataFrame, window: int = 20) -> float:
        """
        计算布林带宽度百分位
        
        BB Width = (Upper Band - Lower Band) / Middle Band
        Percentile = 当前宽度在过去 N 天的分位数
        
        低百分位 → 波动率压缩 → 即将突破
        """
        close = data['close'].values
        
        # 计算布林带
        sma = pd.Series(close).rolling(window).mean()
        std = pd.Series(close).rolling(window).std()
        
        upper_band = sma + 2 * std
        lower_band = sma - 2 * std
        
        bb_width = (upper_band - lower_band) / sma
        bb_width = bb_width.dropna()
        
        if len(bb_width) < 2:
            return 0.5
        
        # 当前宽度的百分位
        current_width = bb_width.iloc[-1]
        percentile = (bb_width < current_width).sum() / len(bb_width)
        
        return percentile
    
    def _get_days_to_earnings(self, symbol: str) -> Optional[int]:
        """
        获取距离下次财报的天数
        
        实际实现可用：
        - Polygon Calendar API
        - Earnings Whisper API
        - 爬虫抓取 earnings.com
        
        这里 mock 返回
        """
        # Mock: 随机 7~60 天
        mock_dte = np.random.randint(7, 60)
        
        # 只有在 7~21 天内才返回（事件驱动窗口）
        if 7 <= mock_dte <= 21:
            return mock_dte
        return None
    
    def _get_news_sentiment(self, symbol: str) -> float:
        """
        获取新闻情感得分 (-1 to 1)
        
        实际实现可用：
        - NewsAPI + FinBERT
        - Polygon News API
        - Twitter/Reddit 爬虫
        
        这里 mock 返回
        """
        # Mock: 随机 -0.5 ~ 0.5
        return np.random.uniform(-0.5, 0.5)
    
    def _calculate_liquidity(self, data: pd.DataFrame) -> float:
        """
        流动性得分 (0-1)
        
        基于：
        - 日均成交量
        - 最近 5 日波动性
        
        高流动性 → 适合期权交易
        """
        if 'volume' not in data.columns or len(data) < 5:
            return 0.5
        
        # 平均成交量
        avg_volume = data['volume'].tail(20).mean()
        
        # 归一化（百万为单位）
        volume_score = min(avg_volume / 10_000_000, 1.0)
        
        # 波动性（低波动 = 高流动性）
        returns = data['close'].pct_change().tail(20)
        volatility = returns.std()
        vol_score = 1 - min(volatility / 0.05, 1.0)
        
        return 0.6 * volume_score + 0.4 * vol_score
    
    def _calculate_iv_rank(self, data: pd.DataFrame, window: int = 252) -> float:
        """
        IV Rank 估算
        
        实际应用需要期权隐含波动率，这里用历史波动率替代
        
        IV Rank = (当前 IV - 52周最低) / (52周最高 - 52周最低) * 100
        """
        returns = data['close'].pct_change().dropna()
        
        if len(returns) < 20:
            return 50.0
        
        # 滚动 20 日波动率
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
        """
        综合信号强度评分
        
        权重分配：
        - BB 百分位: 30% (越低越好)
        - 事件驱动: 25% (有财报加分)
        - 流动性: 20%
        - IV Rank: 15% (中等 IV 最佳)
        - 新闻情感: 10%
        """
        # 1. BB 得分（低百分位高分）
        bb_score = 1 - bb_percentile
        
        # 2. 事件得分
        if dte_to_event:
            event_score = 1.0 if 7 <= dte_to_event <= 14 else 0.7
        else:
            event_score = 0.3
        
        # 3. 流动性得分
        liq_score = liquidity_score
        
        # 4. IV Rank 得分（30-70 最佳）
        if 30 <= iv_rank <= 70:
            iv_score = 1.0
        elif iv_rank < 30:
            iv_score = iv_rank / 30
        else:
            iv_score = (100 - iv_rank) / 30
        
        # 5. 新闻得分（中性最佳，避免极端）
        news_score = 1 - abs(news_sentiment)
        
        # 加权求和
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
    """示例：扫描市场并输出候选信号"""
    
    generator = AISignalGenerator()
    
    # 扫描热门股
    signals_df = generator.scan_market(
        watchlist=['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD'],
        lookback_days=60
    )
    
    if signals_df.empty:
        print("No signals found.")
        return
    
    print("\n" + "="*80)
    print("🔍 AI Signal Generator - Market Scan Results")
    print("="*80 + "\n")
    
    # 显示前 10 个信号
    print(signals_df[['symbol', 'bb_percentile', 'dte_to_event', 
                      'signal_strength', 'status']].head(10).to_string(index=False))
    
    print("\n" + "="*80)
    print(f"✅ Found {len(signals_df)} candidates")
    print(f"   - Strong: {(signals_df['status'] == 'strong').sum()}")
    print(f"   - Moderate: {(signals_df['status'] == 'moderate').sum()}")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()




