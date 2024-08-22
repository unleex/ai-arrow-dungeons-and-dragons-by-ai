import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.config import openai_client
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates
from utils.utils import handle_image_errors, clear_hero_photos, Preloader

from random import randint
import requests

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile
import librosa
from openai.types import ImagesResponse
import soundfile


lexicon = LEXICON_RU
prompts = PROMPTS_RU
ACTION_RELEVANCE_FOR_MISSION = 10


def request_to_chatgpt(content: str, *, model='gpt-4o-mini' , role='user', temperature=1, max_tokens=500):
    completion = openai_client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages = [
                {"role": role, "content": content}
            ]
        )
    result = completion.choices[0].message.content
    return result


def get_photo_from_chatgpt(content: str,
                           target_path="src/generated_images/generated_photo.png",
                           model="dall-e-3",
                           modify_prompt=True,
                           raw_output=False,
                           is_violation=False
                           ):
    is_failed = 0
    if modify_prompt:
        modification = ""
        content = modification + content
    else:
        modification = ""
    try:
        response: ImagesResponse = openai_client.images.generate(
            prompt=content,
            model=model,
            quality="standard"
        )
    except Exception as e:
        print(len(content), content)
        if "content_policy_violation" in str(e):
            print("oops!")
            if len(content) - len(modification) < 10:
                print("my condolences")
                return (None, 1, 2)
            is_violation = True
            content = content.replace(modification, '')
            content = content[:len(content)//2]
            print("retry")
            response, is_failed, is_violation = get_photo_from_chatgpt(
                content, target_path, model,
                modify_prompt, raw_output=True,
                is_violation=is_violation
            )
        else:
            return (None, 2, 0)
    # Save the image to a file
    if is_failed == 1:
        return (None, 1, is_violation)
    if is_failed == 2:
        (None, 2, is_violation)

    image_url = response.data[0].url
    image_response = requests.get(image_url)
    filename = f"generated_image.png"
    if image_response.status_code == 200:
        with open(target_path, 'wb') as f:
            f.write(image_response.content)
    else:
        print("Failed to download the image")
    input_file = FSInputFile(target_path)
    #os.remove(target_path)
    return (response, 0, is_violation) if raw_output else (input_file, 0, is_violation)


def tts(content: str,
        folder="generated_audio",
        model="tts-1",
        voice="onyx",
        ambience_path=None
        ):
    response = openai_client.audio.speech.create(
        model=model,
        voice=voice,
        input=content
    )
    filename = f"generated_audio.wav"
    target_path = f"src/{folder}/{filename}"
    response.write_to_file(target_path)
    if ambience_path:
        voice, voice_sr = librosa.load(target_path)
        ambience, ambience_sr = librosa.load(ambience_path)
        if ambience_sr != voice_sr:
            ambience = librosa.resample(ambience, orig_sr=ambience_sr, target_sr=voice_sr)
        voice_time = len(voice)
        ambience_time = len(ambience)
        ambience_sample_start = randint(0, ambience_time - voice_time - 1)
        ambience_sample = ambience[ambience_sample_start: ambience_sample_start + voice_time]
        result = voice * 2 + ambience_sample / 2.15
        soundfile.write(target_path, result, voice_sr)

    input_file = FSInputFile(target_path)
    #os.remove(target_path)
    return input_file


async def finish_action(topic, chat_data: dict, msg: Message, state: FSMContext, user_id=None):
    if not user_id:
        user_id = msg.from_user.id
    user_id = str(user_id)

    updated = request_to_chatgpt(prompts["update_after_action"].format(
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
    game_end = request_to_chatgpt(prompts["is_game_finished"].format(
        lore=chat_data["lore"],
        hero_data=hero_data,
        recent_actions='\n'.join(
            chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
        )
    ))
    if int(game_end[0]):
        prompt_for_photo = request_to_chatgpt(content=prompts["extract_prompt_for_photo"] % game_end[1:])
        photo, error_code, violation_level = get_photo_from_chatgpt(content=prompt_for_photo)
        voice = tts(game_end[1:], ambience_path="src/ambience/cheerful.mp3")
        if not await handle_image_errors(msg, state, error_code, violation_level):
            return
        await msg.answer_photo(photo)
        await msg.answer(game_end[1:])
        await msg.answer_voice(voice)
        await FSMStates.clear_chat(msg.chat.id)
        clear_hero_photos(chat_data)
        return
    states: dict[str, str] = await FSMStates.multiget_states(str(msg.chat.id), chat_data["heroes"])
    if all([st == "FSMStates:" + FSMStates.DnD_took_action._state for st in list(states.values())]):
        await msg.answer(lexicon["next_turn"])
        preloader = Preloader(msg, ["plot", "voice", "image"])
        
        await preloader.update()

        turn_end = request_to_chatgpt(prompts["next_turn"].format(
            lore=chat_data["lore"],
            recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
                )
            ),
            max_tokens=1000
        )
        chat_data["actions"].append(turn_end)



        await preloader.update()
        voice = tts(turn_end, ambience_path="src/ambience/cheerful.mp3")

        await preloader.update()
        prompt_for_photo = request_to_chatgpt(content=prompts["extract_prompt_for_photo"] % turn_end)
        photo, error_code, violation_level = get_photo_from_chatgpt(content=prompt_for_photo)

        if not await handle_image_errors(msg, state, error_code, violation_level):
            return
        await preloader.update()

        await msg.answer_voice(voice)
        await msg.answer_photo(photo)
        await msg.answer(lexicon["take_action"])
        await FSMStates.multiset_state(chat_data["heroes"], msg.chat.id, FSMStates.DnD_taking_action)
        await FSMStates.clear_chat_data(msg.chat.id)
    else:
        await msg.answer(lexicon["wait_other_players"] % chat_data["heroes"][user_id]["name"])


async def process_action(topic, chat_data: dict, msg: Message, state: FSMContext, user_id=None):
    if not user_id:
        user_id = msg.from_user.id
    user_id = str(user_id)
    ctx = await state.get_data()
    result = request_to_chatgpt(prompts["DnD_taking_action"].format(
            action=topic,
            recent_actions='\n'.join(
                chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
                ),
            hero_data=chat_data["heroes"][user_id],
            successful=ctx["roll_result"])
    )
    voice = tts(result)
    #await msg.answer(result)
    if "upgrade_message" in ctx:
        await msg.answer(ctx["upgrade_message"])
    await msg.answer_voice(voice)
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)
    await finish_action(topic, chat_data, msg, state, user_id)