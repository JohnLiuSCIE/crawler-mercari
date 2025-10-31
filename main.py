#!/usr/bin/env python3
"""
主程序入口 - 抱枕套监控系统
Main entry point for dakimakura monitoring system
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from loguru import logger
from config.settings import settings, platforms_config
from core.scraper import ScraperEngine
from core.report_generator import ReportGenerator
from notifications.email_notifier import EmailNotifier

# 导入适配器
from adapters.mercari import MercariAdapter
from adapters.yahoo_auction import YahooAuctionAdapter
from adapters.surugaya import SurugayaAdapter
from adapters.lashinbang import LashinbangAdapter


def setup_adapters(headless: bool = True) -> dict:
    """
    设置所有启用的平台适配器

    Args:
        headless: 是否使用无头模式

    Returns:
        适配器字典
    """
    adapters = {}
    general_config = platforms_config['general']

    # Mercari
    if platforms_config['platforms']['mercari'].get('enabled', True):
        try:
            mercari_config = platforms_config['platforms']['mercari']
            adapters['mercari'] = MercariAdapter(mercari_config, general_config, headless=headless)
            logger.info("Mercari适配器已加载")
        except Exception as e:
            logger.error(f"加载Mercari适配器失败: {e}")

    # Yahoo Auction / PayPay
    if platforms_config['platforms']['yahoo_auction'].get('enabled', True):
        try:
            yahoo_config = platforms_config['platforms']['yahoo_auction']
            adapters['yahoo_auction'] = YahooAuctionAdapter(yahoo_config, general_config, headless=headless)
            logger.info("Yahoo拍卖适配器已加载")
        except Exception as e:
            logger.error(f"加载Yahoo拍卖适配器失败: {e}")

    # Surugaya
    if platforms_config['platforms']['surugaya'].get('enabled', True):
        try:
            surugaya_config = platforms_config['platforms']['surugaya']
            adapters['surugaya'] = SurugayaAdapter(surugaya_config, general_config, headless=headless)
            logger.info("Suruga-ya适配器已加载")
        except Exception as e:
            logger.error(f"加载Suruga-ya适配器失败: {e}")

    # Lashinbang
    if platforms_config['platforms']['lashinbang'].get('enabled', True):
        try:
            lashinbang_config = platforms_config['platforms']['lashinbang']
            adapters['lashinbang'] = LashinbangAdapter(lashinbang_config, general_config, headless=headless)
            logger.info("Lashinbang适配器已加载")
        except Exception as e:
            logger.error(f"加载Lashinbang适配器失败: {e}")

    return adapters


def close_adapters(adapters: dict):
    """关闭所有适配器"""
    for name, adapter in adapters.items():
        try:
            adapter.close()
            logger.info(f"{name}适配器已关闭")
        except Exception as e:
            logger.error(f"关闭{name}适配器失败: {e}")


def run_scraper(headless: bool = True, send_email: bool = True, parallel: bool = True, max_workers: int = 4) -> bool:
    """
    运行爬虫

    Args:
        headless: 是否使用无头模式
        send_email: 是否发送邮件通知
        parallel: 是否使用并发模式
        max_workers: 最大并发线程数

    Returns:
        是否成功
    """
    logger.info("=" * 80)
    logger.info("开始爬取任务")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"并发模式: {'是' if parallel else '否'} (max_workers={max_workers if parallel else 'N/A'})")
    logger.info("=" * 80)

    # 初始化组件
    engine = ScraperEngine(max_workers=max_workers)
    adapters = {}

    try:
        # 初始化数据库
        engine.initialize_database()

        # 设置适配器
        adapters = setup_adapters(headless=headless)

        if not adapters:
            logger.error("没有可用的适配器")
            return False

        # 开始爬取运行
        engine.start_scrape_run()

        # 执行爬取
        stats = engine.scrape_all(adapters, parallel=parallel)

        # 完成爬取运行
        engine.complete_scrape_run('completed')

        # 显示统计
        logger.info("=" * 80)
        logger.info("爬取完成！")
        logger.info(f"检查商品数: {stats['items_checked']}")
        logger.info(f"检查平台数: {stats['platforms_checked']}")
        logger.info(f"新商品数: {stats['new_listings']}")
        logger.info(f"变化数: {stats['changes']}")
        logger.info(f"错误数: {stats['errors']}")
        logger.info("=" * 80)

        # 获取待通知的事件
        pending_events = engine.get_pending_notifications()

        if send_email and pending_events:
            logger.info(f"发现 {len(pending_events)} 个待通知事件")

            # 生成报告
            report_gen = ReportGenerator()
            report_gen.connect_db()
            report_html = report_gen.generate_html_report()
            summary = report_gen.generate_summary()
            report_gen.close()

            # 发送邮件
            notifier = EmailNotifier()
            if notifier.send_change_notifications(pending_events, report_html):
                # 标记为已通知
                for event in pending_events:
                    engine.mark_notification_sent(event.id)
                logger.info("邮件通知已发送")
            else:
                logger.warning("邮件通知发送失败")

        return True

    except Exception as e:
        logger.error(f"爬取任务失败: {e}")
        import traceback
        traceback.print_exc()

        if engine.current_run:
            engine.complete_scrape_run('failed', str(e))

        return False

    finally:
        # 清理资源
        close_adapters(adapters)
        engine.close()


def generate_report(output_format: str = 'text', output_file: str = None):
    """
    生成报告

    Args:
        output_format: 输出格式 (text/html)
        output_file: 输出文件路径
    """
    logger.info("生成报告...")

    report_gen = ReportGenerator()
    report_gen.connect_db()

    if output_format == 'html':
        report = report_gen.generate_html_report()
    else:
        report = report_gen.generate_text_report()

    # 显示摘要
    summary = report_gen.generate_summary()
    logger.info(f"监控商品: {summary['total_items']} 个")
    logger.info(f"监控平台: {summary['total_platforms']} 个")
    logger.info(f"在售商品: {summary['available_count']} 个")
    logger.info(f"已售商品: {summary['sold_count']} 个")

    # 输出报告
    if output_file:
        Path(output_file).write_text(report, encoding='utf-8')
        logger.info(f"报告已保存到: {output_file}")
    else:
        print("\n" + report)

    report_gen.close()


def send_daily_report():
    """发送每日报告"""
    logger.info("准备发送每日报告...")

    # 生成统计摘要
    report_gen = ReportGenerator()
    report_gen.connect_db()
    summary = report_gen.generate_summary()
    report_gen.close()

    # 生成CSV附件
    from core.csv_generator import CSVGenerator
    csv_gen = CSVGenerator()
    csv_gen.connect_db()
    csv_content = csv_gen.generate_csv()
    csv_gen.close()

    # 发送邮件（HTML表格 + CSV附件）
    notifier = EmailNotifier()
    if notifier.send_daily_report(summary, csv_content):
        logger.info("每日报告已发送（HTML表格 + CSV附件）")
    else:
        logger.error("每日报告发送失败")


def test_email():
    """测试邮件配置"""
    logger.info("测试邮件配置...")

    notifier = EmailNotifier()

    if not notifier.enabled:
        logger.error("邮件通知未启用，请检查 .env 配置")
        return

    logger.info(f"SMTP服务器: {notifier.smtp_server}:{notifier.smtp_port}")
    logger.info(f"发件人: {notifier.email_from}")
    logger.info(f"收件人: {notifier.email_to}")

    if notifier.test_connection():
        logger.info("✅ 邮件配置测试成功")
    else:
        logger.error("❌ 邮件配置测试失败")


def init_database():
    """初始化数据库"""
    logger.info("初始化数据库...")

    engine = ScraperEngine()
    engine.initialize_database()
    engine.close()

    logger.info("✅ 数据库初始化完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='抱枕套监控系统 - 自动监控日本二手市场',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s run                    # 运行爬虫（并发模式，无头模式）
  %(prog)s run --show-browser     # 运行爬虫（显示浏览器）
  %(prog)s run --sequential       # 运行爬虫（顺序模式）
  %(prog)s run --max-workers 8    # 运行爬虫（8个并发线程）
  %(prog)s report                 # 生成文本报告
  %(prog)s report --html          # 生成HTML报告
  %(prog)s report --html -o report.html  # 保存HTML报告到文件
  %(prog)s daily-report           # 发送每日报告邮件
  %(prog)s test-email             # 测试邮件配置
  %(prog)s init-db                # 初始化数据库
        """
    )

    parser.add_argument(
        'command',
        choices=['run', 'report', 'daily-report', 'test-email', 'init-db'],
        help='要执行的命令'
    )

    parser.add_argument(
        '--show-browser',
        action='store_true',
        help='显示浏览器窗口（非无头模式）'
    )

    parser.add_argument(
        '--no-email',
        action='store_true',
        help='不发送邮件通知'
    )

    parser.add_argument(
        '--sequential',
        action='store_true',
        help='使用顺序模式爬取（默认使用并发模式）'
    )

    parser.add_argument(
        '--max-workers',
        type=int,
        default=4,
        help='最大并发线程数（默认4，仅在并发模式下有效）'
    )

    parser.add_argument(
        '--html',
        action='store_true',
        help='生成HTML格式报告'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        help='报告输出文件路径'
    )

    args = parser.parse_args()

    # 执行命令
    if args.command == 'run':
        run_scraper(
            headless=not args.show_browser,
            send_email=not args.no_email,
            parallel=not args.sequential,
            max_workers=args.max_workers
        )

    elif args.command == 'report':
        output_format = 'html' if args.html else 'text'
        generate_report(output_format, args.output)

    elif args.command == 'daily-report':
        send_daily_report()

    elif args.command == 'test-email':
        test_email()

    elif args.command == 'init-db':
        init_database()


if __name__ == "__main__":
    main()
