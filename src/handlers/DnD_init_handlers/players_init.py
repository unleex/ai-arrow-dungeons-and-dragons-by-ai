from keyboards.set_menu import set_game_menu
from lexicon.lexicon import LEXICON_RU
from other_handlers import unblock_api_calls
from prompts.functions import request_to_chatgpt, tts, get_photo_from_chatgpt
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates

import os
import json

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


lexicon = LEXICON_RU
MAX_TOKENS = 500
prompts = PROMPTS_RU
rt = Router()


@rt.message(F.text, StateFilter(FSMStates.getting_amount_of_players))
async def counting_players(msg: Message, state: FSMContext):
    if not msg.text.strip().isdigit():
        await msg.answer(lexicon['amount_of_players_wrong_format'])
    else:
        await msg.answer(lexicon["DnD_init_players"])
        await set_game_menu(msg.chat.id)
        ctx = await state.get_data()
        ctx["number_of_players"] = int(msg.text.strip())
        await FSMStates.set_chat_data(msg.chat.id, ctx)
        await FSMStates.set_chat_state(msg.chat.id, FSMStates.creating_heroes)


@rt.message(F.text, StateFilter(FSMStates.creating_heroes))
async def get_descriptions(msg: Message, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()

    # Проверка на существование героя в базе данных
    if str(msg.from_user.id) in chat_data['heroes']:
        await msg.answer(lexicon['already_in_db'].format(name=msg.from_user.first_name))
        return

    # Проверка на повторный запрос к GPT
    if ctx.get("prompt_sent", False):
        return  # предотвращает повторный запрос к GPT во время обработки
    ctx["prompt_sent"] = True
    await state.set_data(ctx)

    # Запуск прелоадера
    preloader = await msg.answer(lexicon["extracting_hero_data"])

    try:
        # Получение данных героя от GPT
        result = request_to_chatgpt(prompts["extract_hero_data"] % msg.text)
        preloader = await update_preloader(preloader, lexicon["hero_image_preloader"])

        # Обработка изображения героя
        prompt_for_photo = request_to_chatgpt(prompts["extract_prompt_for_hero"] % result)
        hero_image, error_code, violation_level = get_photo_from_chatgpt(
            content=prompt_for_photo, target_path=f"src/hero_images/{msg.from_user.id}_hero.png"
        )
        if not await handle_image_errors(msg, state, error_code, violation_level):
            return

        # Отправка изображения героя
        await preloader.edit_text(preloader.text.replace('...', ' ✅'))
        hero_data = parse_hero_data(result)
        update_chat_data(chat_data, msg.from_user.id, hero_data)
        await msg.answer_photo(hero_image)

        # Проверка на готовность всех игроков
        if len(chat_data['heroes']) == ctx['number_of_players']:
            await start_game(msg, state, chat_data, ctx)
        else:
            await msg.answer(lexicon["wait_other_players"] % msg.from_user.first_name)
    finally:
        # Сброс флага после завершения обработки
        ctx["prompt_sent"] = False
        await state.set_data(ctx)


async def update_preloader(preloader, next_step_text):
    """Обновляет текст прелоадера."""
    return await preloader.edit_text(preloader.text.replace('...', ' ✅') + '\n' + next_step_text)


def parse_hero_data(result):
    """Извлекает и формирует данные героя из ответа GPT."""
    data = result[result.find('{'): result.rfind('}') + 1]
    hero_data = eval(data)
    hero_data["health"] = 100
    return hero_data


def update_chat_data(chat_data, user_id, hero_data):
    """Обновляет данные чата с новым героем."""
    skills = ["Сила", "Ловкость", "Интеллект", "Мудрость"]
    stats = [1] * 4
    skills_exp = [f"{i}_experience" for i in skills]
    exp = [0] * 4

    chat_data["experience_data"][str(user_id)] = dict(zip(skills, stats)) | dict(zip(skills_exp, exp))
    chat_data['heroes'][str(user_id)] = hero_data


async def handle_image_errors(msg, state, error_code, violation_level):
    """Обрабатывает ошибки, связанные с изображением."""
    if violation_level != 2:
        if violation_level == 1:
            await msg.answer(lexicon["content_policy_violation_warning"])
        if error_code == 2:
            await msg.answer(lexicon["openai_error_warning"])
            await unblock_api_calls(msg, state)
            await FSMStates.clear_chat_state(msg.chat.id)
            return False
    else:
        await msg.answer(lexicon["content_policy_violation_warning"])
        await msg.answer(lexicon["content_policy_violation_retries_exhausted"])
        await unblock_api_calls(msg, state)
        return False
    return True


async def start_game(msg, state, chat_data, ctx):
    """Запускает игру после того, как все игроки готовы."""
    await msg.answer(lexicon['game_started'])
    preloader = await msg.answer(lexicon["generating_starting_location"])
    await set_game_menu(msg.chat.id)

    # Получение и обработка начальной локации
    data = request_to_chatgpt(prompts["DnD_init_location"] % chat_data["lore"])
    data = data[data.find('{'): data.rfind('}') + 1]
    try:
        data = eval(data)
    except Exception as e:
        await unblock_api_calls(msg, state)
        print(e, data, sep='\n')
        return

    location, explanation = data["location"], data["explanation"]

    # Обработка изображения локации

    preloader = await update_preloader(preloader, lexicon["image_preloader"])
    prompt_for_photo = request_to_chatgpt(content=prompts["extract_prompt_for_photo"] % explanation)
    photo, error_code, violation_level = get_photo_from_chatgpt(content=prompt_for_photo)
    if not await handle_image_errors(msg, state, error_code, violation_level):
        return

    # Отправка данных о локации
    await preloader.edit_text(preloader.text.replace('...', ' ✅'))
    await msg.answer_photo(photo)
    await msg.answer_voice(tts(explanation, ambience_path="src/ambience/cheerful.mp3"))
    await msg.answer(lexicon["take_action"])

    # Обновление состояний и начало игрового процесса
    await FSMStates.clear(msg.chat.id)
    await FSMStates.multiset_state(chat_data["heroes"], msg.chat.id, FSMStates.DnD_taking_action)
    for user_id in chat_data["heroes"]:
        chat_data["heroes"][user_id]["location"] = location