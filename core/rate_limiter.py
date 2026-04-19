# DEFERRED: not in production path — RateLimiter is defined but not instantiated
# in any production module. Rate limiting is currently handled by RobustErrorHandler
# (retry with exponential backoff). Activate by importing RateLimiter in claude_client.py.
import time
from collections import deque
from threading import Lock


class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60,
                 daily_cost_limit_usd: float = 50.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.daily_cost_limit_usd = daily_cost_limit_usd
        self._requests: deque = deque()
        self._daily_cost: float = 0.0
        self._lock = Lock()

    def check_and_consume(self) -> bool:
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            while self._requests and self._requests[0] < cutoff:
                self._requests.popleft()
            if len(self._requests) >= self.max_requests:
                return False
            self._requests.append(now)
            return True

    def add_cost(self, cost_usd: float):
        with self._lock:
            self._daily_cost += cost_usd

    def cost_within_limit(self) -> bool:
        return self._daily_cost < self.daily_cost_limit_usd

    def reset_daily(self):
        with self._lock:
            self._daily_cost = 0.0

    @property
    def current_cost(self) -> float:
        return self._daily_cost
