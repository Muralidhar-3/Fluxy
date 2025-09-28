"""
Automated NSE Data Fetcher with Scheduler
This script runs the NSE data fetching automatically at regular intervals
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask
from models import db, Announcement
from nse_scraper import fetch_nse_data
from config import SUPABASE_CONNECTION_URLS, DEBUG
from sqlalchemy import create_engine, text
import logging
from datetime import datetime
import atexit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nse_alerts.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def find_working_database_url():
    """Find working Supabase connection"""
    for i, url in enumerate(SUPABASE_CONNECTION_URLS, 1):
        try:
            engine = create_engine(url, pool_timeout=10, pool_recycle=3600)
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
                logger.info(f"✅ Database format {i} works!")
                return url
        except Exception as e:
            logger.warning(f"❌ Database format {i} failed: {str(e)[:100]}...")
            continue
    
    raise Exception("No working database connection found!")

def create_scheduler_app():
    """Create Flask app for scheduler"""
    app = Flask(__name__)
    
    # Database configuration
    working_db_url = find_working_database_url()
    app.config["SQLALCHEMY_DATABASE_URI"] = working_db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["DEBUG"] = DEBUG
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        logger.info("📊 Database tables ready")
    
    return app

def scheduled_fetch():
    """Scheduled NSE data fetch function"""
    try:
        logger.info("🔄 Starting scheduled NSE data fetch...")
        
        with scheduler_app.app_context():
            # Fetch new data
            new_announcements = fetch_nse_data(scheduler_app)
            
            if new_announcements:
                logger.info(f"✅ Found {len(new_announcements)} new announcements!")
                for ann in new_announcements:
                    logger.info(f"📢 {ann.company}: {ann.title[:50]}...")
            else:
                logger.info("📭 No new announcements found")
                
    except Exception as e:
        logger.error(f"❌ Scheduled fetch error: {e}")

def test_fetch_now():
    """Test function to manually trigger fetch"""
    logger.info("🧪 Manual test fetch triggered...")
    scheduled_fetch()

# Create the scheduler app
scheduler_app = create_scheduler_app()

# Create scheduler
scheduler = BackgroundScheduler(daemon=True)

def start_scheduler():
    """Start the automated scheduler"""
    logger.info("🚀 Starting NSE Alert Scheduler...")
    
    # Schedule during market hours (9:15 AM to 3:30 PM IST, Monday-Friday)
    # Fetch every 5 minutes during market hours
    scheduler.add_job(
        func=scheduled_fetch,
        trigger=CronTrigger(
            day_of_week='mon-fri',  # Monday to Friday
            hour='9-15',            # 9 AM to 3 PM IST
            minute='*/5'            # Every 5 minutes
        ),
        id='nse_market_hours_fetch',
        name='NSE Market Hours Fetch',
        replace_existing=True
    )
    
    # Additional fetch after market hours (once at 4 PM)
    scheduler.add_job(
        func=scheduled_fetch,
        trigger=CronTrigger(
            day_of_week='mon-fri',  # Monday to Friday
            hour=16,                # 4 PM IST
            minute=0                # At exactly 4:00 PM
        ),
        id='nse_post_market_fetch',
        name='NSE Post-Market Fetch',
        replace_existing=True
    )
    
    # Test fetch - run once immediately when starting
    scheduler.add_job(
        func=test_fetch_now,
        trigger='date',  # Run once
        id='initial_test_fetch',
        name='Initial Test Fetch'
    )
    
    # Start scheduler
    scheduler.start()
    logger.info("⏰ Scheduler started successfully!")
    
    # Print scheduled jobs
    jobs = scheduler.get_jobs()
    logger.info(f"📅 Scheduled {len(jobs)} jobs:")
    for job in jobs:
        logger.info(f"   - {job.name}: {job.next_run_time}")
    
    # Shutdown scheduler on exit
    atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    start_scheduler()
    
    # Keep the script running
    try:
        logger.info("🔄 NSE Alert System is running...")
        logger.info("📱 Telegram alerts will be sent for new announcements")
        logger.info("📊 Check 'nse_alerts.log' for detailed logs")
        logger.info("⏹️  Press Ctrl+C to stop")
        
        # Run a simple Flask app to keep it alive and provide status
        @scheduler_app.route('/')
        def status():
            from flask import jsonify
            jobs = scheduler.get_jobs()
            return jsonify({
                "status": "running",
                "scheduler_jobs": len(jobs),
                "next_runs": [
                    {
                        "job": job.name,
                        "next_run": str(job.next_run_time)
                    } for job in jobs
                ],
                "total_announcements": Announcement.query.count()
            })
        
        @scheduler_app.route('/fetch-now')
        def manual_fetch():
            from flask import jsonify
            try:
                with scheduler_app.app_context():
                    new_data = fetch_nse_data(scheduler_app)
                    return jsonify({
                        "status": "success",
                        "new_announcements": len(new_data) if new_data else 0
                    })
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "error": str(e)
                }), 500
        
        scheduler_app.run(host='0.0.0.0', port=5001, debug=False)
        
    except KeyboardInterrupt:
        logger.info("👋 Stopping NSE Alert System...")
        scheduler.shutdown()