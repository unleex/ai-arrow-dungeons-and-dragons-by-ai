import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.config import bot, BOT_USERNAME, openai_client
from keyboards.keyboards import roll_kb
from lexicon.lexicon import LEXICON_RU, STATS_RU
from prompts.prompts import PROMPTS_RU
from prompts.functions import (request_to_chatgpt, process_action,tts,
                               finish_action, ACTION_RELEVANCE_FOR_MISSION)
from states.states import FSMStates

from copy import deepcopy
import logging
from random import randint

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, FSInputFile
import asyncio


logger = logging.getLogger(__name__)
rt = Router()
MAX_TOKENS = 1000
NEW_MISSION_CHANCE = 0.2
lexicon: dict[str, str] = LEXICON_RU
stats_lexicon = STATS_RU
prompts = PROMPTS_RU
ROLLING_SLEEP_TIME = 3
reqs = [10]
for i in range(18):
    reqs.append(int(reqs[-1] * 1.2))
required_experience = dict(zip(range(20), reqs + [float("inf")])) # in every level it is 10, 21+ level is unreachable
print(required_experience)

@rt.message(Command("action"), StateFilter(FSMStates.DnD_taking_action))
async def taking_action(msg: Message, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    try:
        await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": True})
        if "user_msg_id" in ctx:
            user_msg_id = str(ctx["user_msg_id"])
            del ctx["user_msg_id"]
            logger.info(f"found user msg id in ctx: {user_msg_id}")
        else:
            user_msg_id = str(msg.from_user.id)
        if "transcripted" in ctx:
            topic = ctx["transcripted"]
            del ctx["transcripted"]
        else:
            topic = msg.text
        transcription_addon = lexicon["transcripted"].replace("%s", '')
        topic = topic.replace("/action", '').replace(BOT_USERNAME,'').replace(transcription_addon, '')
        if not topic.replace(' ',''):
            await msg.answer(lexicon["action_empty"])   
            await state.set_state(FSMStates.DnD_adding_action)
            return
        await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": True})
        logger.info(f"checking skill type {user_msg_id}")
        await msg.answer(lexicon["master_answering"] % chat_data["heroes"][user_msg_id]["name"])
        check_type = request_to_chatgpt(prompts["action_is_roll_required"].format(
                    action=topic,
                    recent_actions='\n'.join(
                        chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
                        ),
                    hero_data=chat_data["heroes"][user_msg_id])
        )
        await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": False})
        await state.set_data(ctx)
        ctx["user_msg_id"] = user_msg_id
        ctx["topic"] = topic
        if check_type[:2] == "-1":
            invalidation_reason = check_type[2:]
            voice = tts(invalidation_reason)
            await msg.answer_voice(voice)
            chat_data["actions"].append(topic)
            chat_data["actions"].append(invalidation_reason)
            await finish_action(topic, chat_data, msg, state, user_msg_id)
            return
        elif check_type[0] == "0":
            ctx["roll_result"] = 20
        else:
            ctx["check_type"] = check_type
            await msg.answer(lexicon["roll"] % check_type,
                            reply_markup=roll_kb,
                            resize_keyboard=False
            )
            await state.set_data(ctx)
            await state.set_state(FSMStates.rolling)
            return
        await state.set_data(ctx)
        await process_action(topic, chat_data, msg, state, user_id=msg.from_user.id)
    finally:
        await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": False})


@rt.message(F.text | F.voice, StateFilter(FSMStates.DnD_adding_action))
async def adding_action(msg: Message, state: FSMContext, chat_data: dict):
    if msg.voice:
        target_path = "src/audios_for_stt/audio.wav"
        await bot.download(msg.voice, target_path)
        audio_file = open(target_path, "rb")
        transcript = openai_client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1"
        )   
        await msg.answer(lexicon["transcripted"] % transcript.text)
        ctx = await state.get_data()
        ctx["user_msg_id"] = msg.from_user.id
        ctx["transcripted"] = transcript.text
        await state.set_data(ctx)
    await taking_action(msg, state, chat_data)


@rt.callback_query(F.data=="roll", StateFilter(FSMStates.rolling))
async def rolling(clb: CallbackQuery, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()
    check_type = ctx["check_type"]
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    await FSMStates.set_chat_data(clb.message.chat.id, {"prompt_sent": True})
    await state.set_data(ctx)
    level = int(request_to_chatgpt(
        prompts["action_gained_experience_amount"] % ctx["topic"]
    ))
    await state.set_data(ctx)
    sent_msg = await clb.message.answer(lexicon["rolling"])
    roll = randint(1, 20)
    await asyncio.sleep(ROLLING_SLEEP_TIME)
    user_msg_id = ctx["user_msg_id"]
    mastery = chat_data["experience_data"][user_msg_id][check_type]
    result = roll - level + mastery
    await sent_msg.edit_text(lexicon["roll_result"].format(
        roll=roll,
        result=result, 
        level=level,
        mastery=mastery,
        mastery_type=check_type
        ))
    gained_experience = level
    hero_experience = chat_data["experience_data"][user_msg_id][check_type + "_experience"]
    exp_required = required_experience[mastery]
    levels_gained, new_exp = divmod(hero_experience + gained_experience, exp_required)
    chat_data["experience_data"][user_msg_id][check_type] += levels_gained
    chat_data["experience_data"][user_msg_id][check_type + "_experience"] = new_exp
    if levels_gained:
        upgrade_message = lexicon["levelup_message"].format(check_type, chat_data["experience_data"][user_msg_id][check_type])
    else:
        upgrade_message = lexicon["experience_gain_message"].format(skill=check_type,
                                                                    gained_experience=gained_experience,
                                                                    left_to_new_level=(exp_required-new_exp))
    ctx["upgrade_message"] = upgrade_message
    await FSMStates.set_chat_data(clb.message.chat.id, {"prompt_sent": False})
    topic = ctx["topic"]
    ctx["roll_result"] = result
    ctx["level"] = level
    await state.set_data(ctx)
    await process_action(topic, chat_data, clb.message, state, user_id=user_msg_id)
    await FSMStates.set_chat_data(clb.message.chat.id, {"prompt_sent": False})
    await state.set_data(ctx)


@rt.message(Command("master"), StateFilter(FSMStates.DnD_taking_action, FSMStates.DnD_took_action))
async def master(msg: Message, state: FSMContext, chat_data: dict):
    if str(msg.from_user.id) not in chat_data["heroes"]:
        return
    ctx = await state.get_data()
    ctx["state_before_master"] = await state.get_state()
    await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": False})
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    if "user_msg_id" in ctx:
        user_msg_id = str(ctx["user_msg_id"])
        del ctx["user_msg_id"]
    else:
        user_msg_id = str(msg.from_user.id)
    if "transcripted" in ctx:
        topic = ctx["transcripted"]
        del ctx["transcripted"]
    else:
        topic = msg.text
    transcription_addon = lexicon["transcripted"].replace("%s", '')
    topic = topic.replace("/master", '').replace(BOT_USERNAME,'').replace(transcription_addon, '')
    if not topic.replace(' ',''):
        await msg.answer(lexicon["master_empty"] % chat_data["heroes"][user_msg_id]["name"])
        await state.set_state(FSMStates.DnD_adding_master)
        await state.set_data(ctx)
        return
    await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": True})
    await state.set_data(ctx)
    await msg.answer(lexicon["master_answering"] % chat_data["heroes"][user_msg_id]["name"])
    result = request_to_chatgpt(prompts["DnD_master"].format(
                phrase=msg.text,
                recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]),
                hero_data=chat_data["heroes"][user_msg_id])              
    )
    await FSMStates.set_chat_data(msg.chat.id, {"prompt_sent": False})
    await msg.answer(result)
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)
    await state.set_data(ctx)

@rt.message(F.text | F.voice, StateFilter(FSMStates.DnD_adding_master))
async def adding_master(msg: Message, state: FSMContext, chat_data: dict):
    if msg.voice:
        target_path = "src/audios_for_stt/audio.wav"
        await bot.download(msg.voice, target_path)
        audio_file = open(target_path, "rb")
        transcript = openai_client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1"
        )   
        await msg.answer(lexicon["transcripted"] % transcript.text)
        ctx = await state.get_data()
        ctx["user_msg_id"] = msg.from_user.id
        ctx["transcripted"] = transcript.text
        await state.set_data(ctx)
    ctx = await state.get_data()
    await state.set_state(eval(ctx["state_before_master"].replace(':','.'))) # avoid infinte cycle
    await master(msg, state, chat_data)


@rt.message(Command("action"), StateFilter(FSMStates.DnD_took_action))
async def already_took_action(msg: Message, chat_data: dict):
    await msg.answer(lexicon["already_took_action"] % chat_data["heroes"][str(msg.from_user.id)]["name"])


@rt.message(Command("stats"), StateFilter(FSMStates.DnD_taking_action, FSMStates.DnD_took_action))
async def stats(msg: Message, chat_data: dict):
    copied = deepcopy(chat_data)
    data: dict = copied["heroes"][str(msg.from_user.id)]
    # avoid bugs if gpt somehow removed the keys
    data.pop("background", None)
    data.pop("backstory", None)
    data.pop("appearance", None)
    data.pop("health_diff", None)
    name = data.pop("name", "")
    str_data = '-' * 5 + name + '-' * 5 + '\n'
    data = data | copied["experience_data"][str(msg.from_user.id)] 
    data.pop("Сила_experience", None)
    data.pop("Ловкость_experience", None)
    data.pop("Интеллект_experience", None)
    data.pop("Мудрость_experience", None) 
    str_data += '\n'.join(f"{stats_lexicon.get(key, key)}: {value}" # default cuz no time to debug
                          for key, value in data.items()) 
    photo_path = f"src/hero_images/{msg.from_user.id}_hero.png"
    photo = FSInputFile(photo_path)
    await msg.answer_photo(photo, caption=str_data)