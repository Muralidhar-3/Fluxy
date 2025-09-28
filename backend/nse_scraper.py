import requests
import pandas as pd
from models import db, Announcement
from config import NSE_API_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import traceback
from datetime import datetime

def fetch_nse_data(app):
    """Fetch NSE data using the exact same method that works in the test"""
    try:
        print("🔄 Starting NSE data fetch...")
        
        # Use EXACT same session setup as the working test
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
        })

        print("📡 Making API request...")
        response = session.get(NSE_API_URL, timeout=15)
        print(f"✅ Response Status: {response.status_code}")
        print(f"📋 Content-Type: {response.headers.get('content-type')}")
        print(f"📏 Content Length: {len(response.text)}")
        
        if response.status_code != 200:
            print(f"❌ API Error: Status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return []

        # Parse JSON - use the same method as test
        try:
            data = response.json()
            print(f"📊 Data type received: {type(data)}")
            
            if isinstance(data, list):
                print(f"📈 Total announcements received: {len(data)}")
            else:
                print(f"❌ Expected list, got {type(data)}")
                return []
                
        except ValueError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Response content (first 200 chars): {response.text[:200]}")
            return []

        new_announcements = []

        # Process data within app context
        with app.app_context():
            print("🗃️ Processing announcements...")
            
            for i, item in enumerate(data):
                try:
                    # Extract data with same field names as test
                    company = str(item.get("symbol", "")).strip()
                    title = str(item.get("desc", "")).strip()
                    link = str(item.get("attchmntFile", "")).strip()
                    
                    # Handle date - use same fields as test showed
                    date_str = item.get("an_dt") or item.get("dt") or item.get("sort_date")
                    date = None
                    
                    if date_str:
                        try:
                            date = pd.to_datetime(date_str, errors="coerce")
                            if pd.isna(date):
                                date = datetime.now()
                        except Exception as date_error:
                            print(f"⚠️ Date parsing error for item {i}: {date_error}")
                            date = datetime.now()
                    else:
                        date = datetime.now()

                    # Skip if essential data is missing
                    if not company or not title:
                        print(f"⚠️ Skipping item {i}: Missing company ({company}) or title ({title[:30]}...)")
                        continue

                    # Check for duplicates
                    exists = Announcement.query.filter_by(
                        company=company, 
                        title=title
                    ).first()
                    
                    if not exists:
                        print(f"🆕 New announcement: {company} - {title[:50]}...")
                        
                        # Create new announcement
                        ann = Announcement(
                            company=company, 
                            title=title, 
                            link=link if link else None, 
                            date=date
                        )
                        
                        try:
                            db.session.add(ann)
                            db.session.commit()
                            new_announcements.append(ann)
                            
                            # Send Telegram alert
                            send_telegram_alert(company, title, link)
                            
                        except Exception as db_error:
                            print(f"❌ Database error for {company}: {db_error}")
                            db.session.rollback()
                    
                    else:
                        print(f"🔄 Duplicate found: {company} - {title[:30]}...")
                        
                except Exception as item_error:
                    print(f"❌ Error processing item {i}: {item_error}")
                    traceback.print_exc()
                    continue

        print(f"✅ Processing complete. New announcements: {len(new_announcements)}")
        return new_announcements

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error in fetch_nse_data: {e}")
        traceback.print_exc()
        return []


def send_telegram_alert(company, title, link):
    """Send Telegram notification with error handling"""
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("⚠️ Telegram credentials missing")
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Create message with better formatting
        msg = f"🚨 <b>{company}</b>\n\n📝 {title}\n\n"
        if link and link.strip():
            msg += f"🔗 <a href='{link}'>View Document</a>"
        else:
            msg += "📄 No attachment available"
        
        payload = {
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": msg, 
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Telegram alert sent for {company}")
        else:
            print(f"❌ Telegram error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Telegram alert error: {e}")