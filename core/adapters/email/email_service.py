"""
邮件服务适配器
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import logging
from datetime import datetime

from core.config import settings


logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务适配器"""
    
    def __init__(self):
        self.enabled = getattr(settings, 'EMAIL_ENABLED', False)
        self.host = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
        self.port = getattr(settings, 'EMAIL_PORT', 587)
        self.username = getattr(settings, 'EMAIL_USERNAME', '')
        self.password = getattr(settings, 'EMAIL_PASSWORD', '')
        self.from_email = getattr(settings, 'EMAIL_FROM', 'noreply@when.trade')
        
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """发送邮件"""
        if not self.enabled:
            logger.info(f"Email service disabled, skipping email to {to_email}")
            return True
            
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # 添加纯文本内容
            msg.attach(MIMEText(body, 'plain'))
            
            # 添加HTML内容（如果有）
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # 发送邮件
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
                
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_verification_email(
        self,
        to_email: str,
        username: str,
        verification_token: str
    ) -> bool:
        """发送邮箱验证邮件"""
        subject = "验证您的 When.Trade 账户邮箱"
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        body = f"""
您好 {username}，

欢迎使用 When.Trade！

请点击以下链接验证您的邮箱地址：
{verification_url}

此链接将在24小时后失效。

如果您没有注册 When.Trade 账户，请忽略此邮件。

祝好，
When.Trade 团队
"""
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">验证您的 When.Trade 账户</h2>
        <p>您好 {username}，</p>
        <p>欢迎使用 When.Trade！</p>
        <p>请点击下方按钮验证您的邮箱地址：</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">验证邮箱</a>
        </div>
        <p style="font-size: 14px; color: #666;">或复制以下链接到浏览器：<br>{verification_url}</p>
        <p style="font-size: 14px; color: #666;">此链接将在24小时后失效。</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="font-size: 12px; color: #999;">如果您没有注册 When.Trade 账户，请忽略此邮件。</p>
    </div>
</body>
</html>
"""
        
        return await self.send_email(to_email, subject, body, html_body)
    
    async def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_token: str
    ) -> bool:
        """发送密码重置邮件"""
        subject = "重置您的 When.Trade 账户密码"
        
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        body = f"""
您好 {username}，

您已请求重置 When.Trade 账户密码。

请点击以下链接重置密码：
{reset_url}

此链接将在1小时后失效。

如果您没有请求重置密码，请忽略此邮件，您的密码不会被更改。

祝好，
When.Trade 团队
"""
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">重置您的密码</h2>
        <p>您好 {username}，</p>
        <p>您已请求重置 When.Trade 账户密码。</p>
        <p>请点击下方按钮重置密码：</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">重置密码</a>
        </div>
        <p style="font-size: 14px; color: #666;">或复制以下链接到浏览器：<br>{reset_url}</p>
        <p style="font-size: 14px; color: #666;">此链接将在1小时后失效。</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="font-size: 12px; color: #999;">如果您没有请求重置密码，请忽略此邮件，您的密码不会被更改。</p>
    </div>
</body>
</html>
"""
        
        return await self.send_email(to_email, subject, body, html_body)
    
    async def send_security_alert(
        self,
        to_email: str,
        username: str,
        alert_type: str,
        details: dict
    ) -> bool:
        """发送安全提醒邮件"""
        subject = f"When.Trade 安全提醒 - {alert_type}"
        
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        alert_messages = {
            "new_login": "检测到新设备登录",
            "password_changed": "您的密码已更改",
            "two_factor_enabled": "双因素认证已启用",
            "two_factor_disabled": "双因素认证已禁用",
            "api_key_created": "新的API密钥已创建",
            "suspicious_activity": "检测到可疑活动"
        }
        
        alert_title = alert_messages.get(alert_type, "安全提醒")
        
        body = f"""
您好 {username}，

{alert_title}

时间：{timestamp}
IP地址：{details.get('ip_address', '未知')}
设备：{details.get('user_agent', '未知')}

如果这不是您本人的操作，请立即：
1. 修改密码
2. 检查账户设置
3. 联系客服

祝好，
When.Trade 团队
"""
        
        return await self.send_email(to_email, subject, body)
    
    async def send_notification(
        self,
        to_email: str,
        username: str,
        notification_type: str,
        title: str,
        content: str
    ) -> bool:
        """发送通用通知邮件"""
        subject = f"When.Trade - {title}"
        
        body = f"""
您好 {username}，

{content}

祝好，
When.Trade 团队
"""
        
        return await self.send_email(to_email, subject, body)