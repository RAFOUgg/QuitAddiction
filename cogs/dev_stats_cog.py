# --- cogs/dev_stats_cog.py (FINAL & ROBUST) ---

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
import traceback
import subprocess
from datetime import datetime, timedelta, date
import calendar
import os
import dotenv
from collections import defaultdict

# --- Imports ---
from utils.embed_builder import create_styled_embed
from utils.logger import get_logger
from utils.helpers import format_time_delta

# --- Setup ---
dotenv.load_dotenv()
logger = get_logger(__name__)
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")


class DevStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def generate_contribution_graph(self, commits: list) -> str:
        """Génère un graphique de contribution textuel pour le mois en cours."""
        today = date.today()
        # Mappe les jours à des emojis de couleur pour l'intensité
        # 0 commits, 1-2, 3-5, 6-9, 10+
        contribution_emojis = ["<:g_d:1186717540974411887>", "<:g_l:1186717537023348836>", "<:g_m:1186717534473175111>", "<:g_h:1186717531956551731>", "<:g_vh:1186717529125023805>"]
        
        # Compte les commits par jour pour le mois en cours
        commits_per_day = defaultdict(int)
        for commit in commits:
            commit_date = datetime.fromisoformat(commit['commit']['author']['date'].replace('Z', '+00:00')).date()
            if commit_date.year == today.year and commit_date.month == today.month:
                commits_per_day[commit_date.day] = commits_per_day.get(commit_date.day, 0) + 1
        
        # Crée la grille du calendrier
        cal = calendar.monthcalendar(today.year, today.month)
        graph = ""

        # En-têtes des jours de la semaine
        days_header = " ".join(["Lu", "Ma", "Me", "Je", "Ve", "Sa", "Di"])
        graph += f"`{days_header}`\n"

        for week in cal:
            week_str = ""
            for day_num in week:
                if day_num == 0:
                    week_str += "  " # Espace vide pour les jours hors du mois
                else:
                    count = commits_per_day.get(day_num, 0)
                    if count == 0: level = 0
                    elif count <= 2: level = 1
                    elif count <= 5: level = 2
                    elif count <= 9: level = 3
                    else: level = 4
                    week_str += contribution_emojis[level]
            graph += week_str + "\n"
            
        return graph.strip()


    async def get_commit_stats(self) -> dict:
        if not all([GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME]):
            return {"error": "Missing GitHub configuration in .env file."}
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        # On prend les commits des 90 derniers jours pour avoir assez de données pour le graphique
        since_date = (datetime.utcnow() - timedelta(days=90)).isoformat()
        api_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/commits"
        all_commits = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, params={"per_page": 100, "since": since_date}) as response:
                    if response.status != 200:
                        logger.error(f"GitHub API Error: {response.status} - {await response.text()}")
                        return {"error": f"GitHub API returned status {response.status}."}
                    all_commits = await response.json()
        except Exception as e:
            logger.error(f"Error fetching commits: {e}", exc_info=True)
            return {"error": "An unexpected error occurred while fetching commits."}

        if not all_commits:
            return {"error": "No commits found for this repository."}

        daily_sessions = {}
        for commit in all_commits:
            commit_date = datetime.fromisoformat(commit['commit']['author']['date'].replace('Z', '+00:00'))
            day = commit_date.date()
            daily_sessions.setdefault(day, []).append(commit_date)

        total_duration = sum(
            (max(commits) - min(commits) for commits in daily_sessions.values() if len(commits) > 1),
            timedelta(0)
        )

        return {
            "raw_commits": all_commits, # On passe les commits bruts pour le graphique
            "total_commits": len(all_commits),
            "estimated_duration": total_duration,
            "first_commit_date": datetime.fromisoformat(all_commits[-1]['commit']['author']['date'].replace('Z', '+00:00')),
            "last_commit_date": datetime.fromisoformat(all_commits[0]['commit']['author']['date'].replace('Z', '+00:00'))
        }

    def get_loc_stats(self) -> dict:
        """Calculates local lines of code statistics using only git and Python."""
        try:
            files_process = subprocess.run(
                ['git', 'ls-files', '*.py'], 
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            file_list = files_process.stdout.strip().split('\n')
            if not file_list or not file_list[0]:
                return {"total_lines": 0, "total_chars": 0, "total_files": 0}
            total_lines, total_chars = 0, 0
            for filepath in file_list:
                if not os.path.exists(filepath): continue
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        total_lines += len(lines)
                        total_chars += sum(len(line) for line in lines)
                except Exception as e:
                    logger.warning(f"Could not read file {filepath}: {e}")
            return {"total_lines": total_lines, "total_chars": total_chars, "total_files": len(file_list)}
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Git command failed. Is '.git' folder in the container? Error: {e}", exc_info=True)
            return {"error": "Impossible d'exécuter les commandes git locales."}
        except Exception as e:
            logger.error(f"Unexpected error in get_loc_stats: {e}", exc_info=True)
            return {"error": "An unexpected error occurred while calculating local stats."}

    @app_commands.command(name="project_stats", description="[STAFF] Displays project development statistics.")
    @app_commands.guild_only() # Recommandé pour les commandes utilisant des emojis custom
    async def project_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            commit_task = self.get_commit_stats()
            loc_task = asyncio.to_thread(self.get_loc_stats)
            commit_data, loc_data = await asyncio.gather(commit_task, loc_task)

            errors = []
            if "error" in commit_data: errors.append(f"GitHub: {commit_data['error']}")
            if "error" in loc_data: errors.append(f"Local Error: {loc_data['error']}")
            if errors:
                await interaction.followup.send(f"❌ " + "\n".join(errors), ephemeral=True)
                return

            embed = create_styled_embed(
                title=f"📊 Project Stats - {GITHUB_REPO_NAME}",
                description=f"A snapshot of development activity for `{calendar.month_name[date.today().month]}`.",
                color=discord.Color.dark_green()
            )

            # NOUVEAU : Génération et ajout du graphique de contribution
            contribution_graph = self.generate_contribution_graph(commit_data['raw_commits'])
            embed.add_field(name="🗓️ Contribution Calendar", value=contribution_graph, inline=False)

            loc_value = (
                f"**Total Lines:** `{loc_data['total_lines']:,}`\n"
                f"**Python Files:** `{loc_data['total_files']}`"
            )
            embed.add_field(name="<:python:1186326476140511313> Codebase", value=loc_value, inline=True)

            commit_value = (
                f"**Commits (90d):** `{commit_data['total_commits']}`\n"
                f"**Last Activity:** <t:{int(commit_data['last_commit_date'].timestamp())}:R>"
            )
            embed.add_field(name="<:github:1186326473212874833> Activity", value=commit_value, inline=True)
            
            embed.set_footer(text=f"Stats as of {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Critical error in /project_stats: {e}", exc_info=True)
            await interaction.followup.send("A critical error occurred.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(DevStatsCog(bot))