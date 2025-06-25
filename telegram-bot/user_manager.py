import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self):
        self.users_file = 'users.json'
        self.users = self._load_users()
    
    def _load_users(self):
        """Load users from JSON file"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading users: {e}")
                return {}
        return {}
    
    def _save_users(self):
        """Save users to JSON file"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def register_user(self, user_id, phone_number, first_name, last_name=None):
        """Register a new user"""
        self.users[str(user_id)] = {
            'phone_number': phone_number,
            'first_name': first_name,
            'last_name': last_name or '',
            'registered_at': datetime.now().isoformat(),
            'current_category': None,
            'current_page': 0,
            'selected_book': None,
            'books_history': []
        }
        self._save_users()
        logger.info(f"User {user_id} registered: {first_name} {last_name}")
    
    def is_user_registered(self, user_id):
        """Check if user is registered"""
        return str(user_id) in self.users
    
    def get_user(self, user_id):
        """Get user information"""
        return self.users.get(str(user_id))
    
    def update_user_category(self, user_id, category):
        """Update user's current category"""
        if str(user_id) in self.users:
            self.users[str(user_id)]['current_category'] = category
            self.users[str(user_id)]['current_page'] = 0  # Reset page when changing category
            self._save_users()
    
    def update_user_page(self, user_id, page):
        """Update user's current page"""
        if str(user_id) in self.users:
            self.users[str(user_id)]['current_page'] = page
            self._save_users()
    
    def set_selected_book(self, user_id, book_index):
        """Set user's selected book"""
        if str(user_id) in self.users:
            self.users[str(user_id)]['selected_book'] = book_index
            self._save_users()
    
    def add_book_to_history(self, user_id, book_index, action):
        """Add book action to user's history"""
        if str(user_id) in self.users:
            if 'books_history' not in self.users[str(user_id)]:
                self.users[str(user_id)]['books_history'] = []
            
            self.users[str(user_id)]['books_history'].append({
                'book_index': book_index,
                'action': action,
                'timestamp': datetime.now().isoformat()
            })
            self._save_users()
    
    def get_user_booked_books(self, user_id):
        """Get books currently booked by user"""
        # This would need to be implemented based on Excel data
        # For now, returning empty list
        return []
    
    def get_user_display_name(self, user_id):
        """Get user's display name"""
        user = self.get_user(user_id)
        if user:
            name = user['first_name']
            if user['last_name']:
                name += f" {user['last_name']}"
            return name
        return "Unknown User" 