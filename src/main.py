import asyncio

from config.config import bot, dp, openai_client
from handlers.other_handlers import other_handlers
from handlers.DnD_init_handlers import DnD_init_adventure
from keyboards.set_menu import set_main_menu


async def main():
    await set_main_menu()
    dp.include_router(DnD_init_adventure.rt)
    dp.include_router(other_handlers.rt)
    print("starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, openai_client=openai_client)


if __name__ == "__main__":
    asyncio.run(main())