from config.config import openai_client, BOT_USERNAME
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from prompts.functions import request_to_chatgpt
from states.states import FSMStates

from random import randint

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message


rt = Router()
MAX_TOKENS = 1000
NEW_MISSION_CHANCE = 0.2
ACTION_RELEVANCE_FOR_MISSION = 10
lexicon = LEXICON_RU
prompts = PROMPTS_RU


@rt.message(StateFilter(FSMStates.DnD_default_state))
async def maybe_generate_mission(msg: Message, state: FSMContext, translate_dict: dict, chat_data: dict):
    if randint(0,100) / 100 < NEW_MISSION_CHANCE:
        result = request_to_chatgpt(content=prompts["DnD_generating_adventure"].format(
                adventure=chat_data["lore"],
                recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]),
                location="random location"))
    await msg.answer(result.translate(translate_dict)) # translate to restrict model using markdown chars, avoiding bugs
    await FSMStates.set_chat_state(msg.chat.id, FSMStates.DnD_taking_action)
    await msg.answer(lexicon["take_action"])


#TODO: check if user doesn't say the action and prompt him to send it in next message
@rt.message(Command("action"), StateFilter(FSMStates.DnD_taking_action))
async def taking_action(msg: Message, state: FSMContext, chat_data: dict):
    if str(msg.from_user.id) not in chat_data["heroes"]:
        return
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
    result = request_to_chatgpt(content=prompts["DnD_taking_action"].format(
                action=topic,
                recent_actions='\n'.join(
                    chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
                    ),
                hero_data=chat_data["heroes"][str(msg.from_user.id)])
    )
    ctx["prompt_sent"] = False
    await state.set_data(ctx)
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)
    updated = request_to_chatgpt(content=prompts["update_after_action"].format(
        action=topic, 
        hero_data=chat_data["heroes"][str(msg.from_user.id)]
        )
    )
    print(updated)
    data = updated[updated.find('{'): updated.rfind('}') + 1]
    try:
        hero_data = eval(data)
    except Exception as e:
        print(e, data, updated, sep='\n')
        return
    hero_data["health"] = min(100, hero_data["health"])
    chat_data["heroes"][str(msg.from_user.id)] = hero_data
    await msg.answer(result)
    await state.set_state(FSMStates.DnD_took_action)
    game_end = request_to_chatgpt(content=prompts["is_game_finished"].format(
        lore=chat_data["lore"],
        hero_data=hero_data,
        recent_actions='\n'.join(
            chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
        ),

    )
    )
    print(game_end)
    if int(game_end[0]):
        print("game over")
        await msg.answer(game_end[1:])
        await FSMStates.clear(msg.chat.id)

    states: dict[str, str] = await FSMStates.get_chat_states(str(msg.chat.id))
    if all([st == "FSMStates:" + FSMStates.DnD_took_action._state for st in list(states.values())]):
        await msg.answer(lexicon["next_turn"])
        turn_end = request_to_chatgpt(content=prompts["DnD_taking_action"].format(
            action=topic,
            hero_data=hero_data,
            recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
                )
            )
        )
        await msg.answer(turn_end)
        await msg.answer(lexicon["take_action"])
        await FSMStates.set_chat_state(msg.chat.id, FSMStates.DnD_taking_action)


@rt.message(StateFilter(FSMStates.DnD_adding_action))
async def adding_action(msg: Message, state: FSMContext, chat_data: dict):
    await taking_action(msg, state, chat_data)


#TODO: append result and prompt to actions  
@rt.message(Command("master"), StateFilter(FSMStates.DnD_taking_action))
async def master(msg: Message, state: FSMContext, chat_data: dict):
    if str(msg.from_user.id) not in chat_data["heroes"]:
        return
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    ctx["prompt_sent"] = True
    await state.set_data(ctx)
    topic = msg.text.replace("/master", '').replace(BOT_USERNAME,'')
    if not topic.replace(' ',''):
        await msg.answer(lexicon["master_empty"] % chat_data["heroes"][str(msg.from_user.id)]["name"])
        await state.set_state(FSMStates.DnD_adding_master)
        return
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


@rt.message(StateFilter(FSMStates.DnD_took_action))
async def already_took_action(msg: Message, chat_data: dict):   
    await msg.answer(lexicon["already_took_action"] % chat_data["heroes"][str(msg.from_user.id)]["name"])