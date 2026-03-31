import discord
from discord.ext import tasks
from collections import deque
from datetime import datetime, timedelta
import os
import asyncio

# Lokális fejlesztéshez dotenv
from dotenv import load_dotenv
load_dotenv()

# Token beolvasása környezeti változóból
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva. Ellenőrizd az Environment Variable-t!")

# Intents beállítása
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

# Bot létrehozása
bot = discord.Bot(intents=intents)

# Csatornánkénti várólista és óra alapú publikálás követése
queues = {}            # queues[channel_id] = deque([(message, timestamp), ...])
published_counts = {}  # csatornánként
hour_starts = {}       # csatornánként

@bot.event
async def on_ready():
    print(f"Bot készen áll! Bejelentkezve mint {bot.user}")
    process_queue.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Parancs: !darky -> írjon zöld pipát az adott csatornába
    if message.content.strip().lower() == "!darky":
        try:
            await message.channel.send("✅")
        except Exception as e:
            print(f"Hiba a parancs küldésekor: {e}")

    channel = message.channel

    # Csak announcement csatornákban próbálkozunk
    if isinstance(channel, discord.TextChannel) and channel.is_news():
        perms = channel.permissions_for(channel.guild.me)
        if not perms.manage_messages:
            return

        now = datetime.utcnow()
        channel_id = channel.id

        # Inicializálás, ha még nincs csatornához adat
        if channel_id not in queues:
            queues[channel_id] = deque()
            published_counts[channel_id] = 0
            hour_starts[channel_id] = now

        # Óraellenőrzés
        if now - hour_starts[channel_id] >= timedelta(hours=1):
            hour_starts[channel_id] = now
            published_counts[channel_id] = 0

        # Publikálás vagy várólistára tétel
        if published_counts[channel_id] < 10:
            try:
                await message.publish()
                published_counts[channel_id] += 1
                print(f"[{now.isoformat()}] Üzenet publikálva csatornában {channel.name}: {message.id}")
            except Exception as e:
                print(f"Hiba a publish során: {e}")
                queues[channel_id].append((message, now))
        else:
            print(f"[{now.isoformat()}] Limit elérve, üzenet sorba állítva csatornában {channel.name}: {message.id}")
            queues[channel_id].append((message, now))

@tasks.loop(seconds=10)
async def process_queue():
    now = datetime.utcnow()
    for channel_id, queue in queues.items():
        if not queue:
            continue

        # Óraellenőrzés csatornánként
        if now - hour_starts[channel_id] >= timedelta(hours=1):
            hour_starts[channel_id] = now
            published_counts[channel_id] = 0

        # Várólista feldolgozása az óránkénti limitig
        while queue and published_counts[channel_id] < 10:
            message, timestamp = queue.popleft()
            try:
                await message.publish()
                published_counts[channel_id] += 1
                print(f"[{datetime.utcnow().isoformat()}] Várólistás üzenet publikálva csatornában {message.channel.name}: {message.id} (eredeti: {timestamp.isoformat()})")
            except Exception as e:
                print(f"Hiba a várólistás publish során: {e}")
                queue.appendleft((message, timestamp))
                break

# --- Mini webserver Flask + asyncio ---
from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return "Bot él!", 200

def run_webserver():
    port = int(os.environ.get("PORT", 8080))  # Render adja a portot
    app.run(host="0.0.0.0", port=port)

# Webserver indítása külön szálon
Thread(target=run_webserver).start()

# Bot futtatása
bot.run(DISCORD_TOKEN)
