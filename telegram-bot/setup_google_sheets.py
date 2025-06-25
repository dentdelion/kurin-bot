#!/usr/bin/env python3
"""
Google Sheets setup script for the Library Bot
Validates Google Sheets configuration and tests connection
"""

import os
import json
import logging
from google_sheets_manager import GoogleSheetsManager
import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_google_credentials():
    """Check if Google credentials file exists"""
    if os.path.exists(config.GOOGLE_CREDENTIALS_FILE):
        print(f"✅ Google credentials file found: {config.GOOGLE_CREDENTIALS_FILE}")
        
        # Validate JSON structure
        try:
            with open(config.GOOGLE_CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)
                if 'type' in creds and creds['type'] == 'service_account':
                    print("✅ Valid service account credentials file")
                    return True
                else:
                    print("❌ Invalid credentials file format")
                    return False
        except json.JSONDecodeError:
            print("❌ Invalid JSON in credentials file")
            return False
    else:
        print(f"❌ Google credentials file not found: {config.GOOGLE_CREDENTIALS_FILE}")
        print_credentials_instructions()
        return False

def print_credentials_instructions():
    """Print instructions for setting up Google credentials"""
    print("\n" + "="*70)
    print("📋 Google Service Account Setup Instructions")
    print("="*70)
    print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable Google Sheets API:")
    print("   - Go to APIs & Services > Library")
    print("   - Search for 'Google Sheets API' and enable it")
    print("4. Create Service Account:")
    print("   - Go to APIs & Services > Credentials")
    print("   - Click 'Create Credentials' > 'Service Account'")
    print("   - Fill in details and create")
    print("5. Create Key:")
    print("   - Click on created service account")
    print("   - Go to 'Keys' tab")
    print("   - Click 'Add Key' > 'Create new key' > 'JSON'")
    print(f"   - Save as '{config.GOOGLE_CREDENTIALS_FILE}' in this directory")
    print("6. Share your Google Sheet with service account email")
    print("   - Open your Google Sheet")
    print("   - Click 'Share' button")
    print("   - Add service account email (from JSON file)")
    print("   - Give 'Editor' permissions")
    print("="*70)

def check_google_sheets_url():
    """Check if Google Sheets URL is configured"""
    if config.GOOGLE_SHEETS_URL:
        print(f"✅ Google Sheets URL configured")
        return True
    else:
        print("❌ GOOGLE_SHEETS_URL not configured in .env file")
        print_url_instructions()
        return False

def print_url_instructions():
    """Print instructions for Google Sheets URL"""
    print("\n" + "="*50)
    print("📋 Google Sheets URL Setup")
    print("="*50)
    print("1. Open your Google Sheet")
    print("2. Copy the URL from browser address bar")
    print("3. Add to .env file:")
    print("   GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/...")
    print("="*50)

def test_google_sheets_connection():
    """Test connection to Google Sheets"""
    try:
        print("🔄 Testing Google Sheets connection...")
        sheets_manager = GoogleSheetsManager()
        print("✅ Successfully connected to Google Sheets")
        
        # Try to read data
        df = sheets_manager.read_books()
        if df.empty:
            print("⚠️  Google Sheet is empty - you need to add book data manually")
            print("📝 Please add books to your Google Sheet with the required columns")
            return True
        else:
            print(f"✅ Google Sheet contains {len(df)} rows of data")
            return True
            
    except Exception as e:
        print(f"❌ Error connecting to Google Sheets: {e}")
        return False

def print_required_columns():
    """Print the required column structure"""
    print("\n" + "="*60)
    print("📋 Required Google Sheet Column Structure")
    print("="*60)
    print("Your Google Sheet must have these columns (in any order):")
    for key, value in config.EXCEL_COLUMNS.items():
        print(f"  - {value}")
    print("\nExample data structure:")
    print("  Назва: Історія України")
    print("  Автор: Грушевський М.С.")
    print("  Видавництво та рік видання: Видавництво 'Освіта', 2020")
    print("  К-сть с.: 450")
    print("  Короткий опис: Фундаментальна праця з історії України")
    print("  Заброньовано до: (leave empty for available books)")
    print("  Categories: історія, українська література")
    print("  In queue for delivery: no")
    print("="*60)

def main():
    """Main setup function"""
    print("🚀 Google Sheets Setup for Library Bot")
    print("=" * 50)
    
    # Check credentials
    if not check_google_credentials():
        return False
    
    # Check URL configuration
    if not check_google_sheets_url():
        return False
    
    # Test connection
    if not test_google_sheets_connection():
        return False
    
    # Show required columns structure
    print_required_columns()
    
    print("\n" + "="*50)
    print("🎉 Google Sheets setup validation completed!")
    print("="*50)
    print("✅ Your bot is configured to use Google Sheets")
    print("📝 Make sure your Google Sheet has the required columns and data")
    print("🤖 Run 'python bot.py' or 'python run.py' to start the bot")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Setup validation failed. Please fix the issues above before running the bot.")
        exit(1) 