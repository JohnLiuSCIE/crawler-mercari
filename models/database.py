"""
数据库模型定义
Database models
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config.settings import settings

Base = declarative_base()


class Item(Base):
    """商品定义表 - 存储要监控的7个抱枕套"""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name_cn = Column(String(200), nullable=False, comment="中文名称")
    name_jp = Column(String(200), nullable=False, comment="日文名称")
    series = Column(String(100), nullable=False, comment="所属系列")
    character = Column(String(100), nullable=False, comment="角色名")
    circle = Column(String(100), nullable=False, comment="社团名")
    event = Column(String(100), nullable=True, comment="活动名称")
    artist = Column(String(100), nullable=False, comment="绘师")
    search_keywords = Column(JSON, nullable=False, comment="搜索关键词列表")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    listings = relationship("Listing", back_populates="item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item(id={self.id}, name_cn='{self.name_cn}', circle='{self.circle}')>"


class Platform(Base):
    """平台表"""
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, comment="平台名称")
    name_cn = Column(String(50), nullable=False, comment="中文名称")
    base_url = Column(String(200), nullable=False, comment="基础URL")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    listings = relationship("Listing", back_populates="platform", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Platform(id={self.id}, name='{self.name}')>"


class Listing(Base):
    """商品列表 - 存储在各平台发现的商品信息"""
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False, comment="关联商品ID")
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False, comment="关联平台ID")

    # 商品信息
    title = Column(String(500), nullable=False, comment="商品标题")
    url = Column(String(500), nullable=False, comment="商品详情页URL")
    price = Column(Float, nullable=True, comment="价格（日元）")
    image_url = Column(String(500), nullable=True, comment="商品图片URL")

    # 状态信息
    status = Column(String(20), nullable=False, comment="状态: available, sold, ended")
    status_text = Column(String(100), nullable=True, comment="状态文本（原始）")

    # 其他信息
    seller = Column(String(200), nullable=True, comment="卖家")
    description = Column(Text, nullable=True, comment="描述")
    extra_metadata = Column(JSON, nullable=True, comment="其他元数据")

    # 时间戳
    first_seen = Column(DateTime, default=datetime.utcnow, comment="首次发现时间")
    last_seen = Column(DateTime, default=datetime.utcnow, comment="最后一次看到")
    last_checked = Column(DateTime, default=datetime.utcnow, comment="最后检查时间")

    # 是否有效
    is_active = Column(Boolean, default=True, comment="是否仍然活跃")

    # 关联
    item = relationship("Item", back_populates="listings")
    platform = relationship("Platform", back_populates="listings")
    price_history = relationship("PriceHistory", back_populates="listing", cascade="all, delete-orphan")
    changes = relationship("ChangeEvent", back_populates="listing", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Listing(id={self.id}, title='{self.title[:30]}...', status='{self.status}', price={self.price})>"


class PriceHistory(Base):
    """价格历史记录"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    price = Column(Float, nullable=False, comment="价格")
    recorded_at = Column(DateTime, default=datetime.utcnow, comment="记录时间")

    # 关联
    listing = relationship("Listing", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory(listing_id={self.listing_id}, price={self.price}, recorded_at={self.recorded_at})>"


class ChangeEvent(Base):
    """变化事件 - 记录重要的变化（新商品、售罄、价格变化等）"""
    __tablename__ = "change_events"

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=True)
    event_type = Column(String(50), nullable=False, comment="事件类型: new_item, sold_out, price_change, back_in_stock")
    description = Column(Text, nullable=True, comment="事件描述")
    old_value = Column(String(200), nullable=True, comment="旧值")
    new_value = Column(String(200), nullable=True, comment="新值")
    notified = Column(Boolean, default=False, comment="是否已通知")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    listing = relationship("Listing", back_populates="changes")

    def __repr__(self):
        return f"<ChangeEvent(id={self.id}, type='{self.event_type}', notified={self.notified})>"


class ScrapeRun(Base):
    """爬取运行记录"""
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, comment="状态: running, completed, failed")
    items_checked = Column(Integer, default=0, comment="检查的商品数")
    platforms_checked = Column(Integer, default=0, comment="检查的平台数")
    new_listings_found = Column(Integer, default=0, comment="发现的新商品")
    changes_detected = Column(Integer, default=0, comment="检测到的变化")
    errors = Column(Text, nullable=True, comment="错误信息")
    error_count = Column(Integer, default=0, comment="错误数量")

    def __repr__(self):
        return f"<ScrapeRun(id={self.id}, status='{self.status}', started_at={self.started_at})>"


class CreatorUpdate(Base):
    """创作者更新记录"""
    __tablename__ = "creator_updates"

    id = Column(Integer, primary_key=True)
    creator_name = Column(String(100), nullable=False, comment="创作者名称")
    platform = Column(String(50), nullable=False, comment="平台: twitter, booth, fanbox, etc")
    update_type = Column(String(50), nullable=False, comment="更新类型: new_product, restock, event, announcement")
    title = Column(String(500), nullable=True, comment="标题")
    content = Column(Text, nullable=True, comment="内容")
    url = Column(String(500), nullable=True, comment="链接")
    posted_at = Column(DateTime, nullable=True, comment="发布时间")
    discovered_at = Column(DateTime, default=datetime.utcnow, comment="发现时间")
    notified = Column(Boolean, default=False, comment="是否已通知")

    def __repr__(self):
        return f"<CreatorUpdate(id={self.id}, creator='{self.creator_name}', type='{self.update_type}')>"


# 数据库引擎和会话
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成！")


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
