#!/usr/bin/env python3
"""
测试 API 访问权限
"""

import os
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

def test_api_access():
    """测试 API 访问权限"""
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("❌ POLYGON_API_KEY not set")
        return
    
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    base_url = "https://api.polygon.io"
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 测试1: 获取股票价格（应该可以工作）
    print("📊 Test 1: Stock Price (Should work)")
    url = f"{base_url}/v2/aggs/ticker/NVDA/prev"
    params = {'adjusted': 'true', 'apiKey': api_key}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                result = data['results'][0]
                print(f"   ✅ Stock Price: ${result.get('c', 0):.2f}")
            else:
                print(f"   ⚠️  No data")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # 测试2: 获取期权链（可能需要更高权限）
    print("📊 Test 2: Options Chain (May require Starter+ plan)")
    url = f"{base_url}/v3/reference/options/contracts"
    params = {
        'underlying_ticker': 'NVDA',
        'expired': 'false',
        'limit': 5,
        'apiKey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            count = data.get('resultsCount', 0)
            print(f"   ✅ Found {count} contracts")
            if count > 0:
                contract = data['results'][0]
                print(f"   Example: {contract.get('ticker', 'N/A')}")
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden - Need Starter+ plan for options data")
        else:
            print(f"   ❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Response: {error_data}")
            except:
                pass
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    print()
    
    # 测试3: 尝试获取已知期权合约的价格
    print("📊 Test 3: Option Price (Previous Close)")
    # 使用一个常见的期权合约格式
    # O:NVDA + YYMMDD + C/P + 行权价
    # 例如: O:NVDA241115C00150000 (NVDA, 2024-11-15, Call, $150)
    
    # 尝试几个可能的合约
    test_contracts = [
        "O:NVDA241115C00150000",  # 2024-11-15 Call $150
        "O:NVDA241115C00200000",  # 2024-11-15 Call $200
        "O:NVDA241122C00150000",  # 2024-11-22 Call $150
    ]
    
    for contract in test_contracts:
        url = f"{base_url}/v2/aggs/ticker/{contract}/prev"
        params = {'adjusted': 'true', 'apiKey': api_key}
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    result = data['results'][0]
                    print(f"   ✅ {contract}: ${result.get('c', 0):.2f}")
                    break
                else:
                    print(f"   ⚠️  {contract}: No data")
            elif response.status_code == 403:
                print(f"   ❌ {contract}: 403 Forbidden")
                break
            else:
                print(f"   ⚠️  {contract}: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ {contract}: Exception {e}")

if __name__ == "__main__":
    test_api_access()



