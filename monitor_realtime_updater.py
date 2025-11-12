#!/usr/bin/env python3
"""
实时监控数据更新器
每天早上 6:00 从POLYGON获取最新数据，更新策略收益并写入结果文件
"""

import os
import sys
import json
import time
import signal
import schedule
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from backtest_engine import OptionBacktest
from monitor_cache import MonitorCache

def get_previous_trading_day(date_str: Optional[str] = None) -> str:
    """
    获取上一个交易日（排除周末）
    
    Args:
        date_str: 基准日期（YYYY-MM-DD），如果为 None 则使用今天
    
    Returns:
        上一个交易日的日期字符串（YYYY-MM-DD）
    """
    if date_str:
        base_date = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        base_date = datetime.now()
    
    # 向前查找，跳过周末（周六=5, 周日=6）
    previous_date = base_date - timedelta(days=1)
    
    # 如果前一天是周末，继续向前查找
    while previous_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
        previous_date -= timedelta(days=1)
    
    return previous_date.strftime('%Y-%m-%d')

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
            
            # 优先从 metadata 中获取 symbol，如果没有则从文件名提取
            symbol = data.get('metadata', {}).get('symbol')
            if not symbol:
                # 从文件名提取：BABA_ST.json -> BABA, BABA_ST_20251110_154656.json -> BABA
                symbol = file.name.split('_')[0]
            
            strategies.append({
                'filename': file.name,
                'symbol': symbol,
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
    
    # 按标的分组，根据 backtest_performance.total_return 选择前10个策略，然后从 2025-04-01 到最新日期回测
    print("🔍 Selecting top 10 strategies by backtest_performance.total_return, then backtesting from 2025-04-01 to latest date...")
    
    monitor_start_date = "2025-04-01"  # 从配置或环境变量读取
    # 使用上一个交易日，因为当前日期可能还没有实时数据
    end_date = get_previous_trading_day()
    print(f"📅 Using previous trading day as end date: {end_date}")
    
    # 按标的分组策略，使用 (name, filename) 作为唯一key去重
    strategies_by_symbol = {}
    strategy_keys = {}  # 存储 (symbol, name, filename) -> strategy 的映射，用于去重
    
    for strategy in strategies:
        symbol = strategy['symbol']
        if not symbol:
            continue
        
        # 使用 (name, filename) 作为唯一key
        strategy_key = (symbol, strategy['name'], strategy['filename'])
        if strategy_key in strategy_keys:
            # 如果已存在相同的key，跳过（保留第一个）
            continue
        
        strategy_keys[strategy_key] = strategy
        
        if symbol not in strategies_by_symbol:
            strategies_by_symbol[symbol] = []
        strategies_by_symbol[symbol].append(strategy)
    
    # 对每个标的，根据 backtest_performance.total_return 排序，取前10个
    # 然后从 2025-04-01 到最新日期进行回测，选择最优策略
    symbol_best_strategies = {}
    symbol_best_strategy_results = {}  # 存储最优策略的回测结果
    
    # 保存策略实际收益到缓存，供前端使用
    strategy_performance_cache = {}
    
    for symbol, symbol_strategies in strategies_by_symbol.items():
        print(f"\n  📊 Processing {symbol}...")
        
        # 根据 backtest_performance.total_return 排序，取前10个
        strategies_with_return = []
        for strategy in symbol_strategies:
            backtest_perf = strategy.get('backtest_performance', {})
            total_return = backtest_perf.get('total_return', -999)
            strategies_with_return.append((strategy, total_return))
        
        # 按 total_return 降序排序，取前10个
        strategies_with_return.sort(key=lambda x: x[1], reverse=True)
        top_strategies = [s[0] for s in strategies_with_return[:10]]
        
        print(f"  📈 Selected top {len(top_strategies)} strategies by backtest_performance.total_return:")
        for idx, strategy in enumerate(top_strategies, 1):
            backtest_perf = strategy.get('backtest_performance', {})
            total_return = backtest_perf.get('total_return', -999)
            print(f"    {idx}. {strategy['name']} ({strategy['filename']}): {total_return:+.2%}")
        
        # 对这10个策略，从 2025-04-01 到最新日期进行回测
        best_strategy = None
        best_return = -999
        best_strategy_name = None
        best_strategy_filename = None
        
        print(f"\n  🔄 Starting backtest evaluation for {len(top_strategies)} strategies...")
        
        for idx, strategy in enumerate(top_strategies, 1):
            try:
                # 加载策略配置
                with open(strategy['path'], 'r', encoding='utf-8') as f:
                    strategy_config = json.load(f)
                
                params = strategy_config.get('params', {})
                signal_weights = strategy_config.get('signal_weights', {})
                
                # 运行从 2025-04-01 到最新日期的回测
                strategy_key = f"{strategy['name']}_{strategy['filename']}"
                print(f"\n    [{idx}/{len(top_strategies)}] 🔄 Testing Strategy: '{strategy['name']}'")
                print(f"        📁 File: {strategy['filename']}")
                print(f"        📅 Period: {monitor_start_date} to {end_date}")
                print(f"        ⚙️  Params: profit_target={params.get('profit_target', 5.0)}%, stop_loss={params.get('stop_loss', -0.5)}%, max_holding={params.get('max_holding_days', 30)}d")
                if signal_weights:
                    signals_str = ", ".join([f"{k}={v:.2f}" for k, v in list(signal_weights.items())[:3]])
                    if len(signal_weights) > 3:
                        signals_str += f", ... (+{len(signal_weights)-3} more)"
                    print(f"        📊 Signals: {signals_str}")
                
                # 运行回测
                backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
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
                
                # 计算实际收益
                if len(result.equity_curve) > 0:
                    final_value = result.equity_curve[-1]
                    actual_return = (final_value - 10000) / 10000
                    strategy_evaluation_result = result
                else:
                    actual_return = -999  # 没有数据
                    strategy_evaluation_result = None
                
                # 保存到缓存（使用策略名和文件名作为key）
                if symbol not in strategy_performance_cache:
                    strategy_performance_cache[symbol] = {}
                cache_key = f"{strategy['name']}_{strategy['filename']}"
                strategy_performance_cache[symbol][cache_key] = {
                    'actual_return': actual_return,
                    'evaluation_period': f"{monitor_start_date} to {end_date}",
                    'evaluated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'strategy_name': strategy['name'],
                    'filename': strategy['filename']
                }
                
                print(f"        ✅ Completed: Actual return = {actual_return:+.2%} | Final value = ${final_value:,.2f} | Trades = {len(result.trades)}")
                
                # 选择收益最大的策略
                if actual_return > best_return:
                    best_return = actual_return
                    best_strategy = strategy
                    best_strategy_name = strategy['name']
                    best_strategy_filename = strategy['filename']
                    # 保存最优策略的回测结果
                    best_strategy_result = strategy_evaluation_result
                    print(f"        🏆 New best strategy! (Previous best: {best_return:+.2%})")
                    
            except Exception as e:
                print(f"        ❌ Error evaluating '{strategy['name']}' ({strategy['filename']}): {str(e)}")
                import traceback
                print(f"        📋 Traceback: {traceback.format_exc().split(chr(10))[-3] if traceback.format_exc() else 'N/A'}")
                continue
        
        if best_strategy:
            symbol_best_strategies[symbol] = best_strategy
            # 保存最优策略的回测结果和收益，供后续使用
            if 'best_strategy_result' in locals() and best_strategy_result is not None:
                symbol_best_strategy_results[symbol] = {
                    'result': best_strategy_result,
                    'return': best_return
                }
            print(f"  ✅ {symbol}: Selected '{best_strategy_name}' ({best_strategy_filename}) (actual return: {best_return:+.2%})")
        else:
            print(f"  ⚠️  {symbol}: No valid strategy found")
    
    print(f"\n📊 Updating {len(symbol_best_strategies)} symbols: {list(symbol_best_strategies.keys())}")
    
    # 保存策略性能评估结果到文件，供前端使用
    strategy_perf_file = Path("strategy_performance_cache.json")
    try:
        with open(strategy_perf_file, 'w', encoding='utf-8') as f:
            json.dump({
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'strategy_performance': strategy_performance_cache
            }, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved strategy performance evaluation to {strategy_perf_file}")
    except Exception as e:
        print(f"⚠️  Failed to save strategy performance cache: {e}")
    
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
            
            # 使用上一个交易日作为结束日期（因为当前日期可能还没有实时数据）
            end_date = get_previous_trading_day()
            
            # 如果开始日期大于结束日期，说明已经是最新数据，跳过
            if update_start_date > end_date:
                print(f"  ⏭️  {symbol}: Already up to date (last update: {last_update}, previous trading day: {end_date})")
                # 从缓存加载数据
                cached_data = cache_manager.get_symbol_data(symbol)
                equity_curve_series = cache_manager.get_equity_curve_series(symbol)
                if cached_data and equity_curve_series is not None:
                    # 将 Series 转换为列表格式，确保 JSON 序列化正确
                    # 只保留到上一个交易日的数据，如果最后一个交易日缺失，用前一个交易日的数据填充
                    equity_curve_data = []
                    prev_trading_day = get_previous_trading_day()
                    prev_trading_day_dt = datetime.strptime(prev_trading_day, '%Y-%m-%d')
                    
                    if isinstance(equity_curve_series.index, pd.DatetimeIndex):
                        for date_idx, value in equity_curve_series.items():
                            date_str = date_idx.strftime('%Y-%m-%d')
                            date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                            # 只保留到上一个交易日的数据
                            if date_dt <= prev_trading_day_dt:
                                equity_curve_data.append({'date': date_str, 'value': float(value)})
                    else:
                        # 如果不是 DatetimeIndex，使用索引作为日期
                        for i, value in enumerate(equity_curve_series):
                            date_str = equity_curve_series.index[i] if hasattr(equity_curve_series.index[i], 'strftime') else str(equity_curve_series.index[i])
                            try:
                                date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                                if date_dt <= prev_trading_day_dt:
                                    equity_curve_data.append({'date': date_str, 'value': float(value)})
                            except:
                                # 如果日期解析失败，跳过
                                continue
                    
                    # 检查最后一个日期是否是上一个交易日，如果不是，用最后一个有效值填充
                    # 但是，如果缓存中已经存在该日期的值，且该值不是初始值（10000），则使用缓存中的值
                    if len(equity_curve_data) > 0:
                        last_date_str = equity_curve_data[-1]['date']
                        last_date_dt = datetime.strptime(last_date_str, '%Y-%m-%d')
                        if last_date_dt < prev_trading_day_dt:
                            # 检查缓存中是否已经有该日期的值
                            prev_trading_day_dt_obj = datetime.strptime(prev_trading_day, '%Y-%m-%d')
                            should_pad = True
                            if isinstance(equity_curve_series.index, pd.DatetimeIndex):
                                if prev_trading_day_dt_obj in equity_curve_series.index:
                                    cached_value = equity_curve_series[prev_trading_day_dt_obj]
                                    # 如果缓存中的值不是初始值（10000），说明已经有正确的数据，使用缓存中的值
                                    if abs(cached_value - 10000.0) > 0.01:
                                        should_pad = False
                                        # 使用缓存中的值，而不是 padding
                                        equity_curve_data.append({'date': prev_trading_day, 'value': float(cached_value)})
                                        print(f"  ⚠️  Using cached value for {prev_trading_day}: ${cached_value:.2f} (not initial capital)")
                            
                            if should_pad:
                                # 用最后一个有效值填充上一个交易日
                                last_value = equity_curve_data[-1]['value']
                                equity_curve_data.append({'date': prev_trading_day, 'value': float(last_value)})
                                print(f"  📅 Padding {prev_trading_day} with previous value: ${last_value:.2f}")
                    
                    # 使用最后一个值作为 final_value（应该是上一个交易日），确保正确计算 total_return
                    final_value = float(equity_curve_data[-1]['value']) if len(equity_curve_data) > 0 else 10000.0
                    total_return = (final_value - 10000) / 10000
                    
                    # 如果策略选择阶段已经运行了从 monitor_start_date 到 end_date 的回测，
                    # 则直接使用策略选择阶段的回测结果，避免重复运行
                    use_evaluation_result = False
                    if symbol in symbol_best_strategy_results:
                        # 策略选择阶段已经运行了从 monitor_start_date 到 end_date 的回测
                        use_evaluation_result = True
                        eval_data = symbol_best_strategy_results[symbol]
                        eval_return = eval_data.get('return', 0)
                        print(f"  ✅ Using strategy evaluation result (from {monitor_start_date} to {end_date})")
                        print(f"     This ensures consistency with strategy selection ({eval_return:+.2%})")
                    
                    try:
                        if use_evaluation_result:
                            # 使用策略选择阶段的回测结果
                            eval_data = symbol_best_strategy_results[symbol]
                            full_backtest_result = eval_data['result']
                        else:
                            # 运行完整回测来获取所有 trades
                            # 但是，不要用完整回测的 equity_curve 更新缓存，因为缓存中可能已经有更新的数据
                            print(f"  📊 Data is up to date, running full backtest to get all trades...")
                            print(f"  ⚠️  Note: Will NOT update cache equity_curve (using cached data to preserve latest values)")
                            backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
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
                        
                        # 序列化 trades
                        trades_data = [
                            {
                                'entry_date': t.entry_date,
                                'exit_date': t.exit_date if t.exit_date else None,
                                'strategy': t.strategy,
                                'strike': t.strike,
                                'entry_price': t.entry_price,
                                'exit_price': t.exit_price if t.exit_price else None,
                                'pnl': t.pnl if t.pnl is not None else None,
                                'pnl_pct': t.pnl_pct if t.pnl_pct is not None else None,
                                'status': t.status,
                                'expiry': t.expiry if hasattr(t, 'expiry') else None,
                                'symbol': t.symbol if hasattr(t, 'symbol') else symbol
                            }
                            for t in full_backtest_result.trades
                        ] if full_backtest_result.trades else []
                        
                        num_trades = len(full_backtest_result.trades)
                        winning_trades = sum(1 for t in full_backtest_result.trades if t.pnl and t.pnl > 0)
                        win_rate = (winning_trades / num_trades * 100) if num_trades > 0 else 0
                        
                        # 使用完整回测的结果计算 final_value 和 total_return，确保与策略选择时的实际收益一致
                        if len(full_backtest_result.equity_curve) > 0:
                            # 使用完整回测的 equity_curve 计算 final_value
                            final_value_from_backtest = float(full_backtest_result.equity_curve.iloc[-1])
                            total_return_from_backtest = (final_value_from_backtest - 10000) / 10000
                            
                            # 将完整回测的 equity_curve 转换为列表格式
                            equity_curve_from_backtest = []
                            if isinstance(full_backtest_result.equity_curve, pd.Series):
                                for date_idx, value in full_backtest_result.equity_curve.items():
                                    date_str = date_idx.strftime('%Y-%m-%d')
                                    equity_curve_from_backtest.append({'date': date_str, 'value': float(value)})
                            else:
                                equity_curve_from_backtest = equity_curve_data  # 回退到缓存数据
                            
                            # 使用完整回测的结果
                            final_value = final_value_from_backtest
                            total_return = total_return_from_backtest
                            equity_curve_data = equity_curve_from_backtest
                            
                            print(f"  ✅ {symbol}: Using full backtest results (Return={total_return:+.2%}, Final Value=${final_value:,.2f})")
                            print(f"     Note: Using backtest equity_curve for consistency with strategy selection")
                        else:
                            # 如果完整回测没有数据，使用缓存数据
                            print(f"  ⚠️  Full backtest has no equity curve, using cached data")
                            print(f"     Final value from cache: ${final_value:,.2f}")
                        
                        monitor_result = {
                            'symbol': symbol,
                            'strategy_name': strategy['name'],
                            'total_return': total_return,  # 使用完整回测的结果
                            'final_value': final_value,  # 使用完整回测的结果
                            'num_trades': num_trades,
                            'win_rate': win_rate,
                            'equity_curve': equity_curve_data,  # 使用完整回测的 equity_curve
                            'trades': trades_data,  # 从完整回测获取所有 trades
                            'is_cached': False,  # 标记为使用回测结果，不是缓存
                            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        print(f"  ✅ {symbol}: Got {num_trades} trades from full backtest")
                    except Exception as e:
                        print(f"  ⚠️  Error running full backtest for trades: {str(e)}")
                        print(f"     Using cached data without trades")
                        # 如果完整回测失败，使用缓存数据但不包含 trades
                        monitor_result = {
                            'symbol': symbol,
                            'strategy_name': strategy['name'],
                            'total_return': total_return,
                            'final_value': final_value,
                            'num_trades': cached_data.get('num_trades', 0),
                            'win_rate': cached_data.get('win_rate', 0),
                            'equity_curve': equity_curve_data,
                            'trades': [],  # 无法获取 trades
                            'is_cached': True,
                            'last_updated': cached_data.get('last_updated', 'N/A')
                        }
                    
                    monitor_results.append(monitor_result)
                    print(f"  ✅ {symbol}: Using cached data (Return={total_return:+.2%}, Final Value=${final_value:,.2f})")
                continue
            
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
                        if isinstance(new_equity_series.index, pd.DatetimeIndex) and isinstance(cached_equity_series.index, pd.DatetimeIndex):
                            # 合并缓存数据和新数据，确保新数据覆盖旧数据（如果有重复日期）
                            combined_series = pd.concat([cached_equity_series, new_equity_series])
                            # 去除重复索引，保留最后一个（新数据优先）
                            combined_series = combined_series[~combined_series.index.duplicated(keep='last')]
                            combined_series = combined_series.sort_index()
                            
                            # 调试：打印合并后的最后几个值
                            if len(combined_series) > 0:
                                last_few = combined_series.tail(3)
                                print(f"     Combined series last 3 values:")
                                for date, val in last_few.items():
                                    print(f"       {date.strftime('%Y-%m-%d')}: ${val:.2f}")
                            
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
                # 只更新到上一个交易日的数据
                prev_trading_day = get_previous_trading_day()
                prev_trading_day_dt = datetime.strptime(prev_trading_day, '%Y-%m-%d')
                
                if isinstance(full_result.equity_curve.index, pd.DatetimeIndex):
                    # Debug: 打印日期范围
                    first_date = full_result.equity_curve.index[0].strftime('%Y-%m-%d')
                    last_date = full_result.equity_curve.index[-1].strftime('%Y-%m-%d')
                    print(f"  📊 Equity curve date range: {first_date} to {last_date} ({len(full_result.equity_curve)} points)")
                    print(f"     Requested end_date: {end_date} (previous trading day: {prev_trading_day})")
                    
                    # 遍历 Series 的日期索引和值，只更新到上一个交易日
                    # 但是，如果缓存中已经存在该日期的值，且该值不是初始值（10000），则不要覆盖
                    last_valid_value = None
                    last_valid_date = None
                    cached_equity_series_check = cache_manager.get_equity_curve_series(symbol)
                    
                    for date_idx, value in full_result.equity_curve.items():
                        date_str = date_idx.strftime('%Y-%m-%d')
                        date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                        
                        # 只更新到上一个交易日的数据
                        if date_dt <= prev_trading_day_dt:
                            # 检查缓存中是否已经有该日期的值，且该值不是初始值（10000）
                            should_update = True
                            if cached_equity_series_check is not None and isinstance(cached_equity_series_check.index, pd.DatetimeIndex):
                                if date_dt in cached_equity_series_check.index:
                                    cached_value = cached_equity_series_check[date_dt]
                                    # 如果缓存中的值不是初始值（10000），且新值也是初始值，说明可能是数据不足，不要覆盖
                                    if abs(cached_value - 10000.0) > 0.01 and abs(value - 10000.0) < 0.01:
                                        should_update = False
                                        print(f"  ⚠️  Skipping update for {date_str}: cache has ${cached_value:.2f}, backtest returned ${value:.2f} (likely data issue)")
                            
                            if should_update:
                                cache_manager.update_equity_curve(symbol, {
                                    'date': date_str,
                                    'value': value
                                })
                                last_valid_value = value
                                last_valid_date = date_str
                            else:
                                # 即使不更新，也要记录最后一个有效值（使用缓存中的值）
                                if cached_equity_series_check is not None and isinstance(cached_equity_series_check.index, pd.DatetimeIndex):
                                    if date_dt in cached_equity_series_check.index:
                                        last_valid_value = cached_equity_series_check[date_dt]
                                        last_valid_date = date_str
                    
                    # 如果最后一个有效日期不是上一个交易日，用最后一个有效值填充
                    # 但是，如果缓存中已经存在该日期的值，且该值不是初始值（10000），则不要覆盖
                    if last_valid_date and last_valid_date < prev_trading_day:
                        # 检查缓存中是否已经有该日期的值
                        cached_equity_series = cache_manager.get_equity_curve_series(symbol)
                        should_pad = True
                        if cached_equity_series is not None and isinstance(cached_equity_series.index, pd.DatetimeIndex):
                            prev_trading_day_dt_obj = datetime.strptime(prev_trading_day, '%Y-%m-%d')
                            if prev_trading_day_dt_obj in cached_equity_series.index:
                                cached_value = cached_equity_series[prev_trading_day_dt_obj]
                                # 如果缓存中的值不是初始值（10000），说明已经有正确的数据，不要覆盖
                                if abs(cached_value - 10000.0) > 0.01:
                                    should_pad = False
                                    print(f"  ⚠️  Skipping padding for {prev_trading_day}: cache already has value ${cached_value:.2f} (not initial capital)")
                        
                        if should_pad:
                            cache_manager.update_equity_curve(symbol, {
                                'date': prev_trading_day,
                                'value': last_valid_value
                            })
                            print(f"  📅 Padding {prev_trading_day} with {last_valid_date} value: ${last_valid_value:.2f}")
                else:
                    # 如果不是 DatetimeIndex，使用旧的逻辑（向后兼容）
                    for i, value in enumerate(full_result.equity_curve):
                        date = (datetime.strptime(monitor_start_date, '%Y-%m-%d') + timedelta(days=i)).strftime('%Y-%m-%d')
                        cache_manager.update_equity_curve(symbol, {
                            'date': date,
                            'value': value
                        })
                
                # 计算指标（将在后面基于 equity_curve_data 重新计算）
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
                # 确保 equity_curve 是列表格式，而不是 Series，以便 JSON 序列化
                # 只保留到上一个交易日的数据，如果最后一个交易日缺失，用前一个交易日的数据填充
                equity_curve_data = []
                prev_trading_day = get_previous_trading_day()
                prev_trading_day_dt = datetime.strptime(prev_trading_day, '%Y-%m-%d')
                
                if isinstance(full_result.equity_curve.index, pd.DatetimeIndex):
                    # 遍历 Series 的日期索引和值，使用实际日期
                    # 过滤掉超过上一个交易日的日期
                    for date_idx, value in full_result.equity_curve.items():
                        date_str = date_idx.strftime('%Y-%m-%d')
                        date_dt = datetime.strptime(date_str, '%Y-%m-%d')
                        
                        # 只保留到上一个交易日的数据
                        if date_dt <= prev_trading_day_dt:
                            equity_curve_data.append({'date': date_str, 'value': float(value)})
                    
                    # 检查最后一个日期是否是上一个交易日，如果不是，用最后一个有效值填充
                    # 但是，如果缓存中已经存在该日期的值，且该值不是初始值（10000），则使用缓存中的值
                    if len(equity_curve_data) > 0:
                        last_date_str = equity_curve_data[-1]['date']
                        last_date_dt = datetime.strptime(last_date_str, '%Y-%m-%d')
                        if last_date_dt < prev_trading_day_dt:
                            # 检查缓存中是否已经有该日期的值
                            prev_trading_day_dt_obj = datetime.strptime(prev_trading_day, '%Y-%m-%d')
                            should_pad = True
                            cached_equity_series_for_padding = cache_manager.get_equity_curve_series(symbol)
                            if cached_equity_series_for_padding is not None and isinstance(cached_equity_series_for_padding.index, pd.DatetimeIndex):
                                if prev_trading_day_dt_obj in cached_equity_series_for_padding.index:
                                    cached_value = cached_equity_series_for_padding[prev_trading_day_dt_obj]
                                    # 如果缓存中的值不是初始值（10000），说明已经有正确的数据，使用缓存中的值
                                    if abs(cached_value - 10000.0) > 0.01:
                                        should_pad = False
                                        # 使用缓存中的值，而不是 padding
                                        equity_curve_data.append({'date': prev_trading_day, 'value': float(cached_value)})
                                        print(f"  ⚠️  Using cached value for {prev_trading_day}: ${cached_value:.2f} (not initial capital)")
                            
                            if should_pad:
                                # 用最后一个有效值填充上一个交易日
                                last_value = equity_curve_data[-1]['value']
                                equity_curve_data.append({'date': prev_trading_day, 'value': float(last_value)})
                                print(f"  📅 Padding {prev_trading_day} with previous value: ${last_value:.2f}")
                else:
                    # 如果不是 DatetimeIndex，使用旧的逻辑（向后兼容）
                    for i, value in enumerate(full_result.equity_curve):
                        date = (datetime.strptime(monitor_start_date, '%Y-%m-%d') + timedelta(days=i)).strftime('%Y-%m-%d')
                        date_dt = datetime.strptime(date, '%Y-%m-%d')
                        if date_dt <= prev_trading_day_dt:
                            equity_curve_data.append({'date': date, 'value': float(value)})
                    
                    # 同样检查并填充
                    if len(equity_curve_data) > 0:
                        last_date_str = equity_curve_data[-1]['date']
                        last_date_dt = datetime.strptime(last_date_str, '%Y-%m-%d')
                        if last_date_dt < prev_trading_day_dt:
                            # 检查缓存中是否已经有该日期的值
                            prev_trading_day_dt_obj = datetime.strptime(prev_trading_day, '%Y-%m-%d')
                            should_pad = True
                            cached_equity_series_for_padding = cache_manager.get_equity_curve_series(symbol)
                            if cached_equity_series_for_padding is not None and isinstance(cached_equity_series_for_padding.index, pd.DatetimeIndex):
                                if prev_trading_day_dt_obj in cached_equity_series_for_padding.index:
                                    cached_value = cached_equity_series_for_padding[prev_trading_day_dt_obj]
                                    # 如果缓存中的值不是初始值（10000），说明已经有正确的数据，使用缓存中的值
                                    if abs(cached_value - 10000.0) > 0.01:
                                        should_pad = False
                                        # 使用缓存中的值，而不是 padding
                                        equity_curve_data.append({'date': prev_trading_day, 'value': float(cached_value)})
                                        print(f"  ⚠️  Using cached value for {prev_trading_day}: ${cached_value:.2f} (not initial capital)")
                            
                            if should_pad:
                                last_value = equity_curve_data[-1]['value']
                                equity_curve_data.append({'date': prev_trading_day, 'value': float(last_value)})
                                print(f"  📅 Padding {prev_trading_day} with previous value: ${last_value:.2f}")
                
                # 确保 final_value 和 total_return 基于实际的最后一个值（应该是上一个交易日）
                if len(equity_curve_data) > 0:
                    final_value = equity_curve_data[-1]['value']
                    total_return = (final_value - 10000) / 10000
                else:
                    final_value = 10000.0
                    total_return = 0.0
                
                monitor_result = {
                    'symbol': symbol,
                    'strategy_name': strategy['name'],
                    'total_return': total_return,  # 基于 equity_curve_data 计算
                    'final_value': final_value,  # 基于 equity_curve_data 计算
                    'num_trades': num_trades,
                    'win_rate': win_rate,
                    'equity_curve': equity_curve_data,  # 确保是列表格式
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
                            'status': t.status,
                            'expiry': t.expiry if hasattr(t, 'expiry') else None,
                            'symbol': t.symbol if hasattr(t, 'symbol') else symbol
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
    # 设置信号处理，以便优雅退出
    def signal_handler(sig, frame):
        print("\n🛑 Received shutdown signal, stopping scheduler...")
        print("✅ Scheduler stopped gracefully")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 Starting real-time monitor updater...")
    print("📅 Schedule: Daily at 06:00 (6:00 AM)")
    print(f"🆔 Process ID: {os.getpid()}")
    print(f"📂 Working directory: {os.getcwd()}")
    print(f"🔑 POLYGON_API_KEY: {'✅ Set' if os.getenv('POLYGON_API_KEY') else '❌ Not set'}")
    
    # 每天早上 6 点运行
    schedule.every().day.at("06:00").do(update_monitor_data)
    
    # 计算到下次运行的时间
    from datetime import time as dt_time
    now = datetime.now()
    next_run = datetime.combine(now.date(), dt_time(6, 0))
    if next_run <= now:
        # 如果今天 6 点已过，则设置为明天 6 点
        next_run += timedelta(days=1)
    time_until_next = (next_run - now).total_seconds() / 3600  # 转换为小时
    print(f"⏰ Next update will be at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏳ Time until next update: {time_until_next:.1f} hours")
    
    # 保持运行
    last_check = datetime.now()
    check_interval = 60  # 每分钟检查一次
    print(f"🔄 Scheduler loop started, checking every {check_interval} seconds...")
    
    try:
        while True:
            schedule.run_pending()
            
            # 每 5 分钟输出一次心跳日志，确认调度器还在运行
            current_time = datetime.now()
            if (current_time - last_check).total_seconds() >= 300:  # 5 分钟
                print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 💓 Scheduler heartbeat - still running, next update at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                last_check = current_time
            
            time.sleep(check_interval)  # 每分钟检查一次
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt received, stopping scheduler...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error in scheduler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # 只运行一次，不启动调度器
        update_monitor_data()
    else:
        # 启动定时任务
        run_scheduler()

