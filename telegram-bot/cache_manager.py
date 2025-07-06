import redis
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
import config

logger = logging.getLogger(__name__)

class BookStatusCache:
    """
    Simple Redis-based cache for book information from Google Sheets.
    
    Cache strategy:
    - Book statuses (booked, delivered, returned) change daily
    - Core book data (name, author, categories) is very stable
    - Uses 1-hour TTL by default (good balance for daily status changes)
    - Stores all books in a single cache entry for simplicity
    - Cache is invalidated when book statuses change
    - No periodic refresh - cache populates on first access
    """
    
    def __init__(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                password=config.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def _get_all_books_key(self) -> str:
        """Get Redis key for all books cache"""
        return "books:all"
    
    def _get_last_update_key(self) -> str:
        """Get Redis key for last update timestamp"""
        return "books:last_update"
    
    def cache_all_books(self, books_data: List[Dict], ttl: Optional[int] = None) -> bool:
        """
        Cache all books data in a single Redis entry
        
        Args:
            books_data: List of all books with their data
            ttl: Time to live in seconds (defaults to config.REDIS_CACHE_TTL)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or config.REDIS_CACHE_TTL
            
            # Convert list to dictionary with book_id as key for faster lookups
            books_dict = {}
            for book in books_data:
                book_id = str(book.get('id', ''))
                if book_id:
                    books_dict[book_id] = book
            
            # Cache all books as a single JSON entry
            all_books_key = self._get_all_books_key()
            books_json = json.dumps(books_dict, default=str)
            self.redis_client.setex(all_books_key, ttl, books_json)
            
            # Update timestamp
            self.redis_client.setex(
                self._get_last_update_key(), 
                ttl, 
                datetime.now().isoformat()
            )
            
            logger.info(f"Cached {len(books_dict)} books in Redis (TTL: {ttl}s, {ttl//3600}h)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache all books: {e}")
            return False
    
    def get_all_books(self) -> Optional[Dict]:
        """
        Get all books data from cache
        
        Returns:
            Optional[Dict]: Dictionary of all books with book_id as keys, or None if not found
        """
        if not self.redis_client:
            return None
        
        try:
            all_books_key = self._get_all_books_key()
            books_json = self.redis_client.get(all_books_key)
            
            if books_json:
                books_dict = json.loads(books_json)
                logger.debug(f"Cache hit for all books ({len(books_dict)} books)")
                return books_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get all books from cache: {e}")
            return None
    
    def get_book(self, book_id: str) -> Optional[Dict]:
        """
        Get specific book by ID from cache
        
        Args:
            book_id: Book ID
            
        Returns:
            Optional[Dict]: Book information or None if not found
        """
        books_dict = self.get_all_books()
        if books_dict:
            return books_dict.get(book_id)
        return None
    
    def get_book_status(self, book_id: str) -> Optional[str]:
        """
        Get book status by ID from cache
        
        Args:
            book_id: Book ID
            
        Returns:
            Optional[str]: Book status or None if not found
        """
        book_info = self.get_book(book_id)
        if book_info:
            return book_info.get('status', '')
        return None
    
    def get_books_by_category(self, category: str) -> List[Dict]:
        """
        Get books filtered by category from cache
        
        Args:
            category: Category name
            
        Returns:
            List[Dict]: List of books in the category
        """
        books_dict = self.get_all_books()
        if not books_dict:
            return []
        
        books = []
        category_lower = category.lower()
        
        for book in books_dict.values():
            book_categories = str(book.get('categories', '')).lower()
            if category_lower in book_categories:
                books.append(book)
        
        logger.debug(f"Found {len(books)} books in category '{category}' from cache")
        return books
    
    def invalidate_all_books(self) -> bool:
        """
        Invalidate all books cache
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            # Delete all books cache and timestamp
            keys_to_delete = [self._get_all_books_key(), self._get_last_update_key()]
            self.redis_client.delete(*keys_to_delete)
            logger.info("Invalidated all books cache")
            return True
            
        except Exception as e:
            logger.error(f"Failed to invalidate all books cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dict: Cache statistics
        """
        if not self.redis_client:
            return {"error": "Redis not connected"}
        
        try:
            all_books = self.get_all_books()
            last_update = self.redis_client.get(self._get_last_update_key())
            
            stats = {
                "total_books": len(all_books) if all_books else 0,
                "cache_exists": all_books is not None,
                "last_update": last_update,
                "ttl_seconds": config.REDIS_CACHE_TTL
            }
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    def is_healthy(self) -> bool:
        """
        Check if Redis connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False 