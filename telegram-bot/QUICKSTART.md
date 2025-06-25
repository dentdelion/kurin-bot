# 🚀 Quick Start Guide - Google Sheets Edition

## 1. Initial Setup (5 minutes)

```bash
cd telegram-bot

# Install dependencies
pip install -r requirements.txt
```

## 2. Google Sheets Setup

### Create Google Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable Google Sheets API
4. Create Service Account credentials
5. Download JSON key file as `credentials.json`

### Create Google Sheet
1. Create new Google Sheet
2. Add required columns (see structure below)
3. Share with service account email (Editor permissions)
4. Copy sheet URL

**Required Columns:**
- Назва
- Автор  
- Видавництво та рік видання
- К-сть с.
- Короткий опис
- Заброньовано до:
- Categories
- In queue for delivery

## 3. Configure Bot Token

Edit `.env` file:
```bash
BOT_TOKEN=YOUR_ACTUAL_BOT_TOKEN_HERE
ADMIN_IDS=your_telegram_id,another_admin_id
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
GOOGLE_CREDENTIALS_FILE=credentials.json
```

**How to get Bot Token:**
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Choose bot name and username
4. Copy the token

**How to get your Telegram ID:**
1. Message @userinfobot on Telegram
2. Copy your ID number

## 4. Test Google Sheets Connection

```bash
python setup_google_sheets.py
```

This will:
- ✅ Verify credentials file
- ✅ Test Google Sheets connection
- ✅ Create sample data (optional)

## 5. Run the Bot

### Option A: Full system (recommended)
```bash
python run.py
```

### Option B: Bot only
```bash
python bot.py
```

### Option C: Separate processes
```bash
# Terminal 1
python bot.py

# Terminal 2  
python scheduler.py
```

## 6. Test the Bot

1. Find your bot on Telegram (search by username)
2. Send `/start`
3. Share your phone number
4. Browse books by category
5. Try booking a book

## 7. Admin Features

If your Telegram ID is in `ADMIN_IDS`:
- You'll see "🔧 Адмін панель" button
- Can view delivery queue
- Can mark books as delivered
- Receive booking notifications

## 📁 File Structure

- `bot.py` - Main bot logic
- `config.py` - Configuration settings  
- `google_sheets_manager.py` - Google Sheets operations
- `user_manager.py` - User data management
- `keyboards.py` - Telegram keyboards
- `notifications.py` - Admin/user notifications
- `scheduler.py` - Overdue book checker
- `setup_google_sheets.py` - Google Sheets setup helper
- `credentials.json` - Google service account key
- `users.json` - User database (auto-created)

## 🔧 Google Sheets Management

### Add More Books
1. Open your Google Sheet in browser
2. Add new rows with required data
3. Ensure Categories column has comma-separated values
4. Set "In queue for delivery" to "no" for available books

### Book Status Colors
- 🟢 **White/Default** - Available
- 🟡 **Yellow** - Currently borrowed
- 📦 **"yes"** in delivery column - Awaiting delivery
- 📚 **"delivered"** in delivery column - Ready for pickup

### Change Categories
Edit `BOOK_CATEGORIES` in `config.py`

### Modify Rules
Edit `RULES_TEXT` in `.env` file

### Change Book Loan Period
Edit `ALLOWED_TIME_TO_READ_THE_BOOK` in `.env` (days)

## ❗ Troubleshooting

### Bot doesn't respond
- Check bot token in `.env`
- Ensure bot is started with @BotFather

### Google Sheets errors
```bash
# Run diagnostics
python setup_google_sheets.py

# Common issues:
# 1. Service account not shared with sheet
# 2. Invalid credentials.json
# 3. Google Sheets API not enabled
# 4. Wrong sheet URL format
```

### Admin features not working  
- Verify your Telegram ID in `ADMIN_IDS`
- Use actual numeric ID, not username

### Dependencies issues
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Connection problems
- Check internet connection
- Verify Google Sheets is accessible
- Ensure service account has editor permissions

## 🚀 Advantages of Google Sheets

- 🌐 **Online Access** - Edit from anywhere
- 👥 **Multi-admin** - Multiple people can manage
- 📱 **Mobile App** - Use Google Sheets app
- 🎨 **Visual Status** - Color coding for borrowed books
- 💾 **Auto Backup** - Google handles backups
- 📊 **Easy Export** - Download as Excel, CSV, etc.
- 🔄 **Real-time Sync** - Changes appear instantly

## 🆘 Need Help?

1. Run `python setup_google_sheets.py` for diagnostics
2. Check logs for error messages
3. Verify Google Sheets configuration
4. Ensure all permissions are set correctly
5. Test with sample data first

## 🔄 Migration from Excel

If upgrading from Excel version:
1. Export your Excel data
2. Create Google Sheet with same structure
3. Import data to Google Sheet
4. Update bot configuration
5. Run setup script to verify 