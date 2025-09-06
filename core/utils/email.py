"""
Email utilities
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from core.config import settings


async def send_magic_link_email(to_email: str, magic_link_url: str) -> None:
    """Send magic link email"""
    # In production, use a proper email service like SendGrid, AWS SES, etc.
    # For now, this is a placeholder that would integrate with your email service
    
    subject = "Your When.Trade Login Link"
    
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
          <h2 style="color: #6366f1;">Welcome to When.Trade</h2>
          <p>Click the link below to log in to your account:</p>
          <p style="margin: 30px 0;">
            <a href="{magic_link_url}" 
               style="background-color: #6366f1; color: white; padding: 12px 24px; 
                      text-decoration: none; border-radius: 6px; display: inline-block;">
              Log In to When.Trade
            </a>
          </p>
          <p style="color: #666; font-size: 14px;">
            This link will expire in 15 minutes. If you didn't request this email, 
            you can safely ignore it.
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
          <p style="color: #999; font-size: 12px;">
            When.Trade - AI-Powered Trading Research Platform
          </p>
        </div>
      </body>
    </html>
    """
    
    text_body = f"""
    Welcome to When.Trade
    
    Click the link below to log in to your account:
    {magic_link_url}
    
    This link will expire in 15 minutes. If you didn't request this email, 
    you can safely ignore it.
    
    When.Trade - AI-Powered Trading Research Platform
    """
    
    # In production, implement actual email sending
    # For development, just log the email
    print(f"[EMAIL] Would send magic link to {to_email}: {magic_link_url}")
    
    # Example implementation with SMTP (configure in production):
    # try:
    #     msg = MIMEMultipart("alternative")
    #     msg["Subject"] = subject
    #     msg["From"] = settings.email_from
    #     msg["To"] = to_email
    #     
    #     part1 = MIMEText(text_body, "plain")
    #     part2 = MIMEText(html_body, "html")
    #     
    #     msg.attach(part1)
    #     msg.attach(part2)
    #     
    #     with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
    #         server.starttls()
    #         server.login(settings.smtp_user, settings.smtp_password)
    #         server.send_message(msg)
    # except Exception as e:
    #     print(f"Failed to send email: {e}")
    #     raise