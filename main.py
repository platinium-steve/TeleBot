import asyncio

from src.services.video_sender import VideoSenderService


async def main() -> None:
    sender = VideoSenderService()

    await sender.bot.initialize()
    await sender.run()


if __name__ == "__main__":
    asyncio.run(main())
