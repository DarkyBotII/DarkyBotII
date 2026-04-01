import discord
from discord.ext import commands
from datetime import datetime, timedelta
import os
import requests

from dotenv import load_dotenv
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva!")

# ✅ HELYES GITHUB LINK
GITHUB_BASE = "https://raw.githubusercontent.com/DarkyBotII/DarkyBotII/main/"

def load_txt(filename):
    try:
        url = GITHUB_BASE + filename
        print(f"Betöltés: {url}")

        response = requests.get(url)

        if response.status_code == 200:
            lines = [line.strip() for line in response.text.splitlines() if line.strip()]
            print(f"Siker: {lines}")
            return lines
        else:
            print(f"HIBA {filename}: {response.status_code}")
            return []

    except Exception as e:
        print(f"TXT hiba: {e}")
        return []

def is_server_allowed(guild_id):
    server_ids = load_txt("serverid.txt")
    return str(guild_id).strip() in [x.strip() for x in server_ids]

def is_user_allowed(member):
    user_ids = load_txt("userid.txt")
    role_names = load_txt("rangid.txt")

    if str(member.id) in user_ids:
        return True

    for role in member.roles:
        if role.name in role_names:
            return True

    return False

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

published_counts = {}
hour_starts = {}
channel_toggle = {}

@bot.event
async def on_ready():
    print(f"Bot készen áll! {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # ❗ csak dbserverid ha nincs engedély
    if message.guild:
        if not is_server_allowed(message.guild.id):
            if message.content.strip().lower() != "!dbserverid":
                return

    # !darky
    if message.content.strip().lower() == "!darky":
        await message.channel.send("✅")

    channel = message.channel

    # 📢 announcement kezelés
    if isinstance(channel, discord.TextChannel) and channel.is_news():
        perms = channel.permissions_for(channel.guild.me)

        if not (perms.send_messages and perms.manage_messages):
            return

        now = datetime.utcnow()
        cid = channel.id

        if cid not in published_counts:
            published_counts[cid] = 0
            hour_starts[cid] = now

        if now - hour_starts[cid] >= timedelta(hours=1):
            hour_starts[cid] = now
            published_counts[cid] = 0

        if published_counts[cid] < 10:
            try:
                await message.publish()
                published_counts[cid] += 1

                # 📊 maradék számláló
                if channel_toggle.get(cid, False):
                    remaining = 10 - published_counts[cid]
                    await channel.send(f"📢 Maradék publish: {remaining}/10")

            except Exception as e:
                print(f"Hiba publish: {e}")

    await bot.process_commands(message)

# ---------------- COMMANDS ----------------

@bot.command()
async def dbserverid(ctx):
    if is_server_allowed(ctx.guild.id):
        await ctx.send("🟢 Engedélyezett szerver")
    else:
        await ctx.send("🔴 Nincs engedélyezve")

@bot.command()
async def dbon(ctx):
    if not is_server_allowed(ctx.guild.id):
        return
    if not is_user_allowed(ctx.author):
        return

    channel_toggle[ctx.channel.id] = True
    await ctx.send("🟢 Bekapcsolva")

@bot.command()
async def dboff(ctx):
    if not is_server_allowed(ctx.guild.id):
        return
    if not is_user_allowed(ctx.author):
        return

    channel_toggle[ctx.channel.id] = False
    await ctx.send("🔴 Kikapcsolva")

@bot.command()
async def dbhelp2(ctx):
    try:
        help_lines = load_txt("help2.txt")
        description = "\n".join(help_lines) if help_lines else "Nincs tartalom."

        embed = discord.Embed(
            title="📘 DarkyBot Help",
            description=description,
            color=discord.Color.blue()
        )

        embed.set_footer(text="Darky rendszer • segítség")
        embed.set_author(
            name=ctx.guild.name,
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )

        await ctx.send(embed=embed)

    except Exception:
        await ctx.send("❌ Hiba a help betöltésekor")

# ---------------- WEB SERVER ----------------

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

# ---------------- RUN ----------------

bot.run(DISCORD_TOKEN)
