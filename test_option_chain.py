#!/usr/bin/env python3
"""
测试查找可用的期权合约
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

load_dotenv()

def find_option_contracts(symbol: str = "NVDA", date: str = None):
    """
    查找可用的期权合约
    
    Args:
        symbol: 标的代码
        date: 日期 (YYYY-MM-DD)，如果为None则使用今天
    """
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ POLYGON_API_KEY not set")
        return
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"📊 Finding option contracts for {symbol}")
    print(f"   Date: {date}")
    print()
    
    base_url = "https://api.polygon.io"
    
    # 方法1: 获取期权链
    print("🔍 Method 1: Options Chain API")
    url = f"{base_url}/v3/reference/options/contracts"
    params = {
        'underlying_ticker': symbol,
        'expired': 'false',  # 只获取未过期的
        'limit': 100,
        'apiKey': api_key
    }
    
    try:
        print(f"   URL: {url}")
        response = requests.get(url, params=params, timeout=15)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results_count = data.get('resultsCount', 0)
            print(f"   ✅ Success! Found {results_count} contracts")
            
            if results_count > 0:
                results = data['results']
                print(f"   Showing first 10 contracts:")
                for i, contract in enumerate(results[:10], 1):
                    print(f"   {i}. {contract.get('ticker', 'N/A')}")
                    print(f"      Strike: ${contract.get('strike_price', 0):.2f}")
                    print(f"      Type: {contract.get('contract_type', 'N/A')}")
                    print(f"      Expiry: {contract.get('expiration_date', 'N/A')}")
                    print()
                
                # 尝试获取一个合约的价格
                if len(results) > 0:
                    test_contract = results[0]
                    test_ticker = test_contract.get('ticker')
                    print(f"   Testing price fetch for: {test_ticker}")
                    test_price(test_ticker, date)
            else:
                print(f"   ⚠️  No contracts found")
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden")
            print(f"      API key may not have access to options data")
        else:
            print(f"   ❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"      Response: {error_data}")
            except:
                print(f"      Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

def test_price(option_ticker: str, date: str):
    """测试获取期权价格"""
    api_key = os.getenv('POLYGON_API_KEY')
    base_url = "https://api.polygon.io"
    
    # 尝试获取前一天的价格（因为当天可能还没有数据）
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    prev_date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"   Testing Previous Close API for {prev_date}...")
    url = f"{base_url}/v2/aggs/ticker/{option_ticker}/prev"
    params = {
        'adjusted': 'true',
        'apiKey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                print(f"   ✅ Found price:")
                print(f"      Close: ${result.get('c', 0):.2f}")
                print(f"      High: ${result.get('h', 0):.2f}")
                print(f"      Low: ${result.get('l', 0):.2f}")
                print(f"      Volume: {result.get('v', 0)}")
            else:
                print(f"   ⚠️  No price data available")
        else:
            print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    symbol = "NVDA"
    date = datetime.now().strftime('%Y-%m-%d')
    
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    if len(sys.argv) > 2:
        date = sys.argv[2]
    
    find_option_contracts(symbol, date)



