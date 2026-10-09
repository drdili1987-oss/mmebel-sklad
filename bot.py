"""Kirish nuqtasi (Render: `python bot.py`)."""
import asyncio
import sys

from mmebel.server import main

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
