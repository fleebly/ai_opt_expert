#!/usr/bin/env python3
"""
运行迭代优化

通过 DeepSeek AI 不断优化策略，最多 10 轮
✅ 支持通过命令行指定标的（symbol）
✅ 支持一揽子标的批量优化
✅ 保留默认参数（BABA, 2024-01-01 至 2025-11-01）
✅ 新增：日志写入 logs/ 目录
✅ 新增：多标的并行/顺序处理
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Railway/Docker 环境：确保能找到模块（不影响本地运行）
# 检查是否在 Docker 容器中（/app 目录存在）
if os.path.exists('/app') and project_root == '/app':
    # 已经在 /app 目录，PYTHONPATH 应该已经设置
    # 但为了确保，再次添加到路径
    if '/app' not in sys.path:
        sys.path.insert(0, '/app')

from iterative_optimizer import IterativeOptimizer


def setup_logger(symbol: str) -> logging.Logger:
    """配置日志：同时输出到控制台和文件"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 日志文件名：optimizer_BABA_20251104_203015.log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"optimizer_{symbol}_{timestamp}.log"

    logger = logging.getLogger(f"Optimizer_{symbol}")
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler
    if logger.handlers:
        logger.handlers.clear()

    # 文件 Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(message)s')  # 简洁输出，保留你的 banner 风格
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"日志文件已创建: {log_file}")
    return logger


def main():
    parser = argparse.ArgumentParser(
        description="🚀 迭代策略优化系统 - DeepSeek AI 驱动",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--symbol", type=str, default="BABA")
    parser.add_argument("--start", type=str, default="2023-01-01")
    parser.add_argument("--end", type=str, default="2025-01-01")
    parser.add_argument("--max-iter", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=0.05)
    parser.add_argument("--eval-start", type=str, default=None, help="Start date of evaluation period (defaults to --end if --eval-end is provided)")
    parser.add_argument("--eval-end", type=str, default=None, help="End date of evaluation period")

    args = parser.parse_args()

    # 初始化日志
    global logger
    logger = setup_logger(args.symbol)

    eval_info = ""
    if args.eval_end:
        eval_start = args.eval_start or args.end
        eval_info = f"\n║              评估周期: {eval_start} → {args.eval_end}                      ║"
    
    banner = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║              🚀 迭代策略优化系统                                          ║
║              标的: {args.symbol:<10}  回测周期: {args.start} → {args.end}     ║{eval_info}
║              DeepSeek AI 驱动 - 自动收敛                                 ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    logger.info("开始执行迭代优化")
    print(banner)  # 保留美观 banner（仅控制台）

    try:
        optimizer = IterativeOptimizer(
            symbol=args.symbol,
            start_date=args.start,
            end_date=args.end,
            max_iterations=args.max_iter,
            convergence_threshold=args.threshold,
            logger=logger,  # 传入 logger
            evaluation_start_date=args.eval_start,
            evaluation_end_date=args.eval_end
        )

        result = optimizer.optimize()

        logger.info(f"优化完成 | 最佳收益: {result['best_return']:+.2%} | 迭代轮数: {result['total_iterations']}")

        print("\n" + "=" * 80)
        print("🎉 优化完成！")
        print("=" * 80)
        print(f"\n🏆 最佳收益: {result['best_return']:+.2%}")
        print(f"🔄 总迭代轮数: {result['total_iterations']}")
        
        # 保存最佳策略 JSON 到 strategies 目录
        best_strategies = result.get('best_strategies', {})
        
        print(f"\n📊 最佳策略组合 (共 {len(best_strategies) if best_strategies else 0} 个):")

        if best_strategies:
            # 打印策略详情
            for i, (name, weights) in enumerate(best_strategies.items(), 1):
                print(f"\n  {i}. {name}")
                for signal, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
                    print(f"     • {signal:<25} {weight:.2f}")
                logger.info(f"策略 #{i}: {name} | 权重: {weights}")
            
            # 保存第一个策略到文件
            strategy_name = next(iter(best_strategies))
            signal_weights = best_strategies[strategy_name]

            # 确保 strategies 目录存在
            import json
            from pathlib import Path
            strategies_dir = Path("strategies")
            strategies_dir.mkdir(exist_ok=True)

            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_json = strategies_dir / f"{args.symbol}_ST_{timestamp}.json"
            
            # 提取回测性能指标
            backtest_perf = {}
            if result.get('best_backtest_results'):
                bt_result = result['best_backtest_results']
                backtest_perf = {
                    "total_return": bt_result.get('total_return', 0),
                    "win_rate": bt_result.get('win_rate', 0),
                    "sharpe_ratio": bt_result.get('sharpe_ratio', 0),
                    "max_drawdown": bt_result.get('max_drawdown', 0),
                    "num_trades": bt_result.get('num_trades', 0),
                    "avg_win": bt_result.get('avg_win', 0),
                    "avg_loss": bt_result.get('avg_loss', 0)
                }
            
            # 策略配置数据（兼容 strategy_scanner 格式）
            json_data = {
                "name": strategy_name,
                "signal_weights": signal_weights,
                "params": {
                    "profit_target": 5.0,
                    "stop_loss": -0.5,
                    "max_holding_days": 30,
                    "position_size": 0.1
                },
                "backtest_performance": backtest_perf,
                "metadata": {
                    "symbol": args.symbol,
                    "best_return": result['best_return'],
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "backtest_period": f"{args.start} to {args.end}",
                    "evaluation_period": f"{args.eval_start or args.end} to {args.eval_end}" if args.eval_end else None
                }
            }

            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            logger.info(f"最佳策略已保存至: {output_json}")
            print(f"\n💾 最佳策略已保存至: {output_json}")
            
            # 同时保存一份到根目录（向后兼容）
            legacy_json = Path(f"best_strategy_{args.symbol}.json")
            with open(legacy_json, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            logger.info(f"向后兼容副本: {legacy_json}")
        else:
            logger.warning("⚠️  未找到有效策略，无法保存 JSON")
            print("\n⚠️  未找到有效策略")

        print(f"\n📄 最终报告: {result['final_report']}")
        print(f"\n💡 查看报告:")
        print(f"   open {result['final_report']}")
        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        logger.exception("优化过程中发生未预期错误")
        raise


if __name__ == '__main__':
    from pathlib import Path
    main()