# --- Fichier : cogs/dev_stats_cog.py ---

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
import traceback
import subprocess
from datetime import datetime, timedelta, timezone
import os
import dotenv
from utils.embed_builder import create_styled_embed # Assurez-vous que le chemin est correct

# --- Imports des configurations et utilitaires ---
dotenv.load_dotenv() 
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")

# Fallbacks pour les imports si ce n'est pas dans config.py
try:
    from config import create_styled_embed, Logger
except ImportError:
    class Logger:
        @staticmethod
        def error(message: str):
            print(f"ERROR: {message}")
        @staticmethod
        def info(message: str):
            print(f"INFO: {message}")

# Assurez-vous que is_staff_or_owner est importé correctement
# from commands import is_staff_or_owner 

# --- Le Cog ---
class DevStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --- Les fonctions SONT MAINTENANT des méthodes de classe ---
    async def get_commit_stats(self) -> dict: # <-- DOIT avoir 'self'
        # ... (votre code actuel pour get_commit_stats) ...
        if not all([GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME]):
            return {"error": "Configuration GitHub manquante (vérifiez .env et config.py)."}

        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/commits"
        
        all_commits = []
        page = 1
        
        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    params = {"per_page": 100, "page": page}
                    async with session.get(api_url, headers=headers, params=params) as response:
                        if response.status == 404:
                            return {"error": f"Le dépôt '{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}' n'a pas été trouvé sur GitHub."}
                        if response.status == 401:
                            return {"error": "Token GitHub invalide ou expiré."}
                        response.raise_for_status()
                        
                        data = await response.json()
                        if not data:
                            break
                        all_commits.extend(data)
                        page += 1
        except aiohttp.ClientError as e:
            print(f"Erreur réseau ou API GitHub : {e}") # Utilisez votre logger
            return {"error": f"Erreur réseau lors de la connexion à GitHub : {e}"}
        except Exception as e:
            print(f"Erreur imprévue dans get_commit_stats : {e}") # Utilisez votre logger
            traceback.print_exc()
            return {"error": f"Une erreur inattendue est survenue : {e}"}

        if not all_commits:
            return {"error": "Aucune commit trouvée pour ce dépôt."}

        daily_sessions = {}
        for commit in all_commits:
            commit_date_str = commit['commit']['author']['date']
            commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
            day = commit_date.date()
            
            if day not in daily_sessions:
                daily_sessions[day] = []
            daily_sessions[day].append(commit_date)

        total_duration = timedelta(0)
        for day, commits_in_day in daily_sessions.items():
            if len(commits_in_day) > 1:
                first_commit = min(commits_in_day)
                last_commit = max(commits_in_day)
                session_duration = last_commit - first_commit
                total_duration += session_duration

        return {
            "total_commits": len(all_commits),
            "estimated_duration": total_duration,
            "first_commit_date": datetime.fromisoformat(all_commits[-1]['commit']['author']['date'].replace('Z', '+00:00')),
            "last_commit_date": datetime.fromisoformat(all_commits[0]['commit']['author']['date'].replace('Z', '+00:00'))
        }

    def get_loc_stats(self) -> dict: # Cette fonction n'est pas async car elle utilise subprocess
        try:
            pathspec = '*.py'

            files_process = subprocess.run(
                ['git', 'ls-files', '-z', pathspec], 
                capture_output=True, text=True, check=True
            )
            file_list = files_process.stdout.strip().split('\0')
            total_files = len(file_list) if file_list and file_list[0] else 0

            if total_files == 0:
                return {"total_lines": 0, "total_chars": 0, "total_files": 0}

            git_process = subprocess.Popen(['git', 'ls-files', '-z', pathspec], stdout=subprocess.PIPE)
            wc_process = subprocess.Popen(['xargs', '-0', 'wc'], stdin=git_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            git_process.stdout.close()
            output, stderr_output = wc_process.communicate()
            
            if wc_process.returncode != 0 or git_process.returncode != 0:
                error_msg = f"git/wc error (wc ret: {wc_process.returncode}, git ret: {git_process.returncode}). Stderr: {stderr_output}"
                print(error_msg) # Utilisez votre logger
                return {"error": "Erreur lors de l'exécution des commandes git locales."}

            lines = output.strip().split('\n')
            if not lines:
                return {"total_lines": 0, "total_chars": 0, "total_files": 0}
                
            total_line = lines[-1]
            parts = total_line.split()
            
            total_lines = int(parts[0])
            total_chars = int(parts[-1])

            return {
                "total_lines": total_lines,
                "total_chars": total_chars,
                "total_files": total_files
            }

        except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError) as e:
            error_msg = f"Erreur lors de l'exécution de git/wc : {e}"
            print(error_msg) # Utilisez votre logger
            return {"error": "Impossible d'exécuter les commandes git locales."}

    # --- La commande Slash ---
    @app_commands.command(name="project_stats", description="[STAFF] Affiche les statistiques de développement du projet.")
    # @app_commands.check(is_staff_or_owner) # Assurez-vous que is_staff_or_owner est bien importé et accessible
    async def project_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        try:
            # Appel des méthodes du cog directement
            commit_task = asyncio.create_task(self.get_commit_stats()) # Appel de la méthode de classe
            loc_task = asyncio.to_thread(self.get_loc_stats)        # Appel de la méthode de classe

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
            Logger.error(f"Erreur dans /project_stats : {e}")
            traceback.print_exc()
            await interaction.followup.send("❌ Une erreur critique est survenue.", ephemeral=True)

async def setup(bot: commands.Bot): # La fonction setup doit être async
    await bot.add_cog(DevStatsCog(bot))