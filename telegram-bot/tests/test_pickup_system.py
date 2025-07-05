#!/usr/bin/env python3
"""
Unit tests for the book pickup system.
Tests the UserManager methods to ensure they work correctly
with the new pickup flow where date_booked and expiry_date are set when user picks up the book.
All tests are pure unit tests with no database dependencies.
"""

import unittest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_manager import UserManager
from database import User, UserStatistics
import config


class TestPickupSystem(unittest.TestCase):
    """Test cases for the book pickup system - Pure unit tests"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Test data
        self.test_user_id = 12345
        self.test_phone = "+380991234567"
        self.test_name = "Test User"
        self.test_book_id = 999
        self.test_book_id_2 = 888
        
        # Mock database session
        self.mock_session = Mock()
        self.mock_user = Mock()
        self.mock_user.id = 1
        self.mock_user.name = self.test_name
        self.mock_user.phone = self.test_phone
        self.mock_user.telegram_id = str(self.test_user_id)
        self.mock_user.created_at = datetime.now()

    def tearDown(self):
        """Clean up after each test method"""
        pass

    def test_register_user_success(self):
        """Test successful user registration"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = None  # User doesn't exist
        
        # Act
        result = user_manager.register_user(self.test_user_id, self.test_phone, self.test_name)
        
        # Assert
        self.assertIsNotNone(result)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()

    def test_register_user_already_exists(self):
        """Test user registration when user already exists"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user  # User exists
        
        # Act
        result = user_manager.register_user(self.test_user_id, self.test_phone, self.test_name)
        
        # Assert
        self.assertEqual(result, self.mock_user)
        self.mock_session.add.assert_not_called()

    def test_register_user_database_error(self):
        """Test user registration with database error"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = None
        self.mock_session.add.side_effect = Exception("Database error")
        
        # Act & Assert
        with self.assertRaises(Exception):
            user_manager.register_user(self.test_user_id, self.test_phone, self.test_name)
        
        self.mock_session.rollback.assert_called_once()

    def test_add_book_to_statistics_success(self):
        """Test successful book addition to statistics without pickup dates"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, self.test_book_id)
        
        # Assert
        self.assertTrue(result)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()
        
        # Verify the added record has null dates
        added_record = self.mock_session.add.call_args[0][0]
        self.assertIsNone(added_record.date_booked)
        self.assertIsNone(added_record.expiry_date)
        self.assertEqual(added_record.book_id, self.test_book_id)
        self.assertEqual(added_record.user_id, self.mock_user.id)

    def test_add_book_to_statistics_user_not_found(self):
        """Test book addition when user is not found"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = None  # User not found
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, self.test_book_id)
        
        # Assert
        self.assertFalse(result)

    def test_add_book_to_statistics_invalid_book_id(self):
        """Test book addition with invalid book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, "invalid_book_id")
        
        # Assert
        self.assertFalse(result)

    def test_add_book_to_statistics_database_error(self):
        """Test book addition with database error"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        self.mock_session.add.side_effect = Exception("Database error")
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, self.test_book_id)
        
        # Assert
        self.assertFalse(result)
        self.mock_session.rollback.assert_called_once()

    def test_mark_book_picked_up_success(self):
        """Test successful book pickup with default expiry date"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock the statistics record
        mock_stat_record = Mock()
        mock_stat_record.date_booked = None
        mock_stat_record.returned = False
        
        # Mock the query chain for finding the book
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_stat_record
        
        # Act
        result = user_manager.mark_book_picked_up(self.test_user_id, self.test_book_id)
        
        # Assert
        self.assertTrue(result)
        self.mock_session.commit.assert_called_once()
        
        # Verify dates were set
        self.assertIsNotNone(mock_stat_record.date_booked)
        self.assertIsNotNone(mock_stat_record.expiry_date)

    def test_mark_book_picked_up_custom_expiry_date(self):
        """Test book pickup with custom expiry date"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock the statistics record
        mock_stat_record = Mock()
        mock_stat_record.date_booked = None
        mock_stat_record.returned = False
        
        # Mock the query chain for finding the book
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_stat_record
        
        custom_expiry = datetime.now() + timedelta(days=30)
        
        # Act
        result = user_manager.mark_book_picked_up(self.test_user_id, self.test_book_id, custom_expiry)
        
        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_stat_record.expiry_date, custom_expiry)

    def test_mark_book_picked_up_user_not_found(self):
        """Test book pickup when user is not found"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = None  # User not found
        
        # Act
        result = user_manager.mark_book_picked_up(self.test_user_id, self.test_book_id)
        
        # Assert
        self.assertFalse(result)

    def test_mark_book_picked_up_book_not_found(self):
        """Test book pickup when book is not found in pending pickup"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock the query chain - no book found
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None  # Book not found
        
        # Act
        result = user_manager.mark_book_picked_up(self.test_user_id, self.test_book_id)
        
        # Assert
        self.assertFalse(result)

    def test_mark_book_picked_up_invalid_book_id(self):
        """Test book pickup with invalid book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.mark_book_picked_up(self.test_user_id, "invalid_book_id")
        
        # Assert
        self.assertFalse(result)

    def test_get_user_pending_pickup_books_success(self):
        """Test getting user's pending pickup books"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock pending books
        mock_pending_books = [
            Mock(book_id=999, date_booked=None, expiry_date=None, returned=False),
            Mock(book_id=888, date_booked=None, expiry_date=None, returned=False)
        ]
        
        # Mock the query chain
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value.all.return_value = mock_pending_books
        
        # Act
        result = user_manager.get_user_pending_pickup_books(self.test_user_id)
        
        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['book_id'], 999)
        self.assertEqual(result[1]['book_id'], 888)

    def test_get_user_pending_pickup_books_user_not_found(self):
        """Test getting pending pickup books when user is not found"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = None  # User not found
        
        # Act
        result = user_manager.get_user_pending_pickup_books(self.test_user_id)
        
        # Assert
        self.assertEqual(result, [])

    def test_get_user_active_books_success(self):
        """Test getting user's active books"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock active books
        mock_active_books = [
            Mock(book_id=999, date_booked=datetime.now(), expiry_date=datetime.now() + timedelta(days=7), returned=False),
            Mock(book_id=888, date_booked=datetime.now(), expiry_date=datetime.now() + timedelta(days=3), returned=False)
        ]
        
        # Mock the query chain
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value.all.return_value = mock_active_books
        
        # Act
        result = user_manager.get_user_active_books(self.test_user_id)
        
        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['book_id'], 999)
        self.assertEqual(result[1]['book_id'], 888)

    def test_get_user_active_books_user_not_found(self):
        """Test getting active books when user is not found"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = None  # User not found
        
        # Act
        result = user_manager.get_user_active_books(self.test_user_id)
        
        # Assert
        self.assertEqual(result, [])

    
    def test_mark_book_returned_success(self):
        """Test successful book return"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock the statistics record
        mock_stat_record = Mock()
        mock_stat_record.returned = False
        
        # Mock the query chain for finding the book
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_stat_record
        
        # Act
        result = user_manager.mark_book_returned(self.test_user_id, self.test_book_id)
        
        # Assert
        self.assertTrue(result)
        self.assertTrue(mock_stat_record.returned)
        self.assertIsNotNone(mock_stat_record.returned_at)
        self.mock_session.commit.assert_called_once()

    def test_mark_book_returned_user_not_found(self):
        """Test book return when user is not found"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = None  # User not found
        
        # Act
        result = user_manager.mark_book_returned(self.test_user_id, self.test_book_id)
        
        # Assert
        self.assertFalse(result)

    def test_mark_book_returned_book_not_found(self):
        """Test book return when book is not found"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock the query chain - no book found
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None  # Book not found
        
        # Act
        result = user_manager.mark_book_returned(self.test_user_id, self.test_book_id)
        
        # Assert
        self.assertFalse(result)

    def test_get_user_statistics_success(self):
        """Test getting user statistics"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Mock statistics records
        mock_stats = [
            Mock(book_id=999, date_booked=datetime.now(), returned=True, returned_at=datetime.now()),
            Mock(book_id=888, date_booked=datetime.now(), returned=False, returned_at=None)
        ]
        
        # Mock the query chain
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value.all.return_value = mock_stats
        
        # Act
        result = user_manager.get_user_statistics(self.test_user_id)
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result['total_books_booked'], 2)
        self.assertEqual(result['books_picked_up'], 2)
        self.assertEqual(result['books_pending_pickup'], 0)
        self.assertEqual(result['returned_books'], 1)
        self.assertEqual(result['active_picked_up_books'], 1)
        self.assertEqual(len(result['books_history']), 2)

    def test_get_user_statistics_user_not_found(self):
        """Test getting user statistics when user is not found"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = None  # User not found
        
        # Act
        result = user_manager.get_user_statistics(self.test_user_id)
        
        # Assert
        self.assertIsNone(result)

    def test_get_overdue_books_success(self):
        """Test getting overdue books"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        # Mock overdue books with user data (join result)
        mock_user1 = Mock(telegram_id="12345", name="User 1", phone="+380991234567")
        mock_user2 = Mock(telegram_id="54321", name="User 2", phone="+380998765432")
        
        mock_stat1 = Mock(book_id=999, date_booked=datetime.now(), expiry_date=datetime.now() - timedelta(days=5))
        mock_stat2 = Mock(book_id=888, date_booked=datetime.now(), expiry_date=datetime.now() - timedelta(days=3))
        
        mock_overdue_books = [(mock_stat1, mock_user1), (mock_stat2, mock_user2)]
        
        # Mock the query chain
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.join.return_value.filter.return_value.all.return_value = mock_overdue_books
        
        # Act
        result = user_manager.get_overdue_books()
        
        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['book_id'], 999)
        self.assertEqual(result[1]['book_id'], 888)

    def test_get_top_books_last_month_success(self):
        """Test getting top books from last month"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        # Mock top books
        mock_top_books = [
            Mock(book_id=999, pickup_count=5),
            Mock(book_id=888, pickup_count=3)
        ]
        
        # Mock the query chain
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.filter.return_value.group_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_top_books
        
        # Act
        result = user_manager.get_top_books_last_month(limit=10)
        
        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['book_id'], 999)
        self.assertEqual(result[0]['pickup_count'], 5)

    def test_get_user_with_active_book_success(self):
        """Test getting user with active book"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        # Mock user with active book
        mock_user = Mock()
        mock_user.telegram_id = "12345"
        mock_user.name = "Test User"
        mock_user.phone = "+380991234567"
        
        mock_stat = Mock(book_id=999, date_booked=datetime.now(), expiry_date=datetime.now() + timedelta(days=7))
        
        # Mock the query chain (join result)
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.join.return_value.filter.return_value.first.return_value = (mock_stat, mock_user)
        
        # Act
        result = user_manager.get_user_with_active_book(self.test_book_id)
        
        # Assert
        self.assertIsNotNone(result)
        if result is not None:  # Add null check to satisfy linter
            self.assertEqual(result['user_id'], "12345")
            self.assertEqual(result['user_name'], "Test User")

    def test_get_user_with_active_book_not_found(self):
        """Test getting user with active book when not found"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        # Mock the query chain - no user found
        mock_query = Mock()
        self.mock_session.query.return_value = mock_query
        mock_query.join.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = user_manager.get_user_with_active_book(self.test_book_id)
        
        # Assert
        self.assertIsNone(result)

    def test_get_user_with_active_book_invalid_book_id(self):
        """Test getting user with active book with invalid book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        # Act
        result = user_manager.get_user_with_active_book("invalid_book_id")
        
        # Assert
        self.assertIsNone(result)

    def test_edge_case_empty_string_book_id(self):
        """Test edge case with empty string book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, "")
        
        # Assert
        self.assertFalse(result)

    def test_edge_case_none_book_id(self):
        """Test edge case with None book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, None)
        
        # Assert
        self.assertFalse(result)

    def test_edge_case_negative_book_id(self):
        """Test edge case with negative book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, -1)
        
        # Assert
        # Negative integers should work (they can be converted to int)
        self.assertTrue(result)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()

    def test_edge_case_zero_book_id(self):
        """Test edge case with zero book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, 0)
        
        # Assert
        # Zero should work (it can be converted to int)
        self.assertTrue(result)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()

    def test_edge_case_very_large_book_id(self):
        """Test edge case with very large book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, 999999999999999999)
        
        # Assert
        # Very large integers should work (they can be converted to int)
        self.assertTrue(result)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()

    def test_edge_case_float_book_id(self):
        """Test edge case with float book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, 999.5)
        
        # Assert
        # Floats should work (they can be converted to int)
        self.assertTrue(result)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()

    def test_edge_case_boolean_book_id(self):
        """Test edge case with boolean book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, True)
        
        # Assert
        # Boolean True should work (it converts to int 1)
        self.assertTrue(result)
        self.mock_session.add.assert_called_once()
        self.mock_session.commit.assert_called_once()

    def test_edge_case_list_book_id(self):
        """Test edge case with list book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, [999])
        
        # Assert
        self.assertFalse(result)

    def test_edge_case_dict_book_id(self):
        """Test edge case with dict book ID"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=self.mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        self.mock_session.query.return_value.filter.return_value.first.return_value = self.mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(self.test_user_id, {"id": 999})
        
        # Assert
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main() 