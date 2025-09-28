import requests
from datetime import datetime
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
        
        if response.status_code != 200:
            print(f"❌ API Error: Status {response.status_code}")
            return []

        # Parse JSON - use the same method as test
        try:
            data = response.json()
            if isinstance(data, list):
                print(f"📈 Total announcements received: {len(data)}")
            else:
                print(f"❌ Expected list, got {type(data)}")
                return []
                
        except ValueError as e:
            print(f"❌ JSON parsing error: {e}")
            return []

        new_announcements = []

        # Process data within app context
        with app.app_context():
            print("🗃️ Processing announcements...")
            
            for i, item in enumerate(data):
                try:
                    # Extract data
                    company = str(item.get("symbol", "")).strip()
                    companyName = str(item.get("sm_name", "")).strip()
                    title = str(item.get("desc", "")).strip()
                    link = str(item.get("attchmntFile", "")).strip()
                    desc = str(item.get("attchmntText", "")).strip()
                    
                    # Handle date
                    date_str = item.get("an_dt") or item.get("dt") or item.get("sort_date")
                    date = None
                    
                    if date_str:
                        try:
                              # Try parsing common NSE format (2025-09-27 17:07:02)
                              date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                              try:
                                    # If format differs (e.g. 27-Sep-2025 05:07:02 PM)
                                    date = datetime.strptime(date_str, "%d-%b-%Y %I:%M:%S %p")
                              except Exception:
                                    date = datetime.now()
                    else:
                        date = datetime.now()

                    # Skip if essential data is missing
                    if not company or not title:
                        continue

                    # Check for duplicates
                    exists = Announcement.query.filter_by(
                        company=company, 
                        title=title
                    ).first()
                    
                    if not exists:
                        print(f"🆕 New: {company} - {title[:50]}...")
                        
                        # Create new announcement
                        ann = Announcement(
                            company=company,
                            companyName=companyName, 
                            title=title,
                            desc=desc if desc else None, 
                            link=link if link else None, 
                            date=date
                        )
                        
                        try:
                            db.session.add(ann)
                            db.session.commit()
                            new_announcements.append(ann)
                            
                            # Send Telegram alert
                            send_telegram_alert(company, companyName, title, desc, link)
                            
                        except Exception as db_error:
                            print(f"❌ Database error for {company}: {db_error}")
                            db.session.rollback()
                        
                except Exception as item_error:
                    print(f"❌ Error processing item {i}: {item_error}")
                    continue

        print(f"✅ Found {len(new_announcements)} new announcements")
        return new_announcements

    except Exception as e:
        print(f"❌ Fetch error: {e}")
        return []


def send_telegram_alert(company, companyName, title, desc, link):
    """Send Telegram notification with improved formatting"""
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # Create message with better formatting
        # Use company name if available, otherwise use symbol
        display_name = f"{companyName} ({company})" if companyName else company
        
        msg = f"🚨 <b>{display_name}</b>\n\n"
        msg += f"📝 <b>Announcement:</b>\n{title}\n\n"
        
        # Add description if available
        if desc and desc.strip():
            # Limit description length to avoid message size limits
            desc_preview = desc[:200] + "..." if len(desc) > 200 else desc
            msg += f"ℹ️ <b>Details:</b>\n{desc_preview}\n\n"
        
        # Add link if available
        if link and link.strip():
            msg += f"🔗 <a href='{link}'>View Document</a>"
        else:
            msg += "📄 No document available"
        
        payload = {
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": msg, 
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Alert sent: {company}")
        else:
            print(f"❌ Alert failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Alert error: {e}")