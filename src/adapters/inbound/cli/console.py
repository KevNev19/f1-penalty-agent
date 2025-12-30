"""Safe console wrapper to prevent encoding errors in production.

In Cloud Run and other headless environments, stdout may use ASCII encoding
which causes Rich console to fail when printing Unicode characters.
This module provides a safe wrapper that falls back to standard logging.
"""

import logging
import sys

logger = logging.getLogger(__name__)

# Check if we're in a headless/production environment
_stdout_encoding = (sys.stdout.encoding or "ascii").lower()
_IS_HEADLESS = not sys.stdout.isatty() or _stdout_encoding not in ("utf-8", "utf8")


class SafeConsole:
    """Wrapper that safely handles console output in any environment."""

    def __init__(self):
        self._console = None
        self._initialized = False

    def _get_console(self):
        """Lazy-load Rich console only if needed."""
        if self._initialized:
            return self._console

        self._initialized = True

        if _IS_HEADLESS:
            # Don't use Rich in headless environments
            self._console = None
            return None

        try:
            from rich.console import Console

            self._console = Console()
        except Exception as e:
            logger.debug(f"Rich console initialization failed: {e}")
            self._console = None

        return self._console

    def print(self, *args, **kwargs):
        """Safe print that falls back to logger if needed."""
        console = self._get_console()
        if console:
            try:
                console.print(*args, **kwargs)
            except (UnicodeEncodeError, OSError):
                # Fall back to logger
                msg = " ".join(str(a) for a in args)
                logger.debug(msg)
        else:
            # Use logger in headless mode
            msg = " ".join(str(a) for a in args)
            logger.debug(msg)


# Global safe console instance
console = SafeConsole()
