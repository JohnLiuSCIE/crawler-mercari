"""
邮件通知系统
Email notification system
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from datetime import datetime
from loguru import logger

from models.database import ChangeEvent, Listing, Item, Platform
from config.settings import settings


class EmailNotifier:
    """邮件通知器"""

    def __init__(self):
        self.enabled = settings.email_enabled
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.email_from = settings.email_from
        self.email_to = settings.email_to
        self.use_tls = settings.smtp_use_tls

    def send_change_notifications(self, events: List[ChangeEvent], report_html: str = None) -> bool:
        """
        发送变化通知邮件

        Args:
            events: 变化事件列表
            report_html: 可选的HTML报告

        Returns:
            是否发送成功
        """
        if not self.enabled:
            logger.warning("邮件通知未启用")
            return False

        if not events:
            logger.info("没有待通知的变化")
            return True

        try:
            # 构建邮件内容
            subject = self._build_subject(events)
            html_body = self._build_html_body(events, report_html)
            text_body = self._build_text_body(events)

            # 发送邮件
            self._send_email(subject, html_body, text_body)

            logger.info(f"成功发送邮件通知，包含 {len(events)} 个变化事件")
            return True

        except Exception as e:
            logger.error(f"发送邮件失败: {e}")
            return False

    def send_daily_report(self, summary: dict, csv_content: str = None) -> bool:
        """
        发送每日报告

        Args:
            summary: 统计摘要
            csv_content: CSV内容（可选）

        Returns:
            是否发送成功
        """
        if not self.enabled:
            logger.warning("邮件通知未启用")
            return False

        try:
            from notifications.email_builder import build_daily_report_html, build_daily_report_text

            subject = f"抱枕套监控 - 每日报告 ({datetime.now().strftime('%Y-%m-%d')})"

            # 生成HTML和纯文本版本
            html_body = build_daily_report_html(summary)
            text_body = build_daily_report_text(summary)

            # 发送邮件（HTML + 纯文本 + CSV附件）
            self._send_html_email_with_attachment(subject, html_body, text_body, csv_content)
            logger.info("成功发送每日报告")
            return True

        except Exception as e:
            logger.error(f"发送每日报告失败: {e}")
            return False

    def _build_subject(self, events: List[ChangeEvent]) -> str:
        """构建邮件主题"""
        new_items = sum(1 for e in events if e.event_type == 'new_item')
        price_changes = sum(1 for e in events if e.event_type == 'price_change')

        if new_items > 0:
            return f"🔔 发现 {new_items} 个新商品！"
        elif price_changes > 0:
            return f"💰 {price_changes} 个商品价格变化"
        else:
            return f"📢 {len(events)} 个商品更新"

    def _build_html_body(self, events: List[ChangeEvent], report_html: Optional[str] = None) -> str:
        """构建HTML邮件正文"""
        html = ['<html><head><meta charset="utf-8"></head><body>']
        html.append('<h2>抱枕套监控通知</h2>')
        html.append(f'<p>时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')
        html.append('<hr>')

        # 分类事件
        new_items = [e for e in events if e.event_type == 'new_item']
        price_changes = [e for e in events if e.event_type == 'price_change']
        sold_out = [e for e in events if e.event_type == 'sold_out']
        back_in_stock = [e for e in events if e.event_type == 'back_in_stock']

        if new_items:
            html.append('<h3>🎉 新发现的商品</h3>')
            html.append('<ul>')
            for event in new_items:
                listing = event.listing
                if listing:
                    html.append(f'<li>')
                    html.append(f'<strong>{listing.title}</strong><br>')
                    html.append(f'价格: {event.new_value}<br>')
                    html.append(f'平台: {listing.platform.name_cn}<br>')
                    html.append(f'<a href="{listing.url}">查看商品 →</a>')
                    html.append('</li>')
            html.append('</ul>')

        if price_changes:
            html.append('<h3>💰 价格变化</h3>')
            html.append('<ul>')
            for event in price_changes:
                listing = event.listing
                if listing:
                    html.append(f'<li>')
                    html.append(f'<strong>{listing.title}</strong><br>')
                    html.append(f'价格: {event.old_value} → <strong>{event.new_value}</strong><br>')
                    html.append(f'<a href="{listing.url}">查看商品 →</a>')
                    html.append('</li>')
            html.append('</ul>')

        if back_in_stock:
            html.append('<h3>✅ 重新上架</h3>')
            html.append('<ul>')
            for event in back_in_stock:
                listing = event.listing
                if listing:
                    html.append(f'<li>')
                    html.append(f'<strong>{listing.title}</strong><br>')
                    html.append(f'<a href="{listing.url}">查看商品 →</a>')
                    html.append('</li>')
            html.append('</ul>')

        if sold_out:
            html.append('<h3>🔄 已售出</h3>')
            html.append('<ul>')
            for event in sold_out:
                listing = event.listing
                if listing:
                    html.append(f'<li><strong>{listing.title}</strong></li>')
            html.append('</ul>')

        # 添加报告
        if report_html:
            html.append('<hr>')
            html.append('<h3>完整报告</h3>')
            html.append(report_html)

        html.append('</body></html>')
        return '\n'.join(html)

    def _build_text_body(self, events: List[ChangeEvent]) -> str:
        """构建纯文本邮件正文"""
        lines = []
        lines.append('抱枕套监控通知')
        lines.append('=' * 60)
        lines.append(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        lines.append('')

        for event in events:
            listing = event.listing
            if listing:
                lines.append(f'[{event.event_type}] {listing.title}')
                lines.append(f'  {event.description}')
                lines.append(f'  链接: {listing.url}')
                lines.append('')

        return '\n'.join(lines)

    def _send_email(self, subject: str, html_body: str, text_body: str):
        """发送邮件"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = self.email_to
        msg['Content-Type'] = 'text/html; charset=utf-8'

        # 添加纯文本和HTML版本（HTML应该放在后面，优先显示）
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')

        msg.attach(part1)
        msg.attach(part2)

        # 发送
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            server.send_message(msg)

        logger.debug(f"邮件已发送: {subject}")

    def _send_email_with_attachment(self, subject: str, text_body: str, csv_content: str = None):
        """发送带CSV附件的纯文本邮件"""
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = self.email_to

        # 添加邮件正文
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))

        # 添加CSV附件
        if csv_content:
            part = MIMEBase('text', 'csv')
            part.set_payload(csv_content.encode('utf-8-sig'))  # utf-8-sig for Excel
            encoders.encode_base64(part)
            filename = f"dakimakura_report_{datetime.now().strftime('%Y%m%d')}.csv"
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

        # 发送
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            server.send_message(msg)

        logger.debug(f"邮件已发送（带附件）: {subject}")

    def _send_html_email_with_attachment(self, subject: str, html_body: str, text_body: str, csv_content: str = None):
        """发送HTML邮件（带纯文本备用和CSV附件）"""
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = self.email_to

        # 创建alternative部分（HTML和纯文本）
        msg_alternative = MIMEMultipart('alternative')
        msg_alternative.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg_alternative.attach(MIMEText(html_body, 'html', 'utf-8'))
        msg.attach(msg_alternative)

        # 添加CSV附件
        if csv_content:
            part = MIMEBase('text', 'csv')
            part.set_payload(csv_content.encode('utf-8-sig'))
            encoders.encode_base64(part)
            filename = f"dakimakura_report_{datetime.now().strftime('%Y%m%d')}.csv"
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

        # 发送
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            server.send_message(msg)

        logger.debug(f"HTML邮件已发送（带附件）: {subject}")

    def test_connection(self) -> bool:
        """测试邮件连接"""
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()

                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)

            logger.info("邮件服务器连接测试成功")
            return True

        except Exception as e:
            logger.error(f"邮件服务器连接测试失败: {e}")
            return False
