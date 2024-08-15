from keyboards.set_menu import set_game_menu
from lexicon.lexicon import LEXICON_RU
from prompts.functions import request_to_chatgpt
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


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
    if ctx.get("prompt_sent", False):
        return # don't let user access gpt while already processing
    ctx["prompt_sent"] = True
    await state.set_data(ctx)

    if str(msg.from_user.id) in chat_data['heroes']:
        await msg.answer(lexicon['already_in_db'].format(name=msg.from_user.first_name))
        return
    await msg.answer(lexicon["extracting_hero_data"])
    result = request_to_chatgpt(content=prompts["extract_hero_data"] % msg.text)
    ctx["prompt_sent"] = False
    await state.set_data(ctx)
    data = result[result.find('{'): result.find('}') + 1]
    hero_data = eval(data)
    hero_data["health"] = 100
    chat_data['heroes'][str(msg.from_user.id)] = hero_data
    await msg.answer(lexicon["extracted_hero_data"])


    # TODO: unnest
    if len(chat_data['heroes']) == ctx['number_of_players']:
        
        await msg.answer(lexicon['game_started'])
        await msg.answer(lexicon["generating_starting_location"])
        await set_game_menu(msg.chat.id)

        data = request_to_chatgpt(content=prompts["DnD_init_location"] % chat_data["lore"])
#         data = """{
#   "location": "Крепость последних магов, расположенная в древнем лесу посреди таинственных топей.",
#   "explanation": "Вы находитесь в таинственном древнем лесу, где густые вековые деревья пронизаны таинственным шепотом. Перед вами возвышается крепость последних магов, огромная строение, вырубленное из прочного камня и украшенное золотыми драгоценностями. В глубине дворца, в одной из темных комнат, стоит таинственный шкаф, отдавая окружающую среду аурой чар и магической энергии. Это место, где вы будете разгадывать тайны древних свитков, изучать любопытные артефакты и подготавливаться к предстояющей войне с драконами."
# }"""
        try:
            data = eval(data)
        except Exception as e:
            print(e, data, sep='\n')
            return
        location = data["location"]
        explanation = data["explanation"]
        await msg.answer(explanation)
        await msg.answer(lexicon["take_action"])
        await FSMStates.clear(msg.chat.id)
        await FSMStates.multiset_state(chat_data["heroes"], msg.chat.id, FSMStates.DnD_taking_action)
        for user_id in chat_data["heroes"]:
            chat_data["heroes"][user_id]["location"] = location
    else:
        await msg.answer(lexicon["wait_other_players"] % msg.from_user.first_name)
