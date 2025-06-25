#!/usr/bin/env python3
"""
Main runner for the Library Bot
Starts both the bot and scheduler in separate processes
"""

import multiprocessing
import logging
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot import LibraryBot
from scheduler import BookScheduler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def run_bot():
    """Run the Telegram bot"""
    try:
        bot = LibraryBot()
        bot.run()
    except Exception as e:
        logger.error(f"Error running bot: {e}")

def run_scheduler():
    """Run the book scheduler"""
    try:
        scheduler = BookScheduler()
        scheduler.start_scheduler()
    except Exception as e:
        logger.error(f"Error running scheduler: {e}")

def main():
    """Main function to start both processes"""
    logger.info("Starting Library Bot system...")
    
    # Check Google Sheets configuration
    import config
    if not config.GOOGLE_SHEETS_URL:
        logger.warning("GOOGLE_SHEETS_URL not configured")
        logger.info("Please set GOOGLE_SHEETS_URL in your .env file")
        return
    
    if not os.path.exists(config.GOOGLE_CREDENTIALS_FILE):
        logger.warning(f"Google credentials file not found: {config.GOOGLE_CREDENTIALS_FILE}")
        logger.info("Please ensure your Google service account credentials file exists")
        return
    
    # Create processes
    bot_process = multiprocessing.Process(target=run_bot, name="BotProcess")
    scheduler_process = multiprocessing.Process(target=run_scheduler, name="SchedulerProcess")
    
    try:
        # Start processes
        logger.info("Starting bot process...")
        bot_process.start()
        
        logger.info("Starting scheduler process...")
        scheduler_process.start()
        
        # Wait for processes
        bot_process.join()
        scheduler_process.join()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        
        # Terminate processes
        if bot_process.is_alive():
            bot_process.terminate()
            bot_process.join()
            
        if scheduler_process.is_alive():
            scheduler_process.terminate()
            scheduler_process.join()
            
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main() 