import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from keyboards.keyboards import DnD_is_adventure_ok_kb
from keyboards.set_menu import set_main_menu
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from prompts.functions import request_to_chatgpt, get_photo_from_chatgpt, tts
from states.states import FSMStates
from utils.utils import handle_image_errors, Preloader

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message


lexicon = LEXICON_RU
prompts = PROMPTS_RU
rt = Router()
MAX_TOKENS = 1000
AMOUNT_OF_TEXT_FOR_PICTURE_GEN = 800


@rt.message(Command("dnd"), StateFilter(default_state))
async def DnD_init_handler(msg: Message, state: FSMContext, chat_data: dict):
    await set_main_menu(msg.chat.id)
    chat_data["heroes"] = {}
    chat_data["lore"]  = ""
    chat_data["actions"] = []
    chat_data["experience_data"] = {}
    await msg.answer(lexicon["DnD_init"])
    await FSMStates.set_chat_state(str(msg.chat.id), FSMStates.waiting)
    await state.set_state(FSMStates.generating_adventure)


@rt.message(F.text, StateFilter(FSMStates.generating_adventure))
async def DnD_generating_adventure_handler(msg: Message, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return
    try:
        ctx.update({"topic": msg.text, "prompt_sent": True})
        await FSMStates.set_chat_data(msg.chat.id, ctx)

        await msg.answer(lexicon["DnD_generating_adventure"])

        preloader = Preloader(msg, steps=["lore", "voice", "image"])

        await preloader.update()
        result = request_to_chatgpt(prompts["DnD_generating_lore"] % ctx["topic"])

        await preloader.update()
        voice = tts(result, ambience_path="src/ambience/anxious.mp3")

        await preloader.update()
        prompt_for_photo = request_to_chatgpt(prompts["extract_prompt_for_photo"] % result)
        photo, error_code, violation_level = get_photo_from_chatgpt(content=prompt_for_photo)

        if not await handle_image_errors(msg, state, error_code, violation_level):
            return
        
        await preloader.update()

        await msg.answer_photo(photo)
        await msg.answer_voice(voice)
        await msg.answer(lexicon["DnD_is_adventure_ok"], reply_markup=DnD_is_adventure_ok_kb, resize_keyboard=False)
        await state.set_state(FSMStates.DnD_is_adventure_ok_choosing)
        chat_data["lore"] = result
    finally:
        await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": False})


@rt.callback_query(F.data=="DnD_is_adventure_ok_yes", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_yes_handler(clb: CallbackQuery, state: FSMContext):
    await clb.message.answer(lexicon['amount_of_players'])
    await state.set_state(FSMStates.getting_amount_of_players)



@rt.callback_query(F.data == "DnD_is_adventure_ok_no", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_no_handler(clb: CallbackQuery, state: FSMContext, translate_dict: dict, chat_data: dict):
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return # drop update if openai api call is already pending
    try:
        await FSMStates.set_chat_data(clb.message.chat.id, {"prompt_sent": True})
        await state.set_data(ctx)
        await clb.message.answer(lexicon["DnD_is_adventure_ok_no"])

        preloader = Preloader(clb.message, ["lore", "image", "tts"])

        await preloader.update()
        result = request_to_chatgpt(prompts["DnD_generating_lore"] % chat_data["lore"])

        await preloader.update()
        prompt_for_photo = request_to_chatgpt(prompts["extract_prompt_for_photo"] % result)
        photo, error_code, violation_level = get_photo_from_chatgpt(content=prompt_for_photo)

        if not await handle_image_errors(clb.message, state, error_code, violation_level):
            return

        await preloader.update()
        voice = tts(result, ambience_path="src/ambience/anxious.mp3")

        await clb.message.answer_photo(photo)
        await clb.message.answer_voice(voice)
        await clb.message.answer(
            lexicon["DnD_is_adventure_ok"],
            reply_markup=DnD_is_adventure_ok_kb,
            resize_keyboard=False
        )
    finally:
        await FSMStates.set_chat_data(clb.message.chat.id, {"prompt_sent": False})
        await state.set_data(ctx)