from urllib.parse import quote_plus
import os

# Database credentials - REPLACE THESE WITH YOUR ACTUAL SUPABASE DETAILS
SUPABASE_PROJECT_REF = "uscdhsnzeqomoaqwtdne"  # Your project reference ID
SUPABASE_PASSWORD = "Supabase8978"     # Your database password
SUPABASE_REGION = "ap-south-1"          # Your region

# Properly encode the password for URL
encoded_password = quote_plus(SUPABASE_PASSWORD)

# Try multiple Supabase connection formats (the app will test these in order)
SUPABASE_CONNECTION_URLS = [
    # Format 1: Connection pooling (most common)
    f"postgresql://postgres.{SUPABASE_PROJECT_REF}:{encoded_password}@aws-0-{SUPABASE_REGION}.pooler.supabase.com:6543/postgres",
    
    # Format 2: Alternative connection pooling 
    f"postgresql://postgres.{SUPABASE_PROJECT_REF}:{encoded_password}@aws-1-{SUPABASE_REGION}.pooler.supabase.com:6543/postgres",
    
    # Format 3: Direct connection
    f"postgresql://postgres:{encoded_password}@db.{SUPABASE_PROJECT_REF}.supabase.co:5432/postgres?sslmode=require",
    
    # Format 4: Connection pooling with SSL
    f"postgresql://postgres.{SUPABASE_PROJECT_REF}:{encoded_password}@aws-0-{SUPABASE_REGION}.pooler.supabase.com:6543/postgres?sslmode=require",
]

# Default to the first URL (will be tested in app.py)
DATABASE_URL = SUPABASE_CONNECTION_URLS[0]

# Environment variable override
if os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL")

# NSE URL (Corporate Announcements API)
NSE_API_URL = "https://www.nseindia.com/api/corporate-announcements?index=equities"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = "8025955874:AAE60iDILQHM7-uyctejwDg3DWErfLuYxCo"
TELEGRAM_CHAT_ID = "622849107"

# Path to Nifty 500 list
NIFTY500_FILE = "assets/nifty500.json"

# Debug settings
DEBUG = True
SQLALCHEMY_ECHO = False  # Set to True to see SQL queries