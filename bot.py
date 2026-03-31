import discord
from discord.ext import tasks
from collections import deque
from datetime import datetime, timedelta
import os

from dotenv import load_dotenv
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN nincs beállítva!")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = discord.Bot(intents=intents)

queues = {}             # channel_id -> deque(messages)
published_counts = {}   # channel_id -> int
hour_starts = {}        # channel_id -> datetime
processed_messages = set()  # loop védelem


@bot.event
async def on_ready():
    print(f"Bot online: {bot.user}")
    process_queue.start()


@bot.event
async def on_message(message):
    # ❗ LOOP VÉDELEM (EZ A LEGFONTOSABB)
    if message.author.bot:
        return

    if message.flags.crossposted:
        return

    if message.type != discord.MessageType.default:
        return

    if message.id in processed_messages:
        return

    processed_messages.add(message.id)

    channel = message.channel

    # ❗ csak announcement csatorna
    if not isinstance(channel, discord.TextChannel):
        return

    if not channel.is_news():
        return

    # ❗ jogosultság check
    perms = channel.permissions_for(channel.guild.me)
    if not perms.manage_messages:
        return

    now = datetime.utcnow()
    cid = channel.id

    # inicializálás
    if cid not in queues:
        queues[cid] = deque()
        published_counts[cid] = 0
        hour_starts[cid] = now

    # ⏱️ 1 órás reset
    if now - hour_starts[cid] >= timedelta(hours=1):
        hour_starts[cid] = now
        published_counts[cid] = 0

    # 🚀 publish vagy queue
    if published_counts[cid] < 10:
        try:
            await message.publish()
            published_counts[cid] += 1
            print(f"Publikálva: {message.id}")
        except Exception as e:
            print(f"Publish hiba: {e}")
            queues[cid].append(message)
    else:
        queues[cid].append(message)
        print(f"Queue-ba rakva: {message.id}")


@tasks.loop(seconds=10)
async def process_queue():
    now = datetime.utcnow()

    for cid, queue in queues.items():
        if not queue:
            continue

        # ⏱️ 1 órás reset
        if now - hour_starts[cid] >= timedelta(hours=1):
            hour_starts[cid] = now
            published_counts[cid] = 0
            print(f"Limit reset csatornában: {cid}")

        # 📤 queue feldolgozás
        while queue and published_counts[cid] < 10:
            message = queue.popleft()
            try:
                await message.publish()
                published_counts[cid] += 1
                print(f"Queue publish: {message.id}")
            except Exception as e:
                print(f"Queue hiba: {e}")
                queue.appendleft(message)
                break


# --- Webserver (Render) ---
from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return "Bot él!", 200


def run_webserver():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


Thread(target=run_webserver).start()

bot.run(DISCORD_TOKEN)
