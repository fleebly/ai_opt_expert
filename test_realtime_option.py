#!/usr/bin/env python3
"""
测试获取当天（2025-11-07）的实时期权价格
"""

import os
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

def test_realtime_option(symbol: str = "NVDA", strike: float = 150.0, option_type: str = "C", date: str = "2025-11-07"):
    """
    测试获取当天的实时期权价格
    """
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ POLYGON_API_KEY not set")
        return
    
    print(f"📊 Testing REAL-TIME option price for {symbol} on {date}")
    print(f"   Strike: ${strike}")
    print(f"   Type: {'Call' if option_type == 'C' else 'Put'}")
    print()
    
    base_url = "https://api.polygon.io"
    
    # 使用 2025-11-21 作为到期日（从之前的测试知道这个合约存在）
    expiry_code = "251121"  # 2025-11-21
    strike_str = f"{int(strike * 1000):08d}"
    option_ticker = f"O:{symbol}{expiry_code}{option_type}{strike_str}"
    
    print(f"   Option Ticker: {option_ticker}")
    print()
    
    # 方法1: 获取当天的聚合数据（1分钟级别）
    print("🔍 Method 1: Today's Minute Bars")
    url = f"{base_url}/v2/aggs/ticker/{option_ticker}/range/1/minute/{date}/{date}"
    params = {
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 5000,
        'apiKey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results_count = data.get('resultsCount', 0)
            print(f"   ✅ Found {results_count} minute bars")
            
            if results_count > 0:
                results = data['results']
                latest = results[-1]
                print(f"   Latest Bar:")
                print(f"     Timestamp: {latest.get('t', 'N/A')}")
                print(f"     Open: ${latest.get('o', 0):.2f}")
                print(f"     High: ${latest.get('h', 0):.2f}")
                print(f"     Low: ${latest.get('l', 0):.2f}")
                print(f"     Close: ${latest.get('c', 0):.2f}")
                print(f"     Volume: {latest.get('v', 0)}")
                
                # 计算中间价
                mid_price = (latest.get('h', 0) + latest.get('l', 0)) / 2
                print(f"     Mid Price: ${mid_price:.2f}")
                print(f"     ✅ Real-time Price: ${latest.get('c', mid_price):.2f}")
            else:
                print(f"   ⚠️  No minute bars found for today")
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden - May need Starter+ plan for minute-level data")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # 方法2: 获取当天的日线数据
    print("🔍 Method 2: Today's Daily Bar")
    url = f"{base_url}/v2/aggs/ticker/{option_ticker}/range/1/day/{date}/{date}"
    params = {
        'adjusted': 'true',
        'apiKey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results_count = data.get('resultsCount', 0)
            print(f"   ✅ Found {results_count} daily bar(s)")
            
            if results_count > 0:
                result = data['results'][0]
                print(f"   Today's Data:")
                print(f"     Open: ${result.get('o', 0):.2f}")
                print(f"     High: ${result.get('h', 0):.2f}")
                print(f"     Low: ${result.get('l', 0):.2f}")
                print(f"     Close: ${result.get('c', 0):.2f}")
                print(f"     Volume: {result.get('v', 0)}")
                
                mid_price = (result.get('h', 0) + result.get('l', 0)) / 2
                print(f"     Mid Price: ${mid_price:.2f}")
                print(f"     ✅ Today's Price: ${result.get('c', mid_price):.2f}")
            else:
                print(f"   ⚠️  No daily bar found for today")
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # 方法3: 获取最新报价（如果可用）
    print("🔍 Method 3: Latest Quote")
    url = f"{base_url}/v2/last/trade/{option_ticker}"
    params = {'apiKey': api_key}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                result = data['results']
                print(f"   ✅ Latest Trade:")
                print(f"     Price: ${result.get('p', 0):.2f}")
                print(f"     Size: {result.get('s', 0)}")
                print(f"     Timestamp: {result.get('t', 'N/A')}")
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden")
        else:
            print(f"   ⚠️  Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    import sys
    
    symbol = "NVDA"
    strike = 150.0
    option_type = "C"
    date = "2025-11-07"
    
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    if len(sys.argv) > 2:
        strike = float(sys.argv[2])
    if len(sys.argv) > 3:
        option_type = sys.argv[3].upper()
    if len(sys.argv) > 4:
        date = sys.argv[4]
    
    test_realtime_option(symbol, strike, option_type, date)



