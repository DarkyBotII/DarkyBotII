import discord
from discord.ext import commands
import os
import requests
from flask import Flask
import threading
import re

# ===== UPTIME FLASK APP =====
app = Flask("")

@app.route("/")
def home():
    return "Bot is alive!"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# ===== LOAD LIST WITH [] SUPPORT =====
def load_list(filename):
    try:
        with open(filename, "r") as f:
            content = f.read()
            matches = re.findall(r"\[(.*?)\]", content)
            cleaned = [m.strip() for m in matches if m.strip()]
            
            print(f"[OK] {filename} betöltve: {cleaned}")
            return cleaned

    except FileNotFoundError:
        print(f"[HIBA] {filename} nem található!")
        return []

    except Exception as e:
        print(f"[HIBA] {filename} olvasási hiba: {e}")
        return []

# ===== LOAD IDS =====
allowed_servers = load_list("serverid.txt")
allowed_users = load_list("userid.txt")
allowed_roles = load_list("rangid.txt")

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== PERMISSION CHECK =====
def check_permissions(ctx):
    # SERVER CHECK
    if allowed_servers:
        if str(ctx.guild.id) not in allowed_servers:
            return False, "Ez a szerver nincs engedélyezve!"

    # USER CHECK
    if allowed_users:
        if str(ctx.author.id) not in allowed_users:
            return False, "Te nem használhatod ezt a parancsot!"

    # ROLE CHECK
    if allowed_roles:
        author_roles = [role.name for role in ctx.author.roles] + [str(role.id) for role in ctx.author.roles]
        
        if not any(r in allowed_roles for r in author_roles):
            return False, "Nincs megfelelő rangod!"

    return True, "OK"

# ===== COMMANDS =====
@bot.command()
async def ping(ctx):
    allowed, reason = check_permissions(ctx)

    if not allowed:
        await ctx.send(f"❌ {reason}")
        print(f"[TILTÁS] {ctx.author} → {reason}")
        return

    await ctx.send(f"🏓 Pong! Latency: {round(bot.latency*1000)}ms")
    print(f"[OK] ping: {ctx.author}")


@bot.command()
async def hello(ctx):
    allowed, reason = check_permissions(ctx)

    if not allowed:
        await ctx.send(f"❌ {reason}")
        print(f"[TILTÁS] {ctx.author} → {reason}")
        return

    await ctx.send(f"👋 Szia, {ctx.author.mention}!")
    print(f"[OK] hello: {ctx.author}")

# ===== EVENTS =====
@bot.event
async def on_ready():
    print(f"[START] {bot.user} elindult!")

    print("===== BETÖLTÖTT ADATOK =====")
    print("Servers:", allowed_servers)
    print("Users:", allowed_users)
    print("Roles:", allowed_roles)
    print("============================")


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    print(f"[ÜZENET] {message.author}: {message.content}")
    await bot.process_commands(message)

# ===== MAIN =====
if __name__ == "__main__":
    keep_alive()

    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

    if not DISCORD_TOKEN:
        print("[HIBA] Nincs DISCORD_TOKEN!")
    else:
        print("[INDÍTÁS] Bot indul...")
        bot.run(DISCORD_TOKEN)
