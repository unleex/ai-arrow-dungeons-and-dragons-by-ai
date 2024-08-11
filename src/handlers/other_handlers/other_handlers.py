from lexicon.lexicon import LEXICON_RU

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, any_state
from aiogram.types import Message


lexicon = LEXICON_RU
rt = Router()


@rt.message(F.chat.type=="private", StateFilter(default_state))
async def not_in_group_handler(msg: Message):
    await msg.answer(lexicon["not_in_group"])


@rt.message(Command("cancel"), StateFilter(any_state))
async def cancel_handler(msg: Message, state: FSMContext):
    await msg.answer(lexicon["cancel_handler"])
    await state.clear()