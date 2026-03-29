#!/usr/bin/env python3
"""Retry with exponential backoff."""
import time, random

class RetryError(Exception):
    def __init__(self, attempts, last_error):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Failed after {attempts} attempts: {last_error}")

def retry(fn, max_attempts=3, base_delay=0.1, max_delay=30.0, backoff=2.0,
          jitter=True, retryable=None):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            if retryable and not retryable(e):
                raise
            last_error = e
            if attempt < max_attempts:
                delay = min(base_delay * (backoff ** (attempt - 1)), max_delay)
                if jitter:
                    delay *= random.uniform(0.5, 1.5)
                time.sleep(delay)
    raise RetryError(max_attempts, last_error)

def with_retry(max_attempts=3, base_delay=0.1, **kwargs):
    def decorator(fn):
        def wrapper(*args, **kw):
            return retry(lambda: fn(*args, **kw), max_attempts=max_attempts,
                        base_delay=base_delay, **kwargs)
        return wrapper
    return decorator

if __name__ == "__main__":
    count = [0]
    @with_retry(max_attempts=3, base_delay=0.01)
    def flaky():
        count[0] += 1
        if count[0] < 3:
            raise ValueError("not yet")
        return "success"
    print(flaky())

def test():
    # Success on third try
    counter = [0]
    def flaky():
        counter[0] += 1
        if counter[0] < 3: raise ValueError("fail")
        return "ok"
    result = retry(flaky, max_attempts=3, base_delay=0.001, jitter=False)
    assert result == "ok"
    assert counter[0] == 3
    # Immediate success
    assert retry(lambda: 42, max_attempts=1) == 42
    # All fail
    try:
        retry(lambda: 1/0, max_attempts=2, base_delay=0.001, jitter=False)
        assert False
    except RetryError as e:
        assert e.attempts == 2
    # Retryable filter
    counter2 = [0]
    def only_value(e): return isinstance(e, ValueError)
    try:
        retry(lambda: 1/0, max_attempts=3, base_delay=0.001, retryable=only_value)
        assert False
    except ZeroDivisionError:
        pass
    print("  retry: ALL TESTS PASSED")
