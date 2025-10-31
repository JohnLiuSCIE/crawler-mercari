"""
Lashinbang (らしんばん) 适配器
Lashinbang marketplace adapter
"""
from typing import List, Optional
from urllib.parse import quote
from playwright.sync_api import sync_playwright, Page, Browser
from loguru import logger
from .base_adapter import BaseAdapter, ScrapedItem
import re


class LashinbangAdapter(BaseAdapter):
    """らしんばん平台适配器"""

    def __init__(self, platform_config: dict, general_config: dict, headless: bool = True):
        super().__init__(platform_config, general_config)
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._init_browser()

    def _init_browser(self):
        """初始化浏览器"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page(
                user_agent=self._get_random_user_agent()
            )
            logger.info("Lashinbang浏览器初始化成功")
        except Exception as e:
            logger.error(f"浏览器初始化失败: {e}")
            raise

    def build_search_url(self, keyword: str) -> str:
        """构建Lashinbang搜索URL"""
        encoded_keyword = quote(keyword)
        # Lashinbang搜索URL可能因网站结构而异
        return f"https://www.lashinbang.com/search/?q={encoded_keyword}"

    def search(self, keywords: List[str]) -> List[str]:
        """
        搜索商品并返回详情页URL列表

        Args:
            keywords: 搜索关键词列表

        Returns:
            商品详情页URL列表
        """
        all_urls = set()

        for keyword in keywords:
            self._apply_rate_limit()

            search_url = self.build_search_url(keyword)
            logger.info(f"搜索Lashinbang: {keyword}")

            try:
                self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                self.page.wait_for_timeout(2000)

                # Lashinbang的商品链接
                # 可能是 /products/{商品ID} 或其他格式
                links = self.page.locator('a[href*="/product"], a[href*="/item"], a.product-link').all()

                for link in links[:20]:
                    try:
                        href = link.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                full_url = f"https://www.lashinbang.com{href}"
                            elif not href.startswith('http'):
                                full_url = f"https://www.lashinbang.com/{href}"
                            else:
                                full_url = href

                            full_url = full_url.split('?')[0]
                            all_urls.add(full_url)
                    except Exception as e:
                        logger.debug(f"提取链接失败: {e}")
                        continue

                logger.info(f"关键词 '{keyword}' 找到 {len(links)} 个商品链接")

            except Exception as e:
                logger.error(f"搜索失败 '{keyword}': {e}")
                continue

        return list(all_urls)

    def scrape_item_detail(self, url: str) -> Optional[ScrapedItem]:
        """
        爬取商品详情页

        Args:
            url: 商品详情页URL

        Returns:
            ScrapedItem对象
        """
        logger.debug(f"爬取Lashinbang商品详情: {url}")

        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(2000)

            # 标题
            title_element = self.page.locator('h1.product-title, h1, .item-title').first
            title = title_element.inner_text().strip() if title_element.count() > 0 else ""

            if not title:
                logger.warning(f"无法提取标题: {url}")
                return None

            # 价格
            price = None
            price_element = self.page.locator('.product-price, .price, [class*="price"]').first
            if price_element.count() > 0:
                price_text = price_element.inner_text().strip()
                price_match = re.search(r'[¥￥]?\s*([0-9,]+)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))

            # 状态判断
            status = "available"
            status_text = None

            page_content = self.page.content()

            # 检查库存状态
            if '在庫なし' in page_content or '品切' in page_content or '品切れ' in page_content:
                status = "sold"
                status_text = "在庫なし"
            elif 'SOLD' in page_content or '売り切れ' in page_content:
                status = "sold"
                status_text = "売り切れ"
            elif '在庫あり' in page_content or 'カートに追加' in page_content or '購入' in page_content:
                status = "available"
                status_text = "在庫あり"

            # 图片
            image_url = None
            img_element = self.page.locator('.product-image img, img.item-img, [class*="product"] img').first
            if img_element.count() > 0:
                image_url = img_element.get_attribute('src')
                if image_url and not image_url.startswith('http'):
                    image_url = f"https://www.lashinbang.com{image_url}"

            # 描述
            description = None
            desc_element = self.page.locator('.product-description, .item-desc, [class*="description"]').first
            if desc_element.count() > 0:
                description = desc_element.inner_text().strip()[:500]

            return ScrapedItem(
                title=title,
                url=url,
                price=price,
                status=status,
                status_text=status_text,
                image_url=image_url,
                seller="らしんばん",
                description=description,
                metadata={'platform': 'lashinbang'}
            )

        except Exception as e:
            logger.error(f"爬取商品详情失败 {url}: {e}")
            return None

    def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Lashinbang浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")
