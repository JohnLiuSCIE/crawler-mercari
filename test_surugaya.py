#!/usr/bin/env python3
"""
Test script for Suruga-ya adapter
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from adapters.surugaya import SurugayaAdapter
from config.settings import platforms_config

def main():
    print("=" * 80)
    print("Testing Suruga-ya Adapter")
    print("=" * 80)

    # Get configuration
    surugaya_config = platforms_config['platforms']['surugaya']
    general_config = platforms_config['general']

    # Initialize adapter (with browser visible for debugging)
    print("\n1. Initializing Suruga-ya adapter...")
    adapter = SurugayaAdapter(surugaya_config, general_config, headless=False)

    try:
        # Test search
        print("\n2. Testing search...")
        keywords = [
            "神里綾華 抱き枕",
            "ナヒーダ 抱き枕 シロガネヒナ"
        ]

        urls = adapter.search(keywords)
        print(f"Found {len(urls)} product URLs")

        for i, url in enumerate(urls[:3], 1):
            print(f"  {i}. {url}")

        # Test scraping first item if found
        if urls:
            print(f"\n3. Testing scrape_item_detail on first URL...")
            first_url = urls[0]
            item = adapter.scrape_item_detail(first_url)

            if item:
                print("\n✅ Successfully scraped item:")
                print(f"  Title: {item.title}")
                print(f"  URL: {item.url}")
                print(f"  Price: ¥{item.price}" if item.price else "  Price: N/A")
                print(f"  Status: {item.status}")
                print(f"  Status Text: {item.status_text}")
                print(f"  Image: {item.image_url[:60]}..." if item.image_url else "  Image: N/A")
                print(f"  Seller: {item.seller}")
                if item.description:
                    print(f"  Description: {item.description[:100]}...")
            else:
                print("❌ Failed to scrape item details")
        else:
            print("\n⚠️  No URLs found to test scraping")

    finally:
        # Close adapter
        print("\n4. Closing adapter...")
        adapter.close()
        print("✅ Test completed")

if __name__ == "__main__":
    main()
