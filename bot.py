import discord
from datetime import datetime, timedelta
import os

# Lokális fejlesztéshez dotenv
from dotenv import load_dotenv
load_dotenv()

# Token beolvasása
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva!")

# Intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

# Bot
bot = discord.Bot(intents=intents)

# Óránkénti limit tracking
published_counts = {}
hour_starts = {}

@bot.event
async def on_ready():
    print(f"Bot készen áll! Bejelentkezve mint {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # !darky parancs
    if message.content.strip().lower() == "!darky":
        try:
            await message.channel.send("✅")
        except Exception as e:
            print(f"Hiba a parancs küldésekor: {e}")

    channel = message.channel

    # Csak announcement (news) csatornák
    if isinstance(channel, discord.TextChannel) and channel.is_news():
        perms = channel.permissions_for(channel.guild.me)

        # Kell minden fontos jog!
        if not (perms.send_messages and perms.manage_messages):
            print("Hiányzó jogosultság!")
            return

        now = datetime.utcnow()
        channel_id = channel.id

        # Inicializálás
        if channel_id not in published_counts:
            published_counts[channel_id] = 0
            hour_starts[channel_id] = now

        # Óra reset
        if now - hour_starts[channel_id] >= timedelta(hours=1):
            hour_starts[channel_id] = now
            published_counts[channel_id] = 0

        # Debug
        print(f"Próbál publish: {message.id} | csatorna: {channel.name}")

        # Limit ellenőrzés
        if published_counts[channel_id] < 10:
            try:
                await message.publish()
                published_counts[channel_id] += 1
                print(f"[{now.isoformat()}] Publikálva: {message.id}")
            except Exception as e:
                print(f"Hiba publish során: {e}")
        else:
            print(f"[{now.isoformat()}] LIMIT ELÉRVE – kihagyva: {message.id}")

# --- Mini webserver Flask ---
from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return "Bot él!", 200

def run_webserver():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Webserver külön szálon
Thread(target=run_webserver).start()

# Bot indítása
bot.run(DISCORD_TOKEN)
