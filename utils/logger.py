"""
日志配置
Logger configuration
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import settings

# 创建logs目录
logs_dir = Path(settings.log_file).parent
logs_dir.mkdir(exist_ok=True)

# 移除默认的handler
logger.remove()

# 添加控制台输出
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    colorize=True
)

# 添加文件输出
logger.add(
    settings.log_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=settings.log_level,
    rotation="10 MB",  # 日志文件大小超过10MB时轮转
    retention="30 days",  # 保留30天
    compression="zip",  # 压缩旧日志
    encoding="utf-8"
)

def get_logger():
    """获取logger实例"""
    return logger
