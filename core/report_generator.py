"""
报告生成器 - 生成商品对照表
Report generator - generates comparison tables
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.database import Item, Platform, Listing, SessionLocal


class ReportGenerator:
    """生成商品对照表报告"""

    def __init__(self):
        self.db: Optional[Session] = None

    def connect_db(self):
        """连接数据库"""
        self.db = SessionLocal()

    def generate_text_report(self) -> str:
        """
        生成文本格式的报告

        Returns:
            格式化的文本报告
        """
        if not self.db:
            self.connect_db()

        # 获取所有商品和平台
        items = self.db.query(Item).order_by(Item.id).all()
        platforms = self.db.query(Platform).filter_by(enabled=True).order_by(Platform.id).all()

        if not items or not platforms:
            return "没有数据可显示"

        # 生成报告
        report_lines = []
        report_lines.append("=" * 120)
        report_lines.append(f"抱枕套商品对照表")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 120)
        report_lines.append("")

        # 表头
        header = f"{'商品':<30}"
        for platform in platforms:
            header += f"{platform.name_cn:<25}"
        report_lines.append(header)
        report_lines.append("-" * 120)

        # 每个商品的数据
        for item in items:
            row = f"{item.name_cn:<30}"

            for platform in platforms:
                cell = self._get_platform_cell(item, platform)
                row += f"{cell:<25}"

            report_lines.append(row)

        report_lines.append("=" * 120)

        # 图例
        report_lines.append("")
        report_lines.append("图例:")
        report_lines.append("  ✅ 在售 - 显示最低价")
        report_lines.append("  🔄 已售 - 显示最近售价")
        report_lines.append("  ❌ 未找到")
        report_lines.append("")

        return "\n".join(report_lines)

    def generate_html_report(self) -> str:
        """
        生成HTML格式的报告

        Returns:
            HTML格式的报告
        """
        if not self.db:
            self.connect_db()

        items = self.db.query(Item).order_by(Item.id).all()
        platforms = self.db.query(Platform).filter_by(enabled=True).order_by(Platform.id).all()

        if not items or not platforms:
            return "<p>没有数据可显示</p>"

        html = []
        html.append('<!DOCTYPE html>')
        html.append('<html>')
        html.append('<head>')
        html.append('<meta charset="utf-8">')
        html.append('<title>抱枕套商品对照表</title>')
        html.append('<style>')
        html.append('''
            body {
                font-family: "Helvetica Neue", Arial, "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
                margin: 20px;
                background: #f5f5f5;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }
            .timestamp {
                color: #666;
                font-size: 14px;
                margin-bottom: 20px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th {
                background: #4CAF50;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }
            td {
                padding: 12px;
                border-bottom: 1px solid #ddd;
            }
            tr:hover {
                background: #f9f9f9;
            }
            .item-name {
                font-weight: bold;
                color: #333;
            }
            .available {
                color: #4CAF50;
                font-weight: bold;
            }
            .sold {
                color: #FF9800;
            }
            .not-found {
                color: #999;
            }
            .price {
                font-size: 16px;
                font-weight: bold;
            }
            .link {
                font-size: 12px;
                color: #2196F3;
                text-decoration: none;
            }
            .link:hover {
                text-decoration: underline;
            }
            .legend {
                margin-top: 30px;
                padding: 15px;
                background: #f9f9f9;
                border-left: 4px solid #4CAF50;
            }
            .legend h3 {
                margin-top: 0;
                color: #333;
            }
        ''')
        html.append('</head>')
        html.append('<body>')
        html.append('<div class="container">')
        html.append('<h1>抱枕套商品对照表</h1>')
        html.append(f'<div class="timestamp">生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>')

        html.append('<table>')
        html.append('<thead>')
        html.append('<tr>')
        html.append('<th>商品</th>')
        for platform in platforms:
            html.append(f'<th>{platform.name_cn}</th>')
        html.append('</tr>')
        html.append('</thead>')
        html.append('<tbody>')

        for item in items:
            html.append('<tr>')
            html.append(f'<td class="item-name">{item.name_cn}<br><small style="color:#666">{item.circle} | {item.artist}</small></td>')

            for platform in platforms:
                cell_html = self._get_platform_cell_html(item, platform)
                html.append(f'<td>{cell_html}</td>')

            html.append('</tr>')

        html.append('</tbody>')
        html.append('</table>')

        # 图例
        html.append('<div class="legend">')
        html.append('<h3>图例</h3>')
        html.append('<p><span class="available">✅ 在售</span> - 显示最低价格</p>')
        html.append('<p><span class="sold">🔄 已售</span> - 显示最近售价</p>')
        html.append('<p><span class="not-found">❌ 未找到</span></p>')
        html.append('</div>')

        html.append('</div>')
        html.append('</body>')
        html.append('</html>')

        return '\n'.join(html)

    def _get_platform_cell(self, item: Item, platform: Platform) -> str:
        """获取平台单元格的文本内容"""
        # 查询该商品在该平台的所有列表
        listings = self.db.query(Listing).filter(
            and_(
                Listing.item_id == item.id,
                Listing.platform_id == platform.id,
                Listing.is_active == True
            )
        ).all()

        if not listings:
            return "❌ 未找到"

        # 分类：在售和已售
        available = [l for l in listings if l.status == 'available']
        sold = [l for l in listings if l.status == 'sold']

        if available:
            # 找最低价
            cheapest = min(available, key=lambda x: x.price or float('inf'))
            if cheapest.price:
                return f"✅ ¥{cheapest.price:,.0f}"
            else:
                return "✅ 在售"
        elif sold:
            # 显示最近售价
            recent = max(sold, key=lambda x: x.last_seen)
            if recent.price:
                return f"🔄 ¥{recent.price:,.0f}"
            else:
                return "🔄 已售"
        else:
            return "❌ 未找到"

    def _get_platform_cell_html(self, item: Item, platform: Platform) -> str:
        """获取平台单元格的HTML内容"""
        listings = self.db.query(Listing).filter(
            and_(
                Listing.item_id == item.id,
                Listing.platform_id == platform.id,
                Listing.is_active == True
            )
        ).all()

        if not listings:
            return '<span class="not-found">❌ 未找到</span>'

        available = [l for l in listings if l.status == 'available']
        sold = [l for l in listings if l.status == 'sold']

        if available:
            cheapest = min(available, key=lambda x: x.price or float('inf'))
            if cheapest.price:
                html = f'<div class="available">✅ 在售</div>'
                html += f'<div class="price">¥{cheapest.price:,.0f}</div>'
                html += f'<a href="{cheapest.url}" target="_blank" class="link">查看商品 →</a>'
                return html
            else:
                return '<span class="available">✅ 在售</span>'
        elif sold:
            recent = max(sold, key=lambda x: x.last_seen)
            if recent.price:
                html = f'<div class="sold">🔄 已售</div>'
                html += f'<div class="price">¥{recent.price:,.0f}</div>'
                html += f'<a href="{recent.url}" target="_blank" class="link">查看商品 →</a>'
                return html
            else:
                return '<span class="sold">🔄 已售</span>'
        else:
            return '<span class="not-found">❌ 未找到</span>'

    def generate_summary(self) -> Dict[str, Any]:
        """
        生成统计摘要

        Returns:
            统计数据字典
        """
        if not self.db:
            self.connect_db()

        total_items = self.db.query(Item).count()
        total_platforms = self.db.query(Platform).filter_by(enabled=True).count()
        total_listings = self.db.query(Listing).filter_by(is_active=True).count()

        available_count = self.db.query(Listing).filter(
            and_(Listing.is_active == True, Listing.status == 'available')
        ).count()

        sold_count = self.db.query(Listing).filter(
            and_(Listing.is_active == True, Listing.status == 'sold')
        ).count()

        return {
            'total_items': total_items,
            'total_platforms': total_platforms,
            'total_listings': total_listings,
            'available_count': available_count,
            'sold_count': sold_count,
            'generated_at': datetime.now().isoformat()
        }

    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
