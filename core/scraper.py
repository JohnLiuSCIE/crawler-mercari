"""
核心爬虫引擎
Core scraper engine with change detection
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from models.database import (
    Item, Platform, Listing, ChangeEvent, ScrapeRun, PriceHistory,
    SessionLocal, init_db
)
from adapters.base_adapter import BaseAdapter, ScrapedItem, SearchResult
from config.settings import items_config, platforms_config


class ScraperEngine:
    """核心爬虫引擎 - 负责协调所有适配器并检测变化"""

    def __init__(self, max_workers: int = 4):
        self.db: Optional[Session] = None
        self.adapters: Dict[str, BaseAdapter] = {}
        self.current_run: Optional[ScrapeRun] = None
        self.max_workers = max_workers  # 并发线程数
        self._db_lock = threading.Lock()  # 数据库操作锁

    def initialize_database(self):
        """初始化数据库和基础数据"""
        init_db()
        self.db = SessionLocal()
        logger.info("数据库初始化完成")

        # 初始化平台数据
        self._init_platforms()

        # 初始化商品数据
        self._init_items()

    def _init_platforms(self):
        """初始化平台数据"""
        platform_configs = platforms_config['platforms']

        for platform_key, config in platform_configs.items():
            if not config.get('enabled', True):
                continue

            # 检查平台是否已存在
            platform = self.db.query(Platform).filter_by(name=platform_key).first()

            if not platform:
                platform = Platform(
                    name=platform_key,
                    name_cn=config['name_cn'],
                    base_url=config['base_url'],
                    enabled=config.get('enabled', True)
                )
                self.db.add(platform)
                logger.info(f"添加平台: {config['name_cn']}")

        self.db.commit()

    def _init_items(self):
        """初始化商品数据"""
        for item_config in items_config['items']:
            # 检查商品是否已存在
            item = self.db.query(Item).filter_by(id=item_config['id']).first()

            if not item:
                item = Item(
                    id=item_config['id'],
                    name_cn=item_config['name_cn'],
                    name_jp=item_config['name_jp'],
                    series=item_config['series'],
                    character=item_config['character'],
                    circle=item_config['circle'],
                    event=item_config.get('event'),
                    artist=item_config['artist'],
                    search_keywords=item_config['search_keywords']
                )
                self.db.add(item)
                logger.info(f"添加商品: {item_config['name_cn']}")
            else:
                # 更新搜索关键词（可能会变化）
                item.search_keywords = item_config['search_keywords']
                item.updated_at = datetime.utcnow()

        self.db.commit()

    def start_scrape_run(self) -> ScrapeRun:
        """开始一次爬取运行"""
        run = ScrapeRun(
            started_at=datetime.utcnow(),
            status='running'
        )
        self.db.add(run)
        self.db.commit()
        self.current_run = run
        logger.info(f"开始爬取运行 #{run.id}")
        return run

    def complete_scrape_run(self, status: str = 'completed', errors: str = None):
        """完成爬取运行"""
        if self.current_run:
            self.current_run.completed_at = datetime.utcnow()
            self.current_run.status = status
            if errors:
                self.current_run.errors = errors
            self.db.commit()
            logger.info(f"爬取运行 #{self.current_run.id} 完成: {status}")

    def process_scraped_result(
        self,
        item: Item,
        platform: Platform,
        scraped_item: ScrapedItem
    ) -> Optional[Listing]:
        """
        处理爬取结果，检测变化并更新数据库
        线程安全版本

        Returns:
            Listing对象如果有变化，否则返回None
        """
        # 整个方法需要锁保护，因为涉及多个数据库操作
        with self._db_lock:
            # 查找是否已存在此商品
            existing_listing = self.db.query(Listing).filter_by(
                item_id=item.id,
                platform_id=platform.id,
                url=scraped_item.url
            ).first()

            now = datetime.utcnow()
            changes_detected = []

            if not existing_listing:
                # 新发现的商品
                listing = Listing(
                    item_id=item.id,
                    platform_id=platform.id,
                    title=scraped_item.title,
                    url=scraped_item.url,
                    price=scraped_item.price,
                    image_url=scraped_item.image_url,
                    status=scraped_item.status,
                    status_text=scraped_item.status_text,
                    seller=scraped_item.seller,
                    description=scraped_item.description,
                    extra_metadata=scraped_item.metadata,
                    first_seen=now,
                    last_seen=now,
                    last_checked=now,
                    is_active=True
                )
                self.db.add(listing)
                self.db.flush()  # 获取ID

                # 创建新商品事件
                change_event = ChangeEvent(
                    listing_id=listing.id,
                    event_type='new_item',
                    description=f"发现新商品: {scraped_item.title}",
                    new_value=f"¥{scraped_item.price}" if scraped_item.price else "N/A",
                    notified=False
                )
                self.db.add(change_event)
                changes_detected.append('new_item')

                # 记录初始价格
                if scraped_item.price:
                    price_history = PriceHistory(
                        listing_id=listing.id,
                        price=scraped_item.price,
                        recorded_at=now
                    )
                    self.db.add(price_history)

                logger.info(f"新商品: {scraped_item.title} - ¥{scraped_item.price}")

            else:
                # 更新现有商品
                listing = existing_listing
                listing.last_seen = now
                listing.last_checked = now

                # 检测价格变化
                if scraped_item.price and scraped_item.price != listing.price:
                    old_price = listing.price
                    change_event = ChangeEvent(
                        listing_id=listing.id,
                        event_type='price_change',
                        description=f"价格变化: ¥{old_price} → ¥{scraped_item.price}",
                        old_value=str(old_price),
                        new_value=str(scraped_item.price),
                        notified=False
                    )
                    self.db.add(change_event)
                    changes_detected.append('price_change')

                    # 记录价格历史
                    price_history = PriceHistory(
                        listing_id=listing.id,
                        price=scraped_item.price,
                        recorded_at=now
                    )
                    self.db.add(price_history)

                    listing.price = scraped_item.price
                    logger.info(f"价格变化: {scraped_item.title} - ¥{old_price} → ¥{scraped_item.price}")

                # 检测状态变化
                if scraped_item.status != listing.status:
                    old_status = listing.status
                    event_type = 'sold_out' if scraped_item.status == 'sold' else 'status_change'

                    if scraped_item.status == 'available' and old_status == 'sold':
                        event_type = 'back_in_stock'

                    change_event = ChangeEvent(
                        listing_id=listing.id,
                        event_type=event_type,
                        description=f"状态变化: {old_status} → {scraped_item.status}",
                        old_value=old_status,
                        new_value=scraped_item.status,
                        notified=False
                    )
                    self.db.add(change_event)
                    changes_detected.append(event_type)

                    listing.status = scraped_item.status
                    listing.status_text = scraped_item.status_text
                    logger.info(f"状态变化: {scraped_item.title} - {old_status} → {scraped_item.status}")

                # 更新其他字段
                if scraped_item.image_url:
                    listing.image_url = scraped_item.image_url
                if scraped_item.seller:
                    listing.seller = scraped_item.seller
                if scraped_item.description:
                    listing.description = scraped_item.description

            self.db.commit()

            # 更新运行统计
            if self.current_run:
                if changes_detected:
                    if 'new_item' in changes_detected:
                        self.current_run.new_listings_found += 1
                    self.current_run.changes_detected += len(changes_detected)

            return listing if changes_detected else None

    def _scrape_platform(self, item: Item, platform_name: str, adapter: BaseAdapter) -> Dict[str, Any]:
        """
        在单个平台上爬取单个商品（用于并发执行）

        Returns:
            包含结果统计的字典
        """
        result_stats = {
            'platform_name': platform_name,
            'new_listings': 0,
            'changes': 0,
            'error': None,
            'success': False
        }

        try:
            # 获取平台信息（使用锁保护数据库查询）
            with self._db_lock:
                platform = self.db.query(Platform).filter_by(name=platform_name).first()
                if not platform or not platform.enabled:
                    return result_stats

            logger.info(f"  [{threading.current_thread().name}] 在 {platform.name_cn} 上搜索 {item.name_cn}...")

            # 执行爬取（不需要锁，因为adapter有自己的browser）
            result = adapter.scrape_item({
                'id': item.id,
                'name_cn': item.name_cn,
                'name_jp': item.name_jp,
                'search_keywords': item.search_keywords,
                'circle': item.circle,
                'artist': item.artist
            })

            # 处理结果（process_scraped_result内部已有锁）
            for scraped_item in result.results:
                listing = self.process_scraped_result(item, platform, scraped_item)
                if listing:
                    result_stats['changes'] += 1

            if result.results:
                result_stats['new_listings'] = len(result.results)

            result_stats['success'] = True
            logger.info(f"  ✓ {platform.name_cn}: 找到 {len(result.results)} 个结果")

        except Exception as e:
            logger.error(f"爬取失败 {item.name_cn} @ {platform_name}: {e}")
            result_stats['error'] = str(e)
            with self._db_lock:
                if self.current_run:
                    self.current_run.error_count += 1

        return result_stats

    def scrape_all(self, adapter_instances: Dict[str, BaseAdapter], parallel: bool = True) -> Dict[str, Any]:
        """
        使用所有适配器爬取所有商品

        Args:
            adapter_instances: 字典，键为平台名称，值为适配器实例
            parallel: 是否使用并发爬取（默认True）

        Returns:
            爬取结果统计
        """
        self.adapters = adapter_instances
        stats = {
            'items_checked': 0,
            'platforms_checked': 0,
            'new_listings': 0,
            'changes': 0,
            'errors': 0
        }

        # 获取所有要监控的商品
        items = self.db.query(Item).all()

        if parallel and len(self.adapters) > 1:
            # 并发模式：对每个商品，并发爬取所有平台
            logger.info(f"使用并发模式爬取，最多 {self.max_workers} 个线程")

            for item in items:
                logger.info(f"开始爬取商品: {item.name_cn}")

                # 使用ThreadPoolExecutor并发爬取所有平台
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # 提交所有平台的爬取任务
                    future_to_platform = {
                        executor.submit(self._scrape_platform, item, platform_name, adapter): platform_name
                        for platform_name, adapter in self.adapters.items()
                    }

                    # 等待所有任务完成并收集结果
                    for future in as_completed(future_to_platform):
                        platform_name = future_to_platform[future]
                        try:
                            result_stats = future.result()
                            if result_stats['success']:
                                stats['platforms_checked'] += 1
                                stats['new_listings'] += result_stats['new_listings']
                                stats['changes'] += result_stats['changes']
                            else:
                                if result_stats['error']:
                                    stats['errors'] += 1
                        except Exception as e:
                            logger.error(f"获取 {platform_name} 结果时出错: {e}")
                            stats['errors'] += 1

                stats['items_checked'] += 1

        else:
            # 顺序模式：一个接一个爬取
            logger.info("使用顺序模式爬取")

            for item in items:
                logger.info(f"开始爬取商品: {item.name_cn}")

                for platform_name, adapter in self.adapters.items():
                    result_stats = self._scrape_platform(item, platform_name, adapter)
                    if result_stats['success']:
                        stats['platforms_checked'] += 1
                        stats['new_listings'] += result_stats['new_listings']
                        stats['changes'] += result_stats['changes']
                    else:
                        if result_stats['error']:
                            stats['errors'] += 1

                stats['items_checked'] += 1

        # 更新运行统计
        with self._db_lock:
            if self.current_run:
                self.current_run.items_checked = stats['items_checked']
                self.current_run.platforms_checked = stats['platforms_checked']
                self.db.commit()

        return stats

    def get_pending_notifications(self) -> List[ChangeEvent]:
        """获取待发送的通知"""
        return self.db.query(ChangeEvent).filter_by(notified=False).all()

    def mark_notification_sent(self, event_id: int):
        """标记通知已发送"""
        event = self.db.query(ChangeEvent).get(event_id)
        if event:
            event.notified = True
            self.db.commit()

    def close(self):
        """关闭资源"""
        if self.db:
            self.db.close()
        logger.info("爬虫引擎已关闭")
