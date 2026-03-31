import discord
from discord.ext import tasks, commands
from collections import deque
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Lokális fejlesztéshez
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva. Ellenőrizd az Environment Variable-t!")

# Intents beállítása
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

# Bot létrehozása commands.Bot-tal
bot = commands.Bot(command_prefix="!", intents=intents)

# Csatornánkénti várólista és óránkénti limit
queues = {}
published_counts = {}
hour_starts = {}

@bot.event
async def on_ready():
    print(f"Bot készen áll! Bejelentkezve mint {bot.user}")
    process_queue.start()

# Announcement csatornák publish logika
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    channel = message.channel

    # !darky parancs
    if message.content.strip().lower() == "!darky":
        await channel.send("✅")
        return

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
                print(f"[{now.isoformat()}] Üzenet publikálva csatornában {channel.name}: {message.id}")
            except Exception as e:
                print(f"Hiba a publish során: {e}")
                queues[channel_id].append((message, now))
        else:
            queues[channel_id].append((message, now))

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
                print(f"[{datetime.utcnow().isoformat()}] Várólistás üzenet publikálva csatornában {message.channel.name}: {message.id}")
            except Exception as e:
                print(f"Hiba a várólistás publish során: {e}")
                queue.appendleft((message, timestamp))
                break

bot.run(DISCORD_TOKEN)
