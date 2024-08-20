from keyboards.set_menu import set_game_menu
from lexicon.lexicon import LEXICON_RU
from other_handlers import unblock_api_calls
from prompts.functions import request_to_chatgpt, tts, get_photo_from_chatgpt
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates
from utils.utils import *

import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


lexicon = LEXICON_RU
MAX_TOKENS = 500
prompts = PROMPTS_RU
logger = logging.getLogger(__name__)
rt = Router()


@rt.message(F.text, StateFilter(FSMStates.getting_amount_of_players))
async def counting_players(msg: Message, state: FSMContext):
    if not msg.text.strip().isdigit():
        await msg.answer(lexicon['amount_of_players_wrong_format'])
        logger.info(f"invalid player amount: {msg.text.strip()}")
    else:
        logger.info(f"creating heroes for {msg.text.strip()} players")
        await msg.answer(lexicon["DnD_init_players"])
        await set_game_menu(msg.chat.id)
        ctx = await state.get_data()
        ctx["number_of_players"] = int(msg.text.strip())
        await FSMStates.set_chat_data(msg.chat.id, ctx)
        await FSMStates.set_chat_state(msg.chat.id, FSMStates.creating_heroes)


@rt.message(F.text, StateFilter(FSMStates.creating_heroes))
async def get_descriptions(msg: Message, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()

    if str(msg.from_user.id) in chat_data['heroes']:
        await msg.answer(lexicon['already_in_db'].format(name=msg.from_user.first_name))
        logger.info(f"{str(msg.from_user.id)} ALREADY IN DATABASE:\n {chat_data["heroes"][str(msg.from_user.id)]}")
        return

    if ctx.get("prompt_sent", False):
        logger.info(f"{msg.text} BLOCKED")
        return
    await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": True})
    print(await state.get_data())

    try:
        preloader = await msg.answer(lexicon["extracting_hero_data"])
        result = request_to_chatgpt(prompts["extract_hero_data"] % msg.text)
        hero_data = parse_hero_data(result)
        if not hero_data:
            await msg.answer(lexicon["invalid_hero_data"])
            logger.info(f"{lexicon["invalid_hero_data"]}: {msg.text}")
            return
        
        preloader = await update_preloader(preloader, lexicon["hero_image_preloader"])
        hero_image, error_code, violation_level = get_photo_from_chatgpt(
            content=result, target_path=f"src/hero_images/{msg.from_user.id}_hero.png"
        )
        if not await handle_image_errors(msg, state, error_code, violation_level):
            return

        await preloader.edit_text(preloader.text.replace('...', ' ✅'))
        update_chat_data(chat_data, msg.from_user.id, hero_data)
        await msg.answer_photo(hero_image)

        if len(chat_data['heroes']) == ctx['number_of_players']:
            logger.info("all heroes done")
            await start_game(msg, chat_data, state)
        else:
            await msg.answer(lexicon["wait_other_players"] % msg.from_user.first_name)
    finally:
        await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": False})
        await state.set_data(ctx)


async def start_game(msg: Message, chat_data, state: FSMContext):
    try:
        await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": True})

        await msg.answer(lexicon['game_started'])
        preloader = await msg.answer(lexicon["generating_starting_location"])
        await set_game_menu(msg.chat.id)

        data = request_to_chatgpt(prompts["DnD_init_location"] % chat_data["lore"])
        data = data[data.find('{'): data.rfind('}') + 1]
        try:
            data = eval(data)
        except Exception as e:
            await unblock_api_calls(msg, state)
            print(e, data, sep='\n')
            return

        location, explanation = data["location"], data["explanation"]

        preloader = await update_preloader(preloader, lexicon["image_preloader"])
        photo, error_code, violation_level = get_photo_from_chatgpt(content=location)
        if not await handle_image_errors(msg, state, error_code, violation_level):
            return

        await preloader.edit_text(preloader.text.replace('...', ' ✅'))
        await msg.answer_photo(photo)
        await msg.answer_voice(tts(explanation, ambience_path="src/ambience/cheerful.mp3"))
        await msg.answer(lexicon["take_action"])

        await FSMStates.clear_chat(msg.chat.id)
        await FSMStates.multiset_state(chat_data["heroes"], msg.chat.id, FSMStates.DnD_taking_action)
        for user_id in chat_data["heroes"]:
            chat_data["heroes"][user_id]["location"] = location
    finally:
        await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": True})