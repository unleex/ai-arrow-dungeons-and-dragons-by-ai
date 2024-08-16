from config.config import openai_client
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates

import os
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


def request_to_chatgpt(content, model='gpt-4o-mini' , role='user', temperature=1, max_tokens=500):
    completion = openai_client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages = [
                {"role": role, "content": content + 
                 f"Умести свой ответ в {max_tokens} токенов. Твой ответ не должен обрываться на середине предложения."}
            ]
        )
    result = completion.choices[0].message.content
    return result


def get_photo_from_chatgpt(prompt,
                           folder="generated_images",
                           model="dall-e-2"
                           ):

    response: ImagesResponse = openai_client.images.generate(
        prompt="Я опишу тебе сцену, а ты нарисуй ее от лица разказчика.\n Сцена:\n" + prompt,
        model=model,
        quality="standard",
        size="512x512"
    )

    # Save the image to a file
    image_url = response.data[0].url
    image_response = requests.get(image_url)
    filename = f"generated_image.png"
    target_path = f'src/{folder}/{filename}'
    if image_response.status_code == 200:
        with open(target_path, 'wb') as f:
            f.write(image_response.content)
    else:
        print("Failed to download the image")
    input_file = FSInputFile(target_path)
    #os.remove(target_path)
    return input_file


def tts(prompt,
        folder="generated_audio",
        model="tts-1",
        voice="onyx",
        ambience_path=None
        ):
    response = openai_client.audio.speech.create(
    model=model,
    voice=voice,
    input=prompt
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
        result = voice + ambience_sample
        soundfile.write(target_path, result, voice_sr)

    input_file = FSInputFile(target_path)
    #os.remove(target_path)
    return input_file


async def finish_action(topic, chat_data: dict, msg: Message, state: FSMContext, user_id=None):
    if not user_id:
        user_id = msg.from_user.id
    user_id = str(user_id)
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
    game_end = request_to_chatgpt(content=prompts["is_game_finished"].format(
        lore=chat_data["lore"],
        hero_data=hero_data,
        recent_actions='\n'.join(
            chat_data["actions"][-ACTION_RELEVANCE_FOR_MISSION:]
        ),

    )
    )
    if int(game_end[0]):
        await msg.answer_photo(get_photo_from_chatgpt(prompt=game_end[1:]))
        await msg.answer(game_end[1:])
        await msg.answer_voice(tts(game_end[1:], ambience_path="src/ambience/anxious.mp3"))
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
            ),
            max_tokens=1000
        )
        chat_data["actions"].append(turn_end)
        await msg.answer(turn_end)
        await msg.answer_voice(tts(turn_end, ambience_path="src/ambience/anxious.mp3"))
        await msg.answer_photo(get_photo_from_chatgpt(prompt=turn_end))
        await msg.answer(lexicon["take_action"])
        await FSMStates.multiset_state(chat_data["heroes"], msg.chat.id, FSMStates.DnD_taking_action)
    else:
        await msg.answer(lexicon["wait_other_players"] % chat_data["heroes"][user_id]["name"])


async def process_action(topic, chat_data: dict, msg: Message, state: FSMContext, user_id=None):
    if not user_id:
        user_id = msg.from_user.id
    user_id = str(user_id)
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
    await msg.answer_voice(tts(result, ambience_path="src/ambience/anxious.mp3"))
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)
    await finish_action(topic, chat_data, msg, state, user_id)