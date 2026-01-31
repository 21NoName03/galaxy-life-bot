import discord
from discord import app_commands
from discord.ui import View, Button
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
# BOTONES DE CONFIRMACIÓN
# =====================
class Confirmacion(View):
    def __init__(self, on_confirm):
        super().__init__(timeout=30)
        self.on_confirm = on_confirm

    @discord.ui.button(label="✅ Sí", style=discord.ButtonStyle.green)
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        await self.on_confirm(interaction)
        self.stop()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.red)
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="❌ Operación cancelada",
            view=None
        )
        self.stop()

# =====================
# AGREGAR COLONIA
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

        embed = discord.Embed(title="✅ Colonia agregada", color=0x00ff00)
        embed.add_field(name="Alianza", value=alianza, inline=False)
        embed.add_field(name="Jugador", value=jugador, inline=False)
        embed.add_field(name="Coordenada", value=coordenada, inline=False)
        embed.add_field(name="Colonia", value=colonia, inline=False)
        embed.add_field(name="Color", value=color.capitalize(), inline=False)

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

    async def ejecutar(inter):
        cursor.execute("""
            SELECT alianza, colonia, coordenada, color
            FROM colonias
            WHERE LOWER(jugador) = LOWER(%s)
        """, (jugador,))
        filas = cursor.fetchall()

        if not filas:
            await inter.response.edit_message(
                content=f"❌ No hay registros para **{jugador}**",
                view=None
            )
            return

        mensaje = f"👤 **Jugador: {jugador}**\n\n"
        for alianza, colonia, coord, color in filas:
            mensaje += (
                f"🏰 Alianza: {alianza}\n"
                f"🏠 Colonia: {colonia}\n"
                f"📍 Coordenada: {coord}\n"
                f"🎨 Color: {color}\n"
                f"──────────────\n"
            )

        await inter.response.edit_message(content=mensaje, view=None)

    await interaction.response.send_message(
        f"🔍 ¿Deseas ver los datos del jugador **{jugador}**?",
        view=Confirmacion(ejecutar),
        ephemeral=True
    )

# =====================
# BUSCAR POR ALIANZA
# =====================
@bot.tree.command(name="buscar_alianza", description="Buscar colonias por alianza")
async def buscar_alianza(interaction: discord.Interaction, alianza: str):

    async def ejecutar(inter):
        cursor.execute("""
            SELECT jugador, colonia, coordenada, color
            FROM colonias
            WHERE LOWER(alianza) = LOWER(%s)
            ORDER BY jugador
        """, (alianza,))
        filas = cursor.fetchall()

        if not filas:
            await inter.response.edit_message(
                content=f"❌ No hay registros para la alianza **{alianza}**",
                view=None
            )
            return

        mensaje = f"🛡️ **Alianza: {alianza}**\n\n"
        for jugador, colonia, coord, color in filas:
            mensaje += (
                f"👤 Jugador: {jugador}\n"
                f"🏠 Colonia: {colonia}\n"
                f"📍 Coordenada: {coord}\n"
                f"🎨 Color: {color}\n"
                f"──────────────\n"
            )

        await inter.response.edit_message(content=mensaje, view=None)

    await interaction.response.send_message(
        f"🔍 ¿Deseas ver todas las colonias de la alianza **{alianza}**?",
        view=Confirmacion(ejecutar),
        ephemeral=True
    )

# =====================
# EDITAR COORDENADA
# =====================
@bot.tree.command(name="editar_coordenada", description="Editar coordenada de un jugador")
async def editar_coordenada(
    interaction: discord.Interaction,
    coordenada_actual: str,
    nueva_coordenada: str
):
    cursor.execute(
        "SELECT jugador FROM colonias WHERE coordenada = %s",
        (coordenada_actual,)
    )
    fila = cursor.fetchone()

    if not fila:
        await interaction.response.send_message(
            "❌ No se encontró esa coordenada",
            ephemeral=True
        )
        return

    jugador = fila[0]

    async def ejecutar(inter):
        cursor.execute(
            "UPDATE colonias SET coordenada = %s WHERE coordenada = %s",
            (nueva_coordenada, coordenada_actual)
        )
        conn.commit()

        await inter.response.edit_message(
            content=f"✏️ Coordenadas de **{jugador}** actualizadas correctamente",
            view=None
        )

    await interaction.response.send_message(
        f"⚠️ Estás a punto de editar las coordenadas de **{jugador}**",
        view=Confirmacion(ejecutar),
        ephemeral=True
    )

# =====================
# ELIMINAR COLONIA
# =====================
@bot.tree.command(name="eliminar", description="Eliminar colonia por coordenada")
async def eliminar(interaction: discord.Interaction, coordenada: str):

    cursor.execute(
        "SELECT jugador FROM colonias WHERE coordenada = %s",
        (coordenada,)
    )
    fila = cursor.fetchone()

    if not fila:
        await interaction.response.send_message(
            "❌ No se encontró esa coordenada",
            ephemeral=True
        )
        return

    jugador = fila[0]

    async def ejecutar(inter):
        cursor.execute(
            "DELETE FROM colonias WHERE coordenada = %s",
            (coordenada,)
        )
        conn.commit()

        await inter.response.edit_message(
            content=f"🗑️ Se eliminó la colonia y coordenadas de **{jugador}**",
            view=None
        )

    await interaction.response.send_message(
        f"⚠️ Estás a punto de eliminar la colonia y coordenadas de **{jugador}**",
        view=Confirmacion(ejecutar),
        ephemeral=True
    )

# =====================
# ARRANQUE
# =====================
bot.run(TOKEN)

