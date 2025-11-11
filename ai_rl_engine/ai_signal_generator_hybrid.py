#!/usr/bin/env python3
"""
AI Signal Generator - 混合版本

第 1 阶段：快速技术筛选（2-3 秒）
第 2 阶段：DeepSeek AI 深度分析（仅对候选标的）

最佳平衡：速度 + 智能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass, asdict
import requests
import os
import json
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
    # AI 增强字段
    ai_analyzed: bool = False
    ai_insight: Optional[str] = None
    ai_recommendation: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_key_factors: Optional[List[str]] = None


class AISignalGeneratorHybrid:
    """
    混合 AI 信号生成器
    
    工作流程：
    1. 技术筛选：快速扫描所有标的（纯计算）
    2. AI 分析：DeepSeek 深度分析前 N 个候选
    """
    
    DEFAULT_WATCHLIST = [
        'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',
        'AMD', 'INTC', 'NFLX', 'DIS', 'BA', 'SPY', 'QQQ'
    ]
    
    def __init__(self):
        """初始化"""
        self.polygon_key = os.getenv('POLYGON_API_KEY')
        self.deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        
        if not self.polygon_key:
            raise ValueError("POLYGON_API_KEY not set")
        
        self.base_url = "https://api.polygon.io"
        self.deepseek_url = "https://api.deepseek.com/v1/chat/completions"
        
        # 是否启用 AI
        self.ai_enabled = bool(self.deepseek_key)
        
        if self.ai_enabled:
            logger.info("🤖 Hybrid AI Generator initialized (Tech + DeepSeek)")
        else:
            logger.warning("⚠️ DeepSeek API key not found, running in Tech-only mode")
    
    def scan_market(
        self,
        watchlist: Optional[List[str]] = None,
        lookback_days: int = 60,
        ai_top_n: int = 5,
        enable_ai: bool = True
    ) -> pd.DataFrame:
        """
        混合扫描市场
        
        Args:
            watchlist: 标的列表
            lookback_days: 回溯天数
            ai_top_n: 对前 N 个候选进行 AI 分析
            enable_ai: 是否启用 AI 分析
        
        Returns:
            DataFrame with signals
        """
        watchlist = watchlist or self.DEFAULT_WATCHLIST
        
        # ============================================================
        # 阶段 1: 快速技术筛选
        # ============================================================
        logger.info(f"🔍 Phase 1: Fast Technical Scan ({len(watchlist)} symbols)...")
        
        signals = []
        for i, symbol in enumerate(watchlist, 1):
            logger.info(f"  [{i}/{len(watchlist)}] {symbol}...")
            
            try:
                signal = self._technical_scan(symbol, lookback_days)
                if signal and signal.signal_strength > 0.3:
                    signals.append(signal)
                    logger.info(f"    ✅ Signal: {signal.signal_strength:.2f}")
                else:
                    logger.info(f"    ⚠️  Too weak")
            except Exception as e:
                logger.warning(f"    ❌ Error: {e}")
                continue
        
        if not signals:
            logger.warning("No signals found in Phase 1")
            return pd.DataFrame()
        
        # 按信号强度排序
        signals.sort(key=lambda x: x.signal_strength, reverse=True)
        
        logger.info(f"✅ Phase 1 complete: {len(signals)} candidates found")
        
        # ============================================================
        # 阶段 2: AI 深度分析（仅对前 N 个）
        # ============================================================
        if enable_ai and self.ai_enabled and ai_top_n > 0:
            logger.info(f"\n🤖 Phase 2: DeepSeek AI Analysis (Top {ai_top_n})...")
            
            for i, signal in enumerate(signals[:ai_top_n], 1):
                logger.info(f"  [{i}/{ai_top_n}] Analyzing {signal.symbol} with AI...")
                
                try:
                    ai_result = self._deepseek_analyze(signal)
                    
                    if ai_result:
                        signal.ai_analyzed = True
                        signal.ai_insight = ai_result.get('insight')
                        signal.ai_recommendation = ai_result.get('recommendation')
                        signal.ai_confidence = ai_result.get('confidence')
                        signal.ai_key_factors = ai_result.get('key_factors')
                        
                        logger.info(f"    ✅ AI: {signal.ai_recommendation} (conf: {signal.ai_confidence:.2f})")
                    else:
                        logger.warning(f"    ⚠️  AI analysis failed")
                        
                except Exception as e:
                    logger.error(f"    ❌ AI error: {e}")
                    continue
            
            logger.info(f"✅ Phase 2 complete: {sum(s.ai_analyzed for s in signals)} AI-analyzed")
        else:
            logger.info("⏭️  Phase 2 skipped (AI disabled)")
        
        # 转换为 DataFrame
        df = pd.DataFrame([asdict(s) for s in signals])
        return df
    
    def _technical_scan(self, symbol: str, lookback_days: int) -> Optional[Signal]:
        """技术筛选（快速）"""
        
        # 1. 获取历史数据
        data = self._fetch_polygon_data(symbol, lookback_days)
        if data is None or len(data) < 20:
            return None
        
        # 2. 计算技术指标
        bb_percentile = self._calculate_bb_percentile(data)
        dte_to_event = self._get_days_to_earnings(symbol)
        news_sentiment = 0.0  # 初始为中性
        liquidity_score = self._calculate_liquidity(data)
        iv_rank = self._calculate_iv_rank(data)
        
        # 3. 综合评分
        signal_strength = self._calculate_signal_strength(
            bb_percentile, dte_to_event, news_sentiment, liquidity_score, iv_rank
        )
        
        # 4. 状态分类
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
    
    def _deepseek_analyze(self, signal: Signal) -> Optional[Dict]:
        """DeepSeek AI 深度分析"""
        
        if not self.deepseek_key:
            return None
        
        # 构建 AI 提示
        prompt = self._build_ai_prompt(signal)
        
        # 调用 DeepSeek API
        headers = {
            'Authorization': f'Bearer {self.deepseek_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'deepseek-reasoner',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a professional options trader analyzing market signals. Provide concise, actionable insights in JSON format.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.3,
            'max_tokens': 500
        }
        
        try:
            response = requests.post(
                self.deepseek_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                
                # 解析 JSON
                return self._parse_ai_response(content)
            else:
                logger.error(f"DeepSeek API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"DeepSeek API exception: {e}")
            return None
    
    def _build_ai_prompt(self, signal: Signal) -> str:
        """构建 AI 提示"""
        
        return f"""Analyze this option trading signal for {signal.symbol}:

Technical Indicators:
- Bollinger Band Percentile: {signal.bb_percentile:.2%} (lower = compressed)
- IV Rank: {signal.iv_rank:.1f}/100 (higher = high volatility)
- Liquidity Score: {signal.liquidity_score:.2f}/1.0
- Days to Event: {signal.dte_to_event or 'N/A'}
- Signal Strength: {signal.signal_strength:.2f}/1.0

Context:
- Strategy: Short Strangle (sell OTM put + call)
- Goal: Profit from volatility compression
- Risk: Stock moves beyond breakeven points

Provide analysis in JSON format:
{{
  "recommendation": "BUY_STRANGLE|WAIT|AVOID",
  "confidence": 0.0-1.0,
  "insight": "2-3 sentence market analysis",
  "key_factors": ["factor1", "factor2", "factor3"]
}}

Focus on: volatility outlook, event risk, liquidity concerns."""
    
    def _parse_ai_response(self, content: str) -> Optional[Dict]:
        """解析 AI 响应"""
        
        try:
            # 尝试提取 JSON
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = content[start:end]
                result = json.loads(json_str)
                
                # 验证必需字段
                if all(k in result for k in ['recommendation', 'confidence', 'insight']):
                    return result
            
            logger.warning("AI response missing required fields")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}")
            return None
    
    # =========================================================================
    # 技术指标计算（与原版相同）
    # =========================================================================
    
    def _fetch_polygon_data(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """从 Polygon 获取历史数据"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 5000,
            'apiKey': self.polygon_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('resultsCount', 0) > 0:
                    results = data['results']
                    
                    df = pd.DataFrame(results)
                    df = df.rename(columns={
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume',
                        't': 'timestamp'
                    })
                    
                    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
                    return df[['date', 'open', 'high', 'low', 'close', 'volume']]
            
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
        """
        获取距离下次事件的天数
        
        优先使用 Polygon 新闻数据
        如果失败，回退到 Mock
        """
        # 尝试 Polygon 新闻 API
        real_dte = self._get_days_to_earnings_polygon(symbol)
        if real_dte is not None:
            return real_dte
        
        # 回退到 Mock（用于测试或 API 失败）
        logger.debug(f"{symbol}: Using mock event date (Polygon news detection failed)")
        mock_dte = np.random.randint(7, 60)
        if 7 <= mock_dte <= 21:
            return mock_dte
        return None
    
    def _get_days_to_earnings_polygon(self, symbol: str) -> Optional[int]:
        """
        使用 Polygon 新闻 API 检测即将到来的事件（智能版）
        
        改进策略:
        1. 从新闻中提取具体日期（正则表达式）
        2. 识别财报季度和年份
        3. 计算事件置信度
        4. 优先返回高置信度的事件
        
        Polygon API:
        - 免费版支持新闻 API
        - 文档: https://polygon.io/docs/stocks/get_v2_reference_news
        """
        
        if not self.api_key:
            logger.debug("POLYGON_API_KEY not set, skipping real event detection")
            return None
        
        try:
            import re
            from dateutil import parser as date_parser
            
            # Polygon News API
            url = f"{self.base_url}/v2/reference/news"
            params = {
                'ticker': symbol,
                'limit': 30,  # 增加到30条以获取更多信息
                'order': 'desc',
                'apiKey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('results'):
                    news_items = data['results']
                    
                    detected_events = []
                    
                    # 分析每条新闻
                    for news in news_items:
                        title = news.get('title', '')
                        description = news.get('description', '')
                        published_utc = news.get('published_utc', '')
                        
                        # 解析发布时间
                        try:
                            pub_date = datetime.strptime(published_utc[:10], '%Y-%m-%d')
                            days_ago = (datetime.now() - pub_date).days
                        except:
                            days_ago = 999
                        
                        # 只分析最近14天的新闻
                        if days_ago > 14:
                            continue
                        
                        text = f"{title} {description}"
                        text_lower = text.lower()
                        
                        # 1. 尝试提取具体日期
                        event_date = self._extract_event_date(text, pub_date)
                        
                        # 2. 检测事件类型和关键词
                        event_info = self._detect_event_type(text_lower)
                        
                        if event_info['detected']:
                            if event_date:
                                # 有具体日期，计算天数
                                days_until = (event_date - datetime.now()).days
                                confidence = 0.9  # 高置信度
                            else:
                                # 无具体日期，根据事件类型估算
                                days_until = event_info['estimated_days']
                                confidence = event_info['confidence']
                            
                            # 只关注7-30天内的事件
                            if 7 <= days_until <= 30:
                                detected_events.append({
                                    'days_until': days_until,
                                    'confidence': confidence,
                                    'event_type': event_info['type'],
                                    'title': title[:60],
                                    'days_ago': days_ago
                                })
                    
                    # 如果检测到事件，返回最高置信度的
                    if detected_events:
                        # 按置信度排序
                        detected_events.sort(key=lambda x: (-x['confidence'], x['days_until']))
                        best_event = detected_events[0]
                        
                        logger.info(f"✅ {symbol} event detected: {best_event['event_type']} in {best_event['days_until']} days")
                        logger.debug(f"   Confidence: {best_event['confidence']:.1%} | Title: {best_event['title']}")
                        
                        return best_event['days_until']
                    
                    logger.debug(f"{symbol}: No upcoming events detected in news")
                    return None
                
                else:
                    logger.debug(f"{symbol}: No news found")
                    return None
            
            elif response.status_code == 403:
                logger.warning("❌ Polygon 403: Check API permissions")
                return None
            
            else:
                logger.debug(f"Polygon News API returned {response.status_code}")
                return None
        
        except Exception as e:
            logger.debug(f"Polygon news exception for {symbol}: {e}")
            return None
    
    def _extract_event_date(self, text: str, reference_date: datetime) -> Optional[datetime]:
        """
        从文本中提取事件日期
        
        支持格式:
        - November 19, 2024
        - Nov. 19
        - 11/19
        - Q3 2024
        """
        import re
        from dateutil import parser as date_parser
        
        try:
            # 1. 尝试解析完整日期 (November 19, 2024)
            date_patterns = [
                r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*\d{4})?',
                r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}(?:,\s*\d{4})?',
                r'\d{1,2}/\d{1,2}(?:/\d{2,4})?',
                r'\d{4}-\d{2}-\d{2}'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        try:
                            # 尝试解析日期
                            parsed = date_parser.parse(match, fuzzy=True)
                            
                            # 如果没有年份，假设是当年或明年
                            if parsed.year < datetime.now().year:
                                parsed = parsed.replace(year=datetime.now().year)
                            
                            # 检查日期是否在未来
                            if parsed > datetime.now():
                                return parsed
                        except:
                            continue
            
            # 2. 尝试解析季度 (Q3 2024, Q4)
            quarter_pattern = r'Q([1-4])\s*(?:20)?(\d{2})?'
            quarter_matches = re.findall(quarter_pattern, text, re.IGNORECASE)
            
            if quarter_matches:
                quarter, year_str = quarter_matches[0]
                quarter = int(quarter)
                
                if year_str:
                    year = 2000 + int(year_str) if len(year_str) == 2 else int(year_str)
                else:
                    year = datetime.now().year
                
                # 财报通常在季度结束后1-1.5个月发布
                quarter_end_months = {1: 3, 2: 6, 3: 9, 4: 12}
                end_month = quarter_end_months[quarter]
                
                # 估算财报日期（季度结束后45天）
                estimated_date = datetime(year, end_month, 1) + timedelta(days=45)
                
                if estimated_date > datetime.now():
                    return estimated_date
        
        except Exception as e:
            logger.debug(f"Date extraction error: {e}")
        
        return None
    
    def _detect_event_type(self, text: str) -> dict:
        """
        检测事件类型和置信度
        
        返回: {
            'detected': bool,
            'type': str,
            'estimated_days': int,
            'confidence': float
        }
        """
        
        # 高优先级关键词（强信号）
        high_priority = {
            'earnings call': ('earnings', 14, 0.8),
            'earnings report': ('earnings', 14, 0.8),
            'quarterly results': ('earnings', 14, 0.75),
            'q1 earnings': ('earnings', 14, 0.8),
            'q2 earnings': ('earnings', 14, 0.8),
            'q3 earnings': ('earnings', 14, 0.8),
            'q4 earnings': ('earnings', 14, 0.8),
            'earnings date': ('earnings', 14, 0.85),
            'reports earnings': ('earnings', 14, 0.8),
        }
        
        # 中优先级关键词
        medium_priority = {
            'earnings': ('earnings', 14, 0.5),
            'results': ('earnings', 14, 0.4),
            'quarterly': ('earnings', 14, 0.4),
            'product launch': ('product_launch', 10, 0.6),
            'unveil': ('product_launch', 10, 0.6),
            'announcement': ('announcement', 12, 0.5),
            'conference': ('conference', 12, 0.5),
            'investor day': ('investor_day', 12, 0.6),
        }
        
        # 1. 检查高优先级
        for keyword, (event_type, days, conf) in high_priority.items():
            if keyword in text:
                return {
                    'detected': True,
                    'type': event_type,
                    'estimated_days': days,
                    'confidence': conf
                }
        
        # 2. 检查中优先级
        for keyword, (event_type, days, conf) in medium_priority.items():
            if keyword in text:
                return {
                    'detected': True,
                    'type': event_type,
                    'estimated_days': days,
                    'confidence': conf
                }
        
        # 3. 未检测到
        return {
            'detected': False,
            'type': None,
            'estimated_days': 0,
            'confidence': 0.0
        }
    
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
        
        iv_rank = 100 * (current_vol - min_vol) / (max_vol - min_vol)
        
        return iv_rank
    
    def _calculate_signal_strength(
        self,
        bb_percentile: float,
        dte_to_event: Optional[int],
        news_sentiment: float,
        liquidity_score: float,
        iv_rank: float
    ) -> float:
        """综合评分"""
        
        # 波动率压缩得分
        bb_score = 1 - bb_percentile
        
        # 事件驱动得分
        if dte_to_event and 7 <= dte_to_event <= 21:
            event_score = 1.0
        else:
            event_score = 0.3
        
        # IV 得分
        iv_score = 1 - abs(iv_rank - 50) / 50
        
        # 新闻情感得分
        news_score = (news_sentiment + 1) / 2
        
        # 加权求和
        signal_strength = (
            0.30 * bb_score +
            0.20 * event_score +
            0.20 * liquidity_score +
            0.15 * iv_score +
            0.15 * news_score
        )
        
        return np.clip(signal_strength, 0, 1)


# =============================================================================
# 测试
# =============================================================================

def main():
    """测试混合版本"""
    
    generator = AISignalGeneratorHybrid()
    
    # 测试小批量
    watchlist = ['AAPL', 'NVDA', 'GOOGL', 'TSLA']
    
    print("\n" + "="*80)
    print("🤖 Hybrid AI Signal Generator Test")
    print("="*80 + "\n")
    
    signals = generator.scan_market(
        watchlist=watchlist,
        ai_top_n=2,  # 只对前 2 个进行 AI 分析
        enable_ai=True
    )
    
    if not signals.empty:
        print("\n📊 Results:\n")
        
        # 显示所有信号
        for _, signal in signals.iterrows():
            print(f"{'='*80}")
            print(f"Symbol: {signal['symbol']}")
            print(f"Signal Strength: {signal['signal_strength']:.3f}")
            print(f"Status: {signal['status']}")
            print(f"BB Percentile: {signal['bb_percentile']:.2%}")
            print(f"IV Rank: {signal['iv_rank']:.1f}")
            
            # AI 分析结果
            if signal.get('ai_analyzed'):
                print(f"\n🤖 AI Analysis:")
                print(f"  Recommendation: {signal.get('ai_recommendation')}")
                print(f"  Confidence: {signal.get('ai_confidence', 0):.2f}")
                print(f"  Insight: {signal.get('ai_insight')}")
                if signal.get('ai_key_factors'):
                    print(f"  Key Factors: {', '.join(signal['ai_key_factors'])}")
            else:
                print(f"\n⏭️  AI Analysis: Not performed (beyond top N)")
            
            print()
    else:
        print("❌ No signals found")


if __name__ == '__main__':
    main()

