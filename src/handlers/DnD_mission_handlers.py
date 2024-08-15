from config.config import bot, BOT_USERNAME
from keyboards.keyboards import roll_kb
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from prompts.functions import request_to_chatgpt
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
ACTION_RELEVANCE_FOR_MISSION = 10
lexicon = LEXICON_RU
prompts = PROMPTS_RU
ROLLING_SLEEP_TIME = 3


@rt.message(StateFilter(FSMStates.DnD_default_state))
async def maybe_generate_mission(msg: Message, state: FSMContext, translate_dict: dict, chat_data: dict):
    if randint(0,100) / 100 < NEW_MISSION_CHANCE:
        result = request_to_chatgpt(content=prompts["DnD_generating_adventure"].format(
                adventure=chat_data["lore"],
                recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]),
                location="random location"))
    await msg.answer(result.translate(translate_dict)) # translate to restrict model using markdown chars, avoiding bugs
    await FSMStates.multiset_state(chat_data["heroes"], msg.chat.id, FSMStates.DnD_taking_action)
    await msg.answer(lexicon["take_action"])


async def process_action(topic, chat_data: dict, msg: Message, state: FSMContext, user_id=None):
    if not user_id:
        user_id = msg.from_user.id
    user_id = str(user_id)
    print("finally", user_id)
    ctx = await state.get_data()
    result = request_to_chatgpt(content=prompts["DnD_taking_action"].format(
            action=topic,
            recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
                ),
            hero_data=chat_data["heroes"][user_id],
            successful=ctx["roll_result"])
    )
    await msg.answer(result)
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)
    updated = request_to_chatgpt(content=prompts["update_after_action"].format(
        action=topic, 
        hero_data=chat_data["heroes"][user_id],
        recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
                ),
        )
    )
    data = updated[updated.find('{'): updated.rfind('}') + 1]
    try:
        hero_data = eval(data)
    except Exception as e:
        print(e, data, updated, sep='\n')
        return
    hero_data["health"] = min(100, chat_data["heroes"][user_id]["health"] + hero_data["health_diff"])
    chat_data["heroes"][user_id] = hero_data
    await state.set_state(FSMStates.DnD_took_action)
    print("is_game_finished")
    game_end = request_to_chatgpt(content=prompts["is_game_finished"].format(
        lore=chat_data["lore"],
        hero_data=hero_data,
        recent_actions='\n'.join(
            chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
        ),

    )
    )
    if int(game_end[0]):
        await msg.answer(game_end[1:])
        await FSMStates.clear(msg.chat.id)
        return
    states: dict[str, str] = await FSMStates.multiget_states(str(msg.chat.id), chat_data["heroes"])
    if all([st == "FSMStates:" + FSMStates.DnD_took_action._state for st in list(states.values())]):
        await msg.answer(lexicon["next_turn"])
        turn_end = request_to_chatgpt(content=prompts["next_turn"].format(
            lore=chat_data["lore"],
            recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
                )
            )
        )
        chat_data["actions"].append(turn_end)
        await msg.answer(turn_end)
        await msg.answer(lexicon["take_action"])
        await FSMStates.multiset_state(chat_data["heroes"], msg.chat.id, FSMStates.DnD_taking_action)
    else:
        await msg.answer(lexicon["wait_other_players"] % chat_data["heroes"][user_id]["name"])


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
    if check_type[0] != "0":
        await msg.answer(lexicon["roll"] % check_type, 
                        reply_markup=roll_kb,
                        resize_keyboard=True
        )
        await state.set_data(ctx)
        await state.set_state(FSMStates.rolling)
        return
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    ctx["prompt_sent"] = True   
    ctx["topic"] = topic
    ctx["roll_result"] = 20
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
    sent_msg = await clb.message.answer(lexicon["rolling"])
    result = randint(1, 20)
    await asyncio.sleep(ROLLING_SLEEP_TIME)
    await sent_msg.edit_text(str(result))
    ctx = await state.get_data()
    topic = ctx["topic"]
    ctx["roll_result"] = result
    ctx["prompt_sent"] = True
    user_msg_id = ctx["user_msg_id"]
    await state.set_data(ctx)
    print("ROLLING ROLLING", user_msg_id)
    await process_action(topic, chat_data, clb.message, state, user_id=user_msg_id)
    ctx["prompt_sent"] = False
    await state.set_data(ctx)


@rt.message(Command("master"), StateFilter(FSMStates.DnD_taking_action))
async def master(msg: Message, state: FSMContext, chat_data: dict):
    if str(msg.from_user.id) not in chat_data["heroes"]:
        return
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    topic = msg.text.replace("/master", '').replace(BOT_USERNAME,'')
    if not topic.replace(' ',''):
        await msg.answer(lexicon["master_empty"] % chat_data["heroes"][str(msg.from_user.id)]["name"])
        await state.set_state(FSMStates.DnD_adding_master)
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
    await state.set_data(ctx)
    await msg.answer(result)
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)

@rt.message(StateFilter(FSMStates.DnD_adding_master))
async def adding_master(msg: Message, state: FSMContext, chat_data: dict):
    await master(msg, state, chat_data)


@rt.message(Command("action"), StateFilter(FSMStates.DnD_took_action))
async def already_took_action(msg: Message, chat_data: dict):   
    await msg.answer(lexicon["already_took_action"] % chat_data["heroes"][str(msg.from_user.id)]["name"])