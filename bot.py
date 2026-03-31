import discord
from discord.ext import tasks, commands
from collections import deque
from datetime import datetime, timedelta
import os

# A dotenv csak lokális fejlesztéshez kell, Render-en a környezeti változókat használjuk
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

# Bot létrehozása prefix-szel
bot = commands.Bot(command_prefix="!", intents=intents)

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
    # Ne reagáljunk saját üzenetre
    if message.author == bot.user:
        return

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

    # Fontos: commands.Bot használatakor mindig hívd az on_message végén
    await bot.process_commands(message)

@tasks.loop(seconds=10)
async def process_queue():
    now = datetime.utcnow()
    for channel_id, queue in queues.items():
        if not queue:
            continue

        # Óraellenőrzés
        if now - hour_starts[channel_id] >= timedelta(hours=1):
            hour_starts[channel_id] = now
            published_counts[channel_id] = 0

        # Várólista feldolgozása
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

# Parancs: !darky -> küld egy zöld pipát
@bot.command(name="darky")
async def darky_command(ctx):
    try:
        # ✅ emoji Unicode
        await ctx.send("✅")
    except Exception as e:
        print(f"Hiba a !darky parancs során: {e}")

# Bot futtatása
bot.run(DISCORD_TOKEN)
