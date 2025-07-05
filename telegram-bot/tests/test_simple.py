#!/usr/bin/env python3
"""
Simple test to verify that unit tests work without database dependencies.
"""

import unittest
import sys
import os
from unittest.mock import Mock

# Add the parent directory to the Python path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_manager import UserManager


class TestSimple(unittest.TestCase):
    """Simple tests to verify unit test setup works"""

    def test_simple_mock(self):
        """Test that basic mocking works"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=Mock())
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        # Act
        with user_manager.db_manager.get_session() as session:
            session.add("test")
        
        # Assert
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()

    def test_simple_book_addition(self):
        """Test simple book addition with mocking"""
        # Arrange
        user_manager = UserManager()
        mock_db_manager = Mock()
        user_manager.db_manager = mock_db_manager
        
        # Create a proper context manager mock
        mock_context = Mock()
        mock_session = Mock()
        mock_context.__enter__ = Mock(return_value=mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context
        
        # Mock user
        mock_user = Mock()
        mock_user.id = 1
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Act
        result = user_manager.add_book_to_statistics(12345, 999)
        
        # Assert
        self.assertTrue(result)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_environment_variables(self):
        """Test that test environment is properly set"""
        self.assertEqual(os.environ.get('TEST_ENVIRONMENT'), 'true')

    def test_imports_work(self):
        """Test that all necessary imports work"""
        # This test verifies that we can import the main modules
        import user_manager
        import config
        self.assertTrue(True)  # If we get here, imports worked


if __name__ == '__main__':
    unittest.main() 