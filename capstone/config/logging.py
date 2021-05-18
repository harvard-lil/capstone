import logging
import sys

"""
    This file offers the equivalent of:
    
        import logging
        logger = logging.getLogger(__name__)
        
    This works the same as the above, via stack inspection:
    
        from config.logging import logger
"""

logger_cache = {}

class CallerLogger:
    def __getattr__(self, attr):
        # get the value of __name__ from the caller:
        caller_name = sys._getframe().f_back.f_globals.get("__name__")
        # fetch and cache caller's logger:
        if caller_name not in logger_cache:
            logger_cache[caller_name] = logging.getLogger(caller_name)
        # pretend to be caller's logger:
        return getattr(logger_cache[caller_name], attr)

logger = CallerLogger()
