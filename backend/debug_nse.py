#!/usr/bin/env python3
"""
Debug script to identify issues with NSE fetching
Run this to diagnose problems before running the main app
"""

import requests
import sys
import traceback
from urllib.parse import quote_plus

def test_nse_api():
    """Test NSE API connection"""
    print("=" * 50)
    print("🧪 TESTING NSE API CONNECTION")
    print("=" * 50)
    
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "Connection": "keep-alive",
        })
        
        url = "https://www.nseindia.com/api/corporate-announcements?index=equities"
        print(f"📡 Making request to: {url}")
        
        response = session.get(url, timeout=15)
        print(f"✅ Status Code: {response.status_code}")
        print(f"📋 Content-Type: {response.headers.get('content-type', 'N/A')}")
        print(f"📏 Content Length: {len(response.text)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"📊 Response Type: {type(data)}")
                
                if isinstance(data, list):
                    print(f"🎯 Total Items: {len(data)}")
                    if len(data) > 0:
                        print("📝 Sample Item Keys:", list(data[0].keys()))
                        return True
                elif isinstance(data, dict):
                    print(f"🗂️ Dict Keys: {list(data.keys())}")
                    if 'data' in data:
                        print(f"📊 Data Items: {len(data['data'])}")
                    return True
                else:
                    print(f"❌ Unexpected data type: {type(data)}")
                    
            except Exception as json_error:
                print(f"❌ JSON Parsing Error: {json_error}")
                print(f"📄 Raw Response (first 500 chars): {response.text[:500]}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"📄 Response: {response.text[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        traceback.print_exc()
        return False

def test_database_connection():
    """Test database connection"""
    print("\n" + "=" * 50)
    print("🗃️ TESTING DATABASE CONNECTION")
    print("=" * 50)
    
    try:
        # Import here to avoid issues if modules are missing
        from sqlalchemy import create_engine, text
        
        # Database credentials
        DB_PASSWORD = "Supabase8978#"
        DB_USER = "postgres.uscdhsnzeqomoaqwtdne"
        DB_HOST = "aws-1-ap-south-1.pooler.supabase.com"
        DB_PORT = "6543"
        DB_NAME = "postgres"
        
        # Encode password
        encoded_password = quote_plus(DB_PASSWORD)
        
        # Try multiple connection string formats
        connection_strings = [
            f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
        ]
        
        for i, conn_str in enumerate(connection_strings, 1):
            print(f"\n🔗 Attempt {i}: Testing connection string format {i}")
            try:
                engine = create_engine(conn_str)
                
                # Test connection
                with engine.connect() as connection:
                    result = connection.execute(text("SELECT version()"))
                    version = result.fetchone()[0]
                    print(f"✅ Connection successful!")
                    print(f"📊 PostgreSQL Version: {version}")
                    
                    # Test basic query
                    result = connection.execute(text("SELECT current_database(), current_user"))
                    db_info = result.fetchone()
                    print(f"🏷️ Database: {db_info[0]}, User: {db_info[1]}")
                    
                    return True
                    
            except Exception as conn_error:
                print(f"❌ Connection {i} failed: {conn_error}")
                continue
                
        print("❌ All connection attempts failed")
        return False
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("💡 Install required packages: pip install sqlalchemy psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Database test error: {e}")
        traceback.print_exc()
        return False

def test_telegram_config():
    """Test Telegram configuration"""
    print("\n" + "=" * 50)
    print("📱 TESTING TELEGRAM CONFIGURATION")
    print("=" * 50)
    
    try:
        bot_token = "8025955874:AAE60iDILQHM7-uyctejwDg3DWErfLuYxCo"
        chat_id = "622849107"
        
        # Test bot token validity
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print(f"✅ Bot Token Valid")
                print(f"🤖 Bot Name: {bot_info.get('first_name', 'N/A')}")
                print(f"🆔 Bot Username: @{bot_info.get('username', 'N/A')}")
            else:
                print(f"❌ Bot Token Invalid: {data}")
                return False
        else:
            print(f"❌ Bot API Error: {response.status_code}")
            return False
            
        # Test sending message
        test_msg = "🧪 Test message from NSE Alert System"
        send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": test_msg,
            "parse_mode": "HTML"
        }
        
        response = requests.post(send_url, data=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Test message sent successfully!")
            return True
        else:
            print(f"❌ Message send failed: {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Telegram test error: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("🔍 NSE ALERT SYSTEM - DIAGNOSTIC TOOL")
    print("=" * 60)
    
    tests = [
        ("NSE API", test_nse_api),
        ("Database", test_database_connection),
        ("Telegram", test_telegram_config)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Your system should work correctly.")
    else:
        print("⚠️  Some tests failed. Fix the issues above before running the main app.")
        sys.exit(1)

if __name__ == "__main__":
    main()