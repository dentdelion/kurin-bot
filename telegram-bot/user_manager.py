from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, func, desc
from database import db_manager, User, UserStatistics
import config

logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self):
        self.db_manager = db_manager
    
    def register_user(self, user_id, phone_number, first_name, last_name=None):
        """Register a new user"""
        with self.db_manager.get_session() as session:
            try:
                # Check if user already exists
                existing_user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if existing_user:
                    logger.info(f"User {user_id} already registered")
                    return existing_user
                
                # Create new user
                full_name = first_name
                if last_name:
                    full_name += f" {last_name}"
                
                new_user = User(
                    name=full_name,
                    phone=phone_number,
                    telegram_id=str(user_id),
                    created_at=datetime.now()
                )
                
                session.add(new_user)
                session.commit()
                
                # Log new user registration with integer ID for admin management
                logger.info(f"NEW USER REGISTERED - User ID for admin addition: {user_id} (integer), Name: {full_name}, Phone: {phone_number}", 
                           extra={'user_id': user_id, 'action': 'new_user_registration', 'admin_candidate': True, 'user_name': full_name, 'phone': phone_number})
                
                logger.info(f"User {user_id} registered: {full_name}")
                return new_user
            except Exception as e:
                session.rollback()
                logger.error(f"Error registering user {user_id}: {e}")
                raise
    
    def is_user_registered(self, user_id):
        """Check if user is registered"""
        with self.db_manager.get_session() as session:
            try:
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                return user is not None
            except Exception as e:
                logger.error(f"Error checking user registration {user_id}: {e}")
                return False
    
    def get_user(self, user_id):
        """Get user information"""
        with self.db_manager.get_session() as session:
            try:
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if user:
                    return {
                        'id': user.id,
                        'name': user.name,
                        'phone_number': user.phone,
                        'telegram_id': user.telegram_id,
                        'created_at': user.created_at.isoformat() if user.created_at else None
                    }
                return None
            except Exception as e:
                logger.error(f"Error getting user {user_id}: {e}")
                return None
    
    def get_user_display_name(self, user_id):
        """Get user's display name"""
        user = self.get_user(user_id)
        if user:
            return user['name']
        return "Unknown User"
    
    def add_book_to_statistics(self, user_id, book_id):
        """Add book booking to user statistics (without setting pickup dates)"""
        with self.db_manager.get_session() as session:
            try:
                # Get user by telegram_id
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if not user:
                    logger.error(f"User {user_id} not found for book statistics")
                    return False
                
                # Convert book_id to integer
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
                return False
    
    def mark_book_picked_up(self, user_id, book_id, expiry_date=None):
        """Mark book as picked up and set pickup dates"""
        with self.db_manager.get_session() as session:
            try:
                # Get user by telegram_id
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if not user:
                    logger.error(f"User {user_id} not found for book pickup")
                    return False
                
                # Convert book_id to integer
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
                return False
    
    def mark_book_returned(self, user_id, book_id):
        """Mark a book as returned"""
        with self.db_manager.get_session() as session:
            try:
                # Get user by telegram_id
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False
                
                # Convert book_id to integer
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
                return False
    
    def get_user_active_books(self, user_id):
        """Get user's currently active (not returned) books that have been picked up"""
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
                return []
    
    def get_user_pending_pickup_books(self, user_id):
        """Get user's books that are booked but not yet picked up"""
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
                return []
    
    def get_overdue_books(self):
        """Get all overdue books across all users (only books that have been picked up)"""
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
                return []
    
    def get_top_books_last_month(self, limit=10):
        """Get top most picked up books in the last month (only books that have been picked up)"""
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
                    func.count(UserStatistics.id).asc()  # ascending order as requested
                ).limit(limit).all()
                
                return [{
                    'book_id': book.book_id,
                    'pickup_count': book.pickup_count
                } for book in top_books]
            except Exception as e:
                logger.error(f"Error getting top books: {e}")
                return []
    
    def get_user_statistics(self, user_id):
        """Get comprehensive statistics for a user"""
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
                return None
    
    def get_user_with_active_book(self, book_id):
        """Get user who currently has a specific book picked up (not just booked)"""
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
                return None 