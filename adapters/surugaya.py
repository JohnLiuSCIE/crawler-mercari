"""
Suruga-ya (駿河屋) 适配器
Suruga-ya marketplace adapter
"""
from typing import List, Optional
from urllib.parse import quote
from playwright.sync_api import sync_playwright, Page, Browser
from loguru import logger
from .base_adapter import BaseAdapter, ScrapedItem
import re


class SurugayaAdapter(BaseAdapter):
    """駿河屋平台适配器"""

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
            logger.info("初始化Suruga-ya浏览器...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page(
                user_agent=self._get_random_user_agent()
            )
            self._browser_initialized = True
            logger.info("Suruga-ya浏览器初始化成功")
        except Exception as e:
            logger.error(f"Suruga-ya浏览器初始化失败: {e}")
            raise

    def build_search_url(self, keyword: str) -> str:
        """构建Suruga-ya搜索URL"""
        encoded_keyword = quote(keyword)
        return f"https://www.suruga-ya.jp/search?category=&search_word={encoded_keyword}"

    def search(self, keywords: List[str]) -> List[str]:
        """
        搜索商品并返回详情页URL列表

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
            logger.info(f"搜索Suruga-ya: {keyword}")

            try:
                self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                self.page.wait_for_timeout(2000)

                # Suruga-ya的商品链接
                # 通常是 /product/detail/{商品ID}
                links = self.page.locator('a[href*="/product/detail/"]').all()

                for link in links[:20]:
                    try:
                        href = link.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                full_url = f"https://www.suruga-ya.jp{href}"
                            elif not href.startswith('http'):
                                full_url = f"https://www.suruga-ya.jp/{href}"
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
        self._ensure_browser()  # 确保浏览器已初始化
        logger.debug(f"爬取Suruga-ya商品详情: {url}")

        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # 等待标题元素出现
            try:
                self.page.wait_for_selector('h1, .item_title, [class*="title"]', timeout=10000, state='visible')
            except Exception as e:
                logger.warning(f"等待标题元素超时: {url}")

            self.page.wait_for_timeout(1000)

            # 标题 - 尝试多个选择器
            title = ""
            for selector in ['h1.title', 'h1', '.item_title', '.product-title', '[itemprop="name"]']:
                title_element = self.page.locator(selector).first
                if title_element.count() > 0:
                    title = title_element.inner_text().strip()
                    if title:
                        break

            if not title:
                logger.warning(f"无法提取标题: {url}")
                return None

            # 价格 - 尝试多个选择器
            price = None
            for selector in ['.price', '.item_price', '[class*="price"]', '[itemprop="price"]', 'p.price']:
                price_element = self.page.locator(selector).first
                if price_element.count() > 0:
                    price_text = price_element.inner_text().strip()
                    price_match = re.search(r'[¥￥]?\s*([0-9,]+)', price_text)
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))
                        break

            # 状态判断
            status = "available"
            status_text = None

            page_content = self.page.content()

            # 检查库存状态
            if '品切' in page_content or '品切れ' in page_content or '通販品切' in page_content:
                status = "sold"
                status_text = "品切"
            elif '在庫なし' in page_content or '売り切れ' in page_content:
                status = "sold"
                status_text = "在庫なし"
            elif 'カートに入れる' in page_content or 'かごに入れる' in page_content:
                status = "available"
                status_text = "在庫あり"

            # 图片
            image_url = None
            # 尝试多个选择器来获取商品图片
            for selector in ['#main_image', '.item_img img', 'img[itemprop="image"]', '.product-img img']:
                img_element = self.page.locator(selector).first
                if img_element.count() > 0:
                    temp_url = img_element.get_attribute('src')
                    # 过滤掉close.png等无效图片
                    if temp_url and 'close.png' not in temp_url and temp_url not in ['', '#']:
                        if not temp_url.startswith('http'):
                            image_url = f"https://www.suruga-ya.jp{temp_url}"
                        else:
                            image_url = temp_url
                        break

            # 描述
            description = None
            desc_element = self.page.locator('.item_detail, .product_detail, [class*="description"]').first
            if desc_element.count() > 0:
                description = desc_element.inner_text().strip()[:500]

            return ScrapedItem(
                title=title,
                url=url,
                price=price,
                status=status,
                status_text=status_text,
                image_url=image_url,
                seller="駿河屋",  # Suruga-ya自己售卖
                description=description,
                metadata={'platform': 'surugaya'}
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
            logger.info("Suruga-ya浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")
