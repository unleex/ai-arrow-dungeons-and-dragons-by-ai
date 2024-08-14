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