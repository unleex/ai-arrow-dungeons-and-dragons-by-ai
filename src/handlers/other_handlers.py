from keyboards.set_menu import set_main_menu
from lexicon.lexicon import LEXICON_RU
from states.states import FSMStates

from aiogram import F, Router
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
async def cancel_handler(msg: Message):
    await msg.answer(lexicon["cancel_handler"])
    await FSMStates.clear_chat_data(msg.chat.id)
    await FSMStates.clear_chat_state(msg.chat.id)
    await set_main_menu(msg.chat.id)


@rt.message(Command("set_state"))
async def set_state(msg: Message, state: FSMContext):
    st = msg.text.replace('/set_state', '').strip()
    await msg.answer(f"setting state {st}")
    await state.set_state(eval(f"FSMStates.{st}"))
    print(f"new state: {await state.get_state()}")


@rt.message(Command("get_states"))
async def get_states(msg: Message):
    states = await FSMStates.get_chat_states(msg.chat.id)
    await msg.answer(str(states))


@rt.message(Command("unlock"))
async def unblock_api_calls(msg: Message, state: FSMContext):
    ctx = await state.get_data()
    ctx["prompt_sent"] = False
    await state.set_data(ctx)
    await msg.answer(lexicon["unblocked_api_calls"])

@rt.message(Command("help"))
async def get_help(msg: Message):
    await msg.answer(lexicon['help_command'])