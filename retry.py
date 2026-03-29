#!/usr/bin/env python3
"""retry: Retry/backoff strategies for resilient operations."""
import time, random, sys

class RetryConfig:
    def __init__(self, max_retries=3, base_delay=1.0, max_delay=60.0,
                 backoff="exponential", jitter=True, retryable=None):
        self.max_retries = max_retries; self.base_delay = base_delay
        self.max_delay = max_delay; self.backoff = backoff
        self.jitter = jitter
        self.retryable = retryable or (lambda e: True)

    def delay(self, attempt):
        if self.backoff == "exponential":
            d = self.base_delay * (2 ** attempt)
        elif self.backoff == "linear":
            d = self.base_delay * (attempt + 1)
        elif self.backoff == "constant":
            d = self.base_delay
        else:
            d = self.base_delay
        d = min(d, self.max_delay)
        if self.jitter:
            d *= random.uniform(0.5, 1.5)
        return d

def retry(fn, config=None):
    if config is None: config = RetryConfig()
    last_error = None
    attempts = []
    for attempt in range(config.max_retries + 1):
        try:
            result = fn()
            attempts.append({"attempt": attempt, "success": True})
            return result, attempts
        except Exception as e:
            last_error = e
            attempts.append({"attempt": attempt, "error": str(e)})
            if attempt < config.max_retries and config.retryable(e):
                delay = config.delay(attempt)
                # In real code: time.sleep(delay)
            else:
                break
    raise last_error

class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=30):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0; self.state = "closed"
        self.last_failure = 0

    def call(self, fn):
        if self.state == "open":
            if time.time() - self.last_failure > self.reset_timeout:
                self.state = "half-open"
            else:
                raise RuntimeError("Circuit breaker is open")
        try:
            result = fn()
            if self.state == "half-open":
                self.state = "closed"; self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "open"
            raise

def test():
    # Successful retry
    calls = [0]
    def flaky():
        calls[0] += 1
        if calls[0] < 3: raise ValueError("not yet")
        return "ok"
    result, attempts = retry(flaky, RetryConfig(max_retries=5, base_delay=0))
    assert result == "ok"
    assert len(attempts) == 3
    # All fail
    def always_fail(): raise RuntimeError("boom")
    try:
        retry(always_fail, RetryConfig(max_retries=2, base_delay=0))
        assert False
    except RuntimeError: pass
    # Delay calculation
    cfg = RetryConfig(base_delay=1.0, jitter=False)
    assert cfg.delay(0) == 1.0
    assert cfg.delay(1) == 2.0
    assert cfg.delay(2) == 4.0
    # Linear
    cfg2 = RetryConfig(base_delay=1.0, backoff="linear", jitter=False)
    assert cfg2.delay(0) == 1.0
    assert cfg2.delay(1) == 2.0
    assert cfg2.delay(2) == 3.0
    # Circuit breaker
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=0.1)
    for _ in range(3):
        try: cb.call(always_fail)
        except: pass
    assert cb.state == "open"
    try:
        cb.call(lambda: "ok")
        assert False
    except RuntimeError as e:
        assert "open" in str(e)
    # After timeout, half-open
    time.sleep(0.15)
    result = cb.call(lambda: "recovered")
    assert result == "recovered"
    assert cb.state == "closed"
    print("All tests passed!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test": test()
    else: print("Usage: retry.py test")
