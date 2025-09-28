import requests

BOT_TOKEN = "8025955874:AAE60iDILQHM7-uyctejwDg3DWErfLuYxCo"
CHAT_ID = "622849107"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=payload)
    print(response.json())

send_telegram_alert("🚨 Test Alert from Flask App!")
