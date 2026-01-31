# =====================
# LIMPIAR LOGS DISCORD
# =====================
import logging
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.client").setLevel(logging.WARNING)
logging.getLogger("discord.gateway").setLevel(logging.WARNING)

# =====================
# IMPORTS
# =====================
import discord
from discord import app_commands
from discord.ui import Button, View
import os
import psycopg2

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
# BOTONES CONFIRMACIÓN
# =====================
class Confirmacion(View):
    def __init__(self, accion_callback):
        super().__init__(timeout=30)
        self.accion_callback = accion_callback

        self.add_item(Button(label="✅ Sí", style=discord.ButtonStyle.green))
        self.add_item(Button(label="❌ Cancelar", style=discord.ButtonStyle.red))

    async def interaction_check(self, interaction: discord.Interaction):
        return True

    async def on_timeout(self):
        self.clear_items()

    async def on_error(self, interaction, error, item):
        await interaction.response.send_message("❌ Error inesperado", ephemeral=True)

# =====================
# AGREGAR
# =====================
@bot.tree.command(name="agregar", description="Agregar colonia")
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
        cursor.execute("""
        INSERT INTO colonias (alianza, jugador, coordenada, colonia, color)
        VALUES (%s, %s, %s, %s, %s)
        """, (alianza, jugador, coordenada, colonia, color))
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
# BUSCAR POR JUGADOR
# =====================
@bot.tree.command(name="buscar_jugador", description="Buscar colonias por jugador")
async def buscar_jugador(interaction: discord.Interaction, jugador: str):
    cursor.execute("SELECT * FROM colonias WHERE jugador ILIKE %s", (jugador,))
    datos = cursor.fetchall()

    if not datos:
        await interaction.response.send_message("❌ No se encontraron datos", ephemeral=True)
        return

    embed = discord.Embed(title=f"📋 Datos de {jugador}", color=0x3498db)

    for d in datos:
        embed.add_field(
            name=f"📍 {d[3]}",
            value=f"Alianza: {d[1]}\nColonia: {d[4]}\nColor: {d[5]}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# =====================
# BUSCAR POR ALIANZA
# =====================
@bot.tree.command(name="buscar_alianza", description="Buscar colonias por alianza")
async def buscar_alianza(interaction: discord.Interaction, alianza: str):
    cursor.execute("SELECT * FROM colonias WHERE alianza ILIKE %s", (alianza,))
    datos = cursor.fetchall()

    if not datos:
        await interaction.response.send_message("❌ No se encontraron datos", ephemeral=True)
        return

    embed = discord.Embed(title=f"🏳️ Alianza {alianza}", color=0xf1c40f)

    for d in datos:
        embed.add_field(
            name=f"👤 {d[2]}",
            value=f"Coord: {d[3]}\nColonia: {d[4]}\nColor: {d[5]}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# =====================
# EDITAR COORDENADA
# =====================
@bot.tree.command(name="editar_coordenada", description="Editar coordenada de un jugador")
async def editar_coordenada(
    interaction: discord.Interaction,
    jugador: str,
    nueva_coordenada: str
):
    cursor.execute("SELECT * FROM colonias WHERE jugador ILIKE %s", (jugador,))
    dato = cursor.fetchone()

    if not dato:
        await interaction.response.send_message("❌ Jugador no encontrado", ephemeral=True)
        return

    async def confirmar(inter):
        cursor.execute(
            "UPDATE colonias SET coordenada=%s WHERE jugador ILIKE %s",
            (nueva_coordenada, jugador)
        )
        conn.commit()
        await inter.response.edit_message(
            content=f"✅ Coordenada actualizada para **{jugador}**",
            view=None
        )

    view = View()
    view.add_item(Button(label="✅ Sí", style=discord.ButtonStyle.green, custom_id="si"))
    view.add_item(Button(label="❌ Cancelar", style=discord.ButtonStyle.red, custom_id="no"))

    async def callback(interaction2):
        if interaction2.data["custom_id"] == "si":
            await confirmar(interaction2)
        else:
            await interaction2.response.edit_message(content="❌ Acción cancelada", view=None)

    for item in view.children:
        item.callback = callback

    await interaction.response.send_message(
        f"⚠️ Estás a punto de **editar las coordenadas de {jugador}**",
        view=view,
        ephemeral=True
    )

# =====================
# ELIMINAR
# =====================
@bot.tree.command(name="eliminar_colonia", description="Eliminar colonia")
async def eliminar_colonia(interaction: discord.Interaction, jugador: str):
    cursor.execute("SELECT * FROM colonias WHERE jugador ILIKE %s", (jugador,))
    dato = cursor.fetchone()

    if not dato:
        await interaction.response.send_message("❌ Jugador no encontrado", ephemeral=True)
        return

    async def confirmar(inter):
        cursor.execute("DELETE FROM colonias WHERE jugador ILIKE %s", (jugador,))
        conn.commit()
        await inter.response.edit_message(
            content=f"🗑️ Colonia y coordenadas de **{jugador}** eliminadas",
            view=None
        )

    view = View()
    view.add_item(Button(label="✅ Sí", style=discord.ButtonStyle.green, custom_id="si"))
    view.add_item(Button(label="❌ Cancelar", style=discord.ButtonStyle.red, custom_id="no"))

    async def callback(interaction2):
        if interaction2.data["custom_id"] == "si":
            await confirmar(interaction2)
        else:
            await interaction2.response.edit_message(content="❌ Acción cancelada", view=None)

    for item in view.children:
        item.callback = callback

    await interaction.response.send_message(
        f"⚠️ Estás a punto de **eliminar la colonia y coordenadas de {jugador}**",
        view=view,
        ephemeral=True
    )

# =====================
# ARRANQUE
# =====================
bot.run(TOKEN)
