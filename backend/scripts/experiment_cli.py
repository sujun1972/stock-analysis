#!/usr/bin/env python3
"""
实验管理命令行工具
快速创建和管理实验批次
"""

import asyncio
import click
import json
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, '/app/src')
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.experiment_service import ExperimentService
from app.services.parameter_grid import ParameterSpaceTemplates
from app.services.model_ranker import ModelRanker


@click.group()
def cli():
    """实验管理CLI工具"""
    pass


@cli.command()
@click.option('--name', required=True, help='批次名称')
@click.option('--template', default='small_grid', type=click.Choice(['minimal', 'small', 'medium', 'large']), help='模板名称')
@click.option('--workers', default=3, help='并行Worker数')
@click.option('--strategy', default='grid', type=click.Choice(['grid', 'random']), help='参数生成策略')
def create(name, template, workers, strategy):
    """创建并运行实验批次"""

    async def run():
        service = ExperimentService()

        # 获取模板
        templates = {
            'minimal': ParameterSpaceTemplates.minimal_test(),
            'small': ParameterSpaceTemplates.small_grid(),
            'medium': ParameterSpaceTemplates.medium_grid(),
            'large': ParameterSpaceTemplates.large_random()
        }

        param_space = templates.get(template)
        if not param_space:
            click.echo(f"❌ 模板不存在: {template}")
            return

        # 创建批次
        click.echo(f"📦 创建批次: {name}")
        click.echo(f"📋 模板: {template}")
        click.echo(f"🎲 策略: {strategy}")

        batch_id = await service.create_batch(
            batch_name=name,
            param_space=param_space,
            strategy=strategy if template != 'large' else 'random',
            max_experiments=100 if template == 'large' else None,
            config={'max_workers': workers, 'auto_backtest': True}
        )

        click.echo(f"✅ 批次ID: {batch_id}")

        # 显示批次信息
        info = await service.get_batch_info(batch_id)
        click.echo(f"📊 总实验数: {info['total_experiments']}")

        # 启动批次
        click.echo(f"\n🚀 启动批次（{workers} Workers）...")
        click.echo("⏳ 这可能需要几分钟到几小时，请耐心等待...\n")

        try:
            await service.run_batch(batch_id, max_workers=workers)
            click.echo("\n🎉 批次执行完成！")

            # 显示Top模型
            top_models = await service.get_top_models(batch_id, top_n=5)

            if top_models:
                click.echo("\n📊 Top 5模型:")
                click.echo("-" * 80)

                for i, model in enumerate(top_models, 1):
                    click.echo(f"\n{i}. {model['model_id']}")
                    click.echo(f"   配置: {model['config'].get('symbol')} | "
                              f"{model['config'].get('model_type')} | "
                              f"T{model['config'].get('target_period')}")

                    if model.get('annual_return'):
                        click.echo(f"   年化收益: {model['annual_return']:.2f}%")
                    if model.get('sharpe_ratio'):
                        click.echo(f"   夏普比率: {model['sharpe_ratio']:.2f}")
                    if model.get('max_drawdown'):
                        click.echo(f"   最大回撤: {model['max_drawdown']:.2f}%")
                    if model.get('rank_score'):
                        click.echo(f"   综合评分: {model['rank_score']:.2f}")

                click.echo("\n" + "-" * 80)

                # 显示摘要
                click.echo(f"\n📈 批次摘要:")
                click.echo(f"   成功实验: {info['completed_experiments']}/{info['total_experiments']}")
                if info.get('duration_hours'):
                    click.echo(f"   耗时: {info['duration_hours']:.2f} 小时")

            else:
                click.echo("\n⚠️  没有找到符合条件的模型")

        except Exception as e:
            click.echo(f"\n❌ 批次执行失败: {e}")
            sys.exit(1)

    asyncio.run(run())


@cli.command()
@click.option('--batch-id', required=True, type=int, help='批次ID')
@click.option('--format', default='text', type=click.Choice(['text', 'json']), help='输出格式')
def report(batch_id, format):
    """生成实验报告"""

    async def run():
        ranker = ModelRanker()

        try:
            report_data = ranker.generate_report(batch_id)

            if format == 'json':
                click.echo(json.dumps(report_data, indent=2, ensure_ascii=False))
            else:
                # 文本格式
                click.echo("\n" + "=" * 80)
                click.echo(f"实验批次报告 - Batch ID: {batch_id}")
                click.echo("=" * 80)

                summary = report_data.get('summary', {})
                click.echo(f"\n批次名称: {summary.get('batch_name')}")
                click.echo(f"策略: {summary.get('strategy')}")
                click.echo(f"状态: {summary.get('status')}")
                click.echo(f"\n总实验数: {summary.get('total_experiments')}")
                click.echo(f"成功: {summary.get('completed_experiments')}")
                click.echo(f"失败: {summary.get('failed_experiments')}")
                click.echo(f"成功率: {summary.get('success_rate_pct', 0):.1f}%")

                if summary.get('duration_hours'):
                    click.echo(f"耗时: {summary.get('duration_hours'):.2f} 小时")

                # 性能统计
                perf = report_data.get('performance_distribution', {})
                if perf:
                    click.echo(f"\n性能统计:")
                    click.echo(f"  平均年化收益: {perf.get('avg_annual_return', 0):.2f}%")
                    click.echo(f"  平均夏普比率: {perf.get('avg_sharpe_ratio', 0):.2f}")
                    click.echo(f"  平均最大回撤: {perf.get('avg_max_drawdown', 0):.2f}%")
                    click.echo(f"  平均IC: {perf.get('avg_ic', 0):.4f}")

                # Top模型
                top_models = report_data.get('top_models', [])
                if top_models:
                    click.echo(f"\nTop 10 模型:")
                    click.echo("-" * 80)

                    for i, model in enumerate(top_models[:10], 1):
                        train_metrics = model.get('train_metrics', {})
                        backtest_metrics = model.get('backtest_metrics', {})

                        click.echo(f"\n{i}. {model.get('model_id')}")
                        click.echo(f"   IC: {train_metrics.get('ic', 0):.4f} | "
                                  f"年化收益: {backtest_metrics.get('annual_return', 0):.2f}% | "
                                  f"夏普: {backtest_metrics.get('sharpe_ratio', 0):.2f}")

                # 参数重要性
                param_importance = report_data.get('parameter_importance', {})
                if param_importance:
                    click.echo(f"\n参数重要性:")
                    for param, importance in list(param_importance.items())[:5]:
                        bar = "█" * int(importance * 20)
                        click.echo(f"  {param:20s} {bar} {importance:.3f}")

                click.echo("\n" + "=" * 80)

        except Exception as e:
            click.echo(f"❌ 生成报告失败: {e}")
            sys.exit(1)

    asyncio.run(run())


@cli.command()
@click.option('--limit', default=10, help='显示数量')
def list(limit):
    """列出所有批次"""

    async def run():
        import sys
        sys.path.insert(0, '/app/src')
        from database.db_manager import DatabaseManager

        try:
            db = DatabaseManager()

            query = """
                SELECT id, batch_name, strategy, status, total_experiments,
                       completed_experiments, created_at
                FROM experiment_batches
                ORDER BY created_at DESC
                LIMIT %s
            """

            results = await asyncio.to_thread(db._execute_query, query, (limit,))

            if not results:
                click.echo("暂无批次记录")
                return

            click.echo("\n批次列表:")
            click.echo("-" * 100)
            click.echo(f"{'ID':<5} {'批次名称':<25} {'策略':<10} {'状态':<12} {'进度':<15} {'创建时间':<20}")
            click.echo("-" * 100)

            for row in results:
                batch_id = row[0]
                name = row[1][:24]
                strategy = row[2]
                status = row[3]
                total = row[4]
                completed = row[5]
                created = row[6].strftime('%Y-%m-%d %H:%M') if row[6] else '-'

                progress = f"{completed}/{total}" if total else "-"

                click.echo(f"{batch_id:<5} {name:<25} {strategy:<10} {status:<12} {progress:<15} {created:<20}")

            click.echo("-" * 100)

        except Exception as e:
            click.echo(f"❌ 列出批次失败: {e}")
            sys.exit(1)

    asyncio.run(run())


@cli.command()
@click.option('--batch-id', required=True, type=int, help='批次ID')
def status(batch_id):
    """查看批次状态"""

    async def run():
        service = ExperimentService()

        try:
            info = await service.get_batch_info(batch_id)

            if not info:
                click.echo(f"❌ 批次 {batch_id} 不存在")
                return

            click.echo(f"\n批次 #{batch_id} 状态:")
            click.echo("-" * 60)
            click.echo(f"名称: {info['batch_name']}")
            click.echo(f"策略: {info['strategy']}")
            click.echo(f"状态: {info['status']}")
            click.echo(f"\n进度:")
            click.echo(f"  总实验数: {info['total_experiments']}")
            click.echo(f"  已完成: {info['completed_experiments']}")
            click.echo(f"  失败: {info['failed_experiments']}")
            click.echo(f"  运行中: {info['running_experiments']}")

            if info['total_experiments'] > 0:
                progress = (info['completed_experiments'] / info['total_experiments']) * 100
                click.echo(f"  完成率: {progress:.1f}%")

            if info.get('started_at'):
                click.echo(f"\n开始时间: {info['started_at']}")
            if info.get('completed_at'):
                click.echo(f"完成时间: {info['completed_at']}")
            if info.get('duration_hours'):
                click.echo(f"耗时: {info['duration_hours']:.2f} 小时")

            if info.get('top_model_id'):
                click.echo(f"\nTop模型: {info['top_model_id']}")
                click.echo(f"最高评分: {info.get('max_rank_score', 0):.2f}")

            click.echo("-" * 60)

        except Exception as e:
            click.echo(f"❌ 查询失败: {e}")
            sys.exit(1)

    asyncio.run(run())


@cli.command()
@click.option('--batch-id', required=True, type=int, help='批次ID')
@click.option('--top-n', default=10, help='显示Top N模型')
def top(batch_id, top_n):
    """显示Top模型"""

    async def run():
        service = ExperimentService()

        try:
            models = await service.get_top_models(batch_id, top_n=top_n)

            if not models:
                click.echo(f"⚠️  批次 {batch_id} 暂无完成的模型")
                return

            click.echo(f"\n批次 #{batch_id} Top {len(models)} 模型:")
            click.echo("=" * 100)

            for i, model in enumerate(models, 1):
                config = model.get('config', {})

                click.echo(f"\n{i}. 模型ID: {model['model_id']}")
                click.echo(f"   配置: {config.get('symbol')} | {config.get('model_type')} | "
                          f"T{config.get('target_period')} | {config.get('scaler_type')}")

                click.echo(f"   年化收益: {model.get('annual_return', 0):.2f}% | "
                          f"夏普比率: {model.get('sharpe_ratio', 0):.2f} | "
                          f"最大回撤: {model.get('max_drawdown', 0):.2f}%")

                click.echo(f"   综合评分: {model.get('rank_score', 0):.2f} | "
                          f"排名: #{model.get('config', {}).get('rank_position', '-')}")

            click.echo("\n" + "=" * 100)

        except Exception as e:
            click.echo(f"❌ 查询失败: {e}")
            sys.exit(1)

    asyncio.run(run())


if __name__ == '__main__':
    cli()
