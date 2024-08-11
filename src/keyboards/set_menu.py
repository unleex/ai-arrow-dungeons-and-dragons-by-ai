from config.config import config 
from lexicon.lexicon import LEXICON_RU

from aiogram import Bot
from aiogram.types import BotCommand


lexicon = LEXICON_RU


async def set_main_menu():
    bot: Bot = config()["bot"]
    main_menu = [
        BotCommand(command="dnd",
                   description=lexicon["DnD_command_description"])
    ]
    await bot.set_my_commands(main_menu)