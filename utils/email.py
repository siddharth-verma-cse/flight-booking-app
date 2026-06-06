from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from dotenv import load_dotenv
from pydantic import EmailStr
import os

load_dotenv()


config = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=os.getenv("MAIL_PORT"),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


async def send_email_async(subject: str, recipient: list[EmailStr], body_text: str):
    html = f"""
    <h2>{subject}</h2>
    <br/>
    <p>{body_text}</p>
    <br/>
    <br/>
    <br/>
    <p>Best regards,</p>
    <p>Aero Bound Ventures</p>

    """
    message = MessageSchema(
        subject=subject, recipients=recipient, body=html, subtype=MessageType.html
    )
    fm = FastMail(config)
    await fm.send_message(message)
