# Telegram Bot Tests

This directory contains unit tests for the telegram bot project. All tests are **pure unit tests** with no database dependencies.

## Test Structure

- `test_pickup_system.py` - Unit tests for the book pickup system functionality
- `test_config.py` - Unit tests for configuration management
- `test_simple.py` - Simple tests to verify the test setup works
- `run_tests.py` - Test runner script

## Running Tests

### Local Development

```bash
# Run all unit tests
python tests/run_tests.py

# Run unit tests only (explicit)
python tests/run_tests.py --unit

# Run tests with coverage
python tests/run_tests.py --coverage

# Run a specific test file
python tests/run_tests.py --test-file test_simple.py

# Run all tests (default)
python tests/run_tests.py --all
```

### Using Docker

```bash
# Run unit tests in Docker (no database required)
docker-compose -f docker-compose.test.yml up --build

# Run tests and remove containers
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

### Using Python unittest directly

```bash
# Run all tests
python -m unittest discover tests/ -v

# Run a specific test file
python -m unittest tests.test_simple -v

# Run a specific test class
python -m unittest tests.test_simple.TestSimple -v

# Run a specific test method
python -m unittest tests.test_simple.TestSimple.test_simple_mock -v
```

## Test Features

### Pure Unit Tests
- **No database dependencies** - All database operations are mocked
- **Fast execution** - Tests run in milliseconds, not seconds
- **Isolated** - Each test is completely independent
- **Reliable** - No external dependencies that can fail

### Mocking Strategy
- Database manager is mocked at the instance level
- SQLAlchemy sessions are mocked
- All database queries return predefined mock data
- No real database connections are made

### Coverage
- Tests cover all major UserManager methods
- Edge cases and error conditions are tested
- Input validation is thoroughly tested
- Business logic is verified with mocked data

## Test Categories

### User Management Tests
- User registration (success, already exists, database errors)
- User lookup and validation
- User statistics retrieval

### Book Management Tests
- Adding books to statistics (with and without pickup dates)
- Marking books as picked up
- Marking books as returned
- Book validation and error handling

### Query Tests
- Getting user's active books
- Getting user's pending pickup books
- Getting overdue books
- Getting top books statistics
- Finding users with active books

### Edge Cases
- Invalid book IDs (strings, None, empty, negative, zero, large numbers)
- Invalid data types (lists, dictionaries, booleans)
- Database errors and exceptions
- User not found scenarios

## Environment Variables

The following environment variables are set for testing:

```bash
TEST_ENVIRONMENT=true
PYTHONPATH=/app
LOG_LEVEL=DEBUG
BOT_TOKEN=test_bot_token
ADMIN_IDS=12345,67890
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/test
GOOGLE_SHEET_NAME=TestBooks
ALLOWED_TIME_TO_READ_THE_BOOK=14
RULES_TEXT=Test rules for books
```

## Test Results

Test results are saved to:
- Console output (detailed test results)
- `test-results/` directory (if using Docker)
- `coverage/` directory (if using coverage)

## Adding New Tests

1. Create a new test file: `test_<feature>.py`
2. Import the necessary modules and Mock from unittest.mock
3. Create test classes that inherit from `unittest.TestCase`
4. Mock the database manager in each test method
5. Test both success and failure scenarios
6. Add edge cases and error conditions

Example test structure:

```python
import unittest
from unittest.mock import Mock
from user_manager import UserManager

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        self.user_manager = UserManager()
        self.mock_db_manager = Mock()
        self.user_manager.db_manager = self.mock_db_manager
        
    def test_feature_success(self):
        # Arrange
        mock_session = Mock()
        self.mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        
        # Act
        result = self.user_manager.new_feature()
        
        # Assert
        self.assertTrue(result)
```

## Troubleshooting

### Import Errors
- Ensure `PYTHONPATH` includes the parent directory
- Check that all required modules are available

### Mock Issues
- Verify that the database manager is properly mocked
- Check that mock return values are set correctly
- Ensure mock assertions match the actual method calls

### Test Failures
- Check that test expectations match the actual method behavior
- Verify that edge cases are handled correctly
- Ensure error conditions are properly tested

## Best Practices

1. **Keep tests fast** - Unit tests should run in milliseconds
2. **Mock external dependencies** - Never connect to real databases in unit tests
3. **Test edge cases** - Include invalid inputs and error conditions
4. **Use descriptive test names** - Test names should explain what is being tested
5. **Arrange-Act-Assert** - Structure tests with clear sections
6. **One assertion per test** - Focus each test on a single behavior
7. **Clean setup** - Use setUp() and tearDown() for common test data 