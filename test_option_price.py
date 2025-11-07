#!/usr/bin/env python3
"""
测试获取当天期权价格
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

def test_option_price(symbol: str = "NVDA", strike: float = 150.0, option_type: str = "C", date: str = None):
    """
    测试获取期权价格
    
    Args:
        symbol: 标的代码
        strike: 行权价
        option_type: 期权类型 ('C' for Call, 'P' for Put)
        date: 日期 (YYYY-MM-DD)，如果为None则使用今天
    """
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ POLYGON_API_KEY not set")
        return
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"📊 Testing option price fetch for {symbol}")
    print(f"   Date: {date}")
    print(f"   Strike: ${strike}")
    print(f"   Type: {'Call' if option_type == 'C' else 'Put'}")
    print()
    
    # 计算到期日（假设30天后到期）
    from datetime import timedelta
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    expiry_date = (date_obj + timedelta(days=30)).strftime('%Y-%m-%d')
    
    # 构造期权代码 (OCC format)
    # 例如: O:NVDA251207C00150000 (NVDA, 2025-12-07, Call, $150)
    # 格式: O:SYMBOL + YYMMDD + C/P + 行权价(8位整数，乘以1000)
    expiry_code = expiry_date[2:4] + expiry_date[5:7] + expiry_date[8:10]  # YYMMDD
    strike_str = f"{int(strike * 1000):08d}"  # 8位整数
    option_ticker = f"O:{symbol}{expiry_code}{option_type}{strike_str}"
    
    print(f"   Option Ticker: {option_ticker}")
    print()
    
    # 获取期权聚合数据
    base_url = "https://api.polygon.io"
    
    # 方法1: 获取当天聚合数据
    print("🔍 Method 1: Aggregates (Bars) API")
    url = f"{base_url}/v2/aggs/ticker/{option_ticker}/range/1/minute/{date}/{date}"
    params = {
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 5000,
        'apiKey': api_key
    }
    
    try:
        print(f"   URL: {url}")
        response = requests.get(url, params=params, timeout=15)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results_count = data.get('resultsCount', 0)
            print(f"   ✅ Success! Found {results_count} data points")
            
            if results_count > 0:
                results = data['results']
                # 获取最新的一条数据
                latest = results[-1]
                print(f"   Latest Data:")
                print(f"     Timestamp: {latest.get('t', 'N/A')}")
                print(f"     Open: ${latest.get('o', 0):.2f}")
                print(f"     High: ${latest.get('h', 0):.2f}")
                print(f"     Low: ${latest.get('l', 0):.2f}")
                print(f"     Close: ${latest.get('c', 0):.2f}")
                print(f"     Volume: {latest.get('v', 0)}")
                print(f"     VWAP: ${latest.get('vw', 0):.2f}")
                
                # 计算中间价
                if latest.get('h') and latest.get('l'):
                    mid_price = (latest.get('h') + latest.get('l')) / 2
                    print(f"     Mid Price: ${mid_price:.2f}")
            else:
                print(f"   ⚠️  No data points found")
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden")
            print(f"      Possible reasons:")
            print(f"      1. API key doesn't have access to option data (needs Starter+ plan)")
            print(f"      2. API key is invalid or expired")
            print(f"      3. API quota exceeded")
        elif response.status_code == 404:
            print(f"   ⚠️  404 Not Found")
            print(f"      Option ticker may not exist or date is invalid")
        else:
            print(f"   ❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"      Response: {error_data}")
            except:
                print(f"      Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # 方法2: 获取期权合约详情
    print("🔍 Method 2: Options Contract Details API")
    url = f"{base_url}/v3/reference/options/contracts/{option_ticker}"
    params = {
        'apiKey': api_key
    }
    
    try:
        print(f"   URL: {url}")
        response = requests.get(url, params=params, timeout=15)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success!")
            print(f"   Contract Details:")
            if 'results' in data:
                contract = data['results']
                print(f"     Ticker: {contract.get('ticker', 'N/A')}")
                print(f"     Name: {contract.get('name', 'N/A')}")
                print(f"     Strike: ${contract.get('strike_price', 0):.2f}")
                print(f"     Type: {contract.get('contract_type', 'N/A')}")
                print(f"     Expiry: {contract.get('expiration_date', 'N/A')}")
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden")
        elif response.status_code == 404:
            print(f"   ⚠️  404 Not Found - Contract may not exist")
        else:
            print(f"   ❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"      Response: {error_data}")
            except:
                print(f"      Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # 方法3: 获取实时报价（如果可用）
    print("🔍 Method 3: Previous Close API")
    url = f"{base_url}/v2/aggs/ticker/{option_ticker}/prev"
    params = {
        'adjusted': 'true',
        'apiKey': api_key
    }
    
    try:
        print(f"   URL: {url}")
        response = requests.get(url, params=params, timeout=15)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success!")
            if 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                print(f"   Previous Close:")
                print(f"     Date: {result.get('t', 'N/A')}")
                print(f"     Open: ${result.get('o', 0):.2f}")
                print(f"     High: ${result.get('h', 0):.2f}")
                print(f"     Low: ${result.get('l', 0):.2f}")
                print(f"     Close: ${result.get('c', 0):.2f}")
                print(f"     Volume: {result.get('v', 0)}")
                print(f"     VWAP: ${result.get('vw', 0):.2f}")
                
                # 计算中间价
                if result.get('h') and result.get('l'):
                    mid_price = (result.get('h') + result.get('l')) / 2
                    print(f"     Mid Price: ${mid_price:.2f}")
                
                # 使用收盘价或中间价作为期权价格
                option_price = result.get('c') or (result.get('h') + result.get('l')) / 2 if (result.get('h') and result.get('l')) else None
                if option_price:
                    print(f"     ✅ Option Price: ${option_price:.2f}")
            else:
                print(f"   ⚠️  No results in response")
                print(f"   Response: {data}")
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden")
        elif response.status_code == 404:
            print(f"   ⚠️  404 Not Found")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    import sys
    
    # 默认参数
    symbol = "NVDA"
    strike = 150.0
    option_type = "C"
    date = "2025-11-07"  # 今天
    
    # 从命令行参数获取
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    if len(sys.argv) > 2:
        strike = float(sys.argv[2])
    if len(sys.argv) > 3:
        option_type = sys.argv[3].upper()
    if len(sys.argv) > 4:
        date = sys.argv[4]
    
    test_option_price(symbol, strike, option_type, date)

