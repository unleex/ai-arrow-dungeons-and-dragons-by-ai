from config.config import openai_client, BOT_USERNAME
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates

from random import randint

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
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
        completion = openai_client.chat.completions.create(
        model="gpt-4",
        max_tokens=MAX_TOKENS,
        temperature=1,
        messages = [
            {"role": "user", 
             "content": prompts["DnD_generating_adventure"].format(
                adventure=chat_data["adventure_topic"],
                recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]),
                location="random location")} 
        ]
    )
    await msg.answer(completion.choices[0].message.content.translate(
        translate_dict
    )
    ) # translate to restrict model using markdown chars, avoiding bugs 
    await FSMStates.set_chat_state(msg.chat.id, FSMStates.DnD_taking_action)
    await msg.answer(lexicon["take_action"])


#TODO: check if user doesn't say the action and prompt him to send it in next message
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
    completion = openai_client.chat.completions.create(
        model="gpt-4",
        max_tokens=MAX_TOKENS,
        temperature=1,
         messages = [
            {"role": "user", 
             "content": prompts["DnD_taking_action"].format(
                action=msg.text,
                recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]),
                hero_data=chat_data["heroes"][str(msg.from_user.id)])}
        ]
    )
    ctx["prompt_sent"] = False
    await state.set_data(ctx)
    result = completion.choices[0].message.content
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)
    await msg.answer(result)
    await state.set_state(FSMStates.DnD_took_action)


@rt.message(StateFilter(FSMStates.DnD_adding_action))
async def adding_action(msg: Message, state: FSMContext, chat_data: dict):
    await taking_action(msg, state, chat_data)


#TODO: append result and prompt to actions  
@rt.message(Command("master"), StateFilter(FSMStates.DnD_taking_action))
async def master(msg: Message, state: FSMContext, chat_data: dict):
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
    completion = openai_client.chat.completions.create(
        model="gpt-4",
        max_tokens=MAX_TOKENS,
        temperature=1,
         messages = [
            {"role": "user", 
             "content": prompts["DnD_master"].format(
                phrase=msg.text,
                recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]),
                hero_data=chat_data["heroes"][str(msg.from_user.id)])} 
        ]
    )
    ctx["prompt_sent"] = False
    await state.set_data(ctx)
    result = completion.choices[0].message.content
    await msg.answer(result)
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)

@rt.message(StateFilter(FSMStates.DnD_adding_master))
async def adding_master(msg: Message, state: FSMContext, chat_data: dict):
    await master(msg, state, chat_data)


@rt.message(StateFilter(FSMStates.DnD_took_action))
async def already_took_action(msg: Message, chat_data: dict):
    await msg.answer(lexicon["already_took_action"] % chat_data["heroes"][str(msg.from_user.id)])