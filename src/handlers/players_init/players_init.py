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
async def DnD_generating_adventure(msg: Message, state: FSMStates, openai_client: OpenAI):
    MAX_TOKENS = 1000
    await msg.answer(lexicon["DnD_generating_adventure"])
    completion = openai_client.chat.completions.create(
        model="gpt-4",
        max_tokens=MAX_TOKENS,
        n=1,
        messages = [
            {"role": "user", "content": prompts["DnD_generating_adventure"] % msg.text}
        ]
    )
    await msg.answer(completion.choices[0].message)
    await state.set_state(FSMStates.creating_heroes)