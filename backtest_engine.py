#!/usr/bin/env python3
"""
期权回测引擎

基于 Polygon 历史数据
支持 Long Call/Put 策略
跟踪收益和风险
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging# pyright: ignore[reportUnusedImport]
from dataclasses import dataclass, field
import requests
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """交易记录"""
    entry_date: str
    symbol: str
    strategy: str  # 'long_call' or 'long_put'
    strike: float
    entry_price: float  # 买入期权的价格
    shares: int  # 期权合约数量
    expiry: str
    
    # 平仓信息
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    status: str = 'open'  # 'open', 'closed', 'expired'
    
    # 标的价格
    entry_underlying: float = 0.0
    exit_underlying: Optional[float] = None


@dataclass
class BacktestResult:
    """回测结果"""
    trades: List[Trade] = field(default_factory=list)
    initial_capital: float = 10000.0
    final_capital: float = 10000.0
    total_pnl: float = 0.0
    total_return: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    num_trades: int = 0
    
    # 日度收益
    daily_returns: pd.Series = field(default_factory=lambda: pd.Series())
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series())


class OptionBacktest:
    """
    期权回测引擎
    
    特点：
    - 基于 Polygon 历史数据
    - 支持 Long Call/Put（做多）
    - 🆕 优先使用真实期权价格，回退到估算
    - 跟踪每日盈亏
    - 显示入场/离场股价
    """
    
    def __init__(self, initial_capital: float = 10000.0, use_real_prices: bool = True):
        """初始化"""
        self.api_key = os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY not set")
        
        self.base_url = "https://api.polygon.io"
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.use_real_prices = True  # 是否使用真实期权价格
        
        # 价格缓存（避免重复API调用）
        self.option_price_cache = {}
        
        logger.info(f"Backtest initialized with ${initial_capital:,.0f}")
        logger.info(f"Real option prices: {'✅ Enabled' if use_real_prices else '❌ Disabled (using estimates)'}")
    
    def run_backtest(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        strategy: str = 'auto',  # 'long_call', 'long_put', or 'auto' (动态选择)
        entry_signal: str = 'bb_compression',  # 入场信号
        exit_strategy: str = 'profit_target',  # 'profit_target', 'time_decay', 'stop_loss'
        profit_target: float = 0.5,  # 50% 利润目标
        stop_loss: float = -0.8,  # -30% 止损
        max_holding_days: int = 30,  # 最大持有天数
        position_size: float = 0.1  # 每次仓位 10%
    ) -> BacktestResult:
        """
        运行回测
        
        Args:
            symbol: 标的代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期
            strategy: 'long_call', 'long_put', or 'auto' (根据市场信号动态选择)
            entry_signal: 入场信号类型
            exit_strategy: 出场策略
            profit_target: 盈利目标 (%)
            stop_loss: 止损 (%)
            max_holding_days: 最大持有天数
            position_size: 仓位比例
        
        Returns:
            BacktestResult
        """
        logger.info(f"Running backtest: {symbol} from {start_date} to {end_date}")
        logger.info(f"Strategy: {strategy}, Position size: {position_size:.1%}")
        
        # Reset current capital to initial capital for each backtest run
        # This ensures each strategy starts with the same initial capital
        self.current_capital = self.initial_capital
        
        # 验证股票代码
        corrected_symbol, suggestion = self._validate_symbol(symbol)
        if suggestion:
            logger.warning(suggestion)
            symbol = corrected_symbol
        
        # 1. 获取历史数据
        data = self._fetch_historical_data(symbol, start_date, end_date)
        if data is None or len(data) < 20:
            logger.error(f"Insufficient data for backtest: {symbol} from {start_date} to {end_date}")
            logger.error("   Possible reasons:")
            logger.error("   1. No market data available for the date range")
            logger.error("   2. Data fetching failed (check API key and network)")
            logger.error("   3. Date range is invalid or too short")
            logger.error("   4. Symbol may be delisted or not available")
            # 提供拼写建议
            if suggestion:
                logger.error(f"   5. ⚠️  Symbol typo detected and corrected: '{symbol}' -> '{corrected_symbol}'")
            elif len(symbol) == 4 or len(symbol) == 5:
                # 提供常见股票代码建议
                common_symbols = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'BABA', 'PLTR']
                logger.error(f"   5. 💡 Common symbols: {', '.join(common_symbols)}")
            # 返回一个包含基础权益曲线的结果，而不是完全空的结果
            eq_df = pd.DataFrame([{'date': pd.to_datetime(start_date), 'equity': self.initial_capital}])
            eq_df.set_index('date', inplace=True)
            return BacktestResult(
                trades=[],
                initial_capital=self.initial_capital,
                final_capital=self.initial_capital,
                total_pnl=0.0,
                total_return=0.0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                num_trades=0,
                daily_returns=pd.Series(dtype='float64'),
                equity_curve=eq_df['equity'] if 'equity' in eq_df.columns else pd.Series(dtype='float64')
            )
        
        # 2. 计算技术指标
        data = self._calculate_indicators(data)
        
        # 2.5. 如果使用组合信号，计算完整指标
        if isinstance(entry_signal, dict):
            try:
                from signal_optimization.signal_library import SignalLibrary
                data = SignalLibrary.calculate_all_indicators(data)
                logger.debug("✅ 使用 SignalLibrary 计算完整指标")
            except ImportError as e:
                logger.error(f"无法导入 SignalLibrary: {e}")
                return BacktestResult()
        
        # 3. 生成交易信号
        trades = []
        open_trade = None
        equity_curve = []
        
        for i, (date, row) in enumerate(data.iterrows()):
            current_date = date.strftime('%Y-%m-%d')
            current_price = row['close']
            
            # 更新资产净值
            if open_trade:
                # 估算当前期权价值
                current_option_value = self._estimate_option_value(
                    current_price,
                    open_trade.strike,
                    open_trade.strategy,
                    (datetime.strptime(open_trade.expiry, '%Y-%m-%d') - date).days
                )
                
                unrealized_pnl = (current_option_value - open_trade.entry_price) * open_trade.shares * 100
                equity = self.current_capital + unrealized_pnl
            else:
                equity = self.current_capital
            
            equity_curve.append({'date': current_date, 'equity': equity})
            
            # 检查出场条件
            if open_trade:
                should_exit, exit_reason = self._check_exit_conditions(
                    open_trade, current_date, current_price, row,
                    profit_target, stop_loss, max_holding_days
                )
                
                if should_exit:
                    # 平仓
                    exit_price = self._estimate_option_value(
                        current_price,
                        open_trade.strike,
                        open_trade.strategy,
                        (datetime.strptime(open_trade.expiry, '%Y-%m-%d') - date).days
                    )
                    
                    pnl = (exit_price - open_trade.entry_price) * open_trade.shares * 100
                    pnl_pct = pnl / (open_trade.entry_price * open_trade.shares * 100)
                    
                    open_trade.exit_date = current_date
                    open_trade.exit_price = exit_price
                    open_trade.exit_underlying = current_price
                    open_trade.pnl = pnl
                    open_trade.pnl_pct = pnl_pct
                    open_trade.status = 'closed'
                    
                    self.current_capital += pnl
                    trades.append(open_trade)
                    
                    logger.info(f"Exit {exit_reason}: {current_date} | PnL: ${pnl:.2f} ({pnl_pct:.1%})")
                    open_trade = None
            
            # 检查入场条件
            if not open_trade and i >= 20:  # 需要足够的历史数据
                # 如果是组合信号，传递额外参数
                if isinstance(entry_signal, dict):
                    should_enter = self._check_entry_signal(row, entry_signal, data, i)
                else:
                    should_enter = self._check_entry_signal(row, entry_signal)
                
                if should_enter:
                    # 计算仓位
                    position_value = self.current_capital * position_size
                    
                    # 动态选择策略方向（如果设置为 'auto'）
                    current_strategy = strategy
                    direction_confidence = 1.0
                    
                    if strategy == 'auto':
                        try:
                            from strategy_selector import StrategyDirectionSelector
                            
                            # 根据市场信号选择方向
                            current_strategy, direction_confidence = StrategyDirectionSelector.select_direction(
                                data, i, entry_signal if isinstance(entry_signal, dict) else None
                            )
                            
                            explanation = StrategyDirectionSelector.explain_direction(
                                data, i, current_strategy, direction_confidence
                            )
                            logger.debug(f"Auto Direction: {explanation}")
                            
                        except Exception as e:
                            logger.warning(f"Direction selection failed, defaulting to long_call: {e}")
                            current_strategy = 'long_call'
                            direction_confidence = 0.5
                    
                    # 动态选择行权价（基于市场条件）
                    try:
                        from strategy_config import DynamicOTMSelector
                        
                        # 提取市场条件指标
                        volatility = row.get('bb_width', 0.04) / 0.08  # 归一化
                        momentum = row.get('rsi', 50) / 50 - 1  # -1 to 1
                        bb_percentile = row.get('bb_percentile', 0.5)
                        
                        # 选择最优 OTM 策略
                        otm_config = DynamicOTMSelector.select_otm_strategy(
                            volatility=volatility,
                            momentum=momentum,
                            bb_percentile=bb_percentile,
                            days_to_expiry=30
                        )
                        
                        if current_strategy == 'long_call':
                            strike = self._round_strike(current_price * otm_config.call_multiplier)
                        else:  # long_put
                            strike = self._round_strike(current_price * otm_config.put_multiplier)
                        
                        logger.debug(f"Dynamic OTM: {otm_config.name}, Strike: ${strike:.2f}")
                        
                    except Exception as e:
                        # 回退到固定策略
                        logger.warning(f"Dynamic OTM failed, using default: {e}")
                        if current_strategy == 'long_call':
                            strike = self._round_strike(current_price * 1.08)  # 8% OTM
                        else:  # long_put
                            strike = self._round_strike(current_price * 0.92)  # 8% OTM
                    
                    # 获取期权价格（真实或估算）
                    option_price = self._get_option_price(
                        symbol, current_date, current_price, strike, current_strategy, 30
                    )
                    
                    # 计算合约数量
                    shares = int(position_value / (option_price * 100))
                    if shares == 0:
                        shares = 1
                    
                    # 创建交易
                    expiry_date = (date + timedelta(days=30)).strftime('%Y-%m-%d')
                    
                    open_trade = Trade(
                        entry_date=current_date,
                        symbol=symbol,
                        strategy=current_strategy,  # 使用实际选择的策略方向
                        strike=strike,
                        entry_price=option_price,
                        shares=shares,
                        expiry=expiry_date,
                        entry_underlying=current_price
                    )
                    
                    logger.info(f"Entry: {current_date} | {current_strategy.upper()} | "
                              f"Strike: ${strike:.2f} | Premium: ${option_price:.2f} | "
                              f"Shares: {shares}")
        
        # 关闭未平仓交易
        if open_trade:
            last_date = data.index[-1].strftime('%Y-%m-%d')
            last_price = data.iloc[-1]['close']
            
            exit_price = self._get_option_price(
                symbol, last_date, last_price, open_trade.strike, open_trade.strategy, 0
            )
            
            pnl = (exit_price - open_trade.entry_price) * open_trade.shares * 100
            pnl_pct = pnl / (open_trade.entry_price * open_trade.shares * 100)
            
            open_trade.exit_date = last_date
            open_trade.exit_price = exit_price
            open_trade.exit_underlying = last_price
            open_trade.pnl = pnl
            open_trade.pnl_pct = pnl_pct
            open_trade.status = 'expired'
            
            self.current_capital += pnl
            trades.append(open_trade)
        
        # 计算结果
        result = self._calculate_results(trades, equity_curve)
        
        return result
    
    def _validate_symbol(self, symbol: str) -> Tuple[str, Optional[str]]:
        """
        验证股票代码，检查常见拼写错误
        
        Returns:
            (corrected_symbol, suggestion_message)
        """
        # 常见拼写错误映射
        common_typos = {
            'TELSA': 'TSLA',
            'APPL': 'AAPL',
            'GOOG': 'GOOGL',
            'MSFT': 'MSFT',  # 这个是对的，但保留用于扩展
        }
        
        symbol_upper = symbol.upper()
        
        # 检查是否是已知的拼写错误
        if symbol_upper in common_typos:
            correct_symbol = common_typos[symbol_upper]
            return correct_symbol, f"⚠️  Detected typo: '{symbol}' -> '{correct_symbol}'"
        
        return symbol, None
    
    def _fetch_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """获取历史数据"""
        
        # 验证并修正股票代码
        corrected_symbol, suggestion = self._validate_symbol(symbol)
        if suggestion:
            logger.warning(suggestion)
            symbol = corrected_symbol
        
        url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': 5000,
            'apiKey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('resultsCount', 0) > 0:
                    results = data['results']
                    
                    df = pd.DataFrame(results)
                    df = df.rename(columns={
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume'
                    })
                    
                    df['date'] = pd.to_datetime(df['t'], unit='ms')
                    df.set_index('date', inplace=True)
                    
                    # Debug: 打印实际获取的数据日期范围
                    first_date = df.index[0].strftime('%Y-%m-%d')
                    last_date = df.index[-1].strftime('%Y-%m-%d')
                    logger.info(f"📊 Fetched data: {first_date} to {last_date} ({len(df)} days)")
                    logger.info(f"   Requested: {start_date} to {end_date}")
                    
                    return df[['open', 'high', 'low', 'close', 'volume']]
            
            logger.error(f"Polygon API returned status {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        
        df = data.copy()
        
        # 布林带
        window = 20
        df['sma'] = df['close'].rolling(window).mean()
        df['std'] = df['close'].rolling(window).std()
        df['upper_bb'] = df['sma'] + 2 * df['std']
        df['lower_bb'] = df['sma'] - 2 * df['std']
        df['bb_width'] = (df['upper_bb'] - df['lower_bb']) / df['sma']
        
        # BB 宽度百分位
        df['bb_percentile'] = df['bb_width'].rolling(60).apply(
            lambda x: (x < x.iloc[-1]).sum() / len(x) if len(x) > 0 else 0.5
        )
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        df['tr'] = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        ], axis=1).max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        return df
    
    def _check_entry_signal(
        self, 
        row: pd.Series, 
        signal_type: Union[str, Dict[str, float]],
        data_with_indicators: Optional[pd.DataFrame] = None,
        idx: Optional[int] = None
    ) -> bool:
        """
        检查入场信号
        
        Args:
            row: 当前行数据
            signal_type: 信号类型（字符串）或信号权重字典
            data_with_indicators: 带指标的完整数据（用于组合信号）
            idx: 当前索引（用于组合信号）
        
        Returns:
            是否触发入场
        """
        
        # 如果是字典（组合信号）
        if isinstance(signal_type, dict):
            if data_with_indicators is None or idx is None:
                logger.warning("组合信号需要 data_with_indicators 和 idx 参数")
                return False
            
            # 导入 SignalLibrary
            try:
                from signal_optimization.signal_library import SignalLibrary
            except ImportError:
                logger.error("无法导入 SignalLibrary，无法使用组合信号")
                return False
            
            # 计算信号得分
            score, direction, details = SignalLibrary.evaluate_signal_combination(
                data_with_indicators,
                idx,
                signal_type
            )
            
            # 入场阈值：得分 >= 0.3 (降低阈值以增加交易机会)
            return score >= 0.3
        
        # 简单字符串信号
        if signal_type == 'bb_compression':
            # BB 压缩到 30% 以下
            return row.get('bb_percentile', 1.0) < 0.3
        
        elif signal_type == 'rsi_oversold':
            # RSI 超卖
            return row.get('rsi', 50) < 30
        
        elif signal_type == 'rsi_overbought':
            # RSI 超买
            return row.get('rsi', 50) > 70
        
        return False
    
    def _check_exit_conditions(
        self,
        trade: Trade,
        current_date: str,
        current_price: float,
        row: pd.Series,
        profit_target: float,
        stop_loss: float,
        max_holding_days: int
    ) -> Tuple[bool, str]:
        """检查出场条件"""
        
        # 估算当前期权价值
        days_to_expiry = (datetime.strptime(trade.expiry, '%Y-%m-%d') - 
                         datetime.strptime(current_date, '%Y-%m-%d')).days
        
        current_value = self._get_option_price(
            'UNKNOWN', current_date, current_price, trade.strike, trade.strategy, days_to_expiry
        )
        
        pnl_pct = (current_value - trade.entry_price) / trade.entry_price
        
        # 盈利目标
        if pnl_pct >= profit_target:
            return True, f"Profit Target ({pnl_pct:.1%})"
        
        # 止损
        if pnl_pct <= stop_loss:
            return True, f"Stop Loss ({pnl_pct:.1%})"
        
        # 时间衰减
        holding_days = (datetime.strptime(current_date, '%Y-%m-%d') - 
                       datetime.strptime(trade.entry_date, '%Y-%m-%d')).days
        
        if holding_days >= max_holding_days:
            return True, f"Max Holding ({holding_days} days)"
        
        # 到期
        if days_to_expiry <= 0:
            return True, "Expiry"
        
        return False, ""
    
    def _get_option_price(
        self,
        symbol: str,
        date: str,
        underlying_price: float,
        strike: float,
        option_type: str,
        days_to_expiry: int
    ) -> float:
        """
        获取期权价格
        
        优先使用 Polygon 真实历史价格
        如果失败，回退到估算
        """
        
        # 如果禁用真实价格，直接估算
        if not self.use_real_prices:
            return self._estimate_option_value(underlying_price, strike, option_type, days_to_expiry)
        
        # 尝试获取真实价格
        try:
            real_price = self._fetch_real_option_price(
                symbol, date, strike, option_type, days_to_expiry
            )
            
            if real_price is not None and real_price > 0:
                logger.debug(f"✅ Real option price: ${real_price:.2f}")
                return real_price
        
        except Exception as e:
            logger.debug(f"Real price fetch failed: {e}")
        
        # 回退到估算
        estimated = self._estimate_option_value(underlying_price, strike, option_type, days_to_expiry)
        logger.debug(f"⚠️ Using estimated price: ${estimated:.2f}")
        return estimated
    
    def _fetch_real_option_price(
        self,
        symbol: str,
        date: str,
        strike: float,
        option_type: str,
        days_to_expiry: int
    ) -> Optional[float]:
        """
        从 Polygon 获取真实期权历史价格
        
        注意: Polygon 免费版可能不支持期权历史数据
        需要 Starter+ 订阅
        """
        
        # 缓存键
        cache_key = f"{symbol}_{date}_{strike}_{option_type}_{days_to_expiry}"
        if cache_key in self.option_price_cache:
            return self.option_price_cache[cache_key]
        
        # 计算到期日
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        expiry_date = (date_obj + timedelta(days=days_to_expiry)).strftime('%Y-%m-%d')
        
        # 构造期权代码 (OCC format)
        # 例如: O:AAPL251219C00150000 (Apple, 2025-12-19, Call, $150)
        option_type_code = 'C' if option_type == 'long_call' else 'P'
        
        # 格式化行权价为8位整数（乘以1000）
        strike_str = f"{int(strike * 1000):08d}"
        
        # 格式化到期日为 YYMMDD
        expiry_formatted = expiry_date.replace('-', '')[2:]  # 251219
        
        option_ticker = f"O:{symbol}{expiry_formatted}{option_type_code}{strike_str}"
        
        # 获取该期权在指定日期的OHLC数据
        url = f"{self.base_url}/v2/aggs/ticker/{option_ticker}/range/1/day/{date}/{date}"
        params = {
            'adjusted': 'true',
            'apiKey': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('results') and len(data['results']) > 0:
                    result = data['results'][0]
                    
                    # 使用收盘价或中间价
                    close_price = result.get('c')
                    open_price = result.get('o')
                    high_price = result.get('h')
                    low_price = result.get('l')
                    
                    # 计算中间价
                    if close_price:
                        mid_price = close_price
                    elif high_price and low_price:
                        mid_price = (high_price + low_price) / 2
                    else:
                        return None
                    
                    # 缓存
                    self.option_price_cache[cache_key] = mid_price
                    
                    logger.debug(f"✅ Found real option price for {option_ticker}: ${mid_price:.2f}")
                    return mid_price
            
            elif response.status_code == 403:
                logger.warning(f"❌ Polygon 403 Forbidden for {option_ticker}")
                logger.warning("   Possible reasons:")
                logger.warning("   1. API key doesn't have access to option historical data (requires Starter+ subscription)")
                logger.warning("   2. API key is invalid or expired")
                logger.warning("   3. API key quota exceeded")
                logger.warning("   → Falling back to estimated option prices")
                # 返回 None，让调用者使用估算价格
                return None
            
            else:
                logger.debug(f"Polygon API returned {response.status_code} for {option_ticker}")
                return None
        
        except Exception as e:
            logger.debug(f"Error fetching real option price: {e}")
            return None
    
    def _estimate_option_value(
        self,
        underlying_price: float,
        strike: float,
        option_type: str,
        days_to_expiry: int
    ) -> float:
        """
        估算期权价值（改进版）
        
        考虑因素：
        - 内在价值
        - 时间价值
        - Moneyness（货币性/虚实程度）
        - 时间衰减
        """
        
        # 1. 内在价值
        if option_type == 'long_call':
            intrinsic = max(underlying_price - strike, 0)
        else:  # long_put
            intrinsic = max(strike - underlying_price, 0)
        
        # 2. 时间价值（考虑 OTM 程度）
        if days_to_expiry > 0:
            # 计算 Moneyness（货币性）
            moneyness = abs(underlying_price - strike) / underlying_price
            
            # 基础时间价值（ATM 附近）
            # ATM 期权时间价值约为标的价格的 1.5-2%
            base_time_value = underlying_price * 0.015 * (days_to_expiry / 30)
            
            # OTM 衰减因子
            # 使用指数衰减：exp(-moneyness * decay_rate)
            # decay_rate 越大，OTM 期权价值衰减越快
            decay_rate = 5  # 调整这个参数可以改变衰减速度
            otm_factor = np.exp(-moneyness * decay_rate)
            
            # 最终时间价值
            time_value = base_time_value * otm_factor
            
            # 设置最小值（深度 OTM 期权仍有微小价值）
            time_value = max(time_value, 0.05)
        else:
            time_value = 0
        
        total_value = intrinsic + time_value
        
        return total_value
    
    def _round_strike(self, price: float) -> float:
        """四舍五入行权价"""
        if price < 10:
            return round(price * 2) / 2
        elif price < 50:
            return round(price)
        elif price < 100:
            return round(price / 5) * 5
        else:
            return round(price / 10) * 10
    
    def _calculate_results(
        self,
        trades: List[Trade],
        equity_curve: List[Dict]
    ) -> BacktestResult:
        """计算回测结果"""
        
        # 即使没有交易，也要处理权益曲线
        if not equity_curve:
            logger.warning("⚠️ No equity curve data generated. This may indicate:")
            logger.warning("   1. No market data available for the date range")
            logger.warning("   2. Data fetching failed")
            logger.warning("   3. Date range is invalid")
            # 创建一个空的权益曲线，至少包含初始资金
            equity_curve = [{'date': datetime.now().strftime('%Y-%m-%d'), 'equity': self.initial_capital}]
        
        # 权益曲线
        eq_df = pd.DataFrame(equity_curve)
        if eq_df.empty:
            logger.warning("⚠️ Equity curve DataFrame is empty, using initial capital")
            eq_df = pd.DataFrame([{'date': datetime.now().strftime('%Y-%m-%d'), 'equity': self.initial_capital}])
        
        eq_df['date'] = pd.to_datetime(eq_df['date'])
        eq_df.set_index('date', inplace=True)
        
        # 如果没有交易，返回基础结果（包含权益曲线）
        if not trades:
            logger.info(f"ℹ️  No trades executed, but equity curve has {len(eq_df)} data points")
            return BacktestResult(
                trades=[],
                initial_capital=self.initial_capital,
                final_capital=self.current_capital,
                total_pnl=0.0,
                total_return=0.0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                num_trades=0,
                daily_returns=pd.Series(dtype='float64'),
                equity_curve=eq_df['equity']
            )
        
        # 基础统计
        total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
        total_return = total_pnl / self.initial_capital
        
        wins = [t for t in trades if t.pnl and t.pnl > 0]
        losses = [t for t in trades if t.pnl and t.pnl < 0]
        
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0
        
        # 最大回撤
        rolling_max = eq_df['equity'].expanding().max()
        drawdown = (eq_df['equity'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 夏普比率
        daily_returns = eq_df['equity'].pct_change().dropna()
        sharpe_ratio = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)) if len(daily_returns) > 0 else 0
        
        return BacktestResult(
            trades=trades,
            initial_capital=self.initial_capital,
            final_capital=self.current_capital,
            total_pnl=total_pnl,
            total_return=total_return,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            num_trades=len(trades),
            daily_returns=daily_returns,
            equity_curve=eq_df['equity']
        )


# =============================================================================
# 测试
# =============================================================================

def main():
    """测试回测引擎"""

    from strategy_selector import StrategyDirectionSelector
    
    backtest = OptionBacktest(initial_capital=10000, use_real_prices=True)
    
    # 回测参数
    result = backtest.run_backtest(
        symbol='NVDA',
        start_date='2024-01-01',
        end_date='2025-11-01',
        strategy='auto',  # 做多看涨期权
        entry_signal='bb_compression',
        profit_target=5,  # 500% 止盈
        stop_loss=-0.5,  # -50% 止损
        max_holding_days=30,
        position_size=0.1  # 10% 仓位
    )
    
    # 打印结果
    print("\n📊 期权回测结果\n")
    
    print(f"初始资金: ${result.initial_capital:,.0f}")
    print(f"最终资金: ${result.final_capital:,.0f}")
    print(f"总盈亏: ${result.total_pnl:,.2f}")
    print(f"总收益率: {result.total_return:.2%}")
    print()
    
    print(f"交易次数: {result.num_trades}")
    print(f"胜率: {result.win_rate:.1%}")
    print(f"平均盈利: ${result.avg_win:.2f}")
    print(f"平均亏损: ${result.avg_loss:.2f}")
    print(f"盈亏比: {abs(result.avg_win/result.avg_loss) if result.avg_loss != 0 else 0:.2f}")
    print()
    
    print(f"最大回撤: {result.max_drawdown:.2%}")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print()
    
    print("最近5笔交易:")
    for trade in result.trades[-5:]:
        print(f"\n交易: {trade.entry_date} → {trade.exit_date} | {trade.strategy.upper()}")
        print(f"  📈 入场: 股价 ${trade.entry_underlying:.2f} | 行权价 ${trade.strike:.0f} | 期权价 ${trade.entry_price:.2f}")
        print(f"  📉 离场: 股价 ${trade.exit_underlying:.2f} | 期权价 ${trade.exit_price:.2f}")
        
        # 计算标的变化
        if trade.exit_underlying:
            stock_change = trade.exit_underlying - trade.entry_underlying
            stock_change_pct = (stock_change / trade.entry_underlying) * 100
            print(f"  📊 标的变化: ${stock_change:+.2f} ({stock_change_pct:+.1f}%)")
        
        print(f"  💰 盈亏: ${trade.pnl:.2f} ({trade.pnl_pct:+.1%}) | {trade.status.upper()}")


if __name__ == '__main__':
    main()

