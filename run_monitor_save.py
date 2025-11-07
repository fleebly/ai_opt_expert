#!/usr/bin/env python3
"""
运行Strategy Monitor并保存完整结果到文件
用于本地预生成数据，前端直接展示
"""

import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from backtest_engine import OptionBacktest
from monitor_cache import MonitorCache

def load_strategies():
    """加载所有策略文件"""
    strategies_dir = Path("strategies")
    if not strategies_dir.exists():
        return []
    
    strategies = []
    for file in strategies_dir.glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            strategies.append({
                'filename': file.name,
                'symbol': file.name.split('_')[0],
                'name': data.get('name', 'Unknown'),
                'signal_weights': data.get('signal_weights', {}),
                'backtest_performance': data.get('backtest_performance', {}),
                'metadata': data.get('metadata', {}),
                'modified': datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'size': file.stat().st_size,
                'path': str(file)
            })
        except Exception as e:
            print(f"Error loading {file}: {e}")
            continue
    
    # 按修改时间排序，最新的在前
    strategies.sort(key=lambda x: x['modified'], reverse=True)
    return strategies

def run_monitor_and_save(monitor_start_date="2025-04-01", output_file="monitor_results.json"):
    """运行monitor并保存完整结果"""
    print("🚀 Starting Strategy Monitor...")
    print(f"📅 Monitor Period: {monitor_start_date} to Today")
    
    # 初始化缓存管理器
    cache_manager = MonitorCache()
    
    # 检查API key
    has_api_key = bool(os.getenv('POLYGON_API_KEY'))
    if not has_api_key:
        print("⚠️  Warning: POLYGON_API_KEY not found, will use cached data only")
    
    # 加载策略
    strategies = load_strategies()
    if not strategies:
        print("❌ No strategies found. Please run optimization first.")
        return
    
    print(f"📊 Found {len(strategies)} strategy files")
    
    # 按标的分组，选择每个标的的最优策略
    symbol_best_strategies = {}
    for strategy in strategies:
        symbol = strategy['symbol']
        if symbol in symbol_best_strategies:
            existing_return = symbol_best_strategies[symbol].get('backtest_performance', {}).get('total_return', -999)
            current_return = strategy.get('backtest_performance', {}).get('total_return', -999)
            if current_return <= existing_return:
                continue
        symbol_best_strategies[symbol] = strategy
    
    print(f"🎯 Monitoring {len(symbol_best_strategies)} symbols: {list(symbol_best_strategies.keys())}")
    
    # 运行monitor并保存结果
    monitor_results = []
    
    for symbol, strategy in symbol_best_strategies.items():
        print(f"\n📈 Processing {symbol}...")
        try:
            # 加载策略配置
            with open(strategy['path'], 'r', encoding='utf-8') as f:
                strategy_config = json.load(f)
            
            params = strategy_config.get('params', {})
            signal_weights = strategy_config.get('signal_weights', {})
            
            # 运行完整回测
            print(f"  🔄 Running backtest from {monitor_start_date} to today...")
            backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
            
            end_date = datetime.now().strftime("%Y-%m-%d")
            result = backtest.run_backtest(
                symbol=symbol,
                start_date=monitor_start_date,
                end_date=end_date,
                strategy='auto',
                entry_signal=signal_weights,
                profit_target=params.get('profit_target', 5.0),
                stop_loss=params.get('stop_loss', -0.5),
                max_holding_days=params.get('max_holding_days', 30),
                position_size=params.get('position_size', 0.1)
            )
            
            # 计算指标
            final_value = result.equity_curve[-1] if len(result.equity_curve) > 0 else 10000
            total_return = (final_value - 10000) / 10000
            num_trades = len(result.trades)
            winning_trades = sum(1 for t in result.trades if t.pnl and t.pnl > 0)
            win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0
            
            # 保存到缓存
            # equity_curve 是一个 pandas Series，索引是日期
            equity_curve_data = []
            if isinstance(result.equity_curve.index, pd.DatetimeIndex):
                # 正确处理：直接从 DatetimeIndex 获取日期
                for date_idx, value in result.equity_curve.items():
                    date_str = date_idx.strftime('%Y-%m-%d')
                    equity_curve_data.append({'date': date_str, 'value': value})
                print(f"  📊 Converted {len(equity_curve_data)} equity curve points")
                print(f"     First: {equity_curve_data[0]['date']}")
                print(f"     Last:  {equity_curve_data[-1]['date']}")
            else:
                # 向后兼容：如果不是 DatetimeIndex
                for i, value in enumerate(result.equity_curve):
                    date = (datetime.strptime(monitor_start_date, '%Y-%m-%d') + timedelta(days=i)).strftime('%Y-%m-%d')
                    equity_curve_data.append({'date': date, 'value': value})
                print(f"  📊 Converted {len(equity_curve_data)} equity curve points (legacy mode)")
            
            # 更新缓存
            for data_point in equity_curve_data:
                cache_manager.update_equity_curve(symbol, data_point)
            
            # 保存指标到缓存
            cached_data = {
                'symbol': symbol,
                'strategy_name': strategy['name'],
                'total_return': total_return,
                'final_value': final_value,
                'num_trades': num_trades,
                'win_rate': win_rate,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            cache_manager.save_symbol_data(symbol, cached_data)
            
            # 准备结果数据
            monitor_result = {
                'symbol': symbol,
                'strategy_name': strategy['name'],
                'total_return': total_return,
                'final_value': final_value,
                'num_trades': num_trades,
                'win_rate': win_rate,
                'equity_curve': equity_curve_data,
                'trades': [  # 保存交易记录的基本信息
                    {
                        'entry_date': t.entry_date,
                        'exit_date': t.exit_date if t.exit_date else None,
                        'strategy': t.strategy,
                        'strike': t.strike,
                        'entry_price': t.entry_price,
                        'exit_price': t.exit_price if t.exit_price else None,
                        'pnl': t.pnl if t.pnl is not None else None,
                        'pnl_pct': t.pnl_pct if t.pnl_pct is not None else None,
                        'status': t.status
                    }
                    for t in result.trades
                ] if result.trades else [],
                'is_cached': True,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 验证保存的数据
            saved_equity_points = len(monitor_result['equity_curve'])
            saved_first_date = monitor_result['equity_curve'][0]['date'] if saved_equity_points > 0 else 'N/A'
            saved_last_date = monitor_result['equity_curve'][-1]['date'] if saved_equity_points > 0 else 'N/A'
            
            monitor_results.append(monitor_result)
            
            print(f"  ✅ {symbol}: Return={total_return:+.2%}, Trades={num_trades}, Win Rate={win_rate:.1f}%")
            print(f"     Saved equity_curve: {saved_equity_points} points ({saved_first_date} to {saved_last_date})")
            
        except Exception as e:
            print(f"  ❌ Error processing {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    # 按收益排序
    monitor_results.sort(key=lambda x: x['total_return'], reverse=True)
    
    # 保存到文件前验证数据
    print(f"\n🔍 Verifying data before saving:")
    for r in monitor_results:
        print(f"   {r['symbol']}: {len(r['equity_curve'])} equity points, {r['equity_curve'][0]['date']} to {r['equity_curve'][-1]['date']}")
    
    # 保存到文件
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'monitor_start_date': monitor_start_date,
            'results': monitor_results
        }, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Monitor results saved to {output_file}")
    
    # 验证保存后的文件
    print(f"\n🔍 Verifying saved file:")
    with open(output_path, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
        for r in saved_data['results']:
            last_date = r['equity_curve'][-1]['date'] if r['equity_curve'] else 'N/A'
            print(f"   {r['symbol']}: {len(r['equity_curve'])} points, last date = {last_date}")
    
    print(f"\n📊 Total symbols: {len(monitor_results)}")
    print(f"📈 Best performer: {monitor_results[0]['symbol']} ({monitor_results[0]['total_return']:+.2%})")
    
    return monitor_results

if __name__ == "__main__":
    import sys
    monitor_start_date = sys.argv[1] if len(sys.argv) > 1 else "2025-04-01"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "monitor_results.json"
    
    run_monitor_and_save(monitor_start_date, output_file)

