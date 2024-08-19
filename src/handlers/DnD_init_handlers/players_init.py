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

    if str(msg.from_user.id) in chat_data['heroes']:
        await msg.answer(lexicon['already_in_db'].format(name=msg.from_user.first_name))
        return

    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    ctx["prompt_sent"] = True
    await state.set_data(ctx)



    #text
    preloader = await msg.answer(lexicon["extracting_hero_data"])
    preloader_text = preloader.text
    #TODO: add preloader like in adventure gen
    result = request_to_chatgpt(prompts["extract_hero_data"] % msg.text)


    #photo
    preloader = await preloader.edit_text(preloader_text.replace('...', ' ✅') + '\n' + lexicon["image_preloader"])
    preloader_text = preloader.text

    hero_image, error_code, violation_level = get_photo_from_chatgpt(
        content=result, target_path=f"src/hero_images/{msg.from_user.id}_hero.png")
    if violation_level != 2:
        if violation_level == 1:
            await msg.answer(lexicon["content_policy_violation_warning"])
        if error_code == 2:
            await msg.answer(lexicon["openai_error_warning"])
            await unblock_api_calls(msg, state)
            await FSMStates.clear_chat_state(msg.chat.id)
    else:
        await msg.answer(lexicon["content_policy_violation_warning"])
        await msg.answer(lexicon["content_policy_violation_retries_exhausted"])
        await unblock_api_calls(msg, state)
        return

    await preloader.edit_text(preloader_text.replace('...', ' ✅'))

    #TODO: add preloader like in adventure gen
    data = result[result.find('{'): result.rfind('}') + 1]
    hero_data = eval(data)
    hero_data["health"] = 100
    skills = ["Сила", "Ловкость" ,"Интеллект" , "Мудрость"]
    stats = [1] * 4
    skills_exp = [i + "_experience" for i in skills]
    exp = [0] * 4
    chat_data["experience_data"][str(msg.from_user.id)] = dict(zip(skills, stats)) | dict(zip(skills_exp, exp))
    chat_data['heroes'][str(msg.from_user.id)] = hero_data
    with open('src/db/chat_database.json', mode='w') as fp:
            json.dump(chat_data, fp, indent='\t')
    await msg.answer_photo(hero_image)


    # TODO: unnest
    if len(chat_data['heroes']) == ctx['number_of_players']:

        await msg.answer(lexicon['game_started'])
        preloader = await msg.answer(lexicon["generating_starting_location"])
        preloader_text = preloader.text
        await set_game_menu(msg.chat.id)

        data = request_to_chatgpt(prompts["DnD_init_location"] % chat_data["lore"])
#         data = """{
#   "location": "Крепость последних магов, расположенная в древнем лесу посреди таинственных топей.",
#   "explanation": "Вы находитесь в таинственном древнем лесу, где густые вековые деревья пронизаны таинственным шепотом. Перед вами возвышается крепость последних магов, огромная строение, вырубленное из прочного камня и украшенное золотыми драгоценностями. В глубине дворца, в одной из темных комнат, стоит таинственный шкаф, отдавая окружающую среду аурой чар и магической энергии. Это место, где вы будете разгадывать тайны древних свитков, изучать любопытные артефакты и подготавливаться к предстояющей войне с драконами."
# }"""
        data = data[data.find('{'): data.rfind('}') + 1]
        try:
            data = eval(data)
        except Exception as e:
            await unblock_api_calls(msg, state)
            print(e, data, sep='\n')
            return
        location = data["location"]
        explanation = data["explanation"]

        #photo
        preloader = await preloader.edit_text(preloader_text.replace('...', ' ✅') + '\n' + lexicon["image_preloader"])
        preloader_text = preloader.text

        photo, error_code, violation_level = get_photo_from_chatgpt(content=location)
        if violation_level != 2:
            if violation_level == 1:
                await msg.answer(lexicon["content_policy_violation_warning"])
            if error_code == 2:
                await msg.answer(lexicon["openai_error_warning"])
                await unblock_api_calls(msg, state)
                await FSMStates.clear_chat_state(msg.chat.id)
        else:
            await msg.answer(lexicon["content_policy_violation_warning"])
            await msg.answer(lexicon["content_policy_violation_retries_exhausted"])
            await unblock_api_calls(msg, state)
            return
        await preloader.edit_text(preloader_text.replace('...', ' ✅'))

        await msg.answer_photo(photo)
        await msg.answer_voice(tts(explanation, ambience_path="src/ambience/cheerful.mp3"))
        await msg.answer(lexicon["take_action"])
        await FSMStates.clear(msg.chat.id)
        await FSMStates.multiset_state(chat_data["heroes"], msg.chat.id, FSMStates.DnD_taking_action)
        for user_id in chat_data["heroes"]:
            chat_data["heroes"][user_id]["location"] = location
    else:
        await msg.answer(lexicon["wait_other_players"] % msg.from_user.first_name)
    ctx["prompt_sent"] = False
    await state.set_data(ctx)