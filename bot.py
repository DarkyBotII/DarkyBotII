import discord
from discord.ext import commands
import os
from flask import Flask
import threading
import re
import asyncio
import time
from collections import deque

# ===== FLASK =====
app = Flask("")

@app.route("/")
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = threading.Thread(target=run)
    t.start()


# ===== LOAD LIST =====
def load_list(filename):
    try:
        with open(filename, "r") as f:
            content = f.read()
            matches = re.findall(r"\[(.*?)\]", content)
            return [m.strip() for m in matches if m.strip()]
    except:
        return []

allowed_servers = load_list("serverid.txt")
allowed_users = load_list("userid.txt")
allowed_roles = load_list("rangid.txt")


# ===== BOT =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ===== RATE LIMIT =====
queue = deque()
timestamps = deque()  # utolsó crosspost időpontok


# ===== PERMISSION =====
def check_permissions(ctx):
    if allowed_servers and str(ctx.guild.id) not in allowed_servers:
        return False, "Ez a szerver nincs engedélyezve!"

    user_ok = str(ctx.author.id) in allowed_users
    role_ok = any(str(r.id) in allowed_roles or r.name in allowed_roles for r in ctx.author.roles)

    if not (user_ok or role_ok):
        return False, "Nincs jogod!"

    return True, "OK"


# ===== COMMAND =====
@bot.command()
async def darky(ctx):
    ok, reason = check_permissions(ctx)
    if not ok:
        await ctx.send(f"❌ {reason}")
        return
    await ctx.send("✅ Működik")


# ===== MESSAGE =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # csak announcement csatorna
    if getattr(message.channel, "is_news", lambda: False)():
        queue.append({
            "channel_id": message.channel.id,
            "content": message.content,
            "author": message.author.display_name
        })
        print(f"[QUEUE] {message.content}")

    await bot.process_commands(message)


# ===== WORKER =====
async def worker():
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = time.time()

        # töröljük az 1 óránál régebbi timestamp-eket
        while timestamps and now - timestamps[0] > 3600:
            timestamps.popleft()

        # ha van hely (max 10/óra)
        if len(timestamps) < 10 and queue:
            data = queue.popleft()

            channel = bot.get_channel(data["channel_id"])
            if channel:
                try:
                    msg = await channel.send(f"**{data['author']}**: {data['content']}")
                    await msg.crosspost()

                    timestamps.append(time.time())

                    print(f"[OK] Közétéve: {data['content']}")

                except Exception as e:
                    print(f"[HIBA] {e}")

        await asyncio.sleep(5)  # 5 másodpercenként próbál


# ===== READY =====
@bot.event
async def on_ready():
    print(f"[START] {bot.user}")
    bot.loop.create_task(worker())


# ===== MAIN =====
if __name__ == "__main__":
    keep_alive()

    TOKEN = os.environ.get("DISCORD_TOKEN")

    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Nincs token!")
