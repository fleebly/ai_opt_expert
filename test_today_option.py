#!/usr/bin/env python3
"""
测试获取今天（2025-11-07）的期权价格
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

load_dotenv()

def test_today_option_price(symbol: str = "NVDA", strike: float = 150.0, option_type: str = "C"):
    """
    测试获取今天的期权价格
    
    Args:
        symbol: 标的代码
        strike: 行权价
        option_type: 期权类型 ('C' for Call, 'P' for Put)
    """
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ POLYGON_API_KEY not set")
        return
    
    today = "2025-11-07"
    print(f"📊 Testing option price for {symbol} on {today}")
    print(f"   Strike: ${strike}")
    print(f"   Type: {'Call' if option_type == 'C' else 'Put'}")
    print()
    
    base_url = "https://api.polygon.io"
    
    # 尝试不同的到期日（从今天开始，30-60天内）
    date_obj = datetime.strptime(today, '%Y-%m-%d')
    
    # 常见的期权到期日通常是周五，且是每月的第三个周五
    # 让我们尝试几个可能的到期日
    test_expiries = []
    for days in [7, 14, 21, 30, 45, 60]:
        expiry_date = date_obj + timedelta(days=days)
        # 找到最近的周五
        days_until_friday = (4 - expiry_date.weekday()) % 7
        if days_until_friday == 0:
            days_until_friday = 7
        expiry_friday = expiry_date + timedelta(days=days_until_friday)
        test_expiries.append(expiry_friday.strftime('%Y-%m-%d'))
    
    # 去重并排序
    test_expiries = sorted(list(set(test_expiries)))
    
    print(f"🔍 Testing {len(test_expiries)} possible expiry dates...")
    print()
    
    strike_str = f"{int(strike * 1000):08d}"
    
    found_price = False
    for expiry_date in test_expiries:
        # 构造期权代码 (OCC format)
        expiry_code = expiry_date[2:4] + expiry_date[5:7] + expiry_date[8:10]  # YYMMDD
        option_ticker = f"O:{symbol}{expiry_code}{option_type}{strike_str}"
        
        # 方法1: Previous Close（获取前一天的价格）
        url = f"{base_url}/v2/aggs/ticker/{option_ticker}/prev"
        params = {'adjusted': 'true', 'apiKey': api_key}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    result = data['results'][0]
                    close_price = result.get('c', 0)
                    if close_price > 0:
                        print(f"   ✅ {option_ticker}")
                        print(f"      Expiry: {expiry_date}")
                        print(f"      Previous Close: ${close_price:.2f}")
                        print(f"      High: ${result.get('h', 0):.2f}")
                        print(f"      Low: ${result.get('l', 0):.2f}")
                        print(f"      Volume: {result.get('v', 0)}")
                        found_price = True
                        break
        except Exception as e:
            continue
        
        # 方法2: 尝试获取当天的聚合数据（可能需要更高权限）
        url = f"{base_url}/v2/aggs/ticker/{option_ticker}/range/1/day/{today}/{today}"
        params = {'adjusted': 'true', 'apiKey': api_key}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('resultsCount', 0) > 0:
                    result = data['results'][0]
                    close_price = result.get('c', 0)
                    if close_price > 0:
                        print(f"   ✅ {option_ticker} (Today's data)")
                        print(f"      Expiry: {expiry_date}")
                        print(f"      Close: ${close_price:.2f}")
                        print(f"      High: ${result.get('h', 0):.2f}")
                        print(f"      Low: ${result.get('l', 0):.2f}")
                        print(f"      Volume: {result.get('v', 0)}")
                        found_price = True
                        break
        except Exception as e:
            continue
    
    if not found_price:
        print(f"   ⚠️  No option price found for {symbol} ${strike} {option_type}")
        print(f"   Possible reasons:")
        print(f"   1. Option contract doesn't exist for this strike/expiry")
        print(f"   2. Date is in the future (today is {datetime.now().strftime('%Y-%m-%d')})")
        print(f"   3. Need to use different expiry dates")
        print()
        print(f"   💡 Try running with different strikes or check available contracts")

if __name__ == "__main__":
    import sys
    
    symbol = "NVDA"
    strike = 150.0
    option_type = "C"
    
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    if len(sys.argv) > 2:
        strike = float(sys.argv[2])
    if len(sys.argv) > 3:
        option_type = sys.argv[3].upper()
    
    test_today_option_price(symbol, strike, option_type)



