import time
import logging

logger = logging.getLogger(__name__)

class LoopGuard:
    """
    Safety guard to prevent infinite loops in agent execution.
    Fails fast if iteration or time limits are exceeded.
    """
    def __init__(self, max_iters=None, max_duration=None, label="Loop"):
        self.max_iters = max_iters
        self.max_duration = max_duration
        self.label = label
        self.start_time = time.time()
        self.iterations = 0

    def check(self):
        self.iterations += 1
        elapsed = time.time() - self.start_time
        
        # Check iteration limit
        if self.max_iters and self.iterations > self.max_iters:
            error_msg = f"❌ {self.label} exceeded max iterations ({self.max_iters})"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Check time limit
        if self.max_duration and elapsed > self.max_duration:
            error_msg = f"❌ {self.label} exceeded max duration ({self.max_duration}s)"
            logger.error(error_msg)
            raise RuntimeError(error_msg)