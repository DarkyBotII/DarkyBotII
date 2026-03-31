import discord
from discord.ext import commands
import os
from flask import Flask
import threading
import re

# ===== FLASK UPTIME =====
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


# ===== CONFIG =====
allowed_servers = load_list("serverid.txt")  # csak ezekben a szerverekben engedélyezett
allowed_users = load_list("userid.txt")      # user ID-k
allowed_roles = load_list("rangid.txt")      # rang ID vagy név


# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ===== PERMISSION CHECK FOR DARKY =====
def check_permissions(ctx):
    # Csak az adott szerverben engedélyezett
    if allowed_servers and str(ctx.guild.id) not in allowed_servers:
        return False, "Ez a szerver nincs engedélyezve!"

    # USER vagy ROLE elég
    user_allowed = str(ctx.author.id) in allowed_users
    roles_allowed = any(str(role.id) in allowed_roles or role.name in allowed_roles for role in ctx.author.roles)

    if not (user_allowed or roles_allowed):
        return False, "Nincs engedélyed a parancs használatára!"

    return True, "OK"


# ===== AUTOMATIC CROSSPOST =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Csak Announcement / News csatornák
    if getattr(message.channel, "is_news", lambda: False)():
        # Ellenőrizni, hogy a bot küldhet-e
        if message.channel.permissions_for(message.guild.me).send_messages:
            try:
                # Crosspostolja az üzenetet, mintha manuálisan nyomtad volna
                await message.crosspost()
                print(f"[CROSSPOST] {message.author} üzenete közzétéve: {message.channel}")
            except Exception as e:
                print(f"[HIBA] Crosspost sikertelen: {e}")

    # Parancsok feldolgozása
    await bot.process_commands(message)


# ===== COMMAND =====
@bot.command()
async def darky(ctx):
    allowed, reason = check_permissions(ctx)
    if not allowed:
        await ctx.send(f"❌ {reason}")
        print(f"[TILTÁS] {ctx.author} → {reason}")
        return
    await ctx.send(f"✅ {ctx.author.mention} sikeresen használta a !darky parancsot!")


# ===== BOT READY =====
@bot.event
async def on_ready():
    print(f"[START] {bot.user} elindult!")
    print("===== BETÖLTÖTT ADATOK =====")
    print("Servers:", allowed_servers)
    print("Users:", allowed_users)
    print("Roles:", allowed_roles)
    print("============================")


# ===== MAIN =====
if __name__ == "__main__":
    keep_alive()

    DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

    if not DISCORD_TOKEN:
        print("[HIBA] Nincs DISCORD_TOKEN!")
    else:
        print("[INDÍTÁS] Bot indul...")
        bot.run(DISCORD_TOKEN)
