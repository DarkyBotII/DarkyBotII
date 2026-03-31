import discord
from discord.ext import tasks
from collections import deque
from datetime import datetime, timedelta
import os
from threading import Thread
from flask import Flask

# === Környezeti változó ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva!")

# === Flask web szerver a uptime monitorhoz ===
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# === Discord bot beállítások ===
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = discord.Bot(intents=intents)

# === Announcement queue ===
queues = {}
published_counts = {}
hour_starts = {}

# === Fájlokból olvasás ===
def read_file_lines(filename):
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

ALLOWED_SERVERS = read_file_lines("serverid.txt")
ALLOWED_USERS = read_file_lines("userid.txt")
ALLOWED_ROLES = read_file_lines("rangid.txt")

# === Helper: ellenőrzés jogosultságra ===
def has_permission(member: discord.Member):
    # Felhasználó ID
    if str(member.id) in ALLOWED_USERS:
        return True
    # Rangnév vagy rang ID
    for role in member.roles:
        if role.name in ALLOWED_ROLES or str(role.id) in ALLOWED_ROLES:
            return True
    return False

# === Bot események ===
@bot.event
async def on_ready():
    print(f"Bot készen áll! Bejelentkezve mint {bot.user}")
    process_queue.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Csak engedélyezett szerverek
    if str(message.guild.id) not in ALLOWED_SERVERS:
        return

    channel = message.channel

    # Announcement csatorna limit
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

    # === Parancsok ===
    if message.content.lower() == "!darky":
        if not has_permission(message.author):
            await message.channel.send("Nincs jogosultságod ehhez a parancshoz!")
            return
        await message.channel.send("✅")  # zöld pipa

# === Queue feldolgozás ===
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

# === Bot indítása ===
bot.run(DISCORD_TOKEN)
