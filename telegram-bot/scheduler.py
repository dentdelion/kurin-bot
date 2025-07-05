import schedule
import time
import asyncio
from telegram import Bot

import config
from user_manager import UserManager
from notifications import NotificationManager
from logging_config import setup_logging, get_logger

# Setup JSON logging
setup_logging(config.LOG_LEVEL)
logger = get_logger(__name__)

class BookScheduler:
    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
        self.user_manager = UserManager()
        self.notification_manager = NotificationManager(self.bot)
    
    def start_scheduler(self):
        """Start the scheduler with all tasks"""
        logger.info("Starting book scheduler...", extra={'action': 'scheduler_start', 'scheduler_task': 'init'})
        
        # Check for overdue books daily at 10:00 AM
        schedule.every().day.at("10:00").do(self.check_overdue_books)
        
        # Check for overdue books every 6 hours as backup
        schedule.every(6).hours.do(self.check_overdue_books)
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def check_overdue_books(self):
        """Check for overdue books and send notifications"""
        logger.info("Checking for overdue books...", extra={'action': 'check_overdue_books', 'scheduler_task': 'overdue_check'})
        
        try:
            overdue_books = self.user_manager.get_overdue_books()
            
            if overdue_books:
                logger.info(f"Found {len(overdue_books)} overdue books", 
                           extra={'action': 'overdue_books_found', 'scheduler_task': 'overdue_check', 'count': len(overdue_books)})
                
                # Run async notification function
                asyncio.run(self._send_overdue_notifications(overdue_books))
            else:
                logger.info("No overdue books found", extra={'action': 'no_overdue_books', 'scheduler_task': 'overdue_check'})
                
        except Exception as e:
            logger.error(f"Error checking overdue books: {e}", 
                        extra={'action': 'overdue_check_error', 'scheduler_task': 'overdue_check'})
    
    async def _send_overdue_notifications(self, overdue_books):
        """Send notifications for overdue books"""
        for book in overdue_books:
            try:
                # Send notification to user
                user_id = book['user_id']
                book_id = book['book_id']
                days_overdue = book['days_overdue']
                expiry_date = book['expiry_date'].strftime('%d.%m.%Y')
                
                # Get book name from sheets using book_id
                book_name = self._get_book_name_by_id(book_id)
                if not book_name:
                    book_name = f"Книга ID: {book_id}"
                
                message = (
                    f"⚠️ <b>Нагадування про повернення книги</b>\n\n"
                    f"📚 <b>Книга:</b> {book_name}\n"
                    f"📅 <b>Термін повернення був:</b> {expiry_date}\n"
                    f"⏰ <b>Прострочено на:</b> {days_overdue} днів\n\n"
                    f"Будь ласка, поверніть книгу якомога швидше!"
                )
                
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='HTML'
                )
                
                # Also notify admins about overdue books
                admin_message = (
                    f"📚 <b>Прострочена книга</b>\n\n"
                    f"👤 <b>Користувач:</b> {book['user_name']}\n"
                    f"📞 <b>Телефон:</b> {book['user_phone']}\n"
                    f"📚 <b>Книга:</b> {book_name}\n"
                    f"📅 <b>Термін був:</b> {expiry_date}\n"
                    f"⏰ <b>Прострочено на:</b> {days_overdue} днів"
                )
                
                for admin_id in config.ADMIN_IDS:
                    try:
                        await self.bot.send_message(
                            chat_id=admin_id,
                            text=admin_message,
                            parse_mode='HTML'
                        )
                    except Exception as admin_e:
                        logger.error(f"Failed to notify admin {admin_id}: {admin_e}")
                
                logger.info(f"Sent overdue notification for book ID '{book_id}' to user {user_id}")
                
            except Exception as e:
                logger.error(f"Error sending overdue notification for book ID {book['book_id']}: {e}")
    
    def _get_book_name_by_id(self, book_id):
        """Get book name by book_id from Google Sheets"""
        try:
            from google_sheets_manager import GoogleSheetsManager
            sheets_manager = GoogleSheetsManager()
            df = sheets_manager.read_books()
            if df.empty:
                return None
            
            # Find book by ID
            book_row = df[df[config.EXCEL_COLUMNS['id']].astype(str) == str(book_id)]
            if not book_row.empty:
                row = book_row.iloc[0]
                return f"{row[config.EXCEL_COLUMNS['name']]} - {row[config.EXCEL_COLUMNS['author']]}"
            return None
        except Exception as e:
            logger.error(f"Error getting book name for ID {book_id}: {e}")
            return None

def main():
    """Main function to run the scheduler"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    scheduler = BookScheduler()
    scheduler.start_scheduler()

if __name__ == "__main__":
    main() 