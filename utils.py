import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL = os.environ.get("APP_EMAIL", "ticketmanagementinternship6742@gmail.com")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "fibx vaeu ivbb fjhx")

def sendEmail(recipient, subject, body):
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = recipient
    msg.attach(MIMEText(body, "plain"))

    # Use SSL on port 465 (less blocked by cloud hosting providers than STARTTLS/587)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
        server.login(EMAIL, APP_PASSWORD)
        server.send_message(msg)

# db = {
#     "host": os.environ.get("DB_HOST", "localhost"),
#     "user": os.environ.get("DB_USER", "root"),
#     "password": os.environ.get("DB_PASSWORD", "Change123$"),
#     "database": os.environ.get("DB_NAME", "internship_db"),
#     "port": int(os.environ.get("DB_PORT", 3306))
# }
db = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "Change123$"),
    "database": os.environ.get("DB_NAME", "internship_db"),
    "port": int(os.environ.get("DB_PORT", 3306))
}


# Absolute uploads directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
