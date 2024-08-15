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
    inline_keyboard=[
        [DnD_is_adventure_ok_yes_butt],
        [DnD_is_adventure_ok_no_butt]
    ]
)

roll_butt = InlineKeyboardButton(
    callback_data="roll",
    text=lexicon["roll_butt"]
)
roll_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [roll_butt]
    ]
)