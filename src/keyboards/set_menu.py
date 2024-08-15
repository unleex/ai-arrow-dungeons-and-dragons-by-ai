from config.config import bot
from lexicon.lexicon import LEXICON_RU

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault


lexicon = LEXICON_RU


async def set_main_menu(chat_id: int | None = None):
    main_menu = [
        BotCommand(
            command="cancel",
            description=lexicon["cancel_command_description"]
        ),
        BotCommand(
            command="dnd",
            description=lexicon["DnD_command_description"]
        )
    ]
    await bot.set_my_commands(main_menu, BotCommandScopeChat(chat_id=chat_id) if chat_id else BotCommandScopeDefault())

async def set_game_menu(chat_id: int | None = None):
    game_menu = [
        BotCommand(
            command="action",
            description=lexicon["action_command_description"]
        ),
        BotCommand(
            command="master",
            description=lexicon["master_command_description"]
        )
    ]
    await bot.set_my_commands(game_menu, BotCommandScopeChat(chat_id=chat_id) if chat_id else BotCommandScopeDefault())