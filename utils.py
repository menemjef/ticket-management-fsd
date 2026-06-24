import os
import smtplib
import ssl
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

    # Use SSL on port 465 (less blocked by cloud hosting providers)
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

# Build database config
_db_host = os.environ.get("DB_HOST", "localhost")
db = {
    "host": _db_host,
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "Change123$"),
    "database": os.environ.get("DB_NAME", "internship_db"),
    "port": int(os.environ.get("DB_PORT", 3306))
}

# TiDB cloud requires SSL - add it automatically when not on localhost
if _db_host != "localhost" and _db_host != "127.0.0.1":
    db["ssl_disabled"] = False
    db["ssl_verify_cert"] = False


# Absolute uploads directory (Use /tmp on Vercel because Vercel filesystem is read-only)
if os.environ.get("VERCEL"):
    UPLOADS_DIR = "/tmp/uploads"
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
