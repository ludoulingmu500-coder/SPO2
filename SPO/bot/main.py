import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from database.database import init_db
from bot.events import setup_events

load_dotenv()
TOKEN = os.getenv("TOKEN", "").strip()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.guild_configs = {}
setup_events(bot)


def run():
    if not TOKEN or TOKEN == "replace_with_your_discord_bot_token":
        raise RuntimeError("Set TOKEN in .env before starting the bot")
    init_db()
    bot.run(TOKEN)
