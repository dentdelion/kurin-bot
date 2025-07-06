from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, func, desc
from database import db_manager, User, UserStatistics
import config
import pandas as pd

logger = logging.getLogger(__name__)

class BookManager:
    """
    Manages all book-related operations including booking, pickup, returns, and statistics.
    
    This class handles:
    - Book booking and pickup tracking
    - Book return processing
    - User book queries (active, pending, overdue)
    - Admin statistics and reporting
    - Performance optimization through efficient queries
    """
    
    def __init__(self):
        """Initialize BookManager with database connection"""
        self.db_manager = db_manager
        
        # Initialize cache manager (will be None if Redis is not available)
        try:
            from cache_manager import BookStatusCache
            self.cache = BookStatusCache()
            logger.info("Cache manager initialized in BookManager")
        except ImportError:
            logger.warning("Redis not available, BookManager running without cache")
            self.cache = None
        except Exception as e:
            logger.warning(f"Failed to initialize cache manager in BookManager: {e}")
            self.cache = None
    
    def add_book_to_statistics(self, user_id, book_id):
        """
        Add book booking to user statistics (without setting pickup dates)
        
        Args:
            user_id (int): Telegram user ID
            book_id (int): Book ID from Google Sheets
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                # Get user by telegram_id
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if not user:
                    logger.error(f"User {user_id} not found for book statistics")
                    return False
                
                # Convert book_id to integer with validation
                try:
                    int_book_id = int(book_id)
                except (ValueError, TypeError) as e:
                    logger.error(f"Cannot convert book_id '{book_id}' to integer: {e}")
                    return False
                
                # Create statistics record without setting pickup dates
                # date_booked and expiry_date will be set when user picks up the book
                stat_record = UserStatistics(
                    user_id=user.id,
                    book_id=int_book_id,
                    date_booked=None,  # Will be set when user picks up
                    expiry_date=None,  # Will be set when user picks up
                    returned=False
                )
                
                session.add(stat_record)
                session.commit()
                
                logger.info(f"Added book ID {int_book_id} to statistics for user {user_id} (pending pickup)")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Error adding book to statistics for user {user_id}: {e}")
                raise
    
    def mark_book_picked_up(self, user_id, book_id, expiry_date=None):
        """
        Mark book as picked up and set pickup dates
        
        Args:
            user_id (int): Telegram user ID
            book_id (int): Book ID from Google Sheets
            expiry_date (datetime, optional): Custom expiry date
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                # Get user by telegram_id
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if not user:
                    logger.error(f"User {user_id} not found for book pickup")
                    return False
                
                # Convert book_id to integer with validation
                try:
                    int_book_id = int(book_id)
                except (ValueError, TypeError) as e:
                    logger.error(f"Cannot convert book_id '{book_id}' to integer: {e}")
                    return False
                
                # Find the unreturned book that hasn't been picked up yet
                stat_record = session.query(UserStatistics).filter(
                    and_(
                        UserStatistics.user_id == user.id,
                        UserStatistics.book_id == int_book_id,
                        UserStatistics.returned == False,
                        UserStatistics.date_booked == None  # Not picked up yet
                    )
                ).first()
                
                if not stat_record:
                    logger.warning(f"Book ID {int_book_id} not found in pending pickup for user {user_id}")
                    return False
                
                # Calculate expiry date if not provided
                if expiry_date is None:
                    expiry_date = datetime.now() + timedelta(days=config.ALLOWED_TIME_TO_READ_THE_BOOK)
                
                # Set pickup dates
                stat_record.date_booked = datetime.now()
                stat_record.expiry_date = expiry_date
                
                session.commit()
                
                logger.info(f"Marked book ID {int_book_id} as picked up for user {user_id} with expiry {expiry_date}")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Error marking book as picked up for user {user_id}: {e}")
                raise
    
    def mark_book_returned(self, user_id, book_id):
        """
        Mark a book as returned
        
        Args:
            user_id (int): Telegram user ID
            book_id (int): Book ID from Google Sheets
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                # Get user by telegram_id
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False
                
                # Convert book_id to integer with validation
                try:
                    int_book_id = int(book_id)
                except (ValueError, TypeError) as e:
                    logger.error(f"Cannot convert book_id '{book_id}' to integer: {e}")
                    return False
                
                # Find the unreturned book
                stat_record = session.query(UserStatistics).filter(
                    and_(
                        UserStatistics.user_id == user.id,
                        UserStatistics.book_id == int_book_id,
                        UserStatistics.returned == False
                    )
                ).first()
                
                if stat_record:
                    stat_record.returned = True
                    stat_record.returned_at = datetime.now()
                    session.commit()
                    logger.info(f"Marked book ID {int_book_id} as returned for user {user_id}")
                    return True
                else:
                    logger.warning(f"Book ID {int_book_id} not found in active loans for user {user_id}")
                    return False
            except Exception as e:
                session.rollback()
                logger.error(f"Error marking book as returned for user {user_id}: {e}")
                raise
    
    def get_user_active_books(self, user_id):
        """
        Get user's currently active (not returned) books that have been picked up
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            list: List of dictionaries containing book information
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if not user:
                    return []
                
                # Get books that have been picked up (date_booked is not null) and not returned
                active_books = session.query(UserStatistics).filter(
                    and_(
                        UserStatistics.user_id == user.id,
                        UserStatistics.returned == False,
                        UserStatistics.date_booked != None  # Only books that have been picked up
                    )
                ).all()
                
                current_time = datetime.now()
                
                result = []
                for book in active_books:
                    # Since we're using timezone-naive datetimes, no timezone conversion needed
                    expiry_date = book.expiry_date
                    
                    # Calculate days left
                    days_left = (expiry_date - current_time).days if expiry_date > current_time else 0
                    
                    result.append({
                        'book_id': book.book_id,
                        'date_booked': book.date_booked,
                        'expiry_date': book.expiry_date,
                        'days_left': days_left
                    })
                
                return result
            except Exception as e:
                logger.error(f"Error getting active books for user {user_id}: {e}")
                raise
    
    def get_user_pending_pickup_books(self, user_id):
        """
        Get user's books that are booked but haven't been picked up yet
        (shows all booked books regardless of delivery status)
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            list: List of dictionaries containing book information
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if not user:
                    return []
                
                # Get all user's booked books that haven't been picked up yet (date_booked is null)
                booked_books = session.query(UserStatistics).filter(
                    and_(
                        UserStatistics.user_id == user.id,
                        UserStatistics.returned == False,
                        UserStatistics.date_booked == None  # Not picked up yet
                    )
                ).all()
                
                result = []
                logger.info(f"Found {len(booked_books)} booked books for user {user_id} that haven't been picked up")
                
                for book in booked_books:
                    book_id = str(book.book_id)
                    
                    # Get book status from cache/Google Sheets
                    status = self.get_book_status(book_id)
                    
                    # Include all booked books, not just those with 'delivered' status
                    # This way users can see all their booked books and their current status
                    result.append({
                        'book_id': book.book_id,
                        'date_booked': None,
                        'expiry_date': None,
                        'days_left': None,
                        'status': status
                    })
                    
                    if status and status.lower() == config.STATUS_VALUES['DELIVERED']:
                        logger.debug(f"Book {book_id} has delivered status, ready for pickup")
                    else:
                        logger.debug(f"Book {book_id} status: {status}, not yet delivered")
                
                logger.info(f"Returning {len(result)} booked books for user {user_id}")
                return result
            except Exception as e:
                logger.error(f"Error getting pending pickup books for user {user_id}: {e}")
                raise
    
    def get_book_status(self, book_id: str) -> str:
        """
        Get book status efficiently using cache first, then Google Sheets
        
        Args:
            book_id (str): Book ID
            
        Returns:
            str: Book status or empty string if not found
        """
        # Try cache first
        if self.cache:
            cached_status = self.cache.get_book_status(book_id)
            if cached_status is not None:
                return cached_status
        
        # Fallback to Google Sheets - we need to get the status directly
        try:
            # Import here to avoid circular imports
            from google_sheets_manager import GoogleSheetsManager
            sheets_manager = GoogleSheetsManager()
            df = sheets_manager.read_books()
            
            if not df.empty:
                book_row = df[df[config.EXCEL_COLUMNS['id']].astype(str) == str(book_id)]
                if not book_row.empty:
                    row = book_row.iloc[0]
                    status = row[config.EXCEL_COLUMNS['status']]
                    return str(status) if pd.notna(status) else ""
            
            logger.debug(f"Book {book_id} not found in Google Sheets")
            return ""
        except Exception as e:
            logger.error(f"Error getting book status for {book_id} from Google Sheets: {e}")
            return ""
    
    def get_book_info(self, book_id: str) -> dict:
        """
        Get complete book information efficiently using cache first
        
        Args:
            book_id (str): Book ID
            
        Returns:
            dict: Book information or empty dict if not found
        """
        # Try cache first
        if self.cache:
            cached_info = self.cache.get_book(book_id)
            if cached_info:
                return cached_info
        
        # Fallback to Google Sheets
        try:
            # Import here to avoid circular imports
            from google_sheets_manager import GoogleSheetsManager
            sheets_manager = GoogleSheetsManager()
            df = sheets_manager.read_books()
            
            if not df.empty:
                book_row = df[df[config.EXCEL_COLUMNS['id']].astype(str) == str(book_id)]
                if not book_row.empty:
                    row = book_row.iloc[0]
                    return {
                        'id': str(row[config.EXCEL_COLUMNS['id']]),
                        'name': str(row[config.EXCEL_COLUMNS['name']]) if pd.notna(row[config.EXCEL_COLUMNS['name']]) else '',
                        'author': str(row[config.EXCEL_COLUMNS['author']]) if pd.notna(row[config.EXCEL_COLUMNS['author']]) else '',
                        'edition': str(row[config.EXCEL_COLUMNS['edition']]) if pd.notna(row[config.EXCEL_COLUMNS['edition']]) else '',
                        'status': str(row[config.EXCEL_COLUMNS['status']]) if pd.notna(row[config.EXCEL_COLUMNS['status']]) else '',
                        'booked_until': str(row[config.EXCEL_COLUMNS['booked_until']]) if pd.notna(row[config.EXCEL_COLUMNS['booked_until']]) else '',
                        'categories': str(row[config.EXCEL_COLUMNS['categories']]) if pd.notna(row[config.EXCEL_COLUMNS['categories']]) else ''
                    }
            
            logger.debug(f"Book {book_id} not found in Google Sheets")
            return {}
        except Exception as e:
            logger.error(f"Error getting book info for {book_id} from Google Sheets: {e}")
            return {}
    
    def get_user_books_with_status(self, user_id: int) -> list:
        """
        Get user's books with their current status from cache/Google Sheets
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            list: List of dictionaries with book info and status
        """
        try:
            # Get user's books from database
            active_books = self.get_user_active_books(user_id)
            pending_books = self.get_user_pending_pickup_books(user_id)
            
            all_books = active_books + pending_books
            result = []
            
            for book in all_books:
                book_id = str(book['book_id'])
                
                # Use status from pending_books if available (already checked via cache)
                # Otherwise get status from cache/Google Sheets
                status = book.get('status') or self.get_book_status(book_id)
                
                # Get book info from cache/Google Sheets
                book_info = self.get_book_info(book_id)
                
                book_data = {
                    'book_id': book_id,
                    'date_booked': book.get('date_booked'),
                    'expiry_date': book.get('expiry_date'),
                    'days_left': book.get('days_left'),
                    'status': status,
                    'name': book_info.get('name', f"Книга ID: {book_id}"),
                    'author': book_info.get('author', 'Невідомий автор')
                }
                
                result.append(book_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting user books with status for user {user_id}: {e}")
            return []
    
    def get_overdue_books(self):
        """
        Get all overdue books across all users (only books that have been picked up)
        
        Returns:
            list: List of dictionaries containing overdue book information
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                current_time = datetime.now()
                
                # Only consider books that have been picked up (date_booked is not null) and are overdue
                overdue_books = session.query(UserStatistics, User).join(User).filter(
                    and_(
                        UserStatistics.returned == False,
                        UserStatistics.date_booked != None,  # Only books that have been picked up
                        UserStatistics.expiry_date < current_time
                    )
                ).all()
                
                result = []
                for stat, user in overdue_books:
                    # Since we're using timezone-naive datetimes, no timezone conversion needed
                    expiry_date = stat.expiry_date
                    
                    # Extract user attributes while session is still active
                    user_telegram_id = user.telegram_id
                    user_name = user.name
                    user_phone = user.phone
                    
                    days_overdue = (current_time - expiry_date).days
                    result.append({
                        'user_id': user_telegram_id,
                        'user_name': user_name,
                        'user_phone': user_phone,
                        'book_id': stat.book_id,
                        'date_booked': stat.date_booked,
                        'expiry_date': stat.expiry_date,
                        'days_overdue': days_overdue
                    })
                
                return result
            except Exception as e:
                logger.error(f"Error getting overdue books: {e}")
                raise
    
    def get_top_booked_books_last_month(self, limit=10):
        """
        Get top most booked books in the last month (books that were booked, regardless of pickup status)
        
        This method provides admin statistics on which books are most popular for booking.
        It counts all booking attempts, not just successful pickups.
        
        Args:
            limit (int): Maximum number of books to return (default: 10)
            
        Returns:
            list: List of dictionaries containing book_id and booking_count
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                # Calculate date one month ago
                month_ago = datetime.now() - timedelta(days=30)
                
                # Query for most often booked books in the last month
                # This counts ALL booking attempts, not just successful pickups
                top_books = session.query(
                    UserStatistics.book_id,
                    func.count(UserStatistics.id).label('booking_count')
                ).filter(
                    UserStatistics.date_booked >= month_ago  # All bookings in last month
                ).group_by(
                    UserStatistics.book_id
                ).order_by(
                    func.count(UserStatistics.id).desc()  # Most booked first
                ).limit(limit).all()
                
                result = [{
                    'book_id': book.book_id,
                    'booking_count': book.booking_count
                } for book in top_books]
                
                logger.info(f"Retrieved top {len(result)} booked books for last month")
                return result
            except Exception as e:
                logger.error(f"Error getting top booked books: {e}")
                raise
    
    def get_top_picked_up_books_last_month(self, limit=10):
        """
        Get top most picked up books in the last month (only books that have been picked up)
        
        This method provides admin statistics on which books are most popular for actual pickup.
        It only counts books that were successfully picked up (date_booked is not null).
        
        Args:
            limit (int): Maximum number of books to return (default: 10)
            
        Returns:
            list: List of dictionaries containing book_id and pickup_count
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                logger.info("Starting get_top_picked_up_books_last_month query")
                
                # Calculate date one month ago
                month_ago = datetime.now() - timedelta(days=30)
                logger.info(f"Calculated month_ago date: {month_ago}")
                
                # Query for most often picked up books in the last month
                # Only consider books that have been picked up (date_booked is not null)
                top_books = session.query(
                    UserStatistics.book_id,
                    func.count(UserStatistics.id).label('pickup_count')
                ).filter(
                    and_(
                        UserStatistics.date_booked != None,  # Only books that have been picked up
                        UserStatistics.date_booked >= month_ago
                    )
                ).group_by(
                    UserStatistics.book_id
                ).order_by(
                    func.count(UserStatistics.id).desc()  # Most picked up first
                ).limit(limit).all()
                
                logger.info(f"Query executed successfully, found {len(top_books)} results")
                
                result = [{
                    'book_id': book.book_id,
                    'pickup_count': book.pickup_count
                } for book in top_books]
                
                logger.info(f"Retrieved top {len(result)} picked up books for last month")
                return result
            except Exception as e:
                logger.error(f"Error getting top picked up books: {e}", exc_info=True)
                raise
    
    
    def get_user_with_booked_book(self, book_id):
        """
        Get user who currently has a specific book booked but not delivered yet 
        
        Args:
            book_id (int): Book ID from Google Sheets
            
        Returns:
            dict: Dictionary containing user information or None if not found
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                logger.info(f"Searching for active pickup with book_id: '{book_id}' (type: {type(book_id)})")
                
                # Convert book_id to integer since it's stored as integer in database
                try:
                    int_book_id = int(book_id)
                    logger.info(f"Converted book_id to integer: {int_book_id}")
                except (ValueError, TypeError) as e:
                    logger.error(f"Cannot convert book_id '{book_id}' to integer: {e}")
                    return None
                
                # Find active pickup for this book using integer book_id
                # Only consider books that have been picked up (date_booked is not null)
                result = session.query(UserStatistics, User).join(User).filter(
                    and_(
                        UserStatistics.book_id == int_book_id,
                        UserStatistics.returned == False,
                        UserStatistics.date_booked == None  # Only books that have been not delivered yet
                    )
                ).first()
                
                if result:
                    stat, user = result
                    # Extract user attributes while session is still active
                    user_telegram_id = user.telegram_id
                    user_name = user.name
                    user_phone = user.phone
                    logger.info(f"Found active pickup: user_id={user_telegram_id}, book_id={stat.book_id}")
                    return {
                        'user_id': user_telegram_id,
                        'user_name': user_name,
                        'user_phone': user_phone,
                        'date_booked': stat.date_booked,
                        'expiry_date': stat.expiry_date
                    }
                else:
                    logger.warning(f"No active pickup found for book_id: {int_book_id}")
                return None
            except Exception as e:
                logger.error(f"Error finding user with book {book_id}: {e}")
                raise
    
    def get_admin_statistics(self):
        """
        Get comprehensive admin statistics for dashboard
        
        Returns:
            dict: Dictionary containing various admin statistics
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                current_time = datetime.now()
                month_ago = datetime.now() - timedelta(days=30)
                
                # Get total users
                total_users = session.query(func.count(User.id)).scalar()
                
                # Get total books booked this month
                total_bookings_this_month = session.query(func.count(UserStatistics.id)).filter(
                    UserStatistics.date_booked >= month_ago
                ).scalar()
                
                # Get total books picked up this month
                total_pickups_this_month = session.query(func.count(UserStatistics.id)).filter(
                    and_(
                        UserStatistics.date_booked != None,
                        UserStatistics.date_booked >= month_ago
                    )
                ).scalar()
                
                # Get total books returned this month
                total_returns_this_month = session.query(func.count(UserStatistics.id)).filter(
                    and_(
                        UserStatistics.returned == True,
                        UserStatistics.returned_at >= month_ago
                    )
                ).scalar()
                
                # Get current active loans (picked up but not returned)
                current_active_loans = session.query(func.count(UserStatistics.id)).filter(
                    and_(
                        UserStatistics.returned == False,
                        UserStatistics.date_booked != None
                    )
                ).scalar()
                
                # Get overdue books count
                overdue_books_count = session.query(func.count(UserStatistics.id)).filter(
                    and_(
                        UserStatistics.returned == False,
                        UserStatistics.date_booked != None,
                        UserStatistics.expiry_date < current_time
                    )
                ).scalar()
                
                # Get pending pickup books count
                pending_pickup_count = session.query(func.count(UserStatistics.id)).filter(
                    and_(
                        UserStatistics.returned == False,
                        UserStatistics.date_booked == None
                    )
                ).scalar()
                
                return {
                    'total_users': total_users,
                    'total_bookings_this_month': total_bookings_this_month,
                    'total_pickups_this_month': total_pickups_this_month,
                    'total_returns_this_month': total_returns_this_month,
                    'current_active_loans': current_active_loans,
                    'overdue_books_count': overdue_books_count,
                    'pending_pickup_count': pending_pickup_count,
                    'month_ago_date': month_ago.isoformat()
                }
            except Exception as e:
                logger.error(f"Error getting admin statistics: {e}")
                raise 