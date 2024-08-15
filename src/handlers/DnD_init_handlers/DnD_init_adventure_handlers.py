from config.config import openai_client
from keyboards.keyboards import DnD_is_adventure_ok_kb
from keyboards.set_menu import set_game_menu
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from prompts.functions import request_to_chatgpt
from states.states import FSMStates

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message


lexicon = LEXICON_RU
prompts = PROMPTS_RU
rt = Router()
MAX_TOKENS = 1000


@rt.message(Command("dnd"), StateFilter(default_state))
async def DnD_init_handler(msg: Message, state: FSMContext, chat_data: dict):
    #chat_data["heroes"] = {}
    #chat_data["lore"] = ""
    chat_data["actions"] = []
    await msg.answer(lexicon["DnD_init"])
    await state.set_state(FSMStates.generating_adventure)


@rt.message(StateFilter(FSMStates.generating_adventure))
async def DnD_generating_adventure_handler(msg: Message, state: FSMContext, translate_dict: dict, chat_data: dict):
    await msg.answer(lexicon["DnD_generating_adventure"])
    # completion = openai_client.chat.completions.create(
    #     model="gpt-4",
    #     max_tokens=MAX_TOKENS,
    #     temperature=1,
    #     messages = [
    #         {"role": "user", "content": prompts["DnD_generating_lore"] % msg.text}
    #     ]
    # )
    #result = completion.choices[0].message.content.translate(translate_dict)
    result = """Недавно, Элгар, несчастный зять древнего клана магов, обнаружил что-то необычное в шкафу своей свекрови. Там глубоко спрятаны были драгоценности и редкие артефакты, а ещё несколько старинных свитков. Элгар, увлекшись изучением свитков, обнаружил, что те были дневниками Мелиндры, предка своей жены и мощного мага, битву с которым вспоминали по всему королевству.
Мелиндра всю жизнь была фанатично увлечена драконами. Она изучала их природу, потребности, образ жизни, и даже смогла наладить контакт с некоторыми из них. Однако, под влиянием злого чародея, она была обманута, и её знания и исследования были использованы для неправильных целей. Злодей превратил драконов в свою личную армию, и развязал войну против королевства.
Чуя измену, Мелиндра подступила к злодею и наложила на него проклятие, которое приковало его душу к шкафу. Однако, вступив в схватку с могущественным драконом, Мелиндра погибла, не успев рассказать о своем замысле другим магам клана.
Элгар, узнав о своей ответственности, предположил, что проклятье Мелиндры все еще связывает драконов с шкафом. Осознав важность своей миссии, он начал готовиться к предстоящей войне. Элгар обратился за помощью к другим магам, воинам и героям, несмотря на их первоначальное недоверие, они поняли серьезность ситуации и присоединились к нему.
И вот теперь, эти герои, лицом к лицу со страшной угрозой, готовы разгадать тайны древних свитков, изучить шкаф у тещи эльфийского мага и остановить предстоящую войну с драконами."""
    await msg.answer(result) # translate to restrict model using markdown chars, avoiding bugs
    await msg.answer(lexicon["DnD_is_adventure_ok"],
                     reply_markup=DnD_is_adventure_ok_kb,
                     resize_keyboard=True)
    await state.set_state(FSMStates.DnD_is_adventure_ok_choosing)
    chat_data["lore"] = result


@rt.callback_query(F.data=="DnD_is_adventure_ok_yes", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_yes_handler(clb: CallbackQuery, state: FSMContext):
    await clb.message.answer(lexicon['amount_of_players'])
    await state.set_state(FSMStates.getting_amount_of_players)



@rt.callback_query(F.data=="DnD_is_adventure_ok_no", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_no_handler(clb: CallbackQuery, state: FSMContext, translate_dict: dict, chat_data: dict):
    await clb.message.answer(lexicon["DnD_is_adventure_ok_no"])
    completion = request_to_chatgpt(content=prompts["DnD_generating_lore"] % chat_data["lore"])
    await clb.message.answer(completion.translate(translate_dict)
    ) # translate to restrict model using markdown chars, avoiding bugs
    await clb.message.answer(lexicon["DnD_is_adventure_ok"],
                     reply_markup=DnD_is_adventure_ok_kb,
                     resize_keyboard=True)