from supabase import create_client
from config import settings
import asyncio
from typing import TypeVar, Callable, Any
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client (simple configuration)
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

T = TypeVar('T')

async def db_retry(
    func: Callable[..., T], 
    *args,
    max_retries: int = 5,
    initial_delay: float = 0.5,
    backoff_factor: float = 1.5,
    timeout: float = 5.0,
    **kwargs
) -> T:
    """
    Execute a database function with automatic retry on timeout/failure.
    
    Args:
        func: The function to execute
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay on each retry
        timeout: Timeout for each attempt in seconds
        *args, **kwargs: Arguments to pass to func
    
    Returns:
        The result of func
        
    Raises:
        The last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            # Wrap the function call in a timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(func, *args, **kwargs),
                    timeout=timeout
                )
            return result
            
        except asyncio.TimeoutError as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"🔄 Database timeout on attempt {attempt}/{max_retries}, retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"❌ Database timeout after {max_retries} attempts")
                
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"🔄 Database error on attempt {attempt}/{max_retries}: {e}, retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"❌ Database error after {max_retries} attempts: {e}")
    
    # If we get here, all retries failed
    raise last_exception
