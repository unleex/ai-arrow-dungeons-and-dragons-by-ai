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
from config.config import openai_client
from openai.types import ImagesResponse
import requests
import uuid




def request_to_chatgpt(model='gpt-4', role='user', temperature=1, max_tokens=500, content=''):
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



def get_photo_from_chatgpt(folder="generated_images",
                           model="dall-e-3",
                           prompt="помощница босса крупной компании, испробовавшая все попытки получить повышение"):

    response: ImagesResponse = openai_client.images.generate(
        prompt=prompt,
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