"""Send emails, such as password reset links.

To send real emails, add these to .env (for example from Gmail with an "app password",
or a free email service like Brevo):
    MAIL_SERVER=smtp.example.com
    MAIL_PORT=587
    MAIL_USERNAME=your-login
    MAIL_PASSWORD=your-password
    MAIL_FROM=Researchify <hello@example.com>
Without them, the email is printed in the terminal instead, which is handy for testing.
"""

import os
import smtplib
from email.message import EmailMessage


def email_is_set_up():
    return bool(os.environ.get("MAIL_SERVER"))


def send_email(to, subject, body):
    if not email_is_set_up():
        print("\n----- Email (not sent: no MAIL_SERVER in .env) -----")
        print("To: " + to)
        print("Subject: " + subject)
        print(body)
        print("-----------------------------------------------------\n")
        return

    message = EmailMessage()
    message["From"] = os.environ.get("MAIL_FROM", os.environ.get("MAIL_USERNAME", ""))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(os.environ["MAIL_SERVER"], int(os.environ.get("MAIL_PORT", "587")), timeout=15) as server:
        # Encrypt the connection before logging in, so the password isn't sent in plain text.
        server.starttls()
        server.login(os.environ["MAIL_USERNAME"], os.environ["MAIL_PASSWORD"])
        server.send_message(message)
