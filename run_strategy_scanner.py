#!/usr/bin/env python3
"""
命令行策略扫描器

支持从命令行运行策略扫描，用于 Web 应用后台任务

使用方法:
python run_strategy_scanner.py --symbols BABA NVDA --start 2025-01-01 --end 2025-11-03
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

# 强制无缓冲输出（重要！用于实时日志）
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategy_scanner import StrategyScanner

# 配置日志 - 输出到 stdout 以便 web_app 捕获
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,  # 明确输出到 stdout
    force=True  # 强制重新配置
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="🔍 策略扫描器 - 批量回测多个标的",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--symbols", 
        type=str, 
        nargs='+',
        required=True,
        help="标的代码列表，如: BABA NVDA AAPL"
    )
    parser.add_argument(
        "--start", 
        type=str, 
        default="2025-01-01",
        help="回测开始日期 (默认: 2025-01-01)"
    )
    parser.add_argument(
        "--end", 
        type=str, 
        default="2025-11-03",
        help="回测结束日期 (默认: 2025-11-03)"
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="report_assets/scan_results.csv",
        help="CSV 输出文件名 (默认: report_assets/scan_results.csv)"
    )
    parser.add_argument(
        "--output-html",
        type=str,
        default="report_assets/scan_report.html",
        help="HTML 报告文件名 (默认: report_assets/scan_report.html)"
    )
    parser.add_argument(
        "--strategies",
        type=str,
        nargs='+',
        help="指定策略文件路径列表（可选，如不指定则自动查找每个标的的最新策略）"
    )

    args = parser.parse_args()

    # 打印 banner - 使用简单的分隔线，避免 Unicode 字符显示问题
    print("=" * 80)
    print(f"🔍 策略扫描器")
    print(f"标的: {', '.join(args.symbols)}")
    print(f"周期: {args.start} → {args.end}")
    print("=" * 80)
    logger.info(f"开始扫描 {len(args.symbols)} 个标的")

    try:
        # 创建扫描器
        scanner = StrategyScanner(strategy_dir="strategies")
        
        # 构建策略映射（如果指定了策略文件）
        strategy_files = None
        if args.strategies:
            # 验证策略文件数量与标的数量是否匹配
            if len(args.strategies) != len(args.symbols):
                logger.error(f"❌ 策略文件数量 ({len(args.strategies)}) 与标的数量 ({len(args.symbols)}) 不匹配")
                return 1
            
            # 使用列表存储 (symbol, strategy_path) 对，支持一个标的多个策略
            strategy_files = []
            for symbol, strategy_file in zip(args.symbols, args.strategies):
                strategy_path = Path(strategy_file)
                if not strategy_path.exists():
                    logger.error(f"❌ 策略文件不存在: {strategy_file}")
                    return 1
                strategy_files.append((symbol, strategy_path))
                logger.info(f"📋 {symbol} 使用策略: {strategy_path.name}")
            
            # 统计信息
            unique_symbols = set([s for s, _ in strategy_files])
            logger.info(f"📊 总计: {len(unique_symbols)} 个标的 × {len(strategy_files)} 个测试")
        
        # 运行扫描
        logger.info(f"正在扫描: {', '.join(args.symbols)}")
        df_results = scanner.run_scan(
            symbols=args.symbols,
            start_date=args.start,
            end_date=args.end,
            output_csv=args.output_csv,
            output_html=args.output_html,
            strategy_files=strategy_files
        )
        
        if not df_results.empty:
            print("\n🏆 扫描结果汇总\n")
            
            # 显示每个标的的最佳策略
            for symbol in df_results['symbol'].unique():
                best = df_results[df_results['symbol'] == symbol].sort_values('total_return', ascending=False).iloc[0]
                print(f"\n标的: {symbol}")
                print(f"  策略: {best['strategy_name']}")
                print(f"  收益: {best['total_return']:+.2%}")
                print(f"  夏普比率: {best['sharpe_ratio']:.2f}")
                print(f"  胜率: {best['win_rate']:.1%}")
                print(f"  最大回撤: {best['max_drawdown']:.2%}")
                print(f"  交易次数: {best['num_trades']}")
                
                logger.info(f"{symbol}: 收益 {best['total_return']:+.2%}, 夏普 {best['sharpe_ratio']:.2f}, 胜率 {best['win_rate']:.1%}")
            
            print(f"\n📄 报告已生成:")
            print(f"   HTML: {args.output_html}")
            print(f"   CSV:  {args.output_csv}\n")
            
            logger.info("✅ 扫描完成")
            return 0
        else:
            logger.error("❌ 无有效回测结果")
            return 1
            
    except Exception as e:
        logger.exception("扫描过程中发生错误")
        print(f"\n❌ 错误: {e}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())

