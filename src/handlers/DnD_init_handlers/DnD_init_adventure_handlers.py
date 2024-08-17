import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from keyboards.keyboards import DnD_is_adventure_ok_kb
from keyboards.set_menu import set_main_menu
from lexicon.lexicon import LEXICON_RU
from handlers.other_handlers import unblock_api_calls
from prompts.prompts import PROMPTS_RU
from prompts.functions import request_to_chatgpt, get_photo_from_chatgpt, tts
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
AMOUNT_OF_TEXT_FOR_PICTURE_GEN = 800


@rt.message(Command("dnd"), StateFilter(default_state))
async def DnD_init_handler(msg: Message, state: FSMContext, chat_data: dict):
    await set_main_menu(msg.chat.id)
    chat_data["heroes"] = {}
    chat_data["lore"]  = ""
    chat_data["actions"] = []
    chat_data["experience_data"] = {}
    await msg.answer(lexicon["DnD_init"])
    await FSMStates.set_chat_state(str(msg.chat.id), FSMStates.waiting)
    await state.set_state(FSMStates.generating_adventure)


@rt.message(F.text, StateFilter(FSMStates.generating_adventure))
async def DnD_generating_adventure_handler(msg: Message, state: FSMContext, chat_data: dict):
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return
    ctx["prompt_sent"] = True
    await state.set_data(ctx)
    await msg.answer(lexicon["DnD_generating_adventure"])
    ctx = {"topic": msg.text}

    #text
    preloader = await msg.answer(lexicon["text_preloader"])
    preloader_text = preloader.text
    result = request_to_chatgpt(prompts["DnD_generating_lore"] % ctx["topic"])

    #voice
    preloader = await preloader.edit_text(preloader_text.replace('...', ' ✅') + '\n' + lexicon["voice_preloader"])
    preloader_text = preloader.text
    voice = tts(result, ambience_path="src/ambience/anxious.mp3")


    #photo
    preloader = await preloader.edit_text(preloader_text.replace('...', ' ✅') + '\n' + lexicon["image_preloader"])
    preloader_text = preloader.text


    photo, error_code, violation_level = get_photo_from_chatgpt(content=result)
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
    #await msg.answer(lexicon["adventure_image_preloader"])
#     result = """Недавно, Элгар, несчастный зять древнего клана магов, обнаружил что-то необычное в шкафу своей свекрови. Там глубоко спрятаны были драгоценности и редкие артефакты, а ещё несколько старинных свитков. Элгар, увлекшись изучением свитков, обнаружил, что те были дневниками Мелиндры, предка своей жены и мощного мага, битву с которым вспоминали по всему королевству.
# Мелиндра всю жизнь была фанатично увлечена драконами. Она изучала их природу, потребности, образ жизни, и даже смогла наладить контакт с некоторыми из них. Однако, под влиянием злого чародея, она была обманута, и её знания и исследования были использованы для неправильных целей. Злодей превратил драконов в свою личную армию, и развязал войну против королевства.
# Чуя измену, Мелиндра подступила к злодею и наложила на него проклятие, которое приковало его душу к шкафу. Однако, вступив в схватку с могущественным драконом, Мелиндра погибла, не успев рассказать о своем замысле другим магам клана.
# Элгар, узнав о своей ответственности, предположил, что проклятье Мелиндры все еще связывает драконов с шкафом. Осознав важность своей миссии, он начал готовиться к предстоящей войне. Элгар обратился за помощью к другим магам, воинам и героям, несмотря на их первоначальное недоверие, они поняли серьезность ситуации и присоединились к нему.
# И вот теперь, эти герои, лицом к лицу со страшной угрозой, готовы разгадать тайны древних свитков, изучить шкаф у тещи эльфийского мага и остановить предстоящую войну с драконами."""
    await msg.answer_photo(photo)
    #await msg.answer(result) # translate to restrict model using markdown chars, avoiding bugs
    await msg.answer_voice(voice)

    await msg.answer(lexicon["DnD_is_adventure_ok"],
                     reply_markup=DnD_is_adventure_ok_kb,
                     resize_keyboard=False)
    await state.set_state(FSMStates.DnD_is_adventure_ok_choosing)
    await state.set_data(ctx)
    chat_data["lore"] = result
    ctx["prompt_sent"] = False
    await state.set_data(ctx)


@rt.callback_query(F.data=="DnD_is_adventure_ok_yes", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_yes_handler(clb: CallbackQuery, state: FSMContext):
    await clb.message.answer(lexicon['amount_of_players'])
    await state.set_state(FSMStates.getting_amount_of_players)



@rt.callback_query(F.data=="DnD_is_adventure_ok_no", StateFilter(FSMStates.DnD_is_adventure_ok_choosing))
async def DnD_is_adventure_ok_no_handler(clb: CallbackQuery, state: FSMContext, translate_dict: dict, chat_data: dict):
    ctx = await state.get_data()
    if ctx.get("prompt_sent", False):
        return
    ctx["prompt_sent"] = True
    await state.set_data(ctx)
    await clb.message.answer(lexicon["DnD_is_adventure_ok_no"])
    result = request_to_chatgpt(
        prompts["DnD_generating_lore"] % chat_data["lore"]).translate(
            translate_dict
        )  # translate to restrict model using markdown chars, avoiding bugs
    photo, error_code, violation_level = get_photo_from_chatgpt(content=result)
    voice = tts(result, ambience_path="src/ambience/anxious.mp3")
    if violation_level != 2:
        if violation_level == 1:
            await clb.message.answer(lexicon["content_policy_violation_warning"])
        if error_code == 2:
            await clb.message.answer(lexicon["openai_error_warning"])
            await unblock_api_calls(clb.message, state)
            await FSMStates.clear_chat_state(clb.message.chat.id)
    else:
        await clb.message.answer(lexicon["content_policy_violation_warning"])
        await clb.message.answer(lexicon["content_policy_violation_retries_exhausted"])
        await unblock_api_calls(clb.message, state)
        ctx["prompt_sent"] = False
        await state.set_data(ctx)
        return
    #await clb.message.answer(result)
    await clb.message.answer_photo(photo)
    await clb.message.answer_voice(voice)
    await clb.message.answer(lexicon["DnD_is_adventure_ok"],
                     reply_markup=DnD_is_adventure_ok_kb,
                     resize_keyboard=False)
    ctx["prompt_sent"] = False
    await state.set_data(ctx)