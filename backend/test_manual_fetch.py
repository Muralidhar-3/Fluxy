#!/usr/bin/env python3
"""
Test script to manually trigger NSE data fetch and see if alerts work
Run this to test if your system is working before setting up automation
"""

from flask import Flask
from models import db, Announcement
from nse_scraper import fetch_nse_data
from config import SUPABASE_CONNECTION_URLS, DEBUG
from sqlalchemy import create_engine, text
import requests

def find_working_database_url():
    """Find working database connection"""
    for i, url in enumerate(SUPABASE_CONNECTION_URLS, 1):
        try:
            engine = create_engine(url, pool_timeout=10, pool_recycle=3600)
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
                print(f"✅ Database format {i} works!")
                return url
        except Exception as e:
            continue
    raise Exception("No working database connection found!")

def create_test_app():
    """Create test Flask app"""
    app = Flask(__name__)
    
    working_db_url = find_working_database_url()
    app.config["SQLALCHEMY_DATABASE_URI"] = working_db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["DEBUG"] = DEBUG
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        print("📊 Database ready")
    
    return app

def clear_all_announcements(app):
    """Clear all existing announcements (for testing)"""
    with app.app_context():
        count = Announcement.query.count()
        if count > 0:
            choice = input(f"Found {count} existing announcements. Clear them for fresh test? (y/N): ")
            if choice.lower() == 'y':
                Announcement.query.delete()
                db.session.commit()
                print(f"🗑️  Cleared {count} announcements")
        else:
            print("📭 No existing announcements")

def test_nse_api_direct():
    """Test NSE API directly"""
    print("\n" + "="*50)
    print("🧪 TESTING NSE API DIRECTLY")
    print("="*50)
    
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
        })
        
        url = "https://www.nseindia.com/api/corporate-announcements?index=equities"
        response = session.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                print(f"✅ API working! Found {len(data)} announcements")
                
                # Show first few announcements
                print("\n📋 Sample announcements:")
                for i, item in enumerate(data[:3]):
                    company = item.get('symbol', 'N/A')
                    desc = item.get('desc', 'N/A')
                    date = item.get('an_dt', 'N/A')
                    print(f"   {i+1}. {company}: {desc[:60]}... ({date})")
                return True
            else:
                print("❌ API returned empty data")
                return False
        else:
            print(f"❌ API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_telegram_connection():
    """Test Telegram bot"""
    print("\n" + "="*50)
    print("📱 TESTING TELEGRAM CONNECTION")
    print("="*50)
    
    try:
        from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        
        # Test message
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        test_msg = "🧪 NSE Alert System Test - Manual Fetch Starting!"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": test_msg,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Telegram test message sent!")
            return True
        else:
            print(f"❌ Telegram error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram test failed: {e}")
        return False

def run_manual_fetch_test():
    """Run the complete manual fetch test"""
    print("🚀 NSE ALERT SYSTEM - MANUAL FETCH TEST")
    print("="*60)
    
    # Create test app
    app = create_test_app()
    
    # Test components
    api_ok = test_nse_api_direct()
    telegram_ok = test_telegram_connection()
    
    if not api_ok:
        print("❌ NSE API test failed. Cannot proceed.")
        return
    
    if not telegram_ok:
        print("⚠️  Telegram test failed. You'll see data but no alerts.")
    
    # Clear existing data if requested
    clear_all_announcements(app)
    
    print("\n" + "="*50)
    print("🔄 RUNNING MANUAL FETCH")
    print("="*50)
    
    # Run the actual fetch
    with app.app_context():
        print("📡 Fetching NSE data...")
        new_announcements = fetch_nse_data(app)
        
        if new_announcements:
            print(f"🎉 SUCCESS! Found {len(new_announcements)} new announcements:")
            print()
            
            # Refresh the session to avoid DetachedInstanceError
            with app.app_context():
                # Re-query the announcements to avoid session issues
                latest_announcements = Announcement.query.order_by(
                    Announcement.id.desc()
                ).limit(len(new_announcements)).all()
                
                for i, ann in enumerate(latest_announcements, 1):
                    print(f"   {i}. 📢 {ann.company}")
                    print(f"      📝 {ann.title}")
                    print(f"      📅 {ann.date}")
                    if ann.link:
                        print(f"      🔗 {ann.link}")
                    print()
            
            print("✅ Telegram alerts should have been sent!")
            print("📱 Check your Telegram for notifications")
            
        else:
            print("📭 No new announcements found.")
            print("💭 This could mean:")
            print("   - All current announcements are already in database")
            print("   - NSE API returned no data")
            print("   - There might be an issue with data processing")
            
            # Check total announcements
            total = Announcement.query.count()
            print(f"   📊 Total announcements in database: {total}")
    
    print("\n" + "="*50)
    print("🎯 TEST COMPLETE")
    print("="*50)
    
    if new_announcements:
        print("✅ Your NSE Alert System is working perfectly!")
        print("🚀 You can now run the automated scheduler:")
        print("   python scheduler.py")
    else:
        print("⚠️  Manual fetch didn't find new announcements.")
        print("🔧 Try running this test again later or check the logs.")

if __name__ == "__main__":
    run_manual_fetch_test()