"""
Yahoo! Auction (ヤフオク) & PayPay Flea Market 适配器
Yahoo Auction & PayPay Flea Market adapter
"""
from typing import List, Optional
from urllib.parse import quote
from playwright.sync_api import sync_playwright, Page, Browser
from loguru import logger
from .base_adapter import BaseAdapter, ScrapedItem
import re


class YahooAuctionAdapter(BaseAdapter):
    """Yahoo! Auction & PayPay Flea Market适配器"""

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
            logger.info("Yahoo Auction浏览器初始化成功")
        except Exception as e:
            logger.error(f"浏览器初始化失败: {e}")
            raise

    def build_search_url(self, keyword: str) -> str:
        """构建Yahoo Auction搜索URL"""
        encoded_keyword = quote(keyword)
        return f"https://auctions.yahoo.co.jp/search/search?p={encoded_keyword}&va={encoded_keyword}"

    def build_paypay_search_url(self, keyword: str) -> str:
        """构建PayPay Flea Market搜索URL"""
        encoded_keyword = quote(keyword)
        return f"https://paypayfleamarket.yahoo.co.jp/search/{encoded_keyword}"

    def search(self, keywords: List[str]) -> List[str]:
        """
        搜索商品并返回详情页URL列表
        同时搜索Yahoo Auction和PayPay Flea Market

        Args:
            keywords: 搜索关键词列表

        Returns:
            商品详情页URL列表
        """
        all_urls = set()

        for keyword in keywords:
            self._apply_rate_limit()

            # 搜索Yahoo Auction
            yahoo_urls = self._search_yahoo_auction(keyword)
            all_urls.update(yahoo_urls)

            self._apply_rate_limit()

            # 搜索PayPay Flea Market
            paypay_urls = self._search_paypay(keyword)
            all_urls.update(paypay_urls)

        return list(all_urls)

    def _search_yahoo_auction(self, keyword: str) -> set:
        """搜索Yahoo Auction"""
        urls = set()
        search_url = self.build_search_url(keyword)
        logger.info(f"搜索Yahoo Auction: {keyword}")

        try:
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(2000)

            # Yahoo Auction的商品链接
            links = self.page.locator('a[href*="/item/"]').all()

            for link in links[:20]:
                try:
                    href = link.get_attribute('href')
                    if href and '/item/' in href:
                        if href.startswith('/'):
                            full_url = f"https://page.auctions.yahoo.co.jp{href}"
                        elif not href.startswith('http'):
                            full_url = f"https://page.auctions.yahoo.co.jp{href}"
                        else:
                            full_url = href

                        full_url = full_url.split('?')[0]
                        urls.add(full_url)
                except Exception as e:
                    logger.debug(f"提取链接失败: {e}")
                    continue

            logger.info(f"Yahoo Auction找到 {len(urls)} 个商品")

        except Exception as e:
            logger.error(f"Yahoo Auction搜索失败 '{keyword}': {e}")

        return urls

    def _search_paypay(self, keyword: str) -> set:
        """搜索PayPay Flea Market"""
        urls = set()
        search_url = self.build_paypay_search_url(keyword)
        logger.info(f"搜索PayPay Flea Market: {keyword}")

        try:
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(2000)

            # PayPay的商品链接
            links = self.page.locator('a[href*="/item/"]').all()

            for link in links[:20]:
                try:
                    href = link.get_attribute('href')
                    if href and '/item/' in href:
                        if href.startswith('/'):
                            full_url = f"https://paypayfleamarket.yahoo.co.jp{href}"
                        elif not href.startswith('http'):
                            full_url = f"https://paypayfleamarket.yahoo.co.jp{href}"
                        else:
                            full_url = href

                        full_url = full_url.split('?')[0]
                        urls.add(full_url)
                except Exception as e:
                    logger.debug(f"提取链接失败: {e}")
                    continue

            logger.info(f"PayPay Flea Market找到 {len(urls)} 个商品")

        except Exception as e:
            logger.error(f"PayPay搜索失败 '{keyword}': {e}")

        return urls

    def scrape_item_detail(self, url: str) -> Optional[ScrapedItem]:
        """
        爬取商品详情页

        Args:
            url: 商品详情页URL

        Returns:
            ScrapedItem对象
        """
        logger.debug(f"爬取Yahoo商品详情: {url}")

        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self.page.wait_for_timeout(2000)

            # 判断是Yahoo Auction还是PayPay
            is_paypay = 'paypayfleamarket' in url

            if is_paypay:
                return self._scrape_paypay_detail(url)
            else:
                return self._scrape_yahoo_auction_detail(url)

        except Exception as e:
            logger.error(f"爬取商品详情失败 {url}: {e}")
            return None

    def _scrape_yahoo_auction_detail(self, url: str) -> Optional[ScrapedItem]:
        """爬取Yahoo Auction商品详情"""
        try:
            # 标题
            title_element = self.page.locator('h1.ProductTitle__text, h1').first
            title = title_element.inner_text().strip() if title_element.count() > 0 else ""

            if not title:
                return None

            # 价格
            price = None
            price_element = self.page.locator('.Price__value, .Price--current').first
            if price_element.count() > 0:
                price_text = price_element.inner_text().strip()
                price_match = re.search(r'[¥￥]?\s*([0-9,]+)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))

            # 状态判断
            status = "available"
            status_text = None

            page_content = self.page.content()

            # 检查拍卖是否已结束
            if '終了' in page_content or 'オークションは終了しました' in page_content:
                status = "ended"
                status_text = "終了"
            elif '入札' in page_content:
                status = "available"
                status_text = "入札中"

            # 即决价格
            buynow_element = self.page.locator('.Price--buynow, [data-label="即決価格"]').first
            if buynow_element.count() > 0:
                status_text = "即決可能"

            # 图片
            image_url = None
            img_element = self.page.locator('.ProductImage__image img, .ImageViewer__image img').first
            if img_element.count() > 0:
                image_url = img_element.get_attribute('src')

            # 卖家
            seller = None
            seller_element = self.page.locator('.Seller__name, [data-label="出品者"]').first
            if seller_element.count() > 0:
                seller = seller_element.inner_text().strip()

            return ScrapedItem(
                title=title,
                url=url,
                price=price,
                status=status,
                status_text=status_text,
                image_url=image_url,
                seller=seller,
                description=None,
                metadata={'platform': 'yahoo_auction', 'type': 'auction'}
            )

        except Exception as e:
            logger.error(f"Yahoo Auction详情爬取失败: {e}")
            return None

    def _scrape_paypay_detail(self, url: str) -> Optional[ScrapedItem]:
        """爬取PayPay Flea Market商品详情"""
        try:
            # 标题
            title_element = self.page.locator('h1, .sc-product-name').first
            title = title_element.inner_text().strip() if title_element.count() > 0 else ""

            if not title:
                return None

            # 价格
            price = None
            price_element = self.page.locator('.sc-price, [class*="price"]').first
            if price_element.count() > 0:
                price_text = price_element.inner_text().strip()
                price_match = re.search(r'[¥￥]?\s*([0-9,]+)', price_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', ''))

            # 状态
            status = "available"
            status_text = None

            page_content = self.page.content()
            if 'SOLD' in page_content or '売り切れ' in page_content:
                status = "sold"
                status_text = "売り切れ"

            # 图片
            image_url = None
            img_element = self.page.locator('.sc-product-image img, img[class*="Product"]').first
            if img_element.count() > 0:
                image_url = img_element.get_attribute('src')

            return ScrapedItem(
                title=title,
                url=url,
                price=price,
                status=status,
                status_text=status_text,
                image_url=image_url,
                seller=None,
                description=None,
                metadata={'platform': 'yahoo_auction', 'type': 'paypay'}
            )

        except Exception as e:
            logger.error(f"PayPay详情爬取失败: {e}")
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
            logger.info("Yahoo Auction浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")
