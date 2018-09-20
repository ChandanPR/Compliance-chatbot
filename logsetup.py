import logging
import sys


class LessThanFilter(logging.Filter):
    def __init__(self, exclusive_maximum, name=""):
        super(LessThanFilter, self).__init__(name)
        self.max_level = exclusive_maximum

    def filter(self, record):
        # non-zero return means we log this message
        return 1 if record.levelno < self.max_level else 0


def configure_logger(logger, base_level):
    # Have to set the root logger level, it defaults to logging.WARNING
    logger.setLevel(base_level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(filename)s:%(lineno)s - %(funcName)20s() %(levelname)s - %(message)s")

    logging_handler_out = logging.StreamHandler(sys.stdout)
    logging_handler_out.setLevel(base_level)
    logging_handler_out.setFormatter(formatter)
    logging_handler_out.addFilter(LessThanFilter(logging.ERROR))
    logger.addHandler(logging_handler_out)

    logging_handler_err = logging.StreamHandler(sys.stderr)
    logging_handler_err.setLevel(logging.ERROR)
    logging_handler_err.setFormatter(formatter)
    logger.addHandler(logging_handler_err)

    return logger


def configure_log(name=None):
    """
    Sets up logging for the given module. This creates a file handler and a console handler for the logger.
    :param name: The name for the logger
    :return: The logger
    """
    logger = configure_logger(logging.getLogger(name), logging.DEBUG)

    # demonstrate the logging levels
    logger.debug('DEBUG')
    logger.info('INFO')
    logger.warning('WARNING')
    logger.error('ERROR')
    logger.critical('CRITICAL')

    return logger
