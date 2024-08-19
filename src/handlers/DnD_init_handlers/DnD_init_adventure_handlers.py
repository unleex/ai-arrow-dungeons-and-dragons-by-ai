import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from keyboards.keyboards import DnD_is_adventure_ok_kb
from keyboards.set_menu import set_main_menu
from lexicon.lexicon import LEXICON_RU
from handlers.other_handlers import unblock_api_calls
from prompts.prompts import PROMPTS_RU
from prompts.functions import request_to_chatgpt, get_photo_from_chatgpt, tts
from states.states import FSMStates

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
    ctx.update({"prompt_sent": True, "topic": msg.text})
    await state.set_data(ctx)

    await msg.answer(lexicon["DnD_generating_adventure"])

    # Прелоадер и генерация текста
    preloader = await msg.answer(lexicon["text_preloader"])
    result = request_to_chatgpt(prompts["DnD_generating_lore"] % ctx["topic"])

    # Обновление прелоадера и генерация голосового сообщения
    preloader = await preloader.edit_text(f"{preloader.text.replace('...', ' ✅')}\n{lexicon['voice_preloader']}")
    voice = tts(result, ambience_path="src/ambience/anxious.mp3")

    # Обновление прелоадера и генерация изображения
    preloader = await preloader.edit_text(f"{preloader.text.replace('...', ' ✅')}\n{lexicon['image_preloader']}")
    prompt_for_photo = request_to_chatgpt(prompts["extract_prompt_for_photo"] % result)
    photo, error_code, violation_level = get_photo_from_chatgpt(content=prompt_for_photo)
    await preloader.edit_text(preloader.text.replace('...', ' ✅'))

    # Обработка ошибок изображения
    if violation_level == 2:
        await msg.answer(lexicon["content_policy_violation_warning"])
        await msg.answer(lexicon["content_policy_violation_retries_exhausted"])
    elif error_code == 2:
        await msg.answer(lexicon["openai_error_warning"])
    else:
        if violation_level == 1:
            await msg.answer(lexicon["content_policy_violation_warning"])
        await msg.answer_photo(photo)
        await msg.answer_voice(voice)

    # Финальное обновление прелоадера и завершение генерации

    await msg.answer(lexicon["DnD_is_adventure_ok"], reply_markup=DnD_is_adventure_ok_kb, resize_keyboard=False)
    await state.set_state(FSMStates.DnD_is_adventure_ok_choosing)
    chat_data["lore"] = result
    ctx["prompt_sent"] = False
    await state.set_data(ctx)


@rt.callback_query(F.data=="DnD_is_adventure_ok_yes", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_yes_handler(clb: CallbackQuery, state: FSMContext):
    await clb.message.answer(lexicon['amount_of_players'])
    await state.set_state(FSMStates.getting_amount_of_players)



@rt.callback_query(F.data == "DnD_is_adventure_ok_no", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_no_handler(clb: CallbackQuery, state: FSMContext, translate_dict: dict, chat_data: dict):
    ctx = await state.get_data()

    # Проверка на повторный запрос к GPT
    if ctx.get("prompt_sent", False):
        return  # предотвращает повторный запрос к GPT во время обработки
    ctx["prompt_sent"] = True
    await state.set_data(ctx)

    try:
        # Ответное сообщение пользователю
        await clb.message.answer(lexicon["DnD_is_adventure_ok_no"])

        # Генерация лора и перевод
        preloader = await clb.message.answer(lexicon["text_preloader"])
        result = await generate_and_translate_lore(chat_data["lore"], translate_dict)
        preloader = await update_preloader(preloader, lexicon["image_preloader"])

        # Генерация изображения и голоса
        prompt_for_photo = request_to_chatgpt(prompts["extract_prompt_for_photo"] % result)
        photo, error_code, violation_level = get_photo_from_chatgpt(content=prompt_for_photo)


        if not await handle_image_errors(clb.message, state, error_code, violation_level):
            print('ERROR ----------------------------------------------------------------------------------------')
            return

        preloader = await update_preloader(preloader, lexicon["voice_preloader"])
        voice = tts(result, ambience_path="src/ambience/anxious.mp3")
        preloader = await preloader.edit_text(preloader.text.replace('...', ' ✅'))


        # Отправка изображения, голоса и клавиатуры с выбором
        await clb.message.answer_photo(photo)
        await clb.message.answer_voice(voice)
        await clb.message.answer(
            lexicon["DnD_is_adventure_ok"],
            reply_markup=DnD_is_adventure_ok_kb,
            resize_keyboard=False
        )
    finally:
        # Сброс флага после завершения обработки
        ctx["prompt_sent"] = False
        await state.set_data(ctx)


async def generate_and_translate_lore(lore, translate_dict):
    """Генерирует лор и переводит его для предотвращения ошибок с Markdown."""
    result = request_to_chatgpt(prompts["DnD_generating_lore"] % lore)
    return result.translate(translate_dict)


async def handle_image_errors(message, state, error_code, violation_level):
    """Обрабатывает ошибки, связанные с изображением."""
    if violation_level != 2:
        if violation_level == 1:
            await message.answer(lexicon["content_policy_violation_warning"])
        if error_code == 2:
            await message.answer(lexicon["openai_error_warning"])
            await unblock_api_calls(message, state)
            await FSMStates.clear_chat_state(message.chat.id)
            return False
    else:
        await message.answer(lexicon["content_policy_violation_warning"])
        await message.answer(lexicon["content_policy_violation_retries_exhausted"])
        await unblock_api_calls(message, state)
        return False
    return True


async def update_preloader(preloader, next_step_text):
    """Обновляет текст прелоадера."""
    return await preloader.edit_text(preloader.text.replace('...', ' ✅') + '\n' + next_step_text)