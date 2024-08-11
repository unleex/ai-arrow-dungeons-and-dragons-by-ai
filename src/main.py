import asyncio

from config.config import config as configure
from handlers.other_handlers import other_handlers
from handlers.DnD_init_handlers import DnD_init_handlers
from keyboards.set_menu import set_main_menu

from aiogram import Bot, Dispatcher
from openai import OpenAI


async def main():
    config = configure()
    bot: Bot = config["bot"]
    dp: Dispatcher = config["dp"]
    openai_client: OpenAI = config["openai_client"]

    await set_main_menu()

    dp.include_router(DnD_init_handlers.rt)
    dp.include_router(other_handlers.rt)
    print("starting...")
    await dp.start_polling(bot, openai_client=openai_client)


if __name__ == "__main__":
    asyncio.run(main())