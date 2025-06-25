import schedule
import time
import asyncio
import logging
from datetime import datetime
from telegram import Bot

import config
from google_sheets_manager import GoogleSheetsManager
from notifications import NotificationManager

logger = logging.getLogger(__name__)

class BookScheduler:
    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
        self.sheets_manager = GoogleSheetsManager()
        self.notification_manager = NotificationManager(self.bot)
    
    def start_scheduler(self):
        """Start the scheduler with all tasks"""
        logger.info("Starting book scheduler...")
        
        # Check for overdue books daily at 10:00 AM
        schedule.every().day.at("10:00").do(self.check_overdue_books)
        
        # Check for overdue books every 6 hours as backup
        schedule.every(6).hours.do(self.check_overdue_books)
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def check_overdue_books(self):
        """Check for overdue books and send notifications"""
        logger.info("Checking for overdue books...")
        
        try:
            overdue_books = self.sheets_manager.get_overdue_books()
            
            if overdue_books:
                logger.info(f"Found {len(overdue_books)} overdue books")
                
                # Run async notification function
                asyncio.run(self._send_overdue_notifications(overdue_books))
            else:
                logger.info("No overdue books found")
                
        except Exception as e:
            logger.error(f"Error checking overdue books: {e}")
    
    async def _send_overdue_notifications(self, overdue_books):
        """Send notifications for overdue books"""
        for book in overdue_books:
            try:
                # Here you would need to find the user_id who has this book
                # This would require enhancing the Google Sheets structure to track user_id
                # For now, we'll log the overdue book
                logger.warning(f"Overdue book: {book['name']} by {book['author']}, "
                             f"due {book['due_date']}, {book['days_overdue']} days overdue")
                
                # If we had user_id, we would do:
                # await self.notification_manager.notify_user_book_overdue(user_id, book)
                
            except Exception as e:
                logger.error(f"Error sending overdue notification for book {book['name']}: {e}")

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