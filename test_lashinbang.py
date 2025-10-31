#!/usr/bin/env python3
"""
Test script for Lashinbang adapter
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from adapters.lashinbang import LashinbangAdapter
from config.settings import platforms_config
from loguru import logger

def main():
    logger.info("=" * 80)
    logger.info("Lashinbang Adapter Test")
    logger.info("=" * 80)

    # Initialize adapter
    lashinbang_config = platforms_config['platforms']['lashinbang']
    general_config = platforms_config['general']

    adapter = LashinbangAdapter(lashinbang_config, general_config, headless=False)

    try:
        # Test search
        test_item = {
            'id': 1,
            'name_cn': '神里绫华 抱枕套',
            'name_jp': '神里綾華 抱き枕カバー',
            'search_keywords': [
                '神里綾華 抱き枕',
                '原神 抱き枕 神里'
            ],
            'circle': 'MILK BAR',
            'artist': 'シロガネヒナ'
        }

        logger.info(f"\nTesting search for: {test_item['name_cn']}")
        result = adapter.scrape_item(test_item)

        logger.info("\n" + "=" * 80)
        logger.info("Search Results:")
        logger.info(f"Platform: {result.platform}")
        logger.info(f"Item ID: {result.item_id}")
        logger.info(f"Keyword: {result.keyword}")
        logger.info(f"Found {len(result.results)} results")

        for i, item in enumerate(result.results, 1):
            logger.info(f"\nResult #{i}:")
            logger.info(f"  Title: {item.title[:80]}...")
            logger.info(f"  URL: {item.url}")
            logger.info(f"  Price: ¥{item.price}" if item.price else "  Price: N/A")
            logger.info(f"  Status: {item.status} ({item.status_text})")
            logger.info(f"  Image: {item.image_url[:60]}..." if item.image_url else "  Image: N/A")

        logger.info("\n" + "=" * 80)
        logger.info("Test completed!")
        logger.info("=" * 80)

    finally:
        adapter.close()

if __name__ == "__main__":
    main()
