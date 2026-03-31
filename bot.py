import discord
from discord.ext import tasks
from collections import deque
from datetime import datetime, timedelta
import os
import requests
from flask import Flask
from threading import Thread

from dotenv import load_dotenv
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva!")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True  # Szükséges a rangok lekéréséhez

bot = discord.Bot(intents=intents)

queues = {}
published_counts = {}
hour_starts = {}

# --- GitHub fájlokból ID listák ---
SERVER_LIST_URL = "https://raw.githubusercontent.com/DarkyBotII/DarkyBotII/main/serverid.txt"
USER_LIST_URL   = "https://raw.githubusercontent.com/DarkyBotII/DarkyBotII/main/userid.txt"
ROLE_LIST_URL   = "https://raw.githubusercontent.com/DarkyBotII/DarkyBotII/main/rangid.txt"

def fetch_id_list(url):
    try:
        r = requests.get(url)
        r.raise_for_status()
        return [line.strip() for line in r.text.splitlines() if line.strip()]
    except Exception as e:
        print(f"Hiba ID lista betöltésekor: {e}")
        return []

ALLOWED_SERVERS = [int(x) for x in fetch_id_list(SERVER_LIST_URL)]
ALLOWED_USERS   = [int(x) for x in fetch_id_list(USER_LIST_URL)]
ALLOWED_ROLES   = fetch_id_list(ROLE_LIST_URL)  # lehet ID vagy név

@bot.event
async def on_ready():
    print(f"Bot készen áll! Bejelentkezve mint {bot.user}")
    process_queue.start()

def has_role_permission(member: discord.Member):
    for role in member.roles:
        if str(role.id) in ALLOWED_ROLES or role.name in ALLOWED_ROLES:
            return True
    return False

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # --- Csak engedélyezett szerverek ---
    if message.guild and message.guild.id not in ALLOWED_SERVERS:
        return

    # --- Parancs ellenőrzés ---
    if message.content.strip().lower() == "!darky":
        allowed = message.author.id in ALLOWED_USERS or has_role_permission(message.author)
        if not allowed:
            await message.channel.send("❌ Nincs jogod használni ezt a parancsot.")
            return
        await message.channel.send("✅")

    # Announcement csatorna feldolgozás
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

# --- Mini webserver Flask + threading ---
app = Flask("")

@app.route("/")
def home():
    return "Bot él!", 200

def run_webserver():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_webserver).start()

bot.run(DISCORD_TOKEN)
