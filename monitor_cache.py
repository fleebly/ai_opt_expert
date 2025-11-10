#!/usr/bin/env python3
"""
Real-time Monitor 缓存管理模块

功能：
1. 持久化存储每个标的的最优策略收益曲线数据
2. 每天只更新一次新的数据点
3. 从缓存加载历史数据，避免重复扫描
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd


class MonitorCache:
    """监控数据缓存管理器"""
    
    def __init__(self, cache_dir: str = "monitor_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "monitor_data.json"
        self.last_update_file = self.cache_dir / "last_update.json"
    
    def load_cache(self) -> Dict:
        """加载缓存数据"""
        if not self.cache_file.exists():
            return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
            return {}
    
    def save_cache(self, data: Dict):
        """保存缓存数据"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def get_last_update_date(self, symbol: str) -> Optional[str]:
        """获取指定标的的最后更新日期"""
        if not self.last_update_file.exists():
            return None
        
        try:
            with open(self.last_update_file, 'r', encoding='utf-8') as f:
                last_updates = json.load(f)
                return last_updates.get(symbol)
        except Exception:
            return None
    
    def set_last_update_date(self, symbol: str, date: str):
        """设置指定标的的最后更新日期"""
        last_updates = {}
        if self.last_update_file.exists():
            try:
                with open(self.last_update_file, 'r', encoding='utf-8') as f:
                    last_updates = json.load(f)
            except Exception:
                pass
        
        last_updates[symbol] = date
        
        try:
            with open(self.last_update_file, 'w', encoding='utf-8') as f:
                json.dump(last_updates, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving last update date: {e}")
    
    def needs_update(self, symbol: str) -> bool:
        """检查是否需要更新（每天只更新一次）"""
        last_update = self.get_last_update_date(symbol)
        if last_update is None:
            return True
        
        try:
            last_date = datetime.strptime(last_update, '%Y-%m-%d').date()
            today = datetime.now().date()
            return today > last_date
        except Exception:
            return True
    
    def get_symbol_data(self, symbol: str) -> Optional[Dict]:
        """获取指定标的的缓存数据"""
        cache = self.load_cache()
        return cache.get(symbol)
    
    def save_symbol_data(self, symbol: str, data: Dict):
        """保存指定标的的数据"""
        cache = self.load_cache()
        cache[symbol] = data
        self.save_cache(cache)
        
        # 更新最后更新日期
        today = datetime.now().strftime('%Y-%m-%d')
        self.set_last_update_date(symbol, today)
    
    def update_equity_curve(self, symbol: str, new_data_point: Dict):
        """更新收益曲线：追加新的数据点"""
        existing_data = self.get_symbol_data(symbol)
        
        if existing_data is None:
            # 首次创建
            equity_curve = {
                'dates': [new_data_point['date']],
                'values': [new_data_point['value']]
            }
        else:
            # 追加新数据点
            equity_curve = existing_data.get('equity_curve', {'dates': [], 'values': []})
            
            # 检查是否已存在今天的日期
            today = new_data_point['date']
            if today not in equity_curve['dates']:
                equity_curve['dates'].append(today)
                equity_curve['values'].append(new_data_point['value'])
            else:
                # 更新今天的数据点
                idx = equity_curve['dates'].index(today)
                equity_curve['values'][idx] = new_data_point['value']
        
        # 更新数据
        if existing_data:
            existing_data['equity_curve'] = equity_curve
            existing_data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            existing_data = {
                'symbol': symbol,
                'equity_curve': equity_curve,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        self.save_symbol_data(symbol, existing_data)
    
    def get_equity_curve_series(self, symbol: str) -> Optional[pd.Series]:
        """获取收益曲线作为 pandas Series"""
        data = self.get_symbol_data(symbol)
        if data is None:
            return None
        
        equity_curve = data.get('equity_curve', {})
        dates = equity_curve.get('dates', [])
        values = equity_curve.get('values', [])
        
        if not dates or not values:
            return None
        
        try:
            dates_parsed = pd.to_datetime(dates)
            return pd.Series(values, index=dates_parsed)
        except Exception as e:
            print(f"Error parsing equity curve for {symbol}: {e}")
            return None
    
    def get_all_symbols(self) -> List[str]:
        """获取所有已缓存的标的列表"""
        cache = self.load_cache()
        return list(cache.keys())




