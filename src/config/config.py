import httpx
from typing import Any

from environs import Env
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from openai import OpenAI


env = Env()
env.read_env()
BOT_TOKEN: str = env("BOT_TOKEN")
bot: Bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="markdown"))
dp = Dispatcher()
openai_client = OpenAI()