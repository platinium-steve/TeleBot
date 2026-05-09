import os
import logging

from src.config import CRON_LOG_PATH

os.makedirs(CRON_LOG_PATH, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"{CRON_LOG_PATH}/cron.log"),
    ],
)


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a logger instance by name. This function leverages the Python logging
    module to provide a configurable logger object, which can be used for
    managing log messages across different parts of the application. If a logger
    with the specified name already exists, it returns the existing instance.
    Otherwise, it creates and configures a new one.

    :param name: The name of the logger to retrieve.
    :type name: Str
    :return: A configured logger instance for handling application logging.
    :rtype: Logging.Logger
    """

    return logging.getLogger(name)
