#!/usr/bin/env python3
"""
实时监控数据更新器
每15分钟从POLYGON获取最新数据，更新策略收益并写入结果文件
"""

import os
import json
import time
import schedule
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
                'path': str(file)
            })
        except Exception as e:
            print(f"Error loading {file}: {e}")
            continue
    
    strategies.sort(key=lambda x: x.get('modified', ''), reverse=True)
    return strategies

def update_monitor_data():
    """更新监控数据"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Starting real-time update...")
    
    # 检查API key
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        print("⚠️  POLYGON_API_KEY not found, skipping update")
        print("   Please set POLYGON_API_KEY environment variable")
        return
    
    # 检查API key格式（Polygon API key通常是字符串）
    if len(api_key) < 10:
        print("⚠️  POLYGON_API_KEY seems invalid (too short)")
        print("   Please check your API key configuration")
        return
    
    # 初始化缓存管理器
    cache_manager = MonitorCache()
    
    # 加载策略
    strategies = load_strategies()
    if not strategies:
        print("❌ No strategies found")
        return
    
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
    
    print(f"📊 Updating {len(symbol_best_strategies)} symbols: {list(symbol_best_strategies.keys())}")
    
    monitor_results = []
    monitor_start_date = "2025-04-01"  # 从配置或环境变量读取
    
    for symbol, strategy in symbol_best_strategies.items():
        try:
            print(f"  📈 Processing {symbol}...")
            
            # 加载策略配置
            with open(strategy['path'], 'r', encoding='utf-8') as f:
                strategy_config = json.load(f)
            
            params = strategy_config.get('params', {})
            signal_weights = strategy_config.get('signal_weights', {})
            
            # 获取最后更新日期
            last_update = cache_manager.get_last_update_date(symbol)
            if last_update:
                # 从最后更新日期+1天开始
                update_start_date = (datetime.strptime(last_update, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                # 首次运行，从监控开始日期
                update_start_date = monitor_start_date
            
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            # 如果开始日期大于结束日期，跳过
            if update_start_date > end_date:
                # 只更新今天的数据点
                update_start_date = end_date
            
            # 运行回测获取最新数据
            try:
                backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
                result = backtest.run_backtest(
                    symbol=symbol,
                    start_date=update_start_date,
                    end_date=end_date,
                    strategy='auto',
                    entry_signal=signal_weights,
                    profit_target=params.get('profit_target', 5.0),
                    stop_loss=params.get('stop_loss', -0.5),
                    max_holding_days=params.get('max_holding_days', 30),
                    position_size=params.get('position_size', 0.1)
                )
            except ValueError as e:
                print(f"  ❌ Error initializing backtest for {symbol}: {e}")
                print(f"     Please check POLYGON_API_KEY configuration")
                continue
            except Exception as e:
                print(f"  ❌ Error running backtest for {symbol}: {str(e)}")
                if "403" in str(e) or "Forbidden" in str(e):
                    print(f"     ⚠️  Polygon API 403 error detected")
                    print(f"     This usually means:")
                    print(f"     1. API key doesn't have access to option data (needs Starter+ plan)")
                    print(f"     2. API key is invalid or expired")
                    print(f"     3. API quota exceeded")
                    print(f"     → The system will use estimated option prices as fallback")
                continue
            
            # 更新收益曲线
            if len(result.equity_curve) > 0:
                # 优先从缓存读取完整的收益曲线，而不是重新运行完整回测
                # 这样可以避免因为 API 数据限制导致的数据回退
                cached_equity_series = cache_manager.get_equity_curve_series(symbol)
                
                if cached_equity_series is not None and len(cached_equity_series) > 0:
                    # 使用缓存中的数据作为基础，但需要运行完整回测来获取所有 trades
                    print(f"  📊 Using cached equity curve ({len(cached_equity_series)} points)")
                    print(f"     Running full backtest to get all trades...")
                    
                    # 运行完整回测以获取所有 trades
                    try:
                        full_backtest_result = backtest.run_backtest(
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
                        
                        # 使用缓存的 equity_curve，但使用完整回测的 trades
                        # 合并新的数据点到缓存的 equity_curve
                        new_equity_series = result.equity_curve
                        if isinstance(new_equity_series.index, pd.DatetimeIndex):
                            # 合并缓存数据和新数据
                            combined_series = pd.concat([cached_equity_series, new_equity_series])
                            combined_series = combined_series[~combined_series.index.duplicated(keep='last')]
                            combined_series = combined_series.sort_index()
                            
                            # 创建一个模拟的 full_result 对象，使用缓存的 equity_curve 和完整回测的 trades
                            class MockResult:
                                def __init__(self, equity_curve, trades):
                                    self.equity_curve = equity_curve
                                    self.trades = trades
                            
                            full_result = MockResult(combined_series, full_backtest_result.trades)
                        else:
                            # 如果新数据不是 DatetimeIndex，使用缓存数据
                            class MockResult:
                                def __init__(self, equity_curve, trades):
                                    self.equity_curve = equity_curve
                                    self.trades = trades
                            
                            full_result = MockResult(cached_equity_series, full_backtest_result.trades)
                    except Exception as e:
                        print(f"  ⚠️  Error running full backtest for trades: {str(e)}")
                        print(f"     Using cached equity curve and partial result")
                        # 如果完整回测失败，使用缓存数据和部分结果
                        new_equity_series = result.equity_curve
                        if isinstance(new_equity_series.index, pd.DatetimeIndex):
                            combined_series = pd.concat([cached_equity_series, new_equity_series])
                            combined_series = combined_series[~combined_series.index.duplicated(keep='last')]
                            combined_series = combined_series.sort_index()
                            
                            class MockResult:
                                def __init__(self, equity_curve, trades):
                                    self.equity_curve = equity_curve
                                    self.trades = trades
                            
                            full_result = MockResult(combined_series, result.trades if hasattr(result, 'trades') else [])
                        else:
                            class MockResult:
                                def __init__(self, equity_curve, trades):
                                    self.equity_curve = equity_curve
                                    self.trades = trades
                            
                            full_result = MockResult(cached_equity_series, result.trades if hasattr(result, 'trades') else [])
                else:
                    # 缓存中没有数据，运行完整回测
                    print(f"  📊 No cached data, running full backtest...")
                    try:
                        full_result = backtest.run_backtest(
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
                        
                        # 检查返回的数据是否只到 08-31（可能是 API 数据限制）
                        if isinstance(full_result.equity_curve.index, pd.DatetimeIndex):
                            last_date = full_result.equity_curve.index[-1].strftime('%Y-%m-%d')
                            if last_date <= '2025-08-31' and end_date > '2025-08-31':
                                print(f"  ⚠️  Warning: API returned data only to {last_date}, but requested end_date is {end_date}")
                                print(f"     This may indicate API data limitation. Using partial result instead.")
                                # 使用部分结果，不要覆盖可能已经更新的数据
                                full_result = result
                    except Exception as e:
                        print(f"  ⚠️  Error getting full equity curve for {symbol}: {str(e)}")
                        print(f"     Using partial result instead")
                        full_result = result
                
                # 更新缓存中的收益曲线
                # equity_curve 是一个 pandas Series，索引是日期
                if isinstance(full_result.equity_curve.index, pd.DatetimeIndex):
                    # Debug: 打印日期范围
                    first_date = full_result.equity_curve.index[0].strftime('%Y-%m-%d')
                    last_date = full_result.equity_curve.index[-1].strftime('%Y-%m-%d')
                    print(f"  📊 Equity curve date range: {first_date} to {last_date} ({len(full_result.equity_curve)} points)")
                    print(f"     Requested end_date: {end_date}")
                    
                    # 遍历 Series 的日期索引和值
                    for date_idx, value in full_result.equity_curve.items():
                        date_str = date_idx.strftime('%Y-%m-%d')
                        cache_manager.update_equity_curve(symbol, {
                            'date': date_str,
                            'value': value
                        })
                else:
                    # 如果不是 DatetimeIndex，使用旧的逻辑（向后兼容）
                    for i, value in enumerate(full_result.equity_curve):
                        date = (datetime.strptime(monitor_start_date, '%Y-%m-%d') + timedelta(days=i)).strftime('%Y-%m-%d')
                        cache_manager.update_equity_curve(symbol, {
                            'date': date,
                            'value': value
                        })
                
                # 计算指标
                final_value = full_result.equity_curve[-1]
                total_return = (final_value - 10000) / 10000
                num_trades = len(full_result.trades)
                winning_trades = sum(1 for t in full_result.trades if t.pnl and t.pnl > 0)
                win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0
                
                # 保存到缓存 - 保留已有的 equity_curve 数据
                existing_cached_data = cache_manager.get_symbol_data(symbol)
                cached_data = {
                    'symbol': symbol,
                    'strategy_name': strategy['name'],
                    'total_return': total_return,
                    'final_value': final_value,
                    'num_trades': num_trades,
                    'win_rate': win_rate,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                # 保留已有的 equity_curve 数据（如果存在）
                if existing_cached_data and 'equity_curve' in existing_cached_data:
                    cached_data['equity_curve'] = existing_cached_data['equity_curve']
                cache_manager.save_symbol_data(symbol, cached_data)
                
                # 准备结果数据 - 使用与缓存更新相同的逻辑，正确处理 DatetimeIndex
                equity_curve_data = []
                if isinstance(full_result.equity_curve.index, pd.DatetimeIndex):
                    # 遍历 Series 的日期索引和值，使用实际日期
                    for date_idx, value in full_result.equity_curve.items():
                        date_str = date_idx.strftime('%Y-%m-%d')
                        equity_curve_data.append({'date': date_str, 'value': value})
                else:
                    # 如果不是 DatetimeIndex，使用旧的逻辑（向后兼容）
                    for i, value in enumerate(full_result.equity_curve):
                        date = (datetime.strptime(monitor_start_date, '%Y-%m-%d') + timedelta(days=i)).strftime('%Y-%m-%d')
                        equity_curve_data.append({'date': date, 'value': value})
                
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
                        for t in full_result.trades
                    ] if full_result.trades else [],
                    'is_cached': True,
                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                monitor_results.append(monitor_result)
                print(f"  ✅ {symbol}: Return={total_return:+.2%}, Value=${final_value:,.0f}")
            else:
                print(f"  ⚠️  {symbol}: No equity curve data")
                print(f"     Possible reasons:")
                print(f"     1. No market data available for the date range")
                print(f"     2. Data fetching failed (check API key and network)")
                print(f"     3. No trading signals generated (strategy too strict)")
                print(f"     4. Date range is invalid or too short")
                print(f"     → Skipping this symbol, will retry on next update")
                
        except Exception as e:
            print(f"  ❌ Error processing {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    # 按收益排序
    monitor_results.sort(key=lambda x: x['total_return'], reverse=True)
    
    # 保存到文件
    output_file = Path("monitor_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'monitor_start_date': monitor_start_date,
            'results': monitor_results
        }, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Updated {len(monitor_results)} symbols, saved to monitor_results.json")
    return monitor_results

def run_scheduler():
    """运行定时任务调度器"""
    print("🚀 Starting real-time monitor updater...")
    print("📅 Schedule: Every 15 minutes")
    print("⏰ Next update will be in 15 minutes")
    
    # 立即运行一次
    update_monitor_data()
    
    # 每15分钟运行一次
    schedule.every(15).minutes.do(update_monitor_data)
    
    # 保持运行
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # 只运行一次，不启动调度器
        update_monitor_data()
    else:
        # 启动定时任务
        run_scheduler()

