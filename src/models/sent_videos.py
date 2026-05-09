from sqlalchemy import Column, Integer, String, DateTime

from datetime import datetime

from src.models.base import Base


class SentVideos(Base):
    """
    Represents a record of videos that have been sent.

    This class is used to track videos that have been sent,
    including their file paths, corresponding Telegram file IDs,
    and timestamps indicating when they were sent.

    :ivar id: The unique identifier for the video that has been sent.
    :type id: Int
    :ivar file_path: The file path of the video that has been sent.
    :type file_path: Str
    :ivar telegram_file_id: The Telegram file ID associated with the video that has been sent.
    :type telegram_file_id: Str
    :ivar sent_at: The timestamp indicating when the video was sent.
    :type sent_at: Datetime
    """

    __tablename__ = "sent_videos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_path = Column(String, unique=True, nullable=False)
    telegram_file_id = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.now)
