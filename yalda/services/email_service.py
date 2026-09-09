import os
import smtplib
import ssl
import time
import secrets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid
from email import encoders

import config


class EmailService:
    """
    Handles secure email delivery (SMTP over SSL/TLS) using Gmail.
    Provides OTP code generation & verification for password recovery,
    and sending backup archives directly to coach emails.
    """

    # In-memory OTP cache: {email.lower(): {"code": "12345", "expires_at": timestamp, "attempts": 0}}
    _otp_cache = {}

    @classmethod
    def generate_and_store_otp(cls, email: str, expiry_minutes: int = 5) -> str:
        """Generates a secure 5-digit OTP code and stores it with an expiry timestamp."""
        clean_email = email.strip().lower()
        # 5-digit random code (10000 to 99999)
        otp = str(secrets.randbelow(90000) + 10000)
        cls._otp_cache[clean_email] = {
            "code": otp,
            "expires_at": time.time() + (expiry_minutes * 60),
            "attempts": 0
        }
        return otp

    @classmethod
    def verify_otp(cls, email: str, entered_code: str) -> tuple[bool, str]:
        """Verifies the entered OTP code against stored cache."""
        clean_email = email.strip().lower()
        record = cls._otp_cache.get(clean_email)

        if not record:
            return False, "هیچ کد تاییدی برای این ایمیل صادر نشده است یا منقضی شده است."

        # Check expiry
        if time.time() > record["expires_at"]:
            del cls._otp_cache[clean_email]
            return False, "کد تایید منقضی شده است. لطفاً مجدداً درخواست ارسال کد دهید."

        # Check max attempts
        record["attempts"] += 1
        if record["attempts"] > 5:
            del cls._otp_cache[clean_email]
            return False, "تعداد تلاش‌های ناموفق بیش از حد مجاز بود. لطفاً کد جدیدی دریافت کنید."

        # Normalize digits for Persian/Arabic input
        norm_entered = "".join(
            str("۰۱۲۳۴۵۶۷۸۹".index(ch)) if ch in "۰۱۲۳۴۵۶۷۸۹"
            else str("٠١٢٣٤٥٦٧٨٩".index(ch)) if ch in "٠١٢٣٤٥٦٧٨٩"
            else ch for ch in entered_code.strip()
        )

        if norm_entered == record["code"]:
            # Clean up on success
            del cls._otp_cache[clean_email]
            return True, "کد تایید با موفقیت تایید شد."

        remaining = 5 - record["attempts"]
        return False, f"کد وارد شده صحیح نمی‌باشد. (تعداد شانس باقی‌مانده: {remaining})"

    @classmethod
    def _create_smtp_connection(cls):
        """Creates an authenticated SMTP connection using SSL (Port 465) or TLS (Port 587)."""
        smtp_host = getattr(config, "SMTP_SERVER", "smtp.gmail.com")
        smtp_port_ssl = getattr(config, "SMTP_PORT_SSL", 465)
        smtp_port_tls = getattr(config, "SMTP_PORT_TLS", 587)
        email_addr = getattr(config, "SUPPORT_EMAIL_ADDRESS", "gymassistantapp.support@gmail.com")
        app_password = getattr(config, "SUPPORT_EMAIL_APP_PASSWORD", "xngruboohbruxqwk")

        # Try Port 465 SSL first
        try:
            ssl_context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_host, smtp_port_ssl, context=ssl_context, timeout=20)
            server.login(email_addr, app_password)
            return server
        except Exception as e_ssl:
            # Fallback to Port 587 STARTTLS
            try:
                tls_context = ssl.create_default_context()
                server = smtplib.SMTP(smtp_host, smtp_port_tls, timeout=20)
                server.starttls(context=tls_context)
                server.login(email_addr, app_password)
                return server
            except Exception as e_tls:
                raise ConnectionError(f"خطا در اتصال به سرور ایمیل: {e_ssl} | {e_tls}")

    @classmethod
    def send_otp_email(cls, to_email: str, trainer_name: str, otp_code: str) -> tuple[bool, str]:
        """
        Sends an HTML email with the 5-digit verification OTP code.
        """
        sender_email = getattr(config, "SUPPORT_EMAIL_ADDRESS", "gymassistantapp.support@gmail.com")
        sender_name = getattr(config, "SUPPORT_EMAIL_SENDER_NAME", "پشتیبانی نرم افزار همیار باشگاه یلدا")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header("کد تایید بازیابی کلمه عبور - باشگاه ورزشی یلدا", "utf-8")
        msg["From"] = formataddr((str(Header(sender_name, "utf-8")), sender_email))
        msg["To"] = to_email
        msg["Reply-To"] = formataddr((str(Header(sender_name, "utf-8")), sender_email))
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="gmail.com")
        msg["X-Mailer"] = f"YaldaGymApp/{getattr(config, 'APP_VERSION', '2.3.0')}"
        msg["Auto-Submitted"] = "auto-generated"

        html_content = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: Tahoma, 'Segoe UI', Arial, sans-serif;
    background-color: #121212;
    color: #E5E7EB;
    margin: 0;
    padding: 20px;
    direction: rtl;
    text-align: right;
  }}
  .container {{
    max-width: 540px;
    margin: 0 auto;
    background-color: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }}
  .header {{
    text-align: center;
    border-bottom: 2px solid #8B0000;
    padding-bottom: 20px;
    margin-bottom: 25px;
  }}
  .logo-title {{
    color: #DC2626;
    font-size: 24px;
    font-weight: bold;
    margin: 0;
  }}
  .subtitle {{
    color: #9CA3AF;
    font-size: 13px;
    margin-top: 6px;
  }}
  .greeting {{
    font-size: 15px;
    line-height: 1.8;
    color: #F3F4F6;
    margin-bottom: 20px;
  }}
  .otp-box {{
    background: linear-gradient(135deg, #2D1517 0%, #1E1E1E 100%);
    border: 2px dashed #DC2626;
    border-radius: 10px;
    text-align: center;
    padding: 20px;
    margin: 25px 0;
  }}
  .otp-code {{
    font-size: 38px;
    font-weight: bold;
    letter-spacing: 12px;
    color: #F87171;
    font-family: Consolas, monospace, sans-serif;
    margin: 10px 0;
  }}
  .otp-desc {{
    font-size: 12px;
    color: #FCA5A5;
  }}
  .warning-box {{
    background-color: #27272A;
    border-right: 4px solid #F59E0B;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 12px;
    color: #D1D5DB;
    line-height: 1.7;
    margin: 20px 0;
  }}
  .footer {{
    text-align: center;
    border-top: 1px solid #333333;
    padding-top: 18px;
    margin-top: 25px;
    font-size: 11px;
    color: #6B7280;
    line-height: 1.6;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo-title">🏋️‍♂️ {config.APP_NAME}</div>
      <div class="subtitle">{sender_name}</div>
    </div>

    <div class="greeting">
      درود بر شما مربی گرامی، <b>{trainer_name or 'همکار گرامی'}</b>؛<br>
      درخواست بازیابی کلمه عبور برای حساب کاربری شما در نرم‌افزار مدیریت باشگاه ثبت شده است.
    </div>

    <div class="otp-box">
      <div class="otp-desc">کد تایید یک‌بارمصرف شما (OTP):</div>
      <div class="otp-code">{otp_code}</div>
      <div class="otp-desc">⏱️ اعتبار این کد ۵ دقیقه می‌باشد</div>
    </div>

    <div class="warning-box">
      ⚠️ <b>نکته امنیتی:</b> این کد صرفاً جهت استفاده شخصی شما صادر شده است. لطفاً آن را تحت هیچ شرایطی در اختیار افراد دیگر قرار ندهید.
    </div>

    <div style="background-color: #1E293B; border-right: 4px solid #10B981; padding: 12px; border-radius: 6px; font-size: 12px; color: #CBD5E1; line-height: 1.7; margin-top: 15px;">
      🛡️ <b>راهنمای دریافت در اینباکس:</b> اگر این پیام در پوشه <b>Spam (هرزنامه)</b> قرار دارد، لطفاً در بالای صفحه دکمه <b>«گزارش به‌عنوان هرزنامه نیست» (Report not spam)</b> را بزنید تا پیام‌های بعدی مستقیماً به صندوق ورودی اصلی (Inbox) ارسال شوند.
    </div>

    <div class="footer">
      این پیام به صورت خودکار توسط سامانه ارسال گردیده است.<br>
      {config.GYM_ADDRESS}
    </div>
  </div>
</body>
</html>"""

        plain_text = f"""درود بر شما مربی گرامی، {trainer_name or 'همکار گرامی'}؛

درخواست بازیابی کلمه عبور برای حساب کاربری شما در نرم‌افزار مدیریت باشگاه یلدا ثبت شده است.

کد تایید یک‌بارمصرف شما (OTP):
{otp_code}

⏱️ مدت اعتبار این کد ۵ دقیقه می‌باشد.
⚠️ نکته امنیتی: این کد صرفاً جهت استفاده شخصی شما صادر شده است. لطفاً آن را در اختیار افراد دیگر قرار ندهید.

🛡️ راهنمای دریافت در اینباکس:
اگر این پیام در پوشه Spam (هرزنامه) قرار دارد، لطفاً در بالای صفحه دکمه «گزارش به‌عنوان هرزنامه نیست» (Report not spam) را بزنید تا پیام‌های بعدی مستقیماً به صندوق ورودی اصلی (Inbox) ارسال شوند.

سیستم خودکار مدیریت باشگاه ورزشی {config.APP_NAME}
{config.GYM_ADDRESS}
"""
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            with cls._create_smtp_connection() as server:
                server.sendmail(sender_email, [to_email], msg.as_string())
            return True, "کد تایید یک‌بارمصرف با موفقیت به ایمیل شما ارسال شد."
        except Exception as e:
            err_msg = str(e)
            if "Authentication" in err_msg:
                return False, "خطای احراز هویت سرویس ایمیل. لطفاً با پشتیبانی تماس بگیرید."
            elif "getaddrinfo" in err_msg or "timed out" in err_msg:
                return False, "عدم برقراری ارتباط با اینترنت. لطفاً اتصال شبکه خود را بررسی کنید."
            return False, f"خطا در ارسال ایمیل: {err_msg}"

    @classmethod
    def send_backup_email(cls, to_email: str, trainer_name: str, backup_filepath: str, metadata: dict = None) -> tuple[bool, str]:
        """
        Sends an HTML email with the backup ZIP or DB file attached directly.
        """
        if not os.path.exists(backup_filepath):
            return False, "فایل پشتیبان در مسیر مشخص‌شده یافت نشد."

        sender_email = getattr(config, "SUPPORT_EMAIL_ADDRESS", "gymassistantapp.support@gmail.com")
        sender_name = getattr(config, "SUPPORT_EMAIL_SENDER_NAME", "پشتیبانی نرم افزار همیار باشگاه یلدا")

        metadata = metadata or {}
        shamsi_date = metadata.get("date", "-")
        backup_size = metadata.get("size", "-")
        members_count = metadata.get("members_count", "-")
        filename = os.path.basename(backup_filepath)

        msg = MIMEMultipart("mixed")
        msg["Subject"] = Header(f"نسخه پشتیبان پایگاه داده باشگاه یلدا - {shamsi_date}", "utf-8")
        msg["From"] = formataddr((str(Header(sender_name, "utf-8")), sender_email))
        msg["To"] = to_email
        msg["Reply-To"] = formataddr((str(Header(sender_name, "utf-8")), sender_email))
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="gmail.com")
        msg["X-Mailer"] = f"YaldaGymApp/{getattr(config, 'APP_VERSION', '2.3.0')}"
        msg["Auto-Submitted"] = "auto-generated"

        html_body = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: Tahoma, 'Segoe UI', Arial, sans-serif;
    background-color: #121212;
    color: #E5E7EB;
    margin: 0;
    padding: 20px;
    direction: rtl;
    text-align: right;
  }}
  .container {{
    max-width: 580px;
    margin: 0 auto;
    background-color: #1E1E1E;
    border: 1px solid #333333;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  }}
  .header {{
    text-align: center;
    border-bottom: 2px solid #8B0000;
    padding-bottom: 20px;
    margin-bottom: 25px;
  }}
  .logo-title {{
    color: #DC2626;
    font-size: 24px;
    font-weight: bold;
    margin: 0;
  }}
  .subtitle {{
    color: #9CA3AF;
    font-size: 13px;
    margin-top: 6px;
  }}
  .info-table {{
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    background-color: #27272A;
    border-radius: 8px;
    overflow: hidden;
  }}
  .info-table td {{
    padding: 12px 16px;
    border-bottom: 1px solid #3F3F46;
    font-size: 13px;
  }}
  .info-table tr:last-child td {{
    border-bottom: none;
  }}
  .info-label {{
    color: #9CA3AF;
    width: 40%;
    font-weight: bold;
  }}
  .info-value {{
    color: #F3F4F6;
    font-weight: bold;
  }}
  .badge {{
    background-color: #059669;
    color: #FFFFFF;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    display: inline-block;
  }}
  .footer {{
    text-align: center;
    border-top: 1px solid #333333;
    padding-top: 18px;
    margin-top: 25px;
    font-size: 11px;
    color: #6B7280;
    line-height: 1.6;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo-title">🏋️‍♂️ {config.APP_NAME}</div>
      <div class="subtitle">سرویس پشتیبان‌گیری ابری ایمیل</div>
    </div>

    <p style="font-size: 14px; line-height: 1.8;">
      با سلام خدمت مربی محترم، <b>{trainer_name or 'همکار گرامی'}</b>؛<br>
      نسخه پشتیبان جدید از پایگاه‌داده باشگاه با موفقیت تهیه شد و فایل دیتابیس (<b>.db</b>) آن به این پیام پیوست شده است.
    </p>

    <table class="info-table">
      <tr>
        <td class="info-label">نام فایل دیتابیس:</td>
        <td class="info-value" dir="ltr" style="text-align: right;">{filename}</td>
      </tr>
      <tr>
        <td class="info-label">تاریخ و ساعت ثبت:</td>
        <td class="info-value">{shamsi_date}</td>
      </tr>
      <tr>
        <td class="info-label">حجم فایل دیتابیس:</td>
        <td class="info-value">{backup_size}</td>
      </tr>
      <tr>
        <td class="info-label">تعداد شاگردان فعال:</td>
        <td class="info-value"><span class="badge">{members_count} ورزشکار</span></td>
      </tr>
      <tr>
        <td class="info-label">وضعیت سلامت دیتابیس:</td>
        <td class="info-value" style="color: #10B981;">✅ تاییدشده و قابل بازگردانی</td>
      </tr>
    </table>

    <div style="background-color: #1E293B; border-right: 4px solid #3B82F6; padding: 12px; border-radius: 6px; font-size: 12px; color: #CBD5E1; line-height: 1.7;">
      💡 <b>راهنما:</b> این ایمیل را به عنوان نسخه ذخیره امن در اینباکس خود نگه دارید. در صورت تعویض سیستم یا نیاز به بازیابی، می‌توانید همین فایل پایگاه‌داده (.db) پیوست را دانلود کرده و از منوی «بازگردانی از فایل خارجی» بارگذاری نمایید.
    </div>

    <div style="background-color: #1E293B; border-right: 4px solid #10B981; padding: 12px; border-radius: 6px; font-size: 12px; color: #CBD5E1; line-height: 1.7; margin-top: 10px;">
      🛡️ <b>دریافت مستقیم در اینباکس:</b> اگر این پیام در پوشه <b>Spam (هرزنامه)</b> قرار دارد، لطفاً در بالای صفحه دکمه <b>«گزارش به‌عنوان هرزنامه نیست» (Report not spam)</b> را بزنید تا ایمیل‌های بعدی مستقیماً به صندوق ورودی اصلی (Inbox) ارسال شوند.
    </div>

    <div class="footer">
      سیستم خودکار مدیریت باشگاه ورزشی {config.APP_NAME}<br>
      {config.GYM_ADDRESS}
    </div>
  </div>
</body>
</html>"""

        plain_text = f"""با سلام خدمت مربی محترم، {trainer_name or 'همکار گرامی'}؛

نسخه پشتیبان جدید از پایگاه‌داده باشگاه ورزشی یلدا با موفقیت تهیه شد و فایل دیتابیس ({filename}) به این پیام پیوست گردیده است.

مشخصات نسخه پشتیبان:
- نام فایل دیتابیس: {filename}
- تاریخ و ساعت ثبت: {shamsi_date}
- حجم فایل دیتابیس: {backup_size}
- تعداد ورزشکاران فعال: {members_count} نفر

راهنما:
این ایمیل را به عنوان نسخه ذخیره امن در اینباکس خود نگه دارید. در صورت تعویض سیستم یا نیاز به بازیابی، می‌توانید همین فایل پایگاه‌داده (.db) پیوست را دانلود کرده و از منوی «بازگردانی از فایل خارجی» بارگذاری نمایید.

🛡️ دریافت مستقیم در اینباکس:
اگر این پیام در پوشه Spam (هرزنامه) قرار دارد، لطفاً در بالای صفحه دکمه «گزارش به‌عنوان هرزنامه نیست» (Report not spam) را بزنید تا پیام‌های بعدی مستقیماً به صندوق ورودی اصلی (Inbox) ارسال شوند.

سیستم خودکار مدیریت باشگاه ورزشی {config.APP_NAME}
{config.GYM_ADDRESS}
"""

        body_part = MIMEMultipart("alternative")
        body_part.attach(MIMEText(plain_text, "plain", "utf-8"))
        body_part.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(body_part)

        # Attach the backup archive file
        try:
            with open(backup_filepath, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{filename}"'
            )
            msg.attach(part)
        except Exception as e_attach:
            return False, f"خطا در پیوست کردن فایل پشتیبان: {e_attach}"

        # Send via SMTP
        try:
            with cls._create_smtp_connection() as server:
                server.sendmail(sender_email, [to_email], msg.as_string())
            return True, f"نسخه پشتیبان با موفقیت به ایمیل {to_email} ارسال شد."
        except Exception as e:
            err_msg = str(e)
            if "Authentication" in err_msg:
                return False, "خطای احراز هویت سرویس ایمیل. لطفاً با پشتیبانی تماس بگیرید."
            elif "getaddrinfo" in err_msg or "timed out" in err_msg:
                return False, "عدم برقراری ارتباط با اینترنت. لطفاً اتصال شبکه را بررسی کنید."
            return False, f"خطا در ارسال ایمیل پشتیبان: {err_msg}"
