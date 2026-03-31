import discord
from discord.ext import tasks
import asyncio
from collections import deque
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = discord.Bot(intents=intents)

# Csatorna ID, ahol figyelni akarjuk az üzeneteket
ANNOUNCEMENT_CHANNEL_ID = 123456789012345678  # cseréld a saját ID-dra

# Üzenet várólista: minden elem (message, timestamp)
queue = deque()

# Időbélyeg és counter a limithez
published_count = 0
hour_start = datetime.utcnow()

@bot.event
async def on_ready():
    print(f'Bot készen áll! Bejelentkezve mint {bot.user}')
    process_queue.start()  # elindítjuk a várólista feldolgozást

@bot.event
async def on_message(message):
    global published_count, hour_start
    if message.channel.id != ANNOUNCEMENT_CHANNEL_ID:
        return
    if message.author == bot.user:
        return

    now = datetime.utcnow()
    if now - hour_start >= timedelta(hours=1):
        hour_start = now
        published_count = 0

    if published_count < 10:
        try:
            await message.publish()
            published_count += 1
            print(f"[{now.isoformat()}] Üzenet publikálva: {message.id}")
        except Exception as e:
            print(f"Hiba a publish során: {e}")
            queue.append((message, now))
    else:
        print(f"[{now.isoformat()}] Limit elérve, üzenet sorba állítva: {message.id}")
        queue.append((message, now))

@tasks.loop(seconds=10)
async def process_queue():
    global published_count, hour_start
    now = datetime.utcnow()
    if now - hour_start >= timedelta(hours=1):
        hour_start = now
        published_count = 0

    while queue and published_count < 10:
        message, timestamp = queue.popleft()
        try:
            await message.publish()
            published_count += 1
            print(f"[{datetime.utcnow().isoformat()}] Várólistás üzenet publikálva: {message.id} (eredeti érkezés: {timestamp.isoformat()})")
        except Exception as e:
            print(f"Hiba a várólistás publish során: {e}")
            queue.appendleft((message, timestamp))  # ha hiba, visszatesszük a queue elejére
            break  # ha hiba van, várjunk a következő ciklusra

bot.run("YOUR_BOT_TOKEN_HERE")