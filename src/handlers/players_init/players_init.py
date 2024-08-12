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


@rt.message(StateFilter(FSMStates.creating_heroes))
async def adding_player(msg: Message, state: FSMStates, openai_client: OpenAI):

    await msg.answer()