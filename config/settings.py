"""
全局配置管理
Global configuration management
"""
import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic_settings import BaseSettings
from pydantic import Field


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 配置文件路径
CONFIG_DIR = BASE_DIR / "config"
ITEMS_CONFIG = CONFIG_DIR / "items.yaml"
PLATFORMS_CONFIG = CONFIG_DIR / "platforms.yaml"


class Settings(BaseSettings):
    """应用设置"""

    # 项目信息
    app_name: str = "Japanese Dakimakura Scraper"
    app_version: str = "1.0.0"

    # 数据库配置
    database_url: str = Field(
        default=f"sqlite:///{BASE_DIR}/scraper.db",
        description="数据库连接URL"
    )

    # 调度配置
    schedule_enabled: bool = Field(default=True, description="是否启用定时任务")
    schedule_hour_1: int = Field(default=9, description="第一次运行时间（小时）")
    schedule_hour_2: int = Field(default=21, description="第二次运行时间（小时）")
    schedule_timezone: str = Field(default="Asia/Tokyo", description="时区")

    # 邮件通知配置
    email_enabled: bool = Field(default=True, description="是否启用邮件通知")
    smtp_server: str = Field(default="smtp.gmail.com", description="SMTP服务器地址")
    smtp_port: int = Field(default=587, description="SMTP端口")
    smtp_use_tls: bool = Field(default=True, description="使用TLS加密")
    smtp_username: str = Field(default="", description="SMTP用户名")
    smtp_password: str = Field(default="", description="SMTP密码")
    email_from: str = Field(default="", description="发件人邮箱")
    email_to: str = Field(default="", description="收件人邮箱（多个用逗号分隔）")

    # 通知配置
    notify_on_new_items: bool = Field(default=True, description="发现新商品时通知")
    notify_on_price_change: bool = Field(default=True, description="价格变化时通知")
    notify_on_sold_out: bool = Field(default=True, description="商品售罄时通知")
    notify_on_creator_updates: bool = Field(default=True, description="创作者更新时通知")

    # 爬虫配置
    scraper_mode: str = Field(
        default="playwright",
        description="爬虫模式: requests, selenium, playwright"
    )
    headless: bool = Field(default=True, description="无头浏览器模式")
    screenshot_on_error: bool = Field(default=True, description="出错时截图")

    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: str = Field(
        default=str(BASE_DIR / "logs" / "scraper.log"),
        description="日志文件路径"
    )

    # Twitter API配置（可选）
    twitter_api_key: Optional[str] = Field(default=None, description="Twitter API Key")
    twitter_api_secret: Optional[str] = Field(default=None, description="Twitter API Secret")
    twitter_access_token: Optional[str] = Field(default=None, description="Twitter Access Token")
    twitter_access_secret: Optional[str] = Field(default=None, description="Twitter Access Secret")

    # 代理配置
    use_proxy: bool = Field(default=False, description="是否使用代理")
    proxy_url: Optional[str] = Field(default=None, description="代理URL")

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def load_items_config() -> dict:
    """加载商品配置"""
    with open(ITEMS_CONFIG, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_platforms_config() -> dict:
    """加载平台配置"""
    with open(PLATFORMS_CONFIG, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# 全局设置实例
settings = Settings()

# 加载YAML配置
items_config = load_items_config()
platforms_config = load_platforms_config()
