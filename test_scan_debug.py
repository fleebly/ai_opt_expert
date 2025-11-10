#!/usr/bin/env python3
"""
测试扫描过程，检查为什么从 2025-05-01 开始就停止
"""

import sys
import os
from datetime import datetime
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import OptionBacktest

def test_data_fetching():
    """测试数据获取"""
    print("=" * 80)
    print("测试 1: 数据获取")
    print("=" * 80)
    
    backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
    
    symbol = "BABA"
    start_date = "2025-05-01"
    end_date = "2025-12-01"
    
    print(f"\n请求数据: {symbol} from {start_date} to {end_date}")
    
    data = backtest._fetch_historical_data(symbol, start_date, end_date)
    
    if data is None:
        print("❌ 数据获取失败：返回 None")
        return None
    
    if len(data) < 20:
        print(f"❌ 数据不足：只有 {len(data)} 个交易日（需要至少 20 个）")
        return None
    
    print(f"✅ 数据获取成功：{len(data)} 个交易日")
    print(f"   日期范围: {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"   前5个交易日: {data.index[:5].strftime('%Y-%m-%d').tolist()}")
    print(f"   后5个交易日: {data.index[-5:].strftime('%Y-%m-%d').tolist()}")
    
    return data

def test_indicator_calculation(data):
    """测试指标计算"""
    print("\n" + "=" * 80)
    print("测试 2: 指标计算")
    print("=" * 80)
    
    if data is None:
        print("❌ 跳过：没有数据")
        return None
    
    backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
    
    print(f"\n计算基础指标...")
    data_with_indicators = backtest._calculate_indicators(data)
    
    print(f"✅ 基础指标计算完成")
    print(f"   数据形状: {data_with_indicators.shape}")
    print(f"   列名: {list(data_with_indicators.columns)}")
    
    # 检查关键指标是否有 NaN
    print(f"\n检查关键指标的 NaN 情况:")
    key_indicators = ['bb_percentile', 'rsi', 'atr', 'bb_width']
    for indicator in key_indicators:
        if indicator in data_with_indicators.columns:
            nan_count = data_with_indicators[indicator].isna().sum()
            valid_count = len(data_with_indicators) - nan_count
            print(f"   {indicator}: {valid_count} 个有效值, {nan_count} 个 NaN")
            
            # 显示第一个有效值的位置
            first_valid_idx = data_with_indicators[indicator].first_valid_index()
            if first_valid_idx is not None:
                first_valid_date = first_valid_idx.strftime('%Y-%m-%d') if hasattr(first_valid_idx, 'strftime') else str(first_valid_idx)
                print(f"      第一个有效值日期: {first_valid_date}")
    
    # 检查 bb_percentile（需要 60 个交易日）
    if 'bb_percentile' in data_with_indicators.columns:
        bb_percentile_valid = data_with_indicators['bb_percentile'].dropna()
        if len(bb_percentile_valid) == 0:
            print(f"\n⚠️  警告: bb_percentile 全部为 NaN（需要 60 个交易日的历史数据）")
        else:
            print(f"\n✅ bb_percentile 有 {len(bb_percentile_valid)} 个有效值")
            print(f"   第一个有效值日期: {bb_percentile_valid.index[0].strftime('%Y-%m-%d')}")
    
    return data_with_indicators

def test_signal_library(data):
    """测试 SignalLibrary"""
    print("\n" + "=" * 80)
    print("测试 3: SignalLibrary 导入和计算")
    print("=" * 80)
    
    if data is None:
        print("❌ 跳过：没有数据")
        return None
    
    try:
        from signal_optimization.signal_library import SignalLibrary
        print("✅ SignalLibrary 导入成功")
        
        print(f"\n计算完整指标（SignalLibrary）...")
        data_full = SignalLibrary.calculate_all_indicators(data)
        
        print(f"✅ SignalLibrary 指标计算完成")
        print(f"   数据形状: {data_full.shape}")
        print(f"   新增列数: {len(data_full.columns) - len(data.columns)}")
        
        # 检查关键指标
        key_indicators = ['bb_width_pct', 'ma50', 'macd', 'cci']
        print(f"\n检查 SignalLibrary 指标的 NaN 情况:")
        for indicator in key_indicators:
            if indicator in data_full.columns:
                nan_count = data_full[indicator].isna().sum()
                valid_count = len(data_full) - nan_count
                print(f"   {indicator}: {valid_count} 个有效值, {nan_count} 个 NaN")
                
                # 显示第一个有效值的位置
                first_valid_idx = data_full[indicator].first_valid_index()
                if first_valid_idx is not None:
                    first_valid_date = first_valid_idx.strftime('%Y-%m-%d') if hasattr(first_valid_idx, 'strftime') else str(first_valid_idx)
                    print(f"      第一个有效值日期: {first_valid_date}")
        
        return data_full
        
    except ImportError as e:
        print(f"❌ SignalLibrary 导入失败: {e}")
        print(f"   这会导致使用组合信号时提前停止")
        return None
    except Exception as e:
        print(f"❌ SignalLibrary 计算失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_backtest_run():
    """测试完整回测流程"""
    print("\n" + "=" * 80)
    print("测试 4: 完整回测流程")
    print("=" * 80)
    
    symbol = "BABA"
    start_date = "2025-05-01"
    end_date = "2025-12-01"
    
    # 测试简单信号
    print(f"\n测试 4.1: 简单信号 (bb_compression)")
    try:
        backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
        result = backtest.run_backtest(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            strategy='auto',
            entry_signal='bb_compression',
            profit_target=5.0,
            stop_loss=-0.5,
            max_holding_days=30,
            position_size=0.1
        )
        
        print(f"✅ 回测完成")
        print(f"   交易次数: {result.num_trades}")
        print(f"   总收益: {result.total_return:.2%}")
        print(f"   权益曲线长度: {len(result.equity_curve)}")
        if len(result.equity_curve) > 0:
            print(f"   权益曲线日期范围: {result.equity_curve.index[0].strftime('%Y-%m-%d')} 到 {result.equity_curve.index[-1].strftime('%Y-%m-%d')}")
        
    except Exception as e:
        print(f"❌ 回测失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试组合信号
    print(f"\n测试 4.2: 组合信号 (dict)")
    try:
        # 模拟一个简单的组合信号
        entry_signal_dict = {
            'bb_compression': 0.3,
            'rsi_oversold': 0.3,
            'volume_surge': 0.4
        }
        
        backtest2 = OptionBacktest(initial_capital=10000, use_real_prices=True)
        result2 = backtest2.run_backtest(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            strategy='auto',
            entry_signal=entry_signal_dict,
            profit_target=5.0,
            stop_loss=-0.5,
            max_holding_days=30,
            position_size=0.1
        )
        
        print(f"✅ 组合信号回测完成")
        print(f"   交易次数: {result2.num_trades}")
        print(f"   总收益: {result2.total_return:.2%}")
        print(f"   权益曲线长度: {len(result2.equity_curve)}")
        if len(result2.equity_curve) > 0:
            print(f"   权益曲线日期范围: {result2.equity_curve.index[0].strftime('%Y-%m-%d')} 到 {result2.equity_curve.index[-1].strftime('%Y-%m-%d')}")
        
    except Exception as e:
        print(f"❌ 组合信号回测失败: {e}")
        import traceback
        traceback.print_exc()

def test_entry_signal_check(data_with_indicators):
    """测试入场信号检查"""
    print("\n" + "=" * 80)
    print("测试 5: 入场信号检查")
    print("=" * 80)
    
    if data_with_indicators is None:
        print("❌ 跳过：没有数据")
        return
    
    backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
    
    # 检查前60个交易日是否有有效的 bb_percentile
    print(f"\n检查前60个交易日的 bb_percentile:")
    first_60 = data_with_indicators.head(60)
    if 'bb_percentile' in first_60.columns:
        bb_valid = first_60['bb_percentile'].dropna()
        print(f"   前60个交易日中，bb_percentile 有效值数量: {len(bb_valid)}")
        if len(bb_valid) == 0:
            print(f"   ⚠️  警告: 前60个交易日全部为 NaN，无法产生入场信号")
        else:
            print(f"   ✅ 从第 {len(first_60) - len(bb_valid) + 1} 个交易日开始有有效值")
    
    # 检查从第20个交易日开始是否有有效的信号
    print(f"\n检查从第20个交易日开始的信号检查:")
    for i in range(20, min(30, len(data_with_indicators))):
        row = data_with_indicators.iloc[i]
        date = data_with_indicators.index[i]
        
        # 检查简单信号
        try:
            should_enter = backtest._check_entry_signal(row, 'bb_compression')
            if should_enter:
                print(f"   ✅ {date.strftime('%Y-%m-%d')} (第{i+1}个交易日): 触发 bb_compression 信号")
                break
        except Exception as e:
            print(f"   ❌ {date.strftime('%Y-%m-%d')}: 信号检查失败: {e}")
            break
    else:
        print(f"   ⚠️  前30个交易日中没有触发入场信号")

def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("扫描停止问题诊断测试")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试标的: BABA")
    print(f"测试日期范围: 2025-05-01 到 2025-12-01")
    print("=" * 80)
    
    # 测试 1: 数据获取
    data = test_data_fetching()
    
    # 测试 2: 指标计算
    data_with_indicators = test_indicator_calculation(data)
    
    # 测试 3: SignalLibrary
    data_full = test_signal_library(data)
    
    # 测试 4: 完整回测
    test_backtest_run()
    
    # 测试 5: 入场信号检查
    test_entry_signal_check(data_with_indicators)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == '__main__':
    main()

