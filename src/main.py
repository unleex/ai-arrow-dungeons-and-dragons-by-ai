import asyncio

from config.config import config as configure
from handlers.other_handlers import other_handlers

from aiogram import Bot, Dispatcher
from openai import OpenAI


async def main():
    config = configure()
    bot: Bot = config["bot"]
    dp: Dispatcher = config["dp"]
    openai_client: OpenAI = config["openai_client"]

    dp.include_router(other_handlers.rt)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())