from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message
from openai import OpenAI


lexicon = LEXICON_RU
prompts = PROMPTS_RU
rt = Router()


@rt.message(StateFilter(FSMStates.getting_amount_of_players))
async def counting_players(msg: Message, state: FSMContext):
    if not msg.text.isdigit():
        await msg.answer(lexicon['amount_of_players'])
    else:
        await msg.answer(lexicon["DnD_init_players"])
        await state.set_state(FSMStates.creating_heroes)
        ctx = await state.get_data()
        ctx["number_of_players"] = msg.text
        await state.set_data(ctx)


@rt.message(StateFilter(FSMStates.creating_heroes))
async def get_descriptions(msg: Message, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()
    if msg.from_user.id in chat_data['heroes']:
        await msg.answer(lexicon['aleready_in_db'].format(name=msg.from_user.first_name))
        return
    chat_data['heroes'][str(msg.from_user.id)] = msg.text
    if len(chat_data['heroes']) == ctx['number_of_players']:
        await msg.answer(lexicon['game_started'])
        await state.set_state(FSMStates.DnD_game_started)
    else:
        await msg.answer(lexicon["wait_other_players"].format(name=msg.from_user.first_name))
