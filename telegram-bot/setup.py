#!/usr/bin/env python3
"""
Setup script for the Library Bot
Helps with initial configuration and dependency installation
"""

import os
import sys
import subprocess
import shutil

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def setup_environment():
    """Setup environment file"""
    env_file = ".env"
    env_example = ".env.example"
    
    if os.path.exists(env_file):
        print(f"⚠️  {env_file} already exists")
        response = input("Do you want to overwrite it? (y/N): ").lower()
        if response != 'y':
            print("Skipping environment setup")
            return True
    
    if os.path.exists(env_example):
        shutil.copy(env_example, env_file)
        print(f"✅ Created {env_file} from {env_example}")
        print("🔧 Please edit .env file with your bot token and admin IDs")
        return True
    else:
        print(f"❌ {env_example} not found")
        return False

def create_sample_data():
    """Create sample Excel file"""
    try:
        from create_sample_excel import create_sample_excel
        create_sample_excel()
        print("✅ Sample Excel file created")
        return True
    except Exception as e:
        print(f"❌ Error creating sample Excel file: {e}")
        return False

def show_next_steps():
    """Show next steps to the user"""
    print("\n" + "="*50)
    print("🎉 Setup completed!")
    print("="*50)
    print("\n📋 Next steps:")
    print("1. Edit .env file with your bot token and admin IDs")
    print("2. Customize books.xlsx with your book catalog")
    print("3. Run the bot:")
    print("   - Single process: python bot.py")
    print("   - With scheduler: python run.py")
    print("   - Or separately:")
    print("     Terminal 1: python bot.py")
    print("     Terminal 2: python scheduler.py")
    print("\n📖 See README.md for detailed instructions")
    print("\n🤖 Bot commands:")
    print("   /start - Start the bot")
    print("   /help - Show help")

def main():
    """Main setup function"""
    print("🚀 Library Bot Setup")
    print("=" * 30)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Setup environment
    if not setup_environment():
        return False
    
    # Create sample data
    if not create_sample_data():
        return False
    
    # Show next steps
    show_next_steps()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 