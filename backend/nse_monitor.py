#!/usr/bin/env python3
"""
NSE Continuous Monitoring Service
Runs in the background and continuously monitors for new NSE announcements
Sends Telegram alerts immediately when new announcements are found
"""

import time
import threading
from datetime import datetime, timedelta
from flask import Flask
from models import db, Announcement
from nse_scraper_simple import fetch_nse_data, send_telegram_alert
from config import SUPABASE_CONNECTION_URLS, DEBUG, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from sqlalchemy import create_engine, text
import logging
import requests
import signal
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nse_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NSEMonitorService:
    def __init__(self):
        self.app = None
        self.running = False
        self.fetch_interval = 120  # 2 minutes default
        self.last_fetch_time = None
        self.total_alerts_sent = 0
        
    def find_working_database_url(self):
        """Find working database connection"""
        for i, url in enumerate(SUPABASE_CONNECTION_URLS, 1):
            try:
                engine = create_engine(url, pool_timeout=10, pool_recycle=3600)
                with engine.connect() as connection:
                    result = connection.execute(text("SELECT 1"))
                    result.fetchone()
                logger.info(f"✅ Database format {i} works!")
                return url
            except Exception:
                continue
        raise Exception("No working database connection found!")

    def create_app(self):
        """Create Flask app for monitoring"""
        app = Flask(__name__)
        
        working_db_url = self.find_working_database_url()
        app.config["SQLALCHEMY_DATABASE_URI"] = working_db_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["DEBUG"] = False  # Disable debug in background service
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            logger.info("📊 Database tables ready")
        
        return app

    def send_startup_notification(self):
        """Send notification that monitoring has started"""
        try:
            if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
                return
                
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            msg = "🚀 <b>NSE Alert System Started!</b>\n\n📡 Monitoring for new corporate announcements...\n⏰ Check interval: 2 minutes during market hours\n🔔 You'll receive detailed alerts for new announcements"
            
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=payload, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Startup notification sent")
            
        except Exception as e:
            logger.error(f"❌ Failed to send startup notification: {e}")

    def send_status_update(self, new_count, total_announcements):
        """Send periodic status update"""
        try:
            if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
                return
                
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            
            if new_count > 0:
                msg = f"📊 <b>NSE Monitor Status</b>\n\n🆕 Found {new_count} new announcements!\n📈 Total tracked: {total_announcements}\n⏰ Last check: {datetime.now().strftime('%H:%M:%S')}"
            else:
                msg = f"💤 <b>NSE Monitor Status</b>\n\n✅ System running normally\n📊 Total announcements: {total_announcements}\n⏰ Last check: {datetime.now().strftime('%H:%M:%S')}"
            
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, data=payload, timeout=10)
            
        except Exception as e:
            logger.error(f"❌ Failed to send status update: {e}")

    def fetch_and_alert(self):
        """Fetch new announcements and send alerts"""
        try:
            with self.app.app_context():
                logger.info("🔄 Checking for new announcements...")
                
                # Get current count before fetch
                before_count = Announcement.query.count()
                
                # Fetch new data
                new_announcements = fetch_nse_data(self.app)
                
                # Get count after fetch
                after_count = Announcement.query.count()
                actual_new = after_count - before_count
                
                if new_announcements and len(new_announcements) > 0:
                    logger.info(f"🎉 Found {len(new_announcements)} new announcements!")
                    self.total_alerts_sent += len(new_announcements)
                    
                    # Send summary if many announcements
                    if len(new_announcements) > 5:
                        self.send_bulk_alert_summary(new_announcements)
                    
                    # Send status update
                    self.send_status_update(len(new_announcements), after_count)
                    
                else:
                    logger.info("📭 No new announcements found")
                    
                self.last_fetch_time = datetime.now()
                
        except Exception as e:
            logger.error(f"❌ Error during fetch: {e}")
            # Send error notification
            try:
                if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                    msg = f"⚠️ <b>NSE Monitor Error</b>\n\n❌ Error: {str(e)[:100]}\n🔄 Will retry in next cycle"
                    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
                    requests.post(url, data=payload, timeout=10)
            except:
                pass

    def send_bulk_alert_summary(self, announcements):
        """Send summary when many announcements are found"""
        try:
            if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
                return
                
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            
            # Group by company with improved formatting
            companies = {}
            for ann in announcements[:10]:  # Limit to first 10 to avoid message size limits
                # Use company name if available, otherwise symbol
                display_key = ann.companyName if ann.companyName else ann.company
                company_symbol = ann.company
                
                if display_key not in companies:
                    companies[display_key] = {
                        'symbol': company_symbol,
                        'announcements': []
                    }
                companies[display_key]['announcements'].append(ann.title[:60] + "...")
            
            msg = f"📢 <b>Bulk Announcements Alert</b>\n\n🆕 Found {len(announcements)} new announcements:\n\n"
            
            for company_name, data in list(companies.items())[:5]:  # Show top 5 companies
                # Show company name and symbol
                if data['symbol'] and company_name != data['symbol']:
                    msg += f"🏢 <b>{company_name} ({data['symbol']})</b>:\n"
                else:
                    msg += f"🏢 <b>{data['symbol']}</b>:\n"
                
                for title in data['announcements'][:2]:  # Show max 2 titles per company
                    msg += f"   • {title}\n"
                if len(data['announcements']) > 2:
                    msg += f"   • ... and {len(data['announcements']) - 2} more\n"
                msg += "\n"
            
            if len(announcements) > 10:
                msg += f"... and {len(announcements) - 10} more announcements\n\n"
            
            msg += f"🔔 Individual detailed alerts sent for each announcement"
            
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "HTML"
            }
            
            requests.post(url, data=payload, timeout=10)
            
        except Exception as e:
            logger.error(f"❌ Failed to send bulk summary: {e}")

    def monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("🔄 Starting monitoring loop...")
        
        while self.running:
            try:
                # Check if it's market hours (9 AM to 6 PM IST, Mon-Fri)
                now = datetime.now()
                is_weekday = now.weekday() < 5  # Monday = 0, Sunday = 6
                is_market_hours = 9 <= now.hour <= 18
                
                if is_weekday and is_market_hours:
                    # More frequent during market hours
                    self.fetch_interval = 120  # 2 minutes
                else:
                    # Less frequent outside market hours
                    self.fetch_interval = 300  # 5 minutes
                
                self.fetch_and_alert()
                
                logger.info(f"⏰ Next check in {self.fetch_interval // 60} minutes...")
                
                # Sleep in small chunks so we can interrupt cleanly
                for _ in range(self.fetch_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("🛑 Keyboard interrupt received")
                self.stop()
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

    def start(self):
        """Start the monitoring service"""
        logger.info("🚀 Starting NSE Monitor Service...")
        
        try:
            # Create Flask app
            self.app = self.create_app()
            
            # Send startup notification
            self.send_startup_notification()
            
            # Start monitoring
            self.running = True
            
            # Run initial fetch
            logger.info("🔄 Running initial fetch...")
            self.fetch_and_alert()
            
            # Start monitoring loop in background
            monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            monitor_thread.start()
            
            # Simple web interface for status
            @self.app.route('/')
            def status():
                from flask import jsonify
                with self.app.app_context():
                    total_announcements = Announcement.query.count()
                    latest = Announcement.query.order_by(Announcement.id.desc()).first()
                    
                    latest_info = None
                    if latest:
                        latest_info = {
                            "company": latest.company,
                            "companyName": latest.companyName,
                            "title": latest.title,
                            "desc": latest.desc[:100] + "..." if latest.desc and len(latest.desc) > 100 else latest.desc,
                            "date": latest.date.isoformat()
                        }
                    
                return jsonify({
                    "status": "running" if self.running else "stopped",
                    "last_fetch": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
                    "fetch_interval_minutes": self.fetch_interval // 60,
                    "total_announcements": total_announcements,
                    "total_alerts_sent": self.total_alerts_sent,
                    "latest_announcement": latest_info
                })
            
            @self.app.route('/force-fetch')
            def force_fetch():
                from flask import jsonify
                logger.info("🔄 Manual fetch triggered via web interface")
                self.fetch_and_alert()
                return jsonify({"status": "fetch_triggered"})
            
            # Run Flask app
            logger.info("🌐 Web interface available at: http://localhost:5001")
            logger.info("📊 Status: http://localhost:5001/")
            logger.info("🔄 Manual fetch: http://localhost:5001/force-fetch")
            logger.info("⏹️  Press Ctrl+C to stop")
            
            self.app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
            
        except Exception as e:
            logger.error(f"❌ Failed to start service: {e}")
            self.stop()

    def stop(self):
        """Stop the monitoring service"""
        logger.info("🛑 Stopping NSE Monitor Service...")
        self.running = False
        
        # Send shutdown notification
        try:
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                msg = f"🛑 <b>NSE Monitor Stopped</b>\n\n📊 Total alerts sent: {self.total_alerts_sent}\n⏰ Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}
                requests.post(url, data=payload, timeout=5)
        except:
            pass

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("🛑 Shutdown signal received")
    if 'monitor' in globals():
        monitor.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Setup signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start monitor
    monitor = NSEMonitorService()
    monitor.start()