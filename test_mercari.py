#!/usr/bin/env python3
"""
Mercari适配器测试脚本
Test script for Mercari adapter
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from config.settings import settings, items_config, platforms_config
from adapters.mercari import MercariAdapter
from utils.logger import logger
from datetime import datetime


def test_mercari():
    """测试Mercari适配器"""
    logger.info("=" * 80)
    logger.info("开始测试 Mercari 适配器")
    logger.info("=" * 80)

    # 获取Mercari平台配置
    mercari_config = platforms_config['platforms']['mercari']
    general_config = platforms_config['general']

    # 获取第一个测试商品（神里绫华）
    test_item = items_config['items'][0]

    logger.info(f"测试商品: {test_item['name_cn']} ({test_item['name_jp']})")
    logger.info(f"社团: {test_item['circle']}")
    logger.info(f"绘师: {test_item['artist']}")
    logger.info(f"搜索关键词: {test_item['search_keywords']}")
    logger.info("-" * 80)

    # 创建Mercari适配器
    try:
        with MercariAdapter(mercari_config, general_config, headless=False) as adapter:
            logger.info("Mercari适配器初始化成功")

            # 执行搜索和爬取
            result = adapter.scrape_item(test_item)

            # 显示结果
            logger.info("=" * 80)
            logger.info("搜索结果汇总")
            logger.info("=" * 80)
            logger.info(f"平台: {result.platform}")
            logger.info(f"商品ID: {result.item_id}")
            logger.info(f"搜索关键词: {result.keyword}")
            logger.info(f"搜索时间: {result.search_time}")
            logger.info(f"找到商品数: {len(result.results)}")

            if result.error:
                logger.error(f"错误: {result.error}")

            if result.results:
                logger.info("-" * 80)
                logger.info("找到的商品列表:")
                logger.info("-" * 80)

                for idx, item in enumerate(result.results, 1):
                    logger.info(f"\n[商品 #{idx}]")
                    logger.info(f"  标题: {item.title}")
                    logger.info(f"  链接: {item.url}")
                    logger.info(f"  价格: ¥{item.price if item.price else 'N/A'}")

                    # 根据状态显示不同的emoji
                    if item.status == "available":
                        status_emoji = "✅"
                        status_cn = "可购买"
                    elif item.status == "sold":
                        status_emoji = "🔄"
                        status_cn = "已售出"
                    else:
                        status_emoji = "❌"
                        status_cn = "未知"

                    logger.info(f"  状态: {status_emoji} {status_cn} ({item.status_text or item.status})")
                    logger.info(f"  卖家: {item.seller or 'N/A'}")

                    if item.image_url:
                        logger.info(f"  图片: {item.image_url[:80]}...")

                logger.info("\n" + "=" * 80)
                logger.info("测试完成！")
                logger.info("=" * 80)

                # 生成简单的表格预览
                logger.info("\n表格预览（Mercari列）:")
                logger.info("-" * 80)
                logger.info(f"商品: {test_item['name_cn']}")

                if result.results:
                    available_items = [r for r in result.results if r.status == "available"]
                    sold_items = [r for r in result.results if r.status == "sold"]

                    if available_items:
                        cheapest = min(available_items, key=lambda x: x.price or float('inf'))
                        logger.info(f"Mercari: ✅ 在售 - 最低价 ¥{cheapest.price}")
                        logger.info(f"  链接: {cheapest.url}")
                    elif sold_items:
                        recent_sold = sold_items[0]
                        logger.info(f"Mercari: 🔄 已售 - 最近价格 ¥{recent_sold.price or 'N/A'}")
                        logger.info(f"  链接: {recent_sold.url}")
                    else:
                        logger.info("Mercari: ❌ 未找到")
                else:
                    logger.info("Mercari: ❌ 未找到匹配商品")

            else:
                logger.warning("未找到任何匹配的商品")
                logger.info("\n可能的原因:")
                logger.info("  1. 搜索关键词需要调整")
                logger.info("  2. Mercari上确实没有这个商品")
                logger.info("  3. 网页结构发生变化，需要更新选择器")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_mercari()
