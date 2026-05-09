# Telegram Bot Video Uploader

Automated Telegram bot that periodically scans a local directory for video files and sends unsent ones to a Telegram group. Tracks sent videos in a PostgreSQL database to avoid duplicates, and reports execution health to Healthchecks.io.

## Features

- Recursively scans a directory for video files (mp4, mkv, avi, mov)
- Skips already-sent videos using a PostgreSQL-backed deduplication log
- Sends up to a configurable number of videos per run
- Caches Telegram file IDs to avoid re-uploading previously sent files
- Retry logic with exponential backoff on send failures
- Healthchecks.io integration for monitoring cron execution
- Runs as a system cron job

## Requirements

- Python 3.13+
- PostgreSQL database
- [uv](https://github.com/astral-sh/uv) package manager

## Setup

**1. Clone and install dependencies**

```bash
git clone <repo-url>
cd TeleBot
uv sync
```

**2. Configure environment**

Copy `.env.example` to `.env` (or create `.env`) and fill in the required values:

```env
BOT_TOKEN=your_telegram_bot_token
GROUP_CHAT_ID=your_telegram_group_chat_id
DATABASE_URL=postgresql://user:password@localhost:5432/telebot

# Optional
VIDEO_STORAGE_PATH=/path/to/videos   # default: /mnt/videos
VIDEOS_PER_DAY=10                     # default: 10
GENERAL_TIMEOUT=10000                 # HTTP timeout in ms, default: 10000
CRON_SCHEDULE=0 9 * * *              # default: daily at 9 AM
HEALTHCHECK_URL=https://hc-ping.com/your-uuid
```

**3. Initialize the database**

```bash
uv run python scripts/init_db.py
```

**4. Install the cron job**

```bash
uv run python scripts/setup_cron.py
```

This installs a crontab entry that runs `main.py` on the configured schedule.

## Manual run

```bash
uv run python main.py
```

## Project structure

```
TeleBot/
├── main.py                  # Entry point
├── src/
│   ├── config.py            # Environment configuration
│   ├── logger.py            # Logging setup
│   ├── models/
│   │   ├── base.py          # SQLAlchemy engine and base
│   │   └── sent_videos.py   # SentVideos ORM model
│   └── services/
│       └── video_sender.py  # Core video scanning and sending logic
├── scripts/
│   ├── init_db.py           # Database table creation
│   └── setup_cron.py        # Cron job installer
└── logs/
    └── cron.log             # Execution logs
```

## Database schema

**`sent_videos`**

| Column             | Type     | Description                        |
|--------------------|----------|------------------------------------|
| id                 | Integer  | Primary key                        |
| file_path          | String   | Unique path to the video file      |
| telegram_file_id   | String   | Cached Telegram file ID            |
| sent_at            | DateTime | Timestamp of when video was sent   |
