"""
Security utilities for the bot
- Rate limiting (in-memory, per-user)
- Telegram webhook validation
- Admin authentication
"""
import time
import hashlib
import hmac
import secrets
from collections import defaultdict
from functools import wraps
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import logging

logger = logging.getLogger(__name__)

# ============== RATE LIMITING ==============

class RateLimiter:
    """In-memory rate limiter - per user/IP"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
        self._last_cleanup = time.time()
    
    def _cleanup_old(self):
        """Периодическая очистка старых записей"""
        current_time = time.time()
        if current_time - self._last_cleanup < 60:  # Раз в минуту
            return
        
        self._last_cleanup = current_time
        cutoff = current_time - self.window
        
        keys_to_delete = []
        for key, timestamps in self.requests.items():
            self.requests[key] = [t for t in timestamps if t > cutoff]
            if not self.requests[key]:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.requests[key]
    
    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """
        Check if request is allowed
        Returns: (allowed: bool, remaining: int)
        """
        current_time = time.time()
        self._cleanup_old()
        
        # Очистка старых записей для этого пользователя
        cutoff = current_time - self.window
        self.requests[identifier] = [
            t for t in self.requests[identifier] if t > cutoff
        ]
        
        current_count = len(self.requests[identifier])
        remaining = max(0, self.max_requests - current_count)
        
        if current_count >= self.max_requests:
            return False, 0
        
        self.requests[identifier].append(current_time)
        return True, remaining - 1
    
    def get_reset_time(self, identifier: str) -> int:
        """Get seconds until rate limit resets"""
        if identifier not in self.requests or not self.requests[identifier]:
            return 0
        
        oldest = min(self.requests[identifier])
        reset_at = oldest + self.window
        return max(0, int(reset_at - time.time()))


# Global rate limiters
webhook_limiter = RateLimiter(max_requests=120, window_seconds=60)  # 120/min per user
api_limiter = RateLimiter(max_requests=60, window_seconds=60)  # 60/min per IP
admin_limiter = RateLimiter(max_requests=20, window_seconds=60)  # 20/min for admin


def check_rate_limit(identifier: str, limiter: RateLimiter = api_limiter) -> bool:
    """Check rate limit and raise exception if exceeded"""
    allowed, remaining = limiter.is_allowed(identifier)
    if not allowed:
        reset_time = limiter.get_reset_time(identifier)
        logger.warning(f"[SECURITY] Rate limit exceeded for {identifier}")
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Try again in {reset_time} seconds.",
            headers={"Retry-After": str(reset_time)}
        )
    return True


# ============== TELEGRAM WEBHOOK VALIDATION ==============

def validate_telegram_webhook(token: str, update_data: dict) -> bool:
    """
    Validate that webhook request is from Telegram
    Basic validation - checks structure of update
    """
    # Check required fields
    if "update_id" not in update_data:
        return False
    
    # Check that update_id is a positive integer
    update_id = update_data.get("update_id")
    if not isinstance(update_id, int) or update_id <= 0:
        return False
    
    # Must have at least one of these
    valid_update_types = [
        "message", "edited_message", "channel_post", 
        "callback_query", "inline_query", "chosen_inline_result",
        "shipping_query", "pre_checkout_query", "poll", "poll_answer"
    ]
    
    has_valid_type = any(key in update_data for key in valid_update_types)
    if not has_valid_type:
        return False
    
    return True


def get_telegram_user_id(update_data: dict) -> str:
    """Extract user ID from Telegram update for rate limiting"""
    # Try different update types
    if "message" in update_data:
        return str(update_data["message"].get("from", {}).get("id", "unknown"))
    if "callback_query" in update_data:
        return str(update_data["callback_query"].get("from", {}).get("id", "unknown"))
    if "inline_query" in update_data:
        return str(update_data["inline_query"].get("from", {}).get("id", "unknown"))
    return "unknown"


# ============== ADMIN AUTHENTICATION ==============

security = HTTPBasic()

# Admin credentials (should be in .env in production)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = None  # Will be set from env


def set_admin_password(password: str):
    """Set admin password hash"""
    global ADMIN_PASSWORD_HASH
    ADMIN_PASSWORD_HASH = hashlib.sha256(password.encode()).hexdigest()


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Verify admin credentials"""
    # Rate limit admin login attempts
    check_rate_limit(f"admin_login_{credentials.username}", admin_limiter)
    
    if ADMIN_PASSWORD_HASH is None:
        # No password set - allow access (for backward compatibility)
        logger.warning("[SECURITY] Admin password not set!")
        return credentials.username
    
    password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    username_correct = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    password_correct = secrets.compare_digest(password_hash, ADMIN_PASSWORD_HASH)
    
    if not (username_correct and password_correct):
        logger.warning(f"[SECURITY] Failed admin login attempt: {credentials.username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


# ============== IP EXTRACTION ==============

def get_client_ip(request: Request) -> str:
    """Get real client IP (handles proxies)"""
    # Check X-Forwarded-For header (set by proxies/load balancers)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"
