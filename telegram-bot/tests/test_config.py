"""
Test configuration and shared test data for the pickup system tests.
"""

from datetime import datetime, timedelta

# Test User Data
TEST_USER_1 = {
    'id': 12345,
    'phone': "+380991234567",
    'name': "Test User",
    'telegram_id': "12345"
}

TEST_USER_2 = {
    'id': 54321,
    'phone': "+380998765432",
    'name': "Integration Test User",
    'telegram_id': "54321"
}

# Test Book Data
TEST_BOOK_1 = {
    'id': 999,
    'name': "Test Book 1"
}

TEST_BOOK_2 = {
    'id': 888,
    'name': "Test Book 2"
}

TEST_BOOK_3 = {
    'id': 777,
    'name': "Integration Test Book"
}

# Test Dates
def get_test_date_booked():
    """Get a test date for when a book was picked up"""
    return datetime.now()

def get_test_expiry_date(days_ahead=14):
    """Get a test expiry date"""
    return datetime.now() + timedelta(days=days_ahead)

def get_test_overdue_date(days_overdue=5):
    """Get a test overdue date"""
    return datetime.now() - timedelta(days=days_overdue)

# Test Statistics Data
def create_mock_statistics_record(book_id, user_id, date_booked=None, expiry_date=None, returned=False):
    """Create a mock statistics record for testing"""
    from unittest.mock import Mock
    
    mock_record = Mock()
    mock_record.book_id = book_id
    mock_record.user_id = user_id
    mock_record.date_booked = date_booked
    mock_record.expiry_date = expiry_date
    mock_record.returned = returned
    mock_record.returned_at = None
    
    return mock_record

def create_mock_user(user_data):
    """Create a mock user for testing"""
    from unittest.mock import Mock
    
    mock_user = Mock()
    mock_user.id = user_data['id']
    mock_user.name = user_data['name']
    mock_user.phone = user_data['phone']
    mock_user.telegram_id = user_data['telegram_id']
    mock_user.created_at = datetime.now()
    
    return mock_user

# Test Scenarios
class TestScenarios:
    """Common test scenarios for reuse across tests"""
    
    @staticmethod
    def user_registration_success():
        """Scenario: Successful user registration"""
        return {
            'user_id': TEST_USER_1['id'],
            'phone': TEST_USER_1['phone'],
            'name': TEST_USER_1['name'],
            'expected_result': True
        }
    
    @staticmethod
    def user_registration_already_exists():
        """Scenario: User registration when user already exists"""
        return {
            'user_id': TEST_USER_1['id'],
            'phone': TEST_USER_1['phone'],
            'name': TEST_USER_1['name'],
            'user_exists': True,
            'expected_result': True  # Should return existing user
        }
    
    @staticmethod
    def book_booking_success():
        """Scenario: Successful book booking"""
        return {
            'user_id': TEST_USER_1['id'],
            'book_id': TEST_BOOK_1['id'],
            'expected_result': True,
            'expected_date_booked': None,
            'expected_expiry_date': None
        }
    
    @staticmethod
    def book_pickup_success():
        """Scenario: Successful book pickup"""
        return {
            'user_id': TEST_USER_1['id'],
            'book_id': TEST_BOOK_1['id'],
            'expected_result': True,
            'expected_date_booked': 'not_none',
            'expected_expiry_date': 'not_none'
        }
    
    @staticmethod
    def book_pickup_custom_expiry():
        """Scenario: Book pickup with custom expiry date"""
        custom_expiry = get_test_expiry_date(30)
        return {
            'user_id': TEST_USER_1['id'],
            'book_id': TEST_BOOK_1['id'],
            'expiry_date': custom_expiry,
            'expected_result': True,
            'expected_expiry_date': custom_expiry
        }
    
    @staticmethod
    def book_return_success():
        """Scenario: Successful book return"""
        return {
            'user_id': TEST_USER_1['id'],
            'book_id': TEST_BOOK_1['id'],
            'expected_result': True,
            'expected_returned': True
        }

# Error Messages
class ErrorMessages:
    """Common error messages for testing"""
    
    USER_NOT_FOUND = "User not found"
    BOOK_NOT_FOUND = "Book not found"
    INVALID_BOOK_ID = "Cannot convert book_id to integer"
    DATABASE_ERROR = "Database error"
    ALREADY_PICKED_UP = "Book already picked up"
    ALREADY_RETURNED = "Book already returned"

# Test Constants
class TestConstants:
    """Constants used in tests"""
    
    # Time periods
    DEFAULT_READING_DAYS = 14
    OVERDUE_DAYS = 5
    EXTENDED_READING_DAYS = 30
    
    # Limits
    MAX_BOOKS_PER_USER = 10
    TOP_BOOKS_LIMIT = 10
    
    # Status values
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_RETURNED = "returned"
    STATUS_OVERDUE = "overdue" 