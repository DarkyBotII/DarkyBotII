import discord
from discord.ext import tasks
from collections import deque
from datetime import datetime, timedelta
import os

import requests
from flask import Flask

from dotenv import load_dotenv
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva!")

# Intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = discord.Bot(intents=intents)

# Flask app a uptime-hoz
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot fut!"

# Várólistás publish logika
queues = {}
published_counts = {}
hour_starts = {}

# Fájlok betöltése
def load_txt(filename):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

server_ids = load_txt("serverid.txt")
user_ids = load_txt("userid.txt")
role_ids = load_txt("rangid.txt")

# Ellenőrző függvények
def is_allowed_server(guild_id):
    return not server_ids or str(guild_id) in server_ids

def is_allowed_user(user_id):
    return not user_ids or str(user_id) in user_ids

def has_allowed_role(member: discord.Member):
    if not role_ids:
        return True
    member_role_ids = [str(role.id) for role in member.roles]
    member_role_names = [role.name for role in member.roles]
    for r in role_ids:
        if r in member_role_ids or r in member_role_names:
            return True
    return False

@bot.event
async def on_ready():
    print(f"Bot készen áll! Bejelentkezve mint {bot.user}")
    process_queue.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Szerver szűrés
    if not is_allowed_server(message.guild.id):
        return

    # Csatorna ellenőrzés
    channel = message.channel
    if isinstance(channel, discord.TextChannel) and channel.is_news():
        perms = channel.permissions_for(channel.guild.me)
        if not perms.manage_messages:
            return

        now = datetime.utcnow()
        channel_id = channel.id

        if channel_id not in queues:
            queues[channel_id] = deque()
            published_counts[channel_id] = 0
            hour_starts[channel_id] = now

        if now - hour_starts[channel_id] >= timedelta(hours=1):
            hour_starts[channel_id] = now
            published_counts[channel_id] = 0

        if published_counts[channel_id] < 10:
            try:
                await message.publish()
                published_counts[channel_id] += 1
                print(f"[{now.isoformat()}] Publikálva {channel.name}: {message.id}")
            except Exception as e:
                print(f"Hiba a publish során: {e}")
                queues[channel_id].append((message, now))
        else:
            queues[channel_id].append((message, now))

# !darky parancs
@bot.event
async def on_message_create(message):
    if message.author == bot.user:
        return

    if not is_allowed_server(message.guild.id):
        return
    if not is_allowed_user(message.author.id):
        return
    if not has_allowed_role(message.author):
        return

    if message.content.lower() == "!darky":
        try:
            await message.channel.send("✅")
        except Exception as e:
            print(f"Hiba a !darky parancs során: {e}")

@tasks.loop(seconds=10)
async def process_queue():
    now = datetime.utcnow()
    for channel_id, queue in queues.items():
        if not queue:
            continue
        if now - hour_starts[channel_id] >= timedelta(hours=1):
            hour_starts[channel_id] = now
            published_counts[channel_id] = 0

        while queue and published_counts[channel_id] < 10:
            message, timestamp = queue.popleft()
            try:
                await message.publish()
                published_counts[channel_id] += 1
                print(f"[{datetime.utcnow().isoformat()}] Várólistás üzenet publikálva {message.channel.name}: {message.id}")
            except Exception as e:
                print(f"Hiba a várólistás publish során: {e}")
                queue.appendleft((message, timestamp))
                break

if __name__ == "__main__":
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=3000)).start()
    bot.run(DISCORD_TOKEN)
