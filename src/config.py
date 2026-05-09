from dotenv import load_dotenv
import os

load_dotenv()


def _require(key: str) -> str:
    """
    Retrieve the value of a required environment variable.

    This function retrieves the value of the specified environment variable.
    If the environment variable is not set, an exception is raised.

    :param key: The name of the environment variable to retrieve.
    :type key: str
    :return: The value of the specified environment variable.
    :rtype: str
    :raises EnvironmentError: If the specified environment variable is not set.
    """

    value = os.getenv(key)

    if not value:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value


# Telegram
BOT_TOKEN = _require("BOT_TOKEN")
GROUP_CHAT_ID = int(_require("GROUP_CHAT_ID"))

# Database
DATABASE_URL = _require("DATABASE_URL")

# Configuration
VIDEO_STORAGE_PATH = os.getenv("VIDEO_STORAGE_PATH", "/mnt/videos")
VIDEOS_PER_DAY = int(os.getenv("VIDEOS_PER_DAY", 10))

GENERAL_TIMEOUT = int(os.getenv("GENERAL_TIMEOUT", 10000))

HEALTHCHECK_URL = os.getenv("HEALTHCHECK_URL", "")

# Cron
CRON_SCHEDULE = os.getenv("CRON_SCHEDULE", "0 9 * * *")
CRON_LOG_PATH = os.getenv("CRON_LOG_PATH", "logs")
