"""
Rate Limiter utility for API endpoints
"""
import time
import redis
from typing import Dict, Optional
from src.core.config import settings


class RateLimiter:
    """
    Rate limiter using Redis for tracking requests
    """
    
    def __init__(self):
        if settings.REDIS_URL:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        else:
            # For development without Redis, use in-memory storage
            self.redis_client = None
            self._memory_store: Dict[str, list] = {}
    
    def is_allowed(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int,
        user_id: Optional[int] = None
    ) -> tuple[bool, int]:
        """
        Check if request is allowed based on rate limit
        
        Args:
            key: Rate limit key (e.g., 'presentation:user:123', 'global:presentations')
            max_requests: Maximum number of requests allowed
            window_seconds: Time window in seconds
            user_id: Optional user ID for user-specific rate limiting
            
        Returns:
            Tuple of (is_allowed: bool, retry_after_seconds: int)
        """
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        if self.redis_client:
            # Use Redis sorted set to track request timestamps
            pipe = self.redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Get current count
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration for the key
            pipe.expire(key, window_seconds)
            
            results = pipe.execute()
            current_count = results[1]
            
            if current_count >= max_requests:
                # Find earliest request in window to calculate retry time
                earliest_timestamp = self.redis_client.zrange(
                    key, 0, 0, withscores=True
                )
                if earliest_timestamp:
                    earliest_time = int(earliest_timestamp[0][1])
                    retry_after = max(1, earliest_time + window_seconds - current_time)
                    return False, retry_after
                return False, window_seconds
            else:
                return True, 0
        else:
            # In-memory implementation for development
            if key not in self._memory_store:
                self._memory_store[key] = []
            
            # Remove old requests outside the window
            self._memory_store[key] = [
                timestamp for timestamp in self._memory_store[key] 
                if timestamp > window_start
            ]
            
            if len(self._memory_store[key]) >= max_requests:
                earliest_time = min(self._memory_store[key])
                retry_after = max(1, earliest_time + window_seconds - current_time)
                return False, retry_after
            else:
                # Add current request
                self._memory_store[key].append(current_time)
                return True, 0


# Global rate limiter instance
rate_limiter = RateLimiter()