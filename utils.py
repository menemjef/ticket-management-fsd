import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL = os.environ.get("APP_EMAIL", "ticketmanagementinternship6742@gmail.com")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "fibx vaeu ivbb fjhx")

def sendEmail(recipient, subject, body):
    # EMAIL TEMPORARILY DISABLED - Render free tier blocks outbound SMTP
    print(f"[EMAIL SKIPPED] To: {recipient} | Subject: {subject}")

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


# Absolute uploads directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
