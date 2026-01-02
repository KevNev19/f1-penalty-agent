import locale
import logging
import sys

logger = logging.getLogger(__name__)


def log_encoding_info() -> None:
    logger.info(f"System encoding: {sys.getfilesystemencoding()}")
    logger.info(f"Stdout encoding: {sys.stdout.encoding}")
    logger.info(f"Locale: {locale.getlocale()}")
    logger.info(f"Default encoding: {sys.getdefaultencoding()}")
