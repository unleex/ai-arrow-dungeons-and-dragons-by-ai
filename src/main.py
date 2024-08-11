import asyncio

from config.config import config as configure

from aiogram import Bot, Dispatcher
from openai import OpenAI


async def main():
    config = configure()
    bot: Bot = config["bot"]
    dp: Dispatcher = config["dp"]
    openai_client: OpenAI = config["openai_client"]
    await bot.send_message(1547173190, "Hello world!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())