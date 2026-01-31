import discord
from discord import app_commands
import os
import psycopg2

# =====================
# VARIABLES DE ENTORNO
# =====================
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN no encontrado")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no encontrado")

# =====================
# CONEXIÓN A POSTGRES
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
# COMANDO AGREGAR
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
            "INSERT INTO colonias (alianza, jugador, coordenada, colonia, color) VALUES (%s, %s, %s, %s, %s)",
            (alianza, jugador, coordenada, colonia, color)
        )
        conn.commit()

        embed = discord.Embed(title="✅ Colonia agregada", color=0x00ff00)
        embed.add_field(name="Alianza", value=alianza)
        embed.add_field(name="Jugador", value=jugador)
        embed.add_field(name="Coordenada", value=coordenada)
        embed.add_field(name="Colonia", value=colonia)
        embed.add_field(name="Color", value=color.capitalize())

        await interaction.response.send_message(embed=embed)

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        await interaction.response.send_message(
            "⚠️ Esa coordenada ya está registrada",
            ephemeral=True
        )

# =====================
# LISTAR ALIANZAS
# =====================
@bot.tree.command(name="listar_alianzas", description="Ver todas las alianzas registradas")
async def listar_alianzas(interaction: discord.Interaction):
    cursor.execute("SELECT DISTINCT alianza FROM colonias ORDER BY alianza")
    filas = cursor.fetchall()

    if not filas:
        await interaction.response.send_message("❌ No hay alianzas registradas")
        return

    alianzas = "\n".join(f"• {a[0]}" for a in filas)
    await interaction.response.send_message(f"📜 **Alianzas registradas:**\n{alianzas}")

# =====================
# VER ALIANZA
# =====================
@bot.tree.command(name="ver_alianza", description="Ver jugadores y colonias de una alianza")
async def ver_alianza(interaction: discord.Interaction, alianza: str):
    cursor.execute(
        "SELECT jugador, colonia, coordenada, color FROM colonias WHERE alianza = %s",
        (alianza,)
    )
    filas = cursor.fetchall()

    if not filas:
        await interaction.response.send_message("❌ No se encontraron datos para esa alianza")
        return

    mensaje = f"🏰 **Alianza {alianza}**\n\n"
    for jugador, colonia, coord, color in filas:
        mensaje += f"👤 {jugador} | 🏠 {colonia} | 📍 {coord} | 🎨 {color}\n"

    await interaction.response.send_message(mensaje)

# =====================
# EDITAR COORDENADA
# =====================
@bot.tree.command(name="editar_coord", description="Editar coordenada de una colonia")
async def editar_coord(
    interaction: discord.Interaction,
    antigua: str,
    nueva: str
):
    cursor.execute(
        "SELECT jugador, colonia, color FROM colonias WHERE coordenada = %s",
        (antigua,)
    )
    row = cursor.fetchone()

    if not row:
        await interaction.response.send_message(
            "❌ No se encontró ninguna colonia con esa coordenada",
            ephemeral=True
        )
        return

    jugador, colonia, color = row

    cursor.execute(
        "UPDATE colonias SET coordenada = %s WHERE coordenada = %s",
        (nueva, antigua)
    )
    conn.commit()

    await interaction.response.send_message(
        f"✏️ **Estás a punto de editar las coordenadas del jugador `{jugador}`**\n"
        f"🏠 Colonia: {colonia}\n"
        f"🎨 Color: {color}\n\n"
        f"✅ Coordenadas actualizadas: `{antigua}` → `{nueva}`"
    )

# =====================
# ELIMINAR COLONIA
# =====================
@bot.tree.command(name="eliminar", description="Eliminar una colonia por coordenada")
async def eliminar(interaction: discord.Interaction, coordenada: str):
    cursor.execute(
        "SELECT jugador, colonia, color FROM colonias WHERE coordenada = %s",
        (coordenada,)
    )
    row = cursor.fetchone()

    if not row:
        await interaction.response.send_message(
            "❌ No se encontró ninguna colonia con esa coordenada",
            ephemeral=True
        )
        return

    jugador, colonia, color = row

    cursor.execute(
        "DELETE FROM colonias WHERE coordenada = %s",
        (coordenada,)
    )
    conn.commit()

    await interaction.response.send_message(
        f"⚠️ **Estás a punto de eliminar la colonia y las coordenadas del jugador `{jugador}`**\n"
        f"🏠 Colonia: {colonia}\n"
        f"🎨 Color: {color}\n\n"
        f"🗑️ Colonia eliminada correctamente"
    )

# =====================
# ARRANQUE
# =====================
bot.run(TOKEN)
