import time
import random
import anthropic
from typing import Callable, TypeVar, Optional

T = TypeVar("T")

FALLBACK_CHAIN = {
    "claude-opus-4-7":   "claude-sonnet-4-6",
    "claude-sonnet-4-6": "claude-haiku-4-5",
    "claude-haiku-4-5":  None,
}

RETRYABLE_ERRORS = (
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
)


class RobustErrorHandler:
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def execute_with_retry(self, fn: Callable[[], T]) -> T:
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                return fn()
            except RETRYABLE_ERRORS as e:
                last_exception = e
                if attempt == self.max_retries:
                    break
                delay = min(self.base_delay * (2 ** attempt) + random.uniform(0, 0.1),
                            self.max_delay)
                time.sleep(delay)
        raise last_exception

    def get_fallback_model(self, current_model: str) -> Optional[str]:
        return FALLBACK_CHAIN.get(current_model)
