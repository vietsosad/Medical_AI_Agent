"""Dịch vụ Gửi Email Xác Thực Lâm Sàng (SMTP Async Email Service).

Tuân thủ quy chuẩn kỹ thuật tại .agents/rules/backend-rules.md:
- An toàn Non-Blocking Loop: Chạy thao tác giao tiếp I/O mạng bên trong asyncio.to_thread để không chặn Event Loop.
- Tự động fallback sang chế độ Giả định Kiểm chứng (Console Mock Logging) nếu chưa điền thông tin tài khoản SMTP thực tế.
"""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import get_settings
from src.services.log_redaction import mask_email

settings = get_settings()


def _send_smtp_email_sync(recipient: str, subject: str, html_content: str, text_content: str) -> bool:
    """Hàm giao tiếp đồng bộ gốc với máy chủ SMTP (được gọi bất đồng bộ qua threadpool)."""
    # Nếu chưa điền cấu hình thật trong .env, chuyển đổi mượt mà sang chế độ In Log DEV
    if not settings.smtp_user or "your-hospital-system-email" in settings.smtp_user or not settings.smtp_password or "your-gmail-app-password" in settings.smtp_password:
        print("\n" + "=" * 80)
        print(f"📧 [DEV MOCK EMAIL SERVICE] Gửi thành công tới: {mask_email(recipient)}")
        print(f"📌 Chủ đề: {subject}")
        print("-" * 80)
        # The body carries the one-time passcode. It is printed only when the
        # deployment is explicitly a development one, so a production instance
        # with unconfigured SMTP degrades without leaking a credential.
        if settings.app_env == "development":
            print(text_content)
        else:
            print("[REDACTED] SMTP unconfigured outside development; body withheld.")
        print("=" * 80 + "\n")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email or settings.smtp_user}>"
        msg["To"] = recipient

        # Gắn kèm cả bản văn bản thường (Text) và bản thiết kế HTML phong phú
        part1 = MIMEText(text_content, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        print(f"🚀 [SMTP Engine] Đang khởi tạo kết nối STARTTLS tới {settings.smtp_host}:{settings.smtp_port}...")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from_email or settings.smtp_user, [recipient], msg.as_string())

        print(f"✅ [SMTP Engine] Đã gửi bức điện xác minh an toàn sang Bác sĩ/Bệnh nhân: {mask_email(recipient)}")
        return True
    except Exception as e:
        print(f"❌ [SMTP Engine Exception] Sự cố gửi thư tới {mask_email(recipient)}: {str(e)}")
        print("💡 Chú ý: Hãy chắc chắn đã bật 'App Passwords' trong tài khoản Google Gmail của bạn.")
        # Phụ đệm hiển thị lại mã OTP ra console để duy trì tiến trình không gián đoạn
        # The passcode is deliberately not echoed here. This path runs in
        # production whenever SMTP fails, and a one-time passcode written to a
        # log is a credential that outlives the delivery it replaced.
        if settings.app_env == "development":
            print(f"📢 [Backup Log Details]: {text_content}")
        else:
            print("[Backup Log Details]: [REDACTED - one-time passcode withheld]")
        return False


async def send_email(recipient: str, subject: str, html_body: str, text_body: str) -> bool:
    """Wrapper hàm gửi Email không đồng bộ tuyệt đối (Non-blocking I/O)."""
    return await asyncio.to_thread(_send_smtp_email_sync, recipient, subject, html_body, text_body)


# =====================================================================
# CÁC HẠNG MỤC THÔNG ĐIỆP Y KHOA CHUYÊN DỤNG
# =====================================================================

async def send_registration_otp(email: str, full_name: str, otp_code: str, valid_minutes: int = 15) -> bool:
    """Gửi email thông báo Mã bảo mật OTP cho người dùng Đăng ký mới."""
    subject = f"[AI Triage Cấp Cứu] Mã bảo mật OTP xác thực định danh: {otp_code}"

    text_body = (
        f"Kính chào Bác sĩ/Bệnh nhân {full_name},\n\n"
        f"Mã bảo mật OTP xác minh tài khoản y khoa của bạn là: {otp_code}\n\n"
        f"Mã có hiệu lực trong vòng {valid_minutes} phút. Vui lòng không chia sẻ cho bất kỳ bên thứ ba nào.\n"
        "Trân trọng,\nHệ thống AI Triage Cấp Cứu - Bệnh Viện Kỹ Thuật Số."
    )

    html_body = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; background-color: #f8fafc; color: #1e293b; padding: 40px 20px; margin: 0;">
      <div style="max-width: 540px; margin: 0 auto; background-color: #ffffff; border-radius: 20px; padding: 36px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
        <div style="text-align: center; margin-bottom: 24px;">
          <span style="background-color: #e0f2fe; color: #0284c7; padding: 6px 16px; border-radius: 50px; font-weight: bold; font-size: 13px; text-transform: uppercase;">Xác Thực Bảo Mật Y Khoa</span>
        </div>
        <h2 style="font-size: 22px; color: #0f172a; margin-top: 0; text-align: center;">Kính chào, {full_name}!</h2>
        <p style="font-size: 15px; line-height: 1.6; color: #475569; text-align: center;">
          Để hoàn tất quy trình thiết lập hồ sơ định danh trên trạm <strong>AI Triage Cấp Cứu</strong>, vui lòng nhập mã PIN bảo mật dưới đây tại màn hình xác thực:
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <div style="display: inline-block; background: linear-gradient(to right, #0284c7, #2563eb); color: #ffffff; font-size: 32px; font-weight: 800; letter-spacing: 12px; padding: 16px 36px; border-radius: 16px; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            {otp_code}
          </div>
        </div>
        <p style="font-size: 13px; color: #64748b; text-align: center; margin-top: 20px;">
          ⏱️ Mã bảo mật này có thời gian hiệu lực trong vòng <strong>{valid_minutes} phút</strong>. Nếu bạn không khởi tạo yêu cầu này, vui lòng bỏ qua email.
        </p>
        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 32px 0;">
        <p style="font-size: 12px; color: #94a3b8; text-align: center; margin: 0;">
          Hệ thống Quản Trị Khám Bệnh AI Triage &bull; Hoạt động 24/7 &bull; Tuân thủ Chuẩn ACID & RBAC
        </p>
      </div>
    </body>
    </html>
    """
    return await send_email(email, subject, html_body, text_body)


async def send_reset_password_otp(email: str, otp_code: str, valid_minutes: int = 15) -> bool:
    """Gửi email thông báo Mã bảo mật OTP cho nghiệp vụ Quên/Khôi phục mật khẩu."""
    subject = f"[AI Triage Cấp Cứu] Mã OTP khôi phục mật khẩu: {otp_code}"

    text_body = (
        f"Kính chào người dùng tài khoản {email},\n\n"
        f"Yêu cầu đặt lại mật khẩu của bạn đã được ghi nhận. Mã xác minh OTP là: {otp_code}\n\n"
        f"Mã có hiệu lực trong vòng {valid_minutes} phút. Nếu bạn không yêu cầu đổi mật khẩu, vui lòng kiểm tra lại an ninh tài khoản ngay lập tức.\n"
        "Trân trọng,\nHệ thống AI Triage Cấp Cứu."
    )

    html_body = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; background-color: #fdf2f8; color: #1e293b; padding: 40px 20px; margin: 0;">
      <div style="max-width: 540px; margin: 0 auto; background-color: #ffffff; border-radius: 20px; padding: 36px; border: 1px solid #fce7f3; box-shadow: 0 10px 25px rgba(225,29,72,0.05);">
        <div style="text-align: center; margin-bottom: 24px;">
          <span style="background-color: #ffe4e6; color: #e11d48; padding: 6px 16px; border-radius: 50px; font-weight: bold; font-size: 13px; text-transform: uppercase;">Khôi Phục Mật Khẩu Khẩn Cấp</span>
        </div>
        <h2 style="font-size: 22px; color: #0f172a; margin-top: 0; text-align: center;">Yêu Cầu Thay Đổi Credentials</h2>
        <p style="font-size: 15px; line-height: 1.6; color: #475569; text-align: center;">
          Hệ thống kiểm toán vừa nhận được tín hiệu xin cập nhật mật khẩu cho tài khoản <strong>{email}</strong>. Sử dụng mã PIN sau để kích hoạt lại quyền hạn:
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <div style="display: inline-block; background: linear-gradient(to right, #e11d48, #4f46e5); color: #ffffff; font-size: 32px; font-weight: 800; letter-spacing: 12px; padding: 16px 36px; border-radius: 16px; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            {otp_code}
          </div>
        </div>
        <p style="font-size: 13px; color: #64748b; text-align: center; margin-top: 20px;">
          ⏱️ Mã khôi phục này hết hiệu lực sau <strong>{valid_minutes} phút</strong>. Đừng tiết lộ với bất kỳ nhân sự kỹ thuật nào!
        </p>
        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 32px 0;">
        <p style="font-size: 12px; color: #94a3b8; text-align: center; margin: 0;">
          Hệ thống Quản Trị Khám Bệnh AI Triage &bull; An Ninh Thông Tin Phẫu Thuật Y Khoa
        </p>
      </div>
    </body>
    </html>
    """
    return await send_email(email, subject, html_body, text_body)
