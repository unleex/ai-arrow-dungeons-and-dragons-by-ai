from config.config import bot 
from lexicon.lexicon import LEXICON_RU

from aiogram import Bot
from aiogram.types import BotCommand


lexicon = LEXICON_RU


async def set_main_menu():
    main_menu = [
        BotCommand(command="cancel",
                   description=lexicon["cancel_command_description"]),
        BotCommand(command="dnd",
                   description=lexicon["DnD_command_description"])
    ]
    await bot.set_my_commands(main_menu)