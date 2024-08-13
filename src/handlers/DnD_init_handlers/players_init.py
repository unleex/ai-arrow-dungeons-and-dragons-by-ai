from config.config import bot, openai_client
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message
from openai import OpenAI


lexicon = LEXICON_RU
MAX_TOKENS = 500
prompts = PROMPTS_RU
rt = Router()


@rt.message(StateFilter(FSMStates.getting_amount_of_players))
async def counting_players(msg: Message, state: FSMContext):
    if not msg.text.isdigit():
        await msg.answer(lexicon['amount_of_players_wrong_format'])
    else:
        await msg.answer(lexicon["DnD_init_players"])
        ctx = await state.get_data()
        ctx["number_of_players"] = int(msg.text)
        await FSMStates.set_chat_data(msg.chat.id, ctx)
        await FSMStates.set_chat_state(msg.chat.id, FSMStates.creating_heroes)


@rt.message(StateFilter(FSMStates.creating_heroes))
async def get_descriptions(msg: Message, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()
    if ctx.get("extracting_hero_data", False):
        return # processing more heroes while generating may cause errors
    ctx["extracting_hero_data"] = True
    await state.set_data(ctx)
    if str(msg.from_user.id) in chat_data['heroes']:
        await msg.answer(lexicon['already_in_db'].format(name=msg.from_user.first_name))
        return
    await msg.answer(lexicon["extracting_hero_data"])
    completion = openai_client.chat.completions.create(
            model="gpt-4",
            max_tokens=MAX_TOKENS,
            temperature=1,
            messages = [
                {"role": "user", "content": prompts["extract_hero_data"] % msg.text}
            ]
        )  
    result = completion.choices[0].message.content
    data = result[result.find('{'): result.find('}') + 1]
    hero_data = eval(data)
    chat_data['heroes'][str(msg.from_user.id)] = hero_data
    await msg.answer(lexicon["extracted_hero_data"])
    # TODO: unnest
    if len(chat_data['heroes']) == ctx['number_of_players']:
        await msg.answer(lexicon['game_started'])
        await msg.answer(lexicon["generating_starting_location"])
        completion = openai_client.chat.completions.create(
            model="gpt-4",
            max_tokens=MAX_TOKENS,
            temperature=1,
            messages = [
                {"role": "user", "content": prompts["DnD_init_location"] % chat_data["adventure_lore"]}
            ]
        )   
        location = completion.choices[0].message.content
        await msg.answer(location)
        await msg.answer(lexicon["take_action"])
        await FSMStates.set_chat_state(msg.chat.id, FSMStates.DnD_taking_action)
        for user_id in chat_data["heroes"]:
            chat_data["heroes"][user_id]["location"] = location
    else:
        await msg.answer(lexicon["wait_other_players"] % msg.from_user.first_name)
