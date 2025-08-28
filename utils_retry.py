# utils_retry.py
import time, random
from typing import Callable, Any

RETRYABLE_KEYWORDS = ("429", "resourceexhausted", "quota", "rate limit", "ratelimit", "exhausted")

def _is_retryable_error(err: BaseException) -> bool:
    msg = str(err).lower()
    return any(k in msg for k in RETRYABLE_KEYWORDS)

def call_with_backoff(fn: Callable, *args, retries: int = 3, base: float = 0.6, jitter: float = 0.25, **kwargs) -> Any:
    last_err = None
    for i in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            if not _is_retryable_error(e) or i == retries - 1:
                break
            time.sleep(base * (2 ** i) + random.uniform(0, jitter))
    raise last_err
