from lexicon.lexicon import LEXICON_RU

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import default_state
from aiogram.types import Message


lexicon = LEXICON_RU
rt = Router()


@rt.message(F.chat.type=="private", StateFilter(default_state))
async def not_in_group_handler(msg: Message):
    await msg.answer(lexicon["not_in_group"])