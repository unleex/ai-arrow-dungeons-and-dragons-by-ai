from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Chat, User

from typing import Callable, Any
import json
import logging


logger = logging.getLogger(__name__)


class DataBaseAccessor(BaseMiddleware):
    async def __call__(self,
                       handler: Callable,
                       event: TelegramObject,
                       data: dict[str,Any]) -> Any:
        chat: Chat|None = data['event_chat']
        user: User|None = data["event_from_user"]

        with open("src/db/chat_database.json", mode='r') as fp:
            db: dict = json.load(fp)
        if str(chat.id) in db.keys():
            data['chat_data'] =  db[str(chat.id)]
        else:
            db[str(chat.id)] = {"name": [], "description": '', "users": {}}
            logger.info(f"New chat: {str(chat.id)}.\nInfo: {chat.active_usernames}\n{chat.bio}")
            data['chat_data'] =  db[str(chat.id)]

        if str(user.id) not in db[str(chat.id)]["users"]:
            db[str(chat.id)]["users"][str(user.id)] = user.username
            logger.info(f"New user in chat: {str(chat.id)}. Id: {user.id}")

        with open('src/db/chat_database.json', mode='w') as fp:
            json.dump(db, fp, indent='\t')

        try:
            result = await handler(event, data)
        except Exception as e:
            print(e)

        with open('src/db/chat_database.json', mode='w') as fp:
            json.dump(db, fp, indent='\t')
        return result