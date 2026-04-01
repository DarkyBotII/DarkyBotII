import discord
from discord.ext import commands
from datetime import datetime, timedelta
import os
import requests
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("A DISCORD_TOKEN nincs beállítva!")

# GitHub base URL
GITHUB_BASE = "https://raw.githubusercontent.com/DarkyBotII/DarkyBotII/main/"

# ---------- TXT BETÖLTÉS ----------
def load_txt(filename):
    try:
        url = GITHUB_BASE + filename
        response = requests.get(url)
        if response.status_code == 200:
            return [line.strip() for line in response.text.splitlines() if line.strip()]
        else:
            print(f"HIBA {filename}: {response.status_code}")
            return []
    except Exception as e:
        print(f"TXT betöltési hiba: {e}")
        return []

def load_ban_txt(filename):
    return load_txt(filename)

# ---------- JOGOSULTSÁGOK ----------
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

# ---------- TILTOTT ÜZENETEK ----------
def is_message_banned(message):
    # 1. Parancsok tiltása
    if message.content.strip().startswith("!"):
        return True
    # 2. Felhasználói tiltás
    banned_users = load_ban_txt("userban.txt")
    if str(message.author.id) in banned_users:
        return True
    # 3. Rang tiltás
    banned_roles = load_ban_txt("rangban.txt")
    user_roles = [role.name for role in message.author.roles]
    for role in user_roles:
        if role in banned_roles:
            return True
    return False

# ---------- BOT BEÁLLÍTÁS ----------
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

published_counts = {}
hour_starts = {}
channel_toggle = {}

# ---------- EVENT: READY ----------
@bot.event
async def on_ready():
    print(f"Bot készen áll! Bejelentkezve mint {bot.user}")

# ---------- EVENT: ON_MESSAGE ----------
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Parancsok mindenképp kezelve a végén
    content_lower = message.content.strip().lower()

    # !darky parancs
    if content_lower == "!darky":
        await message.channel.send("✅")

    channel = message.channel

    # Announcement csatorna publish logika
    if isinstance(channel, discord.TextChannel) and channel.is_news():
        perms = channel.permissions_for(channel.guild.me)
        if not (perms.send_messages and perms.manage_messages):
            return

        # Csak publish-re vonatkozó tiltások
        if is_message_banned(message):
            print(f"Üzenet kihagyva (banned/parancs): {message.id}")
        else:
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
                    if channel_toggle.get(cid, False):
                        remaining = 10 - published_counts[cid]
                        await channel.send(f"📢 Maradék publish: {remaining}/10")
                except Exception as e:
                    print(f"Hiba publish: {e}")

    # ⚡ Parancsok mindig futnak minden csatornában
    await bot.process_commands(message)

# ---------- COMMANDS ----------
@bot.command()
async def dbserverid(ctx):
    """Ellenőrzi, hogy a szerver engedélyezett-e"""
    if is_server_allowed(ctx.guild.id):
        await ctx.send("🟢 Engedélyezett szerver")
    else:
        await ctx.send("🔴 Nincs engedélyezve")

@bot.command()
async def dbuserid(ctx):
    """Ellenőrzi, hogy a felhasználó engedélyezett-e"""
    if is_user_allowed(ctx.author):
        await ctx.send(f"🟢 {ctx.author.mention} – Engedélyezve")
    else:
        await ctx.send(f"🔴 {ctx.author.mention} – Nincs engedély")

@bot.command()
async def dbon(ctx):
    """Bekapcsolja a maradék publish számlálót az aktuális csatornában"""
    if not is_server_allowed(ctx.guild.id):
        return
    if not is_user_allowed(ctx.author):
        return
    channel_toggle[ctx.channel.id] = True
    await ctx.send("🟢 Bekapcsolva")

@bot.command()
async def dboff(ctx):
    """Kikapcsolja a maradék publish számlálót az aktuális csatornában"""
    if not is_server_allowed(ctx.guild.id):
        return
    if not is_user_allowed(ctx.author):
        return
    channel_toggle[ctx.channel.id] = False
    await ctx.send("🔴 Kikapcsolva")

@bot.command()
async def dbhelp2(ctx):
    help_lines = load_txt("help2.txt")
    if not help_lines:
        await ctx.send("❌ Nem található a help2.txt vagy üres!")
        return
    description = "\n".join(help_lines)
    embed = discord.Embed(
        title="📘 DarkyBot Help",
        description=description,
        color=discord.Color.blue()
    )
    embed.set_footer(text="Darky rendszer • segítség")
    icon_url = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
    embed.set_author(name=ctx.guild.name if ctx.guild else "DarkyBot", icon_url=icon_url)
    await ctx.send(embed=embed)

@bot.command()
async def dbidlist(ctx):
    """Listázza az engedélyezett szerverek és felhasználók neveit embedben"""
    server_lines = load_txt("serverid.txt")
    server_names = [server_lines[i].strip() for i in range(0, len(server_lines)-1, 2)]

    user_lines = load_txt("userid.txt")
    user_names = [user_lines[i].strip() for i in range(0, len(user_lines)-1, 2)]

    embed = discord.Embed(
        title="📋 Engedélyezett ID Lista",
        color=discord.Color.green()
    )
    embed.add_field(name="🏰 Engedélyezett szerverek", value="\n".join(server_names) if server_names else "Nincs szerver", inline=False)
    embed.add_field(name="👤 Engedélyezett felhasználók", value="\n".join(user_names) if user_names else "Nincs felhasználó", inline=False)

    embed.set_footer(text="Darky rendszer • ID lista")
    icon_url = ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None
    embed.set_author(name=ctx.guild.name if ctx.guild else "DarkyBot", icon_url=icon_url)
    await ctx.send(embed=embed)

# ---------- MINI WEBSERVER ----------
app = Flask("")
@app.route("/")
def home():
    return "Bot él!", 200
def run_webserver():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
Thread(target=run_webserver).start()

# ---------- RUN BOT ----------
bot.run(DISCORD_TOKEN)
