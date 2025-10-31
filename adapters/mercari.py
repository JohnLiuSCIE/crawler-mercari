"""
Mercari (メルカリ) 适配器
Mercari marketplace adapter
"""
from typing import List, Optional
from urllib.parse import quote
from playwright.sync_api import sync_playwright, Page, Browser
from loguru import logger
from .base_adapter import BaseAdapter, ScrapedItem
import re


class MercariAdapter(BaseAdapter):
    """Mercari平台适配器"""

    def __init__(self, platform_config: dict, general_config: dict, headless: bool = True):
        super().__init__(platform_config, general_config)
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._browser_initialized = False

    def _ensure_browser(self):
        """延迟初始化浏览器 - 只在第一次使用时创建（线程安全）"""
        if self._browser_initialized:
            return

        try:
            logger.info("初始化Mercari浏览器...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page(
                user_agent=self._get_random_user_agent()
            )
            self._browser_initialized = True
            logger.info("Mercari浏览器初始化成功")
        except Exception as e:
            logger.error(f"Mercari浏览器初始化失败: {e}")
            raise

    def build_search_url(self, keyword: str) -> str:
        """构建Mercari搜索URL"""
        encoded_keyword = quote(keyword)
        # Mercari搜索URL格式
        return f"https://jp.mercari.com/search?keyword={encoded_keyword}"

    def search(self, keywords: List[str]) -> List[str]:
        """
        在Mercari搜索商品并返回详情页URL列表

        Args:
            keywords: 搜索关键词列表

        Returns:
            商品详情页URL列表
        """
        self._ensure_browser()  # 延迟初始化浏览器
        all_urls = set()

        for keyword in keywords:
            self._apply_rate_limit()

            search_url = self.build_search_url(keyword)
            logger.info(f"搜索Mercari: {keyword}")

            try:
                self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                self.page.wait_for_timeout(2000)  # 等待页面渲染

                # Mercari使用React，需要等待内容加载
                # 查找商品链接
                # Mercari的商品链接通常是 /item/m{数字ID}
                links = self.page.locator('a[href*="/item/m"]').all()

                for link in links[:20]:  # 限制每个关键词只取前20个结果
                    try:
                        href = link.get_attribute('href')
                        if href:
                            # 构建完整URL
                            if href.startswith('/'):
                                full_url = f"https://jp.mercari.com{href}"
                            else:
                                full_url = href

                            # 移除查询参数，只保留商品ID
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
        爬取Mercari商品详情页

        Args:
            url: 商品详情页URL

        Returns:
            ScrapedItem对象
        """
        self._ensure_browser()  # 确保浏览器已初始化
        logger.debug(f"爬取Mercari商品详情: {url}")

        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # 等待标题元素出现，这样可以确保页面完全加载
            # 使用较长的超时时间以应对反爬虫机制
            try:
                self.page.wait_for_selector('h1', timeout=15000, state='visible')
            except Exception as e:
                logger.warning(f"等待标题元素超时: {url}")
                logger.debug(f"错误: {e}")
                # 即使超时也继续尝试提取，可能页面已经部分加载

            # 检查是否遇到反爬虫页面
            page_content = self.page.content()
            page_url = self.page.url
            page_title = self.page.title()

            # 如果页面被重定向或显示错误
            if page_url != url or "404" in page_content or "not found" in page_content.lower():
                logger.warning(f"页面可能已不存在或被重定向: {url} -> {page_url}")
                logger.debug(f"页面标题: {page_title}")

            # 提取商品标题
            title_element = self.page.locator('h1, [data-testid="name"]').first
            title = title_element.inner_text().strip() if title_element.count() > 0 else ""

            if not title:
                logger.warning(f"无法提取标题: {url}")
                logger.debug(f"实际URL: {page_url}")
                logger.debug(f"页面标题: {page_title}")
                return None

            # 提取价格
            price = None
            price_element = self.page.locator('mer-price, [data-testid="price"], .item-price').first
            if price_element.count() > 0:
                price_text = price_element.inner_text().strip()
                # 提取数字
                price_match = re.search(r'[¥￥]?\s*([0-9,]+)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))

            # 判断商品状态
            status = "available"
            status_text = None

            # 检查是否已售出
            sold_indicators = [
                '売り切れ',
                'SOLD',
                '売切れ',
                '販売終了',
                'この商品は売り切れです'
            ]

            page_content = self.page.content()
            for indicator in sold_indicators:
                if indicator in page_content:
                    status = "sold"
                    status_text = indicator
                    break

            # 如果没有找到售出标识，检查是否有购买按钮
            if status == "available":
                buy_button = self.page.locator('[data-testid="buy-button"], mer-button:has-text("購入手続きへ")').first
                if buy_button.count() == 0:
                    # 没有购买按钮，可能已售出
                    status = "sold"
                    status_text = "购买按钮不可用"

            # 提取图片URL
            image_url = None
            img_element = self.page.locator('img[data-testid="item-image"], .item-photo img, mer-carousel img').first
            if img_element.count() > 0:
                image_url = img_element.get_attribute('src')

            # 提取卖家信息
            seller = None
            seller_element = self.page.locator('[data-testid="seller-name"], .seller-name, mer-text:has-text("出品者")').first
            if seller_element.count() > 0:
                seller = seller_element.inner_text().strip()

            # 提取描述
            description = None
            desc_element = self.page.locator('[data-testid="description"], .item-description, mer-text.description').first
            if desc_element.count() > 0:
                description = desc_element.inner_text().strip()[:500]  # 限制长度

            return ScrapedItem(
                title=title,
                url=url,
                price=price,
                status=status,
                status_text=status_text,
                image_url=image_url,
                seller=seller,
                description=description,
                metadata={
                    'platform': 'mercari',
                    'scrape_method': 'playwright'
                }
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
            logger.info("Mercari浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")
