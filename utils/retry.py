#!/usr/bin/env python3
"""Retry utility functions with Fibonacci backoff."""

import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

FIBONACCI_DELAYS = [
    1,
    1,
    2,
    3,
    5,
    8,
    13,
    21,
    34,
    55,
    89,
    144,
    233,
    377,
    610,
    987,
    1597,
    2584,
    4181,
    6765,
]
MAX_TOTAL_TIME = 72000


def fibonacci_retry[T](
    operation: Callable[[], T],
    max_total_time: int = MAX_TOTAL_TIME,
    callback: Callable[[int, Exception], bool] | None = None,
    operation_name: str = "operation",
) -> T:
    """Retry an operation with Fibonacci backoff delays.

    Args:
        operation: Function to execute (should return result on success)
        max_total_time: Maximum total retry time in seconds (default: 72000 = 20 hours)
        callback: Optional callback function that receives (attempt_num, exception) and returns
                 True to continue retrying, False to abort. If not provided, retries continue
                 until max_total_time is reached.
        operation_name: Name of operation for logging purposes

    Returns:
        The result of operation when successful

    Raises:
        Exception: The last exception if all retries fail
    """
    start_time = time.time()
    attempt_num = 0
    last_exception = None

    while True:
        try:
            result = operation()
            logger.info(f"{operation_name} succeeded on attempt {attempt_num + 1}")
            return result

        except Exception as e:
            last_exception = e
            attempt_num += 1

            elapsed_time = time.time() - start_time

            if elapsed_time >= max_total_time:
                logger.error(
                    f"{operation_name} failed after {attempt_num} attempts "
                    f"({elapsed_time:.1f}s total, {max_total_time}s max): {e}"
                )
                raise last_exception from None

            delay = FIBONACCI_DELAYS[min(attempt_num - 1, len(FIBONACCI_DELAYS) - 1)]

            if callback:
                should_continue = callback(attempt_num, e)
                if not should_continue:
                    logger.warning(
                        f"{operation_name} aborted by callback on attempt {attempt_num}: {e}"
                    )
                    raise last_exception from None

            logger.warning(
                f"{operation_name} attempt {attempt_num} failed: {e}, "
                f"retrying after {delay}s (elapsed: {elapsed_time:.1f}s/{max_total_time}s)"
            )

            time.sleep(delay)
