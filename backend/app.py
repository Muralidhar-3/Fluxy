from flask import Flask, jsonify
from models import db, Announcement
from nse_scraper import fetch_nse_data
from config import SUPABASE_CONNECTION_URLS, DATABASE_URL, DEBUG, SQLALCHEMY_ECHO
from sqlalchemy import create_engine, text
import traceback

def find_working_database_url():
    """Test multiple Supabase connection formats and return the working one"""
    print("🔍 Testing Supabase connection formats...")
    
    for i, url in enumerate(SUPABASE_CONNECTION_URLS, 1):
        try:
            print(f"📡 Testing format {i}...")
            # Hide password in logs
            safe_url = url.split('://')[0] + '://***:***@' + url.split('@')[1]
            print(f"   URL: {safe_url}")
            
            # Test connection
            engine = create_engine(url, pool_timeout=10, pool_recycle=3600)
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
                print(f"✅ Format {i} works!")
                return url
                
        except Exception as e:
            print(f"❌ Format {i} failed: {str(e)[:100]}...")
            continue
    
    print("❌ No working database connection found!")
    raise Exception("Unable to connect to Supabase database. Please check your credentials.")

def create_app():
    """Application factory with automatic database URL detection"""
    app = Flask(__name__)
    
    # Find working database URL
    try:
        working_db_url = find_working_database_url()
        app.config["SQLALCHEMY_DATABASE_URI"] = working_db_url
        print(f"✅ Using working database connection")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        # Fallback to default
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = SQLALCHEMY_ECHO
    app.config["DEBUG"] = DEBUG
    
    # Initialize database
    db.init_app(app)
    
    return app

app = create_app()

# Test database connection and create tables
def init_db():
    """Initialize database with error handling"""
    try:
        with app.app_context():
            print("🔗 Testing database connection...")
            
            # Test connection (SQLAlchemy 2.0 compatible)
            with db.engine.connect() as connection:
                result = connection.execute(text('SELECT 1'))
                result.fetchone()
            print("✅ Database connection successful!")
            
            # Create tables
            print("🗃️ Creating database tables...")
            db.create_all()
            print("✅ Tables created successfully!")
            
            # Test query
            count = Announcement.query.count()
            print(f"📊 Current announcements in database: {count}")
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        traceback.print_exc()
        raise

@app.route("/", methods=["GET"])
def home():
    """Health check endpoint"""
    try:
        with app.app_context():
            count = Announcement.query.count()
            return jsonify({
                "status": "healthy",
                "total_announcements": count,
                "message": "NSE Alert System is running"
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/announcements", methods=["GET"])
def get_announcements():
    """Get recent announcements"""
    try:
        anns = Announcement.query.order_by(
            Announcement.date.desc()
        ).limit(50).all()
        
        return jsonify({
            "status": "success",
            "count": len(anns),
            "announcements": [a.to_dict() for a in anns]
        })
    except Exception as e:
        print(f"❌ Error fetching announcements: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/fetch", methods=["GET"])
def fetch_now():
    """Manually trigger NSE data fetch"""
    try:
        print("🚀 Manual fetch triggered...")
        new_data = fetch_nse_data(app)
        
        return jsonify({
            "status": "success",
            "new_announcements": len(new_data) if new_data else 0,
            "message": f"Fetched {len(new_data) if new_data else 0} new announcements"
        })
    except Exception as e:
        print(f"❌ Error during manual fetch: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/test-db", methods=["GET"])
def test_db():
    """Test database connection"""
    try:
        # Test basic connection (SQLAlchemy 2.0 compatible)
        with db.engine.connect() as connection:
            result = connection.execute(text('SELECT version()'))
            version = result.fetchone()[0]
        
        # Test table existence
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Test announcement count
        count = Announcement.query.count()
        
        return jsonify({
            "status": "success",
            "database_version": version,
            "tables": tables,
            "announcement_count": count
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/test-api", methods=["GET"])
def test_api():
    """Test NSE API connection"""
    import requests
    
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
        })
        
        from config import NSE_API_URL
        response = session.get(NSE_API_URL, timeout=10)
        
        return jsonify({
            "status": "success",
            "api_status_code": response.status_code,
            "content_type": response.headers.get('content-type'),
            "response_length": len(response.text),
            "is_json": response.headers.get('content-type', '').startswith('application/json')
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    # Initialize database on startup
    init_db()
    
    print("🚀 Starting Flask application...")
    app.run(debug=DEBUG, host="0.0.0.0", port=5000)