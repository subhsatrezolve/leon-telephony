import redis
import json
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class RedisSessionStore:
    def __init__(self, url: Optional[str] = None, host: str = 'localhost', port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        Initialize Redis connection

        Args:
            url: Redis connection URL (e.g., rediss://:password@hostname:6380/0 for Azure Redis)
                 If provided, other connection parameters are ignored.
            host: Redis server host (used if url is not provided)
            port: Redis server port (used if url is not provided)
            db: Redis database number (used if url is not provided)
            password: Redis password (used if url is not provided)
        """
        try:
            if url:
                self.redis_client = redis.from_url(
                    url,
                    decode_responses=True
                )
                logger.info("Connecting to Redis using URL")
            else:
                self.redis_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=True
                )
            # Test connection
            self.redis_client.ping()
            logger.info("Successfully connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def store(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """
        Store data in Redis
        
        Args:
            key: Storage key
            value: Data to store (will be JSON serialized)
            expire_seconds: Optional expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)
            
            result = self.redis_client.set(key, serialized_value, ex=expire_seconds)
            logger.debug(f"Stored data with key: {key}")
            return result
        except Exception as e:
            logger.error(f"Failed to store data with key {key}: {e}")
            return False
    
    def fetch(self, key: str) -> Optional[Any]:
        """
        Fetch data from Redis
        
        Args:
            key: Storage key
            
        Returns:
            Retrieved data or None if not found
        """
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # Try to parse as JSON, fallback to string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Failed to fetch data with key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete data from Redis
        
        Args:
            key: Storage key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.redis_client.delete(key)
            logger.debug(f"Deleted data with key: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to delete data with key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis
        
        Args:
            key: Storage key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False
    
    def get_all_keys(self, pattern: str = "*") -> list:
        """
        Get all keys matching pattern
        
        Args:
            pattern: Key pattern (default: all keys)
            
        Returns:
            List of matching keys
        """
        try:
            return self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Failed to get keys with pattern {pattern}: {e}")
            return []
    
    def set_expiry(self, key: str, seconds: int) -> bool:
        """
        Set expiry time for an existing key
        
        Args:
            key: Storage key
            seconds: Expiry time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.redis_client.expire(key, seconds)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to set expiry for key {key}: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """
        Get time to live for a key
        
        Args:
            key: Storage key
            
        Returns:
            TTL in seconds (-1 if no expiry, -2 if key doesn't exist)
        """
        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Failed to get TTL for key {key}: {e}")
            return -2
    
    def close(self):
        """Close Redis connection"""
        if hasattr(self, 'redis_client'):
            self.redis_client.close()
            logger.info("Redis connection closed")