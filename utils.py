import os
import smtplib
from email.mime.text import MIMEText

EMAIL = os.environ.get("APP_EMAIL", "arjunkarthik1223@gmail.com")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "yghm exwg uyqx nepw")

def sendEmail(recipient, subject, body):
    msg = MIMEText(body)

    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = recipient

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL, APP_PASSWORD)
    server.send_message(msg)
    server.quit()

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
