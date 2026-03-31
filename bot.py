import discord
from discord.ext import commands
import os
import requests
from flask import Flask
import threading

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

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== LOAD IDS AND ROLES =====
def load_list(filename):
    """Betölt soronként, üres lista ha nincs fájl vagy üres"""
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

allowed_servers = load_list("serverid.txt")  # csak ezekben fut
allowed_users = load_list("userid.txt")      # csak ezek használhatják a parancsokat
allowed_roles = load_list("rangid.txt")      # csak ezek a rangok használhatják

# ===== CHECK DECORATOR =====
def check_permissions(ctx):
    # Szerver ellenőrzés
    if allowed_servers and str(ctx.guild.id) not in allowed_servers:
        return False

    # Felhasználó ellenőrzés
    if allowed_users and str(ctx.author.id) not in allowed_users:
        return False

    # Rang ellenőrzés
    if allowed_roles:
        author_roles = [role.name for role in ctx.author.roles] + [str(role.id) for role in ctx.author.roles]
        if not any(r in allowed_roles for r in author_roles):
            return False

    return True

# ===== COMMANDS =====
@bot.command()
async def ping(ctx):
    if not check_permissions(ctx):
        await ctx.send("Nincs jogosultságod ehhez a parancshoz!")
        return
    await ctx.send(f"Pong! 🏓 Latency: {round(bot.latency*1000)}ms")

@bot.command()
async def hello(ctx):
    if not check_permissions(ctx):
        await ctx.send("Nincs jogosultságod ehhez a parancshoz!")
        return
    await ctx.send(f"Szia, {ctx.author.mention}!")

# ===== EVENTS =====
@bot.event
async def on_ready():
    print(f"{bot.user} elindult és készen áll!")

# ===== MAIN =====
if __name__ == "__main__":
    keep_alive()  # Flask uptime ping
    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        print("Nincs DISCORD_TOKEN környezeti változó!")
    else:
        bot.run(DISCORD_TOKEN)
        
