"""
基础适配器抽象类
Base adapter abstract class for all platform scrapers
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import time
import random
from loguru import logger


@dataclass
class ScrapedItem:
    """爬取的商品数据结构"""
    title: str
    url: str
    price: Optional[float]
    status: str  # 'available', 'sold', 'ended'
    status_text: Optional[str]
    image_url: Optional[str] = None
    seller: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class SearchResult:
    """搜索结果"""
    platform: str
    item_id: int
    keyword: str
    results: List[ScrapedItem]
    search_time: datetime
    error: Optional[str] = None


class BaseAdapter(ABC):
    """所有平台适配器的基类"""

    def __init__(self, platform_config: dict, general_config: dict):
        """
        初始化适配器

        Args:
            platform_config: 平台特定配置
            general_config: 通用配置
        """
        self.platform_config = platform_config
        self.general_config = general_config
        self.name = platform_config['name']
        self.name_cn = platform_config['name_cn']
        self.base_url = platform_config['base_url']
        self.rate_limit = platform_config.get('rate_limit', {})
        self.selectors = platform_config.get('selectors', {})

        # 速率限制
        self.delay_between_requests = self.rate_limit.get('delay_between_requests', 3)
        self.last_request_time = 0

        logger.info(f"初始化适配器: {self.name_cn} ({self.name})")

    def _apply_rate_limit(self):
        """应用速率限制"""
        if self.last_request_time > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay_between_requests:
                sleep_time = self.delay_between_requests - elapsed
                # 添加随机抖动
                sleep_time += random.uniform(0, 1)
                logger.debug(f"速率限制: 等待 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        user_agents = self.general_config.get('user_agents', [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ])
        return random.choice(user_agents)

    @abstractmethod
    def build_search_url(self, keyword: str) -> str:
        """
        构建搜索URL

        Args:
            keyword: 搜索关键词

        Returns:
            完整的搜索URL
        """
        pass

    @abstractmethod
    def search(self, keywords: List[str]) -> List[str]:
        """
        执行搜索并返回商品详情页URL列表

        Args:
            keywords: 搜索关键词列表

        Returns:
            商品详情页URL列表
        """
        pass

    @abstractmethod
    def scrape_item_detail(self, url: str) -> Optional[ScrapedItem]:
        """
        爬取商品详情页

        Args:
            url: 商品详情页URL

        Returns:
            ScrapedItem对象，如果失败则返回None
        """
        pass

    def scrape_item(self, item_config: dict) -> SearchResult:
        """
        爬取单个商品的所有信息

        Args:
            item_config: 商品配置字典（来自items.yaml）

        Returns:
            SearchResult对象
        """
        logger.info(f"开始爬取: {item_config['name_cn']} @ {self.name_cn}")
        start_time = datetime.now()

        try:
            # 获取搜索关键词
            keywords = item_config.get('search_keywords', [])
            if not keywords:
                logger.warning(f"商品 {item_config['name_cn']} 没有配置搜索关键词")
                return SearchResult(
                    platform=self.name,
                    item_id=item_config['id'],
                    keyword="",
                    results=[],
                    search_time=start_time,
                    error="没有配置搜索关键词"
                )

            # 搜索商品
            detail_urls = self.search(keywords)
            logger.info(f"找到 {len(detail_urls)} 个潜在商品")

            # 爬取每个商品详情
            results = []
            for url in detail_urls:
                self._apply_rate_limit()

                try:
                    item = self.scrape_item_detail(url)
                    if item:
                        # 验证是否匹配（可以在这里添加更精确的匹配逻辑）
                        if self._is_exact_match(item, item_config):
                            results.append(item)
                            logger.info(f"找到匹配商品: {item.title[:50]}... - 状态: {item.status} - 价格: ¥{item.price}")
                        else:
                            logger.debug(f"商品不匹配，跳过: {item.title[:50]}...")
                except Exception as e:
                    logger.error(f"爬取商品详情失败 {url}: {e}")
                    continue

            return SearchResult(
                platform=self.name,
                item_id=item_config['id'],
                keyword=", ".join(keywords[:2]),
                results=results,
                search_time=start_time,
                error=None
            )

        except Exception as e:
            logger.error(f"爬取失败: {e}")
            return SearchResult(
                platform=self.name,
                item_id=item_config['id'],
                keyword="",
                results=[],
                search_time=start_time,
                error=str(e)
            )

    def _is_exact_match(self, scraped_item: ScrapedItem, item_config: dict) -> bool:
        """
        检查爬取的商品是否与目标商品精确匹配

        Args:
            scraped_item: 爬取的商品
            item_config: 目标商品配置

        Returns:
            是否匹配
        """
        title_lower = scraped_item.title.lower()

        # 必须包含角色名
        character = item_config.get('character', '')
        if character and character not in scraped_item.title:
            return False

        # 必须包含社团名
        circle = item_config.get('circle', '')
        if circle and circle not in scraped_item.title:
            return False

        # 如果有绘师，应该包含绘师名（可选）
        artist = item_config.get('artist', '')
        # 注意：有些商品可能不会在标题中标注绘师，所以这个条件可以放宽

        # 必须是抱枕相关
        dakimakura_keywords = ['抱き枕', 'だき枕', 'ダキ枕', 'カバー', '抱枕']
        if not any(kw in scraped_item.title for kw in dakimakura_keywords):
            return False

        return True

    @abstractmethod
    def close(self):
        """关闭适配器，清理资源"""
        pass

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
