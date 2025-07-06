from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, func, desc
from database import db_manager, User, UserStatistics
import config

logger = logging.getLogger(__name__)

class UserManager:
    """
    Manages user-related operations including registration, user info retrieval, and display.
    
    This class handles:
    - User registration and validation
    - User information retrieval
    - User display name formatting
    - User existence checks
    """
    
    def __init__(self):
        """Initialize UserManager with database connection"""
        self.db_manager = db_manager
    
    def register_user(self, user_id, phone_number, first_name, last_name=None):
        """
        Register a new user
        
        Args:
            user_id (int): Telegram user ID
            phone_number (str): User's phone number
            first_name (str): User's first name
            last_name (str, optional): User's last name
            
        Returns:
            dict: Dictionary containing user information
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                # Check if user already exists
                existing_user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if existing_user:
                    logger.info(f"User {user_id} already registered")
                    # Return clean dictionary with primitive values to avoid session binding issues
                    return {
                        'id': existing_user.id,
                        'name': str(existing_user.name),
                        'phone_number': str(existing_user.phone),
                        'telegram_id': str(existing_user.telegram_id),
                        'created_at': existing_user.created_at.isoformat() if existing_user.created_at else None
                    }
                
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
                
                # Return clean dictionary with primitive values to avoid session binding issues
                return {
                    'id': new_user.id,
                    'name': str(new_user.name),
                    'phone_number': str(new_user.phone),
                    'telegram_id': str(new_user.telegram_id),
                    'created_at': new_user.created_at.isoformat() if new_user.created_at else None
                }
            except Exception as e:
                session.rollback()
                logger.error(f"Error registering user {user_id}: {e}")
                raise
    
    def is_user_registered(self, user_id):
        """
        Check if user is registered
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            bool: True if user is registered, False otherwise
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                return user is not None
            except Exception as e:
                logger.error(f"Error checking user registration {user_id}: {e}")
                raise
    
    def get_user(self, user_id):
        """
        Get user information
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            dict: Dictionary containing user information or None if not found
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        with self.db_manager.get_session() as session:
            try:
                user = session.query(User).filter(User.telegram_id == str(user_id)).first()
                if user:
                    # Return clean dictionary with primitive values to avoid session binding issues
                    return {
                        'id': user.id,
                        'name': str(user.name),
                        'phone_number': str(user.phone),
                        'telegram_id': str(user.telegram_id),
                        'created_at': user.created_at.isoformat() if user.created_at else None
                    }
                return None
            except Exception as e:
                logger.error(f"Error getting user {user_id}: {e}")
                raise
    
    def get_user_display_name(self, user_id):
        """
        Get user's display name
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            str: User's display name or "Unknown User" if not found
            
        Raises:
            Exception: Database errors are logged and re-raised
        """
        user = self.get_user(user_id)
        if user:
            return user['name']
        return "Unknown User"
    
 