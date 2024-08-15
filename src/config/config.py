from environs import Env
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import Redis, RedisStorage
from openai import OpenAI


env = Env()
env.read_env()
BOT_TOKEN: str = env("BOT_TOKEN")
BOT_USERNAME = "@ai_dnd_bot"
bot: Bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="html"))
redis = Redis(host='localhost')
storage = RedisStorage(redis=redis)
dp = Dispatcher(storage=storage)
openai_client = OpenAI()