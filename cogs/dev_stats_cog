# --- Fichier : cogs/dev_stats_cog.py ---

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
import traceback
import subprocess
from datetime import datetime, timedelta, timezone

# --- ADAPTATION DES IMPORTS ---
import os
import dotenv
import config # Importez votre fichier config.py

# Chargez les variables d'environnement (comme GITHUB_TOKEN)
dotenv.load_dotenv() 

# Accès aux configurations
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

# Importez create_styled_embed et Logger depuis votre fichier config
# Assurez-vous que le chemin d'importation est correct
try:
    from config import create_styled_embed, Logger
except ImportError:
    # Fallback si le logger ou create_styled_embed ne sont pas dans config.py
    # Si vous les avez mis ailleurs, adaptez l'import.
    # Exemple de fallback :
    class Logger:
        @staticmethod
        def error(message: str):
            print(f"ERROR: {message}")
        @staticmethod
        def info(message: str):
            print(f"INFO: {message}")
    def create_styled_embed(title, description, color):
        embed = discord.Embed(title=title, description=description, color=color)
        return embed

# Assurez-vous que is_staff_or_owner est importé correctement
# from commands import is_staff_or_owner # Si is_staff_or_owner est dans un dossier commands
# Ou si c'est une fonction globale dans bot.py ou shared_utils (qui serait maintenant config)
# from config import is_staff_or_owner # Exemple si c'est dans config.py

# Si is_staff_or_owner est une fonction globale et non un décorateur importé,
# assurez-vous qu'elle est accessible. Si elle est définie dans un autre cog,
# son import et son utilisation peuvent être plus complexes.
# Pour cet exemple, je suppose qu'elle est importable.

# Assurez-vous que GITHUB_REPO_NAME est disponible ici aussi (il est chargé plus haut)


# --- Le Cog ---
class DevStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ... (get_commit_stats et get_loc_stats sont maintenant méthodes de cette classe) ...
    # ... (et elles utilisent les constantes chargées depuis l'environnement/.env) ...

    @app_commands.command(name="project_stats", description="[STAFF] Affiche les statistiques de développement du projet.")
    # @app_commands.check(is_staff_or_owner) # Assurez-vous que is_staff_or_owner est bien importé et accessible
    async def project_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            commit_task = asyncio.create_task(self.get_commit_stats())
            loc_task = asyncio.to_thread(self.get_loc_stats)

            commit_data, loc_data = await asyncio.gather(commit_task, loc_task)
            
            if "error" in commit_data:
                await interaction.followup.send(f"❌ Erreur GitHub : {commit_data['error']}", ephemeral=True)
                return
            if "error" in loc_data:
                await interaction.followup.send(f"❌ Erreur Locale : {loc_data['error']}", ephemeral=True)
                return

            # Utilisation de create_styled_embed importé depuis config
            embed = create_styled_embed(
                title=f"📊 Statistiques du Projet - {GITHUB_REPO_NAME}",
                description="Un aperçu de l'activité de développement du projet.",
                color=discord.Color.dark_green()
            )

            first_commit_ts = int(commit_data['first_commit_date'].timestamp())
            last_commit_ts = int(commit_data['last_commit_date'].timestamp())

            project_duration = commit_data['last_commit_date'] - commit_data['first_commit_date']
            project_duration_days = project_duration.days
            
            commit_text = (
                f"**Nombre total de commits :** `{commit_data['total_commits']}`\n"
                f"**Premier commit :** <t:{first_commit_ts}:D>\n"
                f"**Dernier commit :** <t:{last_commit_ts}:R>\n"
                f"**Durée du projet :** `{project_duration_days} jours`"
            )
            embed.add_field(name="⚙️ Activité des Commits", value=commit_text, inline=False)
            
            loc_text = (
                f"**Lignes de code :** `{loc_data['total_lines']:,}`\n"
                f"**Caractères :** `{loc_data['total_chars']:,}`\n"
                f"**Fichiers Python :** `{loc_data['total_files']}`"
            )
            embed.add_field(name="💻 Code Source (.py)", value=loc_text, inline=True)

            total_seconds = commit_data['estimated_duration'].total_seconds()
            total_hours = total_seconds / 3600
            time_text = f"**Estimation :**\n`{total_hours:.2f} heures`"
            embed.add_field(name="⏱️ Amplitude de Développement", value=time_text, inline=True)

            embed.set_footer(text="Données via API GitHub & commandes git locales.")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            Logger.error(f"Erreur dans /project_stats : {e}") # Utilisez votre logger
            traceback.print_exc()
            await interaction.followup.send("❌ Une erreur critique est survenue.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(DevStatsCog(bot))