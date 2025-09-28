#!/usr/bin/env python3
"""
Database Migration Script
Adds companyName and desc columns to existing announcements table
Run this once to update your existing database schema
"""

from flask import Flask
from models import db, Announcement
from config import SUPABASE_CONNECTION_URLS
from sqlalchemy import create_engine, text
import sys

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
        except Exception:
            continue
    raise Exception("No working database connection found!")

def create_app():
    """Create Flask app for migration"""
    app = Flask(__name__)
    
    working_db_url = find_working_database_url()
    app.config["SQLALCHEMY_DATABASE_URI"] = working_db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    return app

def migrate_database():
    """Add new columns to existing table"""
    print("🔄 Starting database migration...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            with db.engine.connect() as connection:
                # Check for companyName column
                result = connection.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'announcements' 
                    AND column_name = 'companyName'
                """))
                
                company_name_exists = result.fetchone() is not None
                
                # Check for desc column
                result = connection.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'announcements' 
                    AND column_name = 'desc'
                """))
                
                desc_exists = result.fetchone() is not None
                
                print(f"📊 companyName column exists: {company_name_exists}")
                print(f"📊 desc column exists: {desc_exists}")
                
                # Add companyName column if it doesn't exist
                if not company_name_exists:
                    print("➕ Adding companyName column...")
                    connection.execute(text("""
                        ALTER TABLE announcements 
                        ADD COLUMN "companyName" VARCHAR(500)
                    """))
                    connection.commit()
                    print("✅ companyName column added")
                else:
                    print("✅ companyName column already exists")
                
                # Add desc column if it doesn't exist
                if not desc_exists:
                    print("➕ Adding desc column...")
                    connection.execute(text("""
                        ALTER TABLE announcements 
                        ADD COLUMN "desc" TEXT
                    """))
                    connection.commit()
                    print("✅ desc column added")
                else:
                    print("✅ desc column already exists")
                
                # Check final table structure
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'announcements'
                    ORDER BY ordinal_position
                """))
                
                print("\n📋 Final table structure:")
                for row in result:
                    nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                    print(f"   - {row[0]}: {row[1]} ({nullable})")
                
                # Check record count
                result = connection.execute(text("SELECT COUNT(*) FROM announcements"))
                count = result.fetchone()[0]
                print(f"\n📊 Total records in table: {count}")
                
            print("\n✅ Database migration completed successfully!")
            print("🚀 You can now run your updated NSE monitor with the new fields")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

def verify_migration():
    """Verify the migration was successful"""
    print("\n🔍 Verifying migration...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Try to create the tables with new schema (should update existing)
            db.create_all()
            
            # Test if we can query with new columns
            latest = Announcement.query.order_by(Announcement.id.desc()).first()
            
            if latest:
                print(f"✅ Can access record ID: {latest.id}")
                print(f"✅ Company: {latest.company}")
                print(f"✅ CompanyName: {getattr(latest, 'companyName', 'N/A')}")
                print(f"✅ Title: {latest.title}")
                print(f"✅ Desc: {getattr(latest, 'desc', 'N/A')}")
                print(f"✅ Date: {latest.date}")
            else:
                print("ℹ️  No records in database yet")
            
            print("✅ Migration verification successful!")
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🗃️ NSE DATABASE MIGRATION TOOL")
    print("=" * 50)
    
    choice = input("Do you want to proceed with the migration? (y/N): ")
    if choice.lower() != 'y':
        print("❌ Migration cancelled")
        sys.exit(0)
    
    migrate_database()
    verify_migration()
    
    print("\n🎉 All done! Your database is ready for the enhanced NSE monitor.")