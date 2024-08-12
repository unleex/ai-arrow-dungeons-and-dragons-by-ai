import asyncio

from config.config import config as configure
from handlers.other_handlers import other_handlers
from handlers.DnD_init_handlers import DnD_init_handlers
from handlers.DnD_init_handlers import players_init
from keyboards.set_menu import set_main_menu
from middlewares.middlewares import DataBaseAccessor

from aiogram import Bot, Dispatcher
from openai import OpenAI


async def main():
    config = configure()
    bot: Bot = config["bot"]
    dp: Dispatcher = config["dp"]
    openai_client: OpenAI = config["openai_client"]
    translate_syms_dict = {'*':'','_': '', '<': '', '>': '', '/': ''}
    dp['translate_dict'] = translate_syms_dict

    await set_main_menu()

    dp.include_router(DnD_init_handlers.rt)
    dp.include_router(other_handlers.rt)
    dp.include_router(players_init.rt)
    dp.update.middleware(DataBaseAccessor())
    print("starting...")
    await dp.start_polling(bot, openai_client=openai_client)


if __name__ == "__main__":
    asyncio.run(main())