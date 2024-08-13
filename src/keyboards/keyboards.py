import json

from aiogram.methods.get_chat_member import GetChatMember
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config.config import bot
from lexicon.lexicon import LEXICON_RU

lexicon = LEXICON_RU


DnD_is_adventure_ok_yes_butt = InlineKeyboardButton(
    callback_data="DnD_is_adventure_ok_yes",
    text=lexicon["DnD_is_adventure_ok_yes_butt"]
)
DnD_is_adventure_ok_no_butt = InlineKeyboardButton(
    callback_data="DnD_is_adventure_ok_no",
    text=lexicon["DnD_is_adventure_ok_no_butt"]
)
DnD_is_adventure_ok_kb = InlineKeyboardMarkup(
    inline_keyboard= [
        [DnD_is_adventure_ok_yes_butt],
        [DnD_is_adventure_ok_no_butt]
    ]
)