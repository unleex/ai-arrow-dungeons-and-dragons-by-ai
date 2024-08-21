import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


from lexicon.lexicon import LEXICON_RU
from states.states import FSMStates

from typing import Literal

from aiogram.types import Message


lexicon  = LEXICON_RU


async def handle_image_errors(message, state, error_code, violation_level):
    if violation_level != 2:
        if violation_level == 1:
            await message.answer(lexicon["content_policy_violation_warning"])
        if error_code == 2:
            await message.answer(lexicon["openai_error_warning"])
            await FSMStates.set_chat_data(message.chat.id, {"prompt_sent": False})
            await FSMStates.clear_chat_state(message.chat.id)
            return False
    else:
        await message.answer(lexicon["content_policy_violation_warning"])
        await message.answer(lexicon["content_policy_violation_retries_exhausted"])
        await FSMStates.set_chat_data(message.chat.id, {"prompt_sent": False})
        return False
    return True


def parse_hero_data(result):
    """Извлекает и формирует данные героя из ответа GPT."""
    if not ('{' in result and '}' in result):
        return False
    data = result[result.find('{'): result.rfind('}') + 1]
    hero_data = eval(data)
    hero_data["health"] = 100
    return hero_data


def update_chat_data(chat_data, user_id, hero_data):
    """Обновляет данные чата с новым героем."""
    skills = ["Сила", "Ловкость", "Интеллект", "Мудрость"]
    stats = [1] * 4
    skills_exp = [f"{i}_experience" for i in skills]
    exp = [0] * 4

    chat_data["experience_data"][str(user_id)] = dict(zip(skills, stats)) | dict(zip(skills_exp, exp))
    chat_data['heroes'][str(user_id)] = hero_data


def clear_hero_photos(chat_data: dict):
    for user_id in chat_data["users"]:
        if os.path.exists(f"src/hero_images/{user_id}_hero.png"):
            os.remove(f"src/hero_images/{user_id}_hero.png")


class Preloader:

    def __init__(self, msg: Message, steps: list[Literal["image", "voice", "lore"]]):
        self._steps = iter(steps)
        self._msg = msg
        self._first = True

    async def update(self):
        step = next(self._steps, "done")
        if step == "done":
            self._msg = await self._msg.edit_text(self._msg.text.replace("...", "✅"))
            return
        if self._first:
            self._msg = await self._msg.answer(lexicon[f"{step}_preloader"])
            self._first = False
        else:
            self._msg = await self._msg.edit_text(self._msg.text.replace("...", "✅") 
                                                + '\n' + lexicon[f"{step}_preloader"])