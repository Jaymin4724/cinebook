from pathlib import Path
from fastapi import HTTPException, status
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings
import qrcode
import tempfile


class EmailService:
    """Send OTP email to user."""

    def __init__(self):
        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
            TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates/email",
        )
        self.fastmail = FastMail(self.conf)

    async def send_otp_email(self, email_to: str, otp: str):
        """Sends a 6-digit OTP email asynchronously using your previous template."""
        body = f"""
        <html>
            <body>
                <h1>Verify Your Account</h1>
                <p>Thank you for registering. Please use the following One-Time Password (OTP) to complete your signup:</p>
                <h2 style="color: #4CAF50;">{otp}</h2>
                <p>This code is valid for 10 minutes.</p>
            </body>
        </html>
        """
        message = MessageSchema(
            subject="Your Verification Code",
            recipients=[email_to],
            body=body,
            subtype=MessageType.html,
        )
        try:
            await self.fastmail.send_message(message)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email.",
            )
        

    async def send_qr_ticket(self, email_to: str, ticket_hash: str):
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(ticket_hash.decode('utf-8'))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            img.save(temp_file.name)
            temp_path = temp_file.name
        
        body = f"""
        <html>
            <body style="text-align: center;">
                <h1>Your Digital Ticket</h1>
                <img src="cid:ticket_qr" alt="QR Code" />
            </body>
        </html>
        """
        
        message = MessageSchema(
            subject="Your Digital Ticket",
            recipients=[email_to],
            body=body,
            subtype=MessageType.html,
            attachments=[temp_path]
        )
        
        try:
            await self.fastmail.send_message(message)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send ticket email.",
            )