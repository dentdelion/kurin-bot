from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, func, desc
from database import db_manager, User, UserStatistics
import config

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
        Get user's books that are booked but not yet picked up
        
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
                
                # Get books that are booked but not picked up yet (date_booked is null)
                pending_books = session.query(UserStatistics).filter(
                    and_(
                        UserStatistics.user_id == user.id,
                        UserStatistics.returned == False,
                        UserStatistics.date_booked == None  # Not picked up yet
                    )
                ).all()
                
                result = []
                for book in pending_books:
                    result.append({
                        'book_id': book.book_id,
                        'date_booked': None,
                        'expiry_date': None,
                        'days_left': None
                    })
                
                return result
            except Exception as e:
                logger.error(f"Error getting pending pickup books for user {user_id}: {e}")
                raise
    
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
                    
                    days_overdue = (current_time - expiry_date).days
                    result.append({
                        'user_id': user.telegram_id,
                        'user_name': user.name,
                        'user_phone': user.phone,
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
                # Calculate date one month ago
                month_ago = datetime.now() - timedelta(days=30)
                
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
                
                result = [{
                    'book_id': book.book_id,
                    'pickup_count': book.pickup_count
                } for book in top_books]
                
                logger.info(f"Retrieved top {len(result)} picked up books for last month")
                return result
            except Exception as e:
                logger.error(f"Error getting top picked up books: {e}")
                raise
    
    def get_user_statistics(self, user_id):
        """
        Get comprehensive statistics for a user
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            dict: Dictionary containing user statistics or None if user not found
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if not user:
                    return None
                
                # Get all user statistics
                all_books = session.query(UserStatistics).filter(
                    UserStatistics.user_id == user.id
                ).all()
                
                total_books = len(all_books)
                returned_books = len([book for book in all_books if book.returned])
                picked_up_books = len([book for book in all_books if book.date_booked is not None])
                active_picked_up_books = len([book for book in all_books if book.date_booked is not None and not book.returned])
                pending_pickup_books = len([book for book in all_books if book.date_booked is None and not book.returned])
                
                return {
                    'total_books_booked': total_books,
                    'books_picked_up': picked_up_books,
                    'books_pending_pickup': pending_pickup_books,
                    'returned_books': returned_books,
                    'active_picked_up_books': active_picked_up_books,
                    'books_history': [{
                        'book_id': book.book_id,
                        'date_booked': book.date_booked,
                        'expiry_date': book.expiry_date,
                        'returned': book.returned,
                        'returned_at': book.returned_at,
                        'picked_up': book.date_booked is not None
                    } for book in all_books]
                }
            except Exception as e:
                logger.error(f"Error getting user statistics for {user_id}: {e}")
                raise
    
    def get_user_with_active_book(self, book_id):
        """
        Get user who currently has a specific book picked up (not just booked)
        
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
                        UserStatistics.date_booked != None  # Only books that have been picked up
                    )
                ).first()
                
                if result:
                    stat, user = result
                    logger.info(f"Found active pickup: user_id={user.telegram_id}, book_id={stat.book_id}")
                    return {
                        'user_id': user.telegram_id,
                        'user_name': user.name,
                        'user_phone': user.phone,
                        'date_booked': stat.date_booked,
                        'expiry_date': stat.expiry_date
                    }
                else:
                    logger.warning(f"No active pickup found for book_id: {int_book_id}")
                    
                    # Debug: Show all active pickups
                    all_active = session.query(UserStatistics).filter(
                        and_(
                            UserStatistics.returned == False,
                            UserStatistics.date_booked != None  # Only books that have been picked up
                        )
                    ).all()
                    if all_active:
                        logger.info(f"All active pickups: {[(stat.book_id, type(stat.book_id), stat.user_id) for stat in all_active]}")
                    else:
                        logger.info("No active pickups found in database")
                    
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