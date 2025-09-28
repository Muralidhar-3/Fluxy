import requests
import pandas as pd
import json
from models import db, Announcement
from config import NSE_API_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, NIFTY500_FILE

# Load Nifty 500 companies once at startup
with open(NIFTY500_FILE, "r") as f:
    NIFTY500_LIST = set(json.load(f))  # list of company symbols

def fetch_nse_data(app):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(NSE_API_URL, headers=headers)

    if response.status_code != 200:
        print("Failed to fetch data")
        return []

    data = response.json()["rows"]  # NSE JSON
    new_announcements = []

    with app.app_context():
        for item in data:
            company = item["symbol"].strip()
            title = item["headline"].strip()
            link = item.get("pdfLink", "")
            date = pd.to_datetime(item["dt"])

            # Only Nifty 500 companies
            if company not in NIFTY500_LIST:
                continue

            exists = Announcement.query.filter_by(company=company, title=title).first()
            if not exists:
                ann = Announcement(company=company, title=title, link=link, date=date)
                db.session.add(ann)
                db.session.commit()
                new_announcements.append(ann)

                send_telegram_alert(company, title, link)

    return new_announcements

def send_telegram_alert(company, title, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    msg = f"🚨 <b>{company}</b>: {title}\n🔗 {link}"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
    requests.post(url, data=payload)
