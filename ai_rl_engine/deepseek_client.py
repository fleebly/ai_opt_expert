#!/usr/bin/env python3
"""
DeepSeek AI Client for Strategy Analysis

DeepSeek API 文档: https://platform.deepseek.com/api-docs/
"""

import os
import json
import logging
from typing import Dict, Optional
import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    DeepSeek API 客户端
    
    使用 DeepSeek-V3 模型进行策略分析
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 DeepSeek 客户端
        
        Args:
            api_key: DeepSeek API Key，如果不提供则从环境变量读取
        """
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not found in environment or parameter")
        
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-reasoner"  # deepseek-reasoner 或 deepseek-chat
        
        logger.info("DeepSeek client initialized")
    
    def chat_completion(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> Dict:
        """
        调用 DeepSeek Chat API
        
        Args:
            messages: 对话消息列表 [{"role": "system/user/assistant", "content": "..."}]
            temperature: 温度参数 (0-2)
            max_tokens: 最大返回 tokens
            response_format: 响应格式，如 {"type": "json_object"}
        
        Returns:
            API 响应字典
        """
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # 添加 JSON 模式（如果指定）
        if response_format:
            payload["response_format"] = response_format
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"DeepSeek API HTTP error: {e}")
            logger.error(f"Response: {response.text}")
            raise
        except requests.exceptions.Timeout:
            logger.error("DeepSeek API timeout")
            raise
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise
    
    def analyze_market(
        self,
        symbol: str,
        market_data: Dict,
        option_data: Optional[Dict] = None,
        news_data: Optional[Dict] = None
    ) -> Dict:
        """
        使用 DeepSeek 分析市场数据并生成期权策略
        
        Args:
            symbol: 标的代码
            market_data: 市场数据（价格、技术指标等）
            option_data: 期权数据（可选）
            news_data: 新闻数据（可选）
        
        Returns:
            策略建议字典
        """
        # 构建 system prompt
        system_prompt = """You are a professional quantitative options trading analyst.
Your task is to analyze market data and generate option strategy recommendations.

IMPORTANT: You must respond in valid JSON format with the following structure:
{
    "action": "STRANGLE" or "WAIT",
    "confidence": 0-1,
    "reasoning": "brief explanation",
    "legs": [
        {
            "type": "put" or "call",
            "action": "sell" or "buy",
            "strike": float,
            "expiry": "YYYY-MM-DD",
            "quantity": int
        }
    ],
    "risk_metrics": {
        "max_profit": float,
        "max_loss": float,
        "breakeven_points": [float, float],
        "expected_return": float
    },
    "stop_loss": float,
    "take_profit": float
}

Focus on:
1. Volatility compression (Bollinger Band width percentile < 30%)
2. Delta neutral strategies
3. Liquid options (bid-ask spread < 5%, open interest > 100)
4. Risk-reward ratio > 2:1
"""
        
        # 构建 user prompt
        market_summary = self._format_market_data(symbol, market_data, option_data, news_data)
        
        user_prompt = f"""Analyze the following market data and recommend an option strategy:

{market_summary}

Requirements:
- Strategy type: Short Strangle (sell OTM put + sell OTM call)
- Target DTE: 30-60 days
- Net Delta: close to 0 (delta neutral)
- Premium: maximize credit received
- Liquidity: bid-ask spread < 5%, OI > 100

If no good opportunity (low IV, poor liquidity, or high risk), return action="WAIT".

Respond ONLY with valid JSON, no additional text."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 调用 DeepSeek API（使用 JSON 模式）
        response = self.chat_completion(
            messages=messages,
            temperature=0.3,  # 较低温度以获得更一致的输出
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        # 提取结果
        content = response['choices'][0]['message']['content']
        
        try:
            strategy = json.loads(content)
            return strategy
        except json.JSONDecodeError:
            logger.error(f"Failed to parse DeepSeek response as JSON: {content}")
            # 尝试提取 JSON
            return self._extract_json(content)
    
    def _format_market_data(
        self,
        symbol: str,
        market_data: Dict,
        option_data: Optional[Dict],
        news_data: Optional[Dict]
    ) -> str:
        """格式化市场数据为文本"""
        
        summary = f"Symbol: {symbol}\n\n"
        
        # 市场数据
        summary += "Market Data:\n"
        summary += f"  Current Price: ${market_data.get('price', 0):.2f}\n"
        summary += f"  Change: {market_data.get('change_pct', 0):.2%}\n"
        summary += f"  Volume: {market_data.get('volume', 0):,.0f}\n"
        
        if 'technical' in market_data:
            tech = market_data['technical']
            summary += f"\nTechnical Indicators:\n"
            summary += f"  RSI(14): {tech.get('rsi', 0):.1f}\n"
            summary += f"  BB Width Percentile: {tech.get('bb_percentile', 0):.2%}\n"
            summary += f"  MA(20): ${tech.get('ma20', 0):.2f}\n"
            summary += f"  MA(50): ${tech.get('ma50', 0):.2f}\n"
        
        # 期权数据
        if option_data:
            summary += f"\nOption Chain Summary:\n"
            summary += f"  Average IV: {option_data.get('avg_iv', 0):.2%}\n"
            summary += f"  IV Rank: {option_data.get('iv_rank', 0):.1f}\n"
            summary += f"  Put/Call Ratio: {option_data.get('pcr', 0):.2f}\n"
            
            if 'contracts' in option_data:
                summary += f"  Available contracts: {len(option_data['contracts'])}\n"
        
        # 新闻数据
        if news_data:
            summary += f"\nNews Sentiment:\n"
            summary += f"  Score: {news_data.get('sentiment', 0):.2f}\n"
            summary += f"  Article Count: {news_data.get('count', 0)}\n"
        
        return summary
    
    def _extract_json(self, text: str) -> Dict:
        """从文本中提取 JSON（如果 API 返回了额外文本）"""
        import re
        
        # 尝试找到 JSON 块
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # 返回默认 WAIT 响应
        return {
            "action": "WAIT",
            "confidence": 0.0,
            "reasoning": "Failed to parse AI response",
            "legs": [],
            "risk_metrics": {},
            "stop_loss": 0,
            "take_profit": 0
        }


# =============================================================================
# 使用示例
# =============================================================================

def main():
    """测试 DeepSeek 客户端"""
    
    client = DeepSeekClient()
    
    # Mock 市场数据
    market_data = {
        'price': 125.50,
        'change_pct': 0.023,
        'volume': 15_000_000,
        'technical': {
            'rsi': 45.2,
            'bb_percentile': 0.28,
            'ma20': 123.50,
            'ma50': 120.00
        }
    }
    
    option_data = {
        'avg_iv': 0.35,
        'iv_rank': 42.5,
        'pcr': 0.85
    }
    
    print("\n" + "="*80)
    print("🤖 DeepSeek AI Strategy Analysis")
    print("="*80 + "\n")
    
    print("Analyzing market data...")
    
    result = client.analyze_market(
        symbol='NVDA',
        market_data=market_data,
        option_data=option_data
    )
    
    print("\n📊 Strategy Recommendation:\n")
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()




