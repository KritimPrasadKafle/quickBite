import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings

def send_reset_email(to_email:str, reset_token: str) -> None:

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Reset your Quickbite password"
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email

    html = f"""
    <html>
      <body>
        <h2>Reset your password</h2>
        <p>Click the link below to reset your password. This link expires in 15 minutes.</p>
        <a href="{reset_url}" style="
            background-color: #f97316;
            color: white;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            display: inline-block;
        ">Reset Password</a>
        <p>If you didn't request this, ignore this email.</p>
      </body>
    </html>
    """

    message.attach(MIMEText(html, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.sendmail(settings.SMTP_FROM, to_email, message.as_string())