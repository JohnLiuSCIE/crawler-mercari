"""
CSV报告生成器
CSV report generator
"""
import csv
from io import StringIO
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.database import Item, Platform, Listing, SessionLocal


class CSVGenerator:
    """生成CSV格式的报告"""

    def __init__(self):
        self.db: Optional[Session] = None

    def connect_db(self):
        """连接数据库"""
        self.db = SessionLocal()

    def generate_csv(self) -> str:
        """
        生成CSV格式的报告

        Returns:
            CSV字符串
        """
        if not self.db:
            self.connect_db()

        # 获取所有商品和平台
        items = self.db.query(Item).order_by(Item.id).all()
        platforms = self.db.query(Platform).filter_by(enabled=True).order_by(Platform.id).all()

        # 创建CSV
        output = StringIO()
        writer = csv.writer(output)

        # 写入表头
        header = ['商品名称', 'ID', '社团', '绘师']
        for platform in platforms:
            header.append(f'{platform.name_cn}_状态')
            header.append(f'{platform.name_cn}_价格')
            header.append(f'{platform.name_cn}_链接')
        writer.writerow(header)

        # 写入数据
        for item in items:
            row = [item.name_cn, item.id, item.circle, item.artist]

            for platform in platforms:
                # 查询该商品在该平台的列表
                listings = self.db.query(Listing).filter(
                    and_(
                        Listing.item_id == item.id,
                        Listing.platform_id == platform.id,
                        Listing.is_active == True
                    )
                ).all()

                if not listings:
                    row.extend(['未找到', '', ''])
                    continue

                # 分类
                available = [l for l in listings if l.status == 'available']
                sold = [l for l in listings if l.status == 'sold']

                if available:
                    cheapest = min(available, key=lambda x: x.price or float('inf'))
                    row.append('在售')
                    row.append(f'¥{cheapest.price:,.0f}' if cheapest.price else '')
                    row.append(cheapest.url)
                elif sold:
                    recent = max(sold, key=lambda x: x.last_seen)
                    row.append('已售')
                    row.append(f'¥{recent.price:,.0f}' if recent.price else '')
                    row.append(recent.url)
                else:
                    row.extend(['未找到', '', ''])

            writer.writerow(row)

        return output.getvalue()

    def save_to_file(self, filename: str):
        """保存CSV到文件"""
        csv_content = self.generate_csv()
        with open(filename, 'w', encoding='utf-8-sig') as f:  # utf-8-sig for Excel
            f.write(csv_content)

    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
