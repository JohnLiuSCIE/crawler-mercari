"""
邮件HTML构建器 - 使用内联样式确保兼容性
Email HTML builder with inline styles for compatibility
"""
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.database import Item, Platform, Listing, SessionLocal


def build_daily_report_html(summary: dict) -> str:
    """
    构建每日报告的HTML（使用内联样式）

    Args:
        summary: 包含统计信息的字典

    Returns:
        HTML字符串
    """
    # 获取数据
    db = SessionLocal()
    items = db.query(Item).order_by(Item.id).all()
    platforms = db.query(Platform).filter_by(enabled=True).order_by(Platform.id).all()

    html = []
    html.append('<!DOCTYPE html>')
    html.append('<html>')
    html.append('<head><meta charset="UTF-8"></head>')
    html.append('<body style="font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5;">')
    html.append('<div style="max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 5px;">')

    # 标题
    html.append('<h2 style="color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px;">抱枕套监控 - 每日报告</h2>')
    html.append(f'<p style="color: #666; font-size: 14px;">生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')

    # 统计摘要
    html.append('<h3 style="color: #333;">统计摘要</h3>')
    html.append('<ul style="line-height: 1.8;">')
    html.append(f'<li>监控商品数: <strong>{summary.get("total_items", 0)}</strong></li>')
    html.append(f'<li>监控平台数: <strong>{summary.get("total_platforms", 0)}</strong></li>')
    html.append(f'<li>在售商品: <strong style="color: #4CAF50;">{summary.get("available_count", 0)}</strong></li>')
    html.append(f'<li>已售商品: <strong style="color: #FF9800;">{summary.get("sold_count", 0)}</strong></li>')
    html.append('</ul>')

    # 表格
    html.append('<h3 style="color: #333; margin-top: 30px;">商品对照表</h3>')
    html.append('<table style="width: 100%; border-collapse: collapse; margin-top: 20px;">')

    # 表头
    html.append('<thead>')
    html.append('<tr style="background-color: #4CAF50;">')
    html.append('<th style="padding: 12px; text-align: left; color: white; border: 1px solid #ddd;">商品</th>')
    for platform in platforms:
        html.append(f'<th style="padding: 12px; text-align: left; color: white; border: 1px solid #ddd;">{platform.name_cn}</th>')
    html.append('</tr>')
    html.append('</thead>')

    # 表体
    html.append('<tbody>')
    for idx, item in enumerate(items):
        bg_color = '#f9f9f9' if idx % 2 == 0 else 'white'
        html.append(f'<tr style="background-color: {bg_color};">')
        html.append(f'<td style="padding: 12px; border: 1px solid #ddd;"><strong>{item.name_cn}</strong><br><small style="color: #666;">{item.circle}</small></td>')

        for platform in platforms:
            cell_html = _get_platform_cell_html(db, item, platform)
            html.append(f'<td style="padding: 12px; border: 1px solid #ddd;">{cell_html}</td>')

        html.append('</tr>')
    html.append('</tbody>')
    html.append('</table>')

    # 图例
    html.append('<div style="margin-top: 30px; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #4CAF50;">')
    html.append('<h4 style="margin-top: 0; color: #333;">图例</h4>')
    html.append('<p style="margin: 5px 0;"><span style="color: #4CAF50; font-weight: bold;">✅ 在售</span> - 显示最低价格</p>')
    html.append('<p style="margin: 5px 0;"><span style="color: #FF9800; font-weight: bold;">🔄 已售</span> - 显示最近售价</p>')
    html.append('<p style="margin: 5px 0;"><span style="color: #999;">❌ 未找到</span></p>')
    html.append('</div>')

    # 附件说明
    html.append('<p style="margin-top: 20px; color: #666; font-size: 13px;">💡 提示：详细数据请查看附件中的CSV文件，可用Excel或Google Sheets打开。</p>')

    html.append('</div>')
    html.append('</body>')
    html.append('</html>')

    db.close()
    return '\n'.join(html)


def _get_platform_cell_html(db: Session, item: Item, platform: Platform) -> str:
    """获取平台单元格的HTML内容（内联样式）"""
    listings = db.query(Listing).filter(
        and_(
            Listing.item_id == item.id,
            Listing.platform_id == platform.id,
            Listing.is_active == True
        )
    ).all()

    if not listings:
        return '<span style="color: #999;">❌ 未找到</span>'

    available = [l for l in listings if l.status == 'available']
    sold = [l for l in listings if l.status == 'sold']

    if available:
        cheapest = min(available, key=lambda x: x.price or float('inf'))
        if cheapest.price:
            html = '<div style="color: #4CAF50; font-weight: bold;">✅ 在售</div>'
            html += f'<div style="font-size: 16px; font-weight: bold; margin: 5px 0;">¥{cheapest.price:,.0f}</div>'
            html += f'<a href="{cheapest.url}" style="color: #2196F3; text-decoration: none; font-size: 12px;">查看商品 →</a>'
            return html
        else:
            return '<span style="color: #4CAF50; font-weight: bold;">✅ 在售</span>'
    elif sold:
        recent = max(sold, key=lambda x: x.last_seen)
        if recent.price:
            html = '<div style="color: #FF9800; font-weight: bold;">🔄 已售</div>'
            html += f'<div style="font-size: 16px; font-weight: bold; margin: 5px 0;">¥{recent.price:,.0f}</div>'
            html += f'<a href="{recent.url}" style="color: #2196F3; text-decoration: none; font-size: 12px;">查看商品 →</a>'
            return html
        else:
            return '<span style="color: #FF9800; font-weight: bold;">🔄 已售</span>'
    else:
        return '<span style="color: #999;">❌ 未找到</span>'


def build_daily_report_text(summary: dict) -> str:
    """构建纯文本版本的报告（作为备用）"""
    from core.report_generator import ReportGenerator

    gen = ReportGenerator()
    gen.connect_db()
    text = gen.generate_text_report()
    gen.close()

    header = f"""
抱枕套监控 - 每日报告
{'=' * 80}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

统计摘要:
  监控商品数: {summary.get('total_items', 0)}
  监控平台数: {summary.get('total_platforms', 0)}
  在售商品: {summary.get('available_count', 0)}
  已售商品: {summary.get('sold_count', 0)}

{text}

{'=' * 80}
注：如果看不到表格，请在邮件客户端中启用HTML显示，或查看附件中的CSV文件。
"""
    return header
