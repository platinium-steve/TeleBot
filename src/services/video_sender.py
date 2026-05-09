import os
import glob
import asyncio

import httpx

from telegram import Bot, InputMediaVideo
from telegram.request import HTTPXRequest
from sqlalchemy.orm import Session as DBSession

from src.config import (
    BOT_TOKEN,
    GROUP_CHAT_ID,
    VIDEO_STORAGE_PATH,
    VIDEOS_PER_DAY,
    GENERAL_TIMEOUT,
    HEALTHCHECK_URL,
)
from src.models import SentVideos, SessionLocal
from src.logger import get_logger

VIDEO_FORMAT = ["*.mp4", "*.mkv", "*.avi", "*.mov"]
logger = get_logger(__name__)


class VideoSenderService:

    def __init__(self):
        """
        Initialize the class instance with required dependencies and configurations.

        Attributes:
            bot: Bot
                An instance of the bot initialized with the given bot token.
            db: DBSession
                A database session object for database operations.
        """

        self.bot = Bot(
            token=BOT_TOKEN,
            request=HTTPXRequest(
                connect_timeout=30,
                read_timeout=GENERAL_TIMEOUT,
                write_timeout=GENERAL_TIMEOUT,
                media_write_timeout=GENERAL_TIMEOUT,
            ),
        )
        self.db: DBSession = SessionLocal()

    # Healthcheck
    async def ping_healthcheck(self) -> None:
        """
        Performs an asynchronous ping to a health check endpoint.

        This method sends a GET request to the health check URL specified by the
        `HEALTHCHECK_URL` variable using an asynchronous HTTP client. If the
        `HEALTHCHECK_URL` is not set, the method exits without performing any operations.
        In case of a successful ping, a success message will be logged; otherwise,
        a warning is logged with the exception details.

        :return: None
        """

        if not HEALTHCHECK_URL:
            return
        try:
            async with httpx.AsyncClient() as client:
                await client.get(HEALTHCHECK_URL, timeout=10)

            logger.info("Healthcheck pinged successfully")
        except Exception as e:
            logger.warning(f"Healthcheck ping failed: {e}")

    # Database
    def get_sent_paths(self) -> set[str]:
        """
        Retrieves all the paths to sent files from the current system state.

        The function scans the relevant data sources and collects unique paths to files
        that have been marked or designated as sent, returning these paths as a set.

        :return: A set of strings representing the paths of sent files.
        :rtype: Set[str]
        """

        return {row.file_path for row in self.db.query(SentVideos).all()}

    def get_cached_file_id(self, path: str) -> str | None:
        """
        Retrieves the Telegram file ID for a given file path from the database cache.

        :param path: The file path to search in the database.
        :type path: Str
        :return: The Telegram file ID if found; otherwise, None.
        :rtype: Str | None
        """

        row = self.db.query(SentVideos).filter_by(file_path=path).first()

        return row.telegram_file_id if row else None

    def mark_as_sent(self, path: str, file_id: str | None) -> None:
        """
        Marks a video as sent by adding its details to the database.

        This method records the file path and optional Telegram file ID of a video that
        has been sent into the database. It ensures that the information about videos
        that have been sent is tracked persistently.

        :param path: The file path of the video that has been sent, including the file name.
        :param file_id: The Telegram file ID of the video that has been sent. This parameter is optional.
        :return: None
        """

        self.db.add(SentVideos(file_path=path, telegram_file_id=file_id))
        self.db.commit()

    # Storage
    def scan_video(self) -> list[str]:
        """
        Scans the video storage path recursively for video files with specified
        extensions and returns a sorted list of their file paths.

        The method searches for files matching predefined video extensions
        in the defined video storage directory and subdirectories. The search
        results are sorted alphabetically before being returned.

        :return: A sorted list of file paths representing the located video files.
        :rtype: List[str]
        """

        videos = []
        for ext in VIDEO_FORMAT:
            videos.extend(
                glob.glob(os.path.join(VIDEO_STORAGE_PATH, "**", ext), recursive=True)
            )

        return sorted(videos)

    def pick_unsent(self) -> list[str]:
        """
        Identify and return a list of unsent video files based on the available video
        files and the previously sent video paths. The function ensures that the
        returned list does not exceed the predefined limit.

        :return: A list of unsent video file paths, up to the specified daily limit.
        :rtype: List[str]
        """

        all_videos = self.scan_video()
        sent = self.get_sent_paths()
        unsent = [v for v in all_videos if v not in sent][:VIDEOS_PER_DAY]

        logger.info(f"Found {len(unsent)} unsent from {len(all_videos)} total")

        return unsent

    # Media
    def make_media_item(self, path: str, is_first: bool):
        """
        Creates a media item for uploading or retrieves it from the cache if available.

        Depending on whether the media item is already cached or not, this method either retrieves
        the cached identifier or opens the file for uploading. Additionally, assigns a caption of
        "Daily batch" if it's the first media item being processed.

        :param path: The file path of the media item to process.
        :type path: Str
        :param is_first: Indicates if this is the first media item in a batch and determines if a
            caption should be added.
        :type is_first: Bool
        :return: A tuple containing the `InputMediaVideo` object and either None (if cached) or a
            file handle (if opened for upload).
        :rtype: Tuple
        """

        cached_id = self.get_cached_file_id(path)

        if cached_id:
            logger.debug(f"Cached: {os.path.basename(path)}")

            return InputMediaVideo(media=cached_id), None

        logger.debug(f"Uploading: {os.path.basename(path)}")

        fh = open(path, "rb")

        return InputMediaVideo(media=fh), fh

    def build_media_group(self, videos: list[str]) -> tuple[list, list]:
        """
        Builds a media group and collects file handles from a list of video file paths.

        This method processes a list of video paths and creates corresponding media
        group items. It determines whether a file handle is necessary for each video
        and retains them accordingly.

        :param videos: List of video file paths to be processed.
        :type videos: List[str]
        :return: A tuple containing the media group and file handles. The media group
            is a list of media items, and the file handles is a list of the file
            handles required for the videos.
        :rtype: Tuple[list, list]
        """

        media_group, file_handles = [], []

        for i, path in enumerate(videos):
            item, fh = self.make_media_item(path, i == 0)
            media_group.append(item)

            if fh:
                file_handles.append(fh)

        return media_group, file_handles

    # Send
    async def send_group(self, videos: list[str], media_group: list) -> dict:
        """
        Sends a group of videos to a specified chat group one by one and maintains a cache
        of video file IDs for further use.

        :param videos: A list of file paths (strings) for the videos being sent.
        :param media_group: A list of media objects representing the videos and their
            respective captions to be sent as part of a media group.
        :return: A dictionary mapping the video file paths to their respective cached
            file IDs after being successfully sent.
        """

        logger.info(
            f"Sending {len(media_group)} videos one by one to group {GROUP_CHAT_ID}"
        )
        cached_ids = {}

        for i, (path, item) in enumerate(zip(videos, media_group)):
            try:
                msg = await self.bot.send_video(
                    GROUP_CHAT_ID,
                    item.media,
                    caption=item.caption,
                )

                if msg.video:
                    cached_ids[path] = msg.video.file_id

                logger.info(
                    f"Sent {i + 1}/{len(media_group)}: {os.path.basename(path)}"
                )

                await asyncio.sleep(2)
            except Exception as e:
                logger.warning(
                    f"Failed to send {os.path.basename(path)}: {e}. Skipping."
                )

        logger.info("All videos sent")
        return cached_ids

    async def send_single(self, video: str, media_item) -> dict:
        """
        Send a single video message using the send_video fallback.

        This method is used when only one video needs to be sent. It sends the video to
        a predefined group chat along with a caption.

        :param video: The identifier or reference string for the video being sent.
        :type video: Str
        :param media_item: A media object containing the video file or link to be sent.
        :return: A dictionary with the video identifier as the key and the file ID of
            the scent video as the value. If the message does not contain a video,
            an empty dictionary is returned.
        :rtype: Dict
        """

        logger.info("Only 1 video — using send_video fallback")

        for attempt in range(1, 4):
            try:
                msg = await self.bot.send_video(GROUP_CHAT_ID, media_item.media)

                return {video: msg.video.file_id} if msg.video else {}
            except Exception as e:
                logger.warning(f"Attempt {attempt}/3 failed: {e}")

                if attempt == 3:
                    raise

                await asyncio.sleep(5 * attempt)

    async def send_album(self, videos: list[str]) -> dict:
        """
        Sends an album consisting of multiple videos or a single video if only one is provided.

        This method determines whether to send a single video or a media group based on the
        number of videos in the provided list. For a single video, it delegates the processing
        to `send_single`. For multiple videos, it delegates to `send_group`. In either case,
        file handles are managed and closed after the operation.

        :param videos: A list of file paths or IDs representing the videos to be uploaded.
        :return: A dictionary containing metadata or result information of the sending
                 operation.
        :rtype: Dict
        """

        media_group, file_handles = self.build_media_group(videos)

        try:
            if len(media_group) == 1:
                return await self.send_single(videos[0], media_group[0])

            return await self.send_group(videos, media_group)
        finally:
            for fh in file_handles:
                fh.close()

    # Record
    def record_sent(self, videos: list[str], cached_ids: dict) -> None:
        """
        Marks videos as sent and logs the operation. The function updates
        the status of every video path from the provided list, optionally
        using associated cached IDs for processing. Once done, it logs the
        total number of videos marked as sent.

        :param videos: A list of file paths representing the videos to be
            marked as sent.
        :param cached_ids: A dictionary mapping video paths to their
            corresponding cached IDs. This is used to associate additional
            context for processing.
        :return: None
        """

        for path in videos:
            self.mark_as_sent(path, cached_ids.get(path))

        logger.info(f"Recorded {len(videos)} video(s) as sent")

    # Orchestrator
    async def run(self) -> None:
        """
        Executes the process of sending unsent videos in an asynchronous manner.

        This method handles the selection of unsent videos, sending them as an album,
        and recording their statuses in the system. If no unsent videos are available,
        a warning is logged. Proper error handling and resource cleanup are performed
        to ensure stability during the execution.

        :return: None
        :rtype: None
        :raises Exception: If any error occurs during the execution of the process.
        """

        try:
            videos = self.pick_unsent()

            if not videos:
                logger.warning("No unsent videos — add more files to storage")
                await self.ping_healthcheck()

                return

            cached_ids = await self.send_album(videos)
            self.record_sent(videos, cached_ids)

            logger.info(f"Done — {len(videos)} video(s) sent and recorded")

            await self.ping_healthcheck()
        except Exception:
            logger.exception("Send job failed")

            raise
        finally:
            self.db.close()
            await self.bot.shutdown()
