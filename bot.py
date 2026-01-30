import discord
from discord import app_commands
import os
import psycopg2
from psycopg2 import errors

# =====================
# VARIABLES DE ENTORNO
# =====================
TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise RuntimeError("TOKEN no encontrado")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no encontrada")

# =====================
# BASE DE DATOS
# =====================
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS colonias (
    id SERIAL PRIMARY KEY,
    alianza TEXT,
    jugador TEXT,
    coordenada TEXT UNIQUE,
    colonia TEXT,
    color TEXT
)
""")
conn.commit()

# =====================
# BOT
# =====================
class GalaxyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = GalaxyBot()

COLORES_VALIDOS = ["verde", "azul", "blanco", "amarillo", "morado", "rojo"]

@bot.event
async def on_ready():
    print(f"🟢 Bot conectado como {bot.user}")

# =====================
# COMANDO /agregar
# =====================
@bot.tree.command(name="agregar", description="Agregar colonia Galaxy Life")
async def agregar(
    interaction: discord.Interaction,
    alianza: str,
    jugador: str,
    coordenada: str,
    colonia: str,
    color: str
):
    color = color.lower()

    if color not in COLORES_VALIDOS:
        await interaction.response.send_message(
            f"❌ Color inválido. Usa: {', '.join(COLORES_VALIDOS)}",
            ephemeral=True
        )
        return

    try:
        cursor.execute(
            """
            INSERT INTO colonias (alianza, jugador, coordenada, colonia, color)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (alianza, jugador, coordenada, colonia, color)
        )
        conn.commit()

        embed = discord.Embed(
            title="✅ Colonia agregada",
            color=0x00ff00
        )
        embed.add_field(name="Alianza", value=alianza)
        embed.add_field(name="Jugador", value=jugador)
        embed.add_field(name="Coordenada", value=coordenada)
        embed.add_field(name="Colonia", value=colonia)
        embed.add_field(name="Color", value=color.capitalize())

        await interaction.response.send_message(embed=embed)

    except errors.UniqueViolation:
        conn.rollback()
        await interaction.response.send_message(
            "⚠️ Esa coordenada ya está registrada",
            ephemeral=True
        )

# =====================
# ARRANQUE
# =====================
bot.run(TOKEN)
