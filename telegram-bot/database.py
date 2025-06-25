from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    telegram_id = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationship to user statistics
    statistics = relationship("UserStatistics", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', phone='{self.phone}')>"

class UserStatistics(Base):
    __tablename__ = 'user_statistics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    book_id = Column(Integer, nullable=False)
    date_booked = Column(DateTime, default=datetime.now)
    expiry_date = Column(DateTime, nullable=False)
    returned = Column(Boolean, default=False)
    returned_at = Column(DateTime, nullable=True)
    
    # Relationship to user
    user = relationship("User", back_populates="statistics")
    
    def __repr__(self):
        return f"<UserStatistics(user_id={self.user_id}, book_id={self.book_id}, returned={self.returned})>"

class DatabaseManager:
    def __init__(self):
        try:
            self.engine = create_engine(config.DATABASE_URL, echo=False)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.error(f"Failed to establish database connection: {e}")
            raise
    
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all tables (for development only)"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.get_session() as session:
                session.execute(func.now())
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager() 