import asyncio
import logging
import logging.config

from config.config import bot, dp
from handlers import DnD_mission_handlers
from handlers import other_handlers
from handlers.DnD_init_handlers import DnD_init_adventure_handlers, players_init
from keyboards.set_menu import set_main_menu
from middlewares.middlewares import DataBaseAccessor


async def main():
    logging.basicConfig(level=logging.INFO)
    translate_syms_dict = {'*':'','_': '', '<': '', '>': '', '/': ''}
    dp['translate_dict'] = translate_syms_dict

    await set_main_menu()

    dp.include_router(other_handlers.rt)
    dp.include_router(DnD_mission_handlers.rt)
    dp.include_router(DnD_init_adventure_handlers.rt)
    dp.include_router(players_init.rt)
    dp.update.middleware(DataBaseAccessor())
    print("starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())