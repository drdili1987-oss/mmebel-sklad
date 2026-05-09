"""
MMebel Bot - Entry Point
Bu fayl faqat bot.py ni ishga tushirish uchun.
Asosiy kod bot.py da joylashgan.
"""
import asyncio
import sys

# bot.py dagi main funksiyani import qilamiz
from bot import main

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
