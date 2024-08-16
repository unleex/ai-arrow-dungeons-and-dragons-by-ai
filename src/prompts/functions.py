from config.config import openai_client
from lexicon.lexicon import LEXICON_RU
from prompts.prompts import PROMPTS_RU
from states.states import FSMStates

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

lexicon = LEXICON_RU
prompts = PROMPTS_RU
from config.config import openai_client
from openai.types import ImagesResponse
import requests
import uuid



ACTION_RELEVANCE_FOR_MISSION = 10

def request_to_chatgpt(content, model='gpt-4' , role='user', temperature=1, max_tokens=500):
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



def get_photo_from_chatgpt(prompt,
                           folder="generated_images",
                           model="dall-e-3"
                           ):

    response: ImagesResponse = openai_client.images.generate(
        prompt="Я опишу тебе сцену, а ты нарисуй ее от лица разказчика.\n " + prompt,
        model=model
    )

    # Save the image to a file
    image_url = response.data[0].url
    image_response = requests.get(image_url)
    filename = f"generated{uuid.uuid1()}_image.png"
    if image_response.status_code == 200:
        with open(f'src/{folder}/{filename}', 'wb') as f:
            f.write(image_response.content)
        print(f"Image downloaded and saved as '{filename}'")
    else:
        print("Failed to download the image")
    return FSInputFile(f'src/{folder}/{filename}')


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
    chat_data["actions"].append(topic)
    chat_data["actions"].append(result)
    await finish_action(topic, chat_data, msg, state, user_id)