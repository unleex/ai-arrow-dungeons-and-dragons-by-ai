from config.config import bot, BOT_USERNAME
from keyboards.keyboards import roll_kb
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from prompts.functions import (request_to_chatgpt, process_action, 
                               finish_action, ACTION_RELEVANCE_FOR_MISSION)
from states.states import FSMStates

from random import randint

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
import asyncio


rt = Router()
MAX_TOKENS = 1000
NEW_MISSION_CHANCE = 0.2
lexicon = LEXICON_RU
prompts = PROMPTS_RU
ROLLING_SLEEP_TIME = 3


@rt.message(StateFilter(FSMStates.DnD_default_state))
async def maybe_generate_mission(msg: Message, translate_dict: dict, chat_data: dict):
    if randint(0,100) / 100 < NEW_MISSION_CHANCE:
        result = request_to_chatgpt(content=prompts["DnD_generating_adventure"].format(
                adventure=chat_data["lore"],
                recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]),
                location="random location"))
    await msg.answer(result.translate(translate_dict)) # translate to restrict model using markdown chars, avoiding bugs
    await FSMStates.multiset_state(chat_data["heroes"], msg.chat.id, FSMStates.DnD_taking_action)
    await msg.answer(lexicon["take_action"])


@rt.message(Command("action"), StateFilter(FSMStates.DnD_taking_action))
async def taking_action(msg: Message, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    topic = msg.text.replace("/action", '').replace(BOT_USERNAME,'')
    if not topic.replace(' ',''):
        await msg.answer(lexicon["action_empty"])   
        await state.set_state(FSMStates.DnD_adding_action)
        return
    ctx["prompt_sent"] = True   
    await state.set_data(ctx)
    await msg.answer(lexicon["master_answering"] % chat_data["heroes"][str(msg.from_user.id)]["name"])
    check_type = request_to_chatgpt(content=prompts["action_is_roll_required"].format(
                action=topic,
                recent_actions='\n'.join(
                    chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
                    ),
                hero_data=chat_data["heroes"][str(msg.from_user.id)]
                )
    )
    ctx["prompt_sent"] = False   
    await state.set_data(ctx)
    ctx = await state.get_data()
    ctx["user_msg_id"] = msg.from_user.id
    ctx["topic"] = topic
    if check_type[:2] == "-1":
        invalidation_reason = check_type[2:]
        await msg.answer(invalidation_reason)
        chat_data["actions"].append(topic)
        chat_data["actions"].append(invalidation_reason)
        await finish_action(topic, chat_data, msg, state, msg.from_user.id)
        return
    elif check_type[0] == "0":
        ctx["roll_result"] = 20
    else:
        await msg.answer(lexicon["roll"] % check_type, 
                        reply_markup=roll_kb,
                        resize_keyboard=True
        )
        await state.set_data(ctx)
        await state.set_state(FSMStates.rolling)
        return   
    ctx["topic"] = topic
    print(check_type)
    await state.set_data(ctx)
    await process_action(topic, chat_data, msg, state, user_id=msg.from_user.id)
    ctx = await state.get_data()
    ctx["prompt_sent"] = False
    await state.set_data(ctx)


@rt.message(StateFilter(FSMStates.DnD_adding_action))
async def adding_action(msg: Message, state: FSMContext, chat_data: dict):
    await taking_action(msg, state, chat_data)


@rt.callback_query(F.data=="roll", StateFilter(FSMStates.rolling))
async def rolling(clb: CallbackQuery, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    ctx["prompt_sent"] = True
    await state.set_data(ctx)
    sent_msg = await clb.message.answer(lexicon["rolling"])
    result = randint(1, 20)
    await asyncio.sleep(ROLLING_SLEEP_TIME)
    await sent_msg.edit_text(str(result))
    ctx = await state.get_data()
    topic = ctx["topic"]
    ctx["roll_result"] = result
    user_msg_id = ctx["user_msg_id"]
    await state.set_data(ctx)
    await process_action(topic, chat_data, clb.message, state, user_id=user_msg_id)
    ctx["prompt_sent"] = False
    await state.set_data(ctx)


@rt.message(Command("master"), StateFilter(FSMStates.DnD_taking_action, FSMStates.DnD_took_action))
async def master(msg: Message, state: FSMContext, chat_data: dict):
    if str(msg.from_user.id) not in chat_data["heroes"]:
        return
    ctx = await state.get_data()
    ctx["state_before_master"] = await state.get_state()    
    ctx["prompt_sent"] = False
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing

    topic = msg.text.replace("/master", '').replace(BOT_USERNAME,'')
    if not topic.replace(' ',''):
        await msg.answer(lexicon["master_empty"] % chat_data["heroes"][str(msg.from_user.id)]["name"])
        await state.set_state(FSMStates.DnD_adding_master)
        await state.set_data(ctx)
        return
    ctx["prompt_sent"] = True
    await state.set_data(ctx)
    await msg.answer(lexicon["master_answering"] % chat_data["heroes"][str(msg.from_user.id)]["name"])
    result = request_to_chatgpt(content=prompts["DnD_master"].format(
                phrase=msg.text,
                recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]),
                hero_data=chat_data["heroes"][str(msg.from_user.id)])
    )
    ctx["prompt_sent"] = False
    await msg.answer(result)
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)
    await state.set_data(ctx)

@rt.message(StateFilter(FSMStates.DnD_adding_master))
async def adding_master(msg: Message, state: FSMContext, chat_data: dict):
    await msg.answer("срабатывает драный adding_master")
    ctx = await state.get_data()
    await state.set_state(eval(ctx["state_before_master"].replace(':','.'))) # avoid infinte cycle
    await master(msg, state, chat_data)


@rt.message(Command("action"), StateFilter(FSMStates.DnD_took_action))
async def already_took_action(msg: Message, chat_data: dict):   
    await msg.answer(lexicon["already_took_action"] % chat_data["heroes"][str(msg.from_user.id)]["name"])