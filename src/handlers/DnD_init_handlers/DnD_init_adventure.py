from config.config import openai_client
from keyboards.keyboards import DnD_is_adventure_ok_kb
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message
from openai import OpenAI
from openai.types.chat import ChatCompletion


lexicon = LEXICON_RU
prompts = PROMPTS_RU
rt = Router()
MAX_TOKENS = 1000
N_CHOICES = 3


@rt.message(Command("dnd"), StateFilter(default_state))
async def DnD_init_handler(msg: Message, state: FSMContext):
    await msg.answer(lexicon["DnD_init"])
    await state.set_state(FSMStates.DnD_init)


@rt.message(StateFilter(FSMStates.DnD_init))
async def DnD_generating_adventure_handler(msg: Message, state: FSMContext):
    await msg.answer(lexicon["DnD_generating_adventure"])
    completion = openai_client.chat.completions.create(
        model="gpt-4",
        max_tokens=MAX_TOKENS,
        temperature=1,
        messages = [
            {"role": "user", "content": prompts["DnD_generating_adventure"] % msg.text}
        ]
    )
    await msg.answer(completion.choices[0].message.content.translate(
        {'*':'','_': '', '<': '', '>': '', '/': ''}
        )
    ) # translate to restrict model using markdown chars, avoiding bugs
    await msg.answer(lexicon["DnD_is_adventure_ok"],
                     reply_markup=DnD_is_adventure_ok_kb,
                     resize_keyboard=True)
    await state.set_state(FSMStates.DnD_is_adventure_ok_choosing)
    ctx = await state.get_data()
    ctx["adventure_topic"] = msg.text
    await state.set_data(ctx)


@rt.callback_query(F.data=="DnD_is_adventure_ok_yes", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_yes_handler(clb: CallbackQuery):
    ...


@rt.callback_query(F.data=="DnD_is_adventure_ok_no", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_no_handler(clb: CallbackQuery, state: FSMContext):
    await clb.message.answer(lexicon["DnD_is_adventure_ok_no"])
    ctx = await state.get_data()
    completion = openai_client.chat.completions.create(
        model="gpt-4",
        max_tokens=MAX_TOKENS,
        temperature=1,
        messages = [
            {"role": "user", "content": prompts["DnD_generating_adventure"] % ctx["adventure_topic"]}
        ]
    )
    await clb.message.answer(completion.choices[0].message.content.translate(
        {'*':'','_': '', '<': '', '>': '', '/': ''}
        )
    ) # translate to restrict model using markdown chars, avoiding bugs 