#!/usr/bin/env python3
"""
Test runner for the telegram bot project.
Runs pure unit tests without any database dependencies.
"""

import os
import sys
import subprocess
import argparse
import unittest
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_unit_tests():
    """Run unit tests without database dependencies"""
    print("🧪 Running unit tests...")
    
    # Discover and run unit tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_specific_test(test_file):
    """Run a specific test file"""
    print(f"🧪 Running specific test: {test_file}")
    
    # Import and run the specific test
    test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), test_file)
    
    if not os.path.exists(test_path):
        print(f"❌ Test file not found: {test_path}")
        return False
    
    # Run the specific test file
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(test_path), pattern=os.path.basename(test_path))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_with_coverage():
    """Run tests with coverage reporting"""
    print("📊 Running tests with coverage...")
    
    try:
        # Check if coverage is installed
        import coverage
    except ImportError:
        print("❌ Coverage not installed. Install with: pip install coverage")
        return False
    
    # Create coverage object
    cov = coverage.Coverage(
        source=['../user_manager.py', '../database.py', '../config.py'],
        omit=['*/tests/*', '*/venv/*', '*/env/*']
    )
    
    # Start coverage
    cov.start()
    
    # Run tests
    success = run_unit_tests()
    
    # Stop coverage
    cov.stop()
    cov.save()
    
    # Generate reports
    print("\n📊 Coverage Report:")
    cov.report()
    
    # Generate HTML report
    cov_dir = Path("../coverage")
    cov_dir.mkdir(exist_ok=True)
    cov.html_report(directory=str(cov_dir / "html"))
    print(f"📁 HTML coverage report saved to: {cov_dir / 'html'}")
    
    return success

def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(description='Run telegram bot tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--coverage', action='store_true', help='Run tests with coverage')
    parser.add_argument('--test-file', type=str, help='Run a specific test file')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    
    args = parser.parse_args()
    
    print("🚀 Starting test runner...")
    print("📁 Working directory:", os.getcwd())
    print("🐍 Python version:", sys.version)
    
    # Set test environment
    os.environ['TEST_ENVIRONMENT'] = 'true'
    os.environ['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    success = False
    
    try:
        if args.test_file:
            success = run_specific_test(args.test_file)
        elif args.coverage:
            success = run_with_coverage()
        elif args.unit or args.all:
            success = run_unit_tests()
        else:
            # Default: run unit tests
            success = run_unit_tests()
            
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        return 1
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == '__main__':
    exit(main()) 