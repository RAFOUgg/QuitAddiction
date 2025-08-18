# --- cogs/dev_stats_cog.py (FINAL & COMPLETE) ---

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
import traceback
import subprocess
from datetime import datetime, timedelta
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

    async def get_commit_stats(self) -> dict:
        """Récupère et analyse TOUS les commits d'un projet pour des statistiques complètes."""
        if not all([GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME]):
            return {"error": "Missing GitHub configuration in .env file."}
        
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/commits"
        repo_url = f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}" # NEW: Repo URL for linking
        
        all_commits = []
        page = 1
        try:
            async with aiohttp.ClientSession() as session:
                while True:
                    params = {"per_page": 100, "page": page}
                    async with session.get(api_url, headers=headers, params=params) as response:
                        if response.status != 200:
                            logger.error(f"GitHub API Error: {response.status} - {await response.text()}")
                            return {"error": f"GitHub API returned status {response.status}."}
                        
                        data = await response.json()
                        if not data:
                            break # Plus de commits à récupérer
                        all_commits.extend(data)
                        page += 1
        except Exception as e:
            logger.error(f"Error fetching commits: {e}", exc_info=True)
            return {"error": "An unexpected error occurred while fetching commits."}

        if not all_commits:
            return {"error": "No commits found for this repository."}

        # --- Calculs des statistiques ---
        now = datetime.now().astimezone()
        first_commit_date = datetime.fromisoformat(all_commits[-1]['commit']['author']['date'].replace('Z', '+00:00'))
        last_commit_date = datetime.fromisoformat(all_commits[0]['commit']['author']['date'].replace('Z', '+00:00'))

        commits_last_7_days = 0
        commits_last_30_days = 0
        contributors = defaultdict(int)
        daily_sessions = defaultdict(list)

        for commit in all_commits:
            commit_date = datetime.fromisoformat(commit['commit']['author']['date'].replace('Z', '+00:00'))
            
            if (now - commit_date).days < 7:
                commits_last_7_days += 1
            if (now - commit_date).days < 30:
                commits_last_30_days += 1
            
            if commit.get('author') and commit['author'].get('login'):
                contributors[commit['author']['login']] += 1

            daily_sessions[commit_date.date()].append(commit_date)

        # Durée de développement estimée sur toute la vie du projet
        total_duration = sum(
            (max(times) - min(times) for times in daily_sessions.values() if len(times) > 1),
            timedelta(0)
        )
        
        # Trier les contributeurs par nombre de commits
        sorted_contributors = sorted(contributors.items(), key=lambda item: item[1], reverse=True)

        return {
            "total_commits": len(all_commits),
            "first_commit_date": first_commit_date,
            "last_commit_date": last_commit_date,
            "estimated_duration": total_duration,
            "commits_last_7_days": commits_last_7_days,
            "commits_last_30_days": commits_last_30_days,
            "top_contributors": sorted_contributors,
            "repo_url": repo_url # NEW: Pass the repo URL
        }

    def get_loc_stats(self) -> dict:
        """Calcule les stats locales sur les lignes de code."""
        try:
            files_process = subprocess.run(
                ['git', 'ls-files', '*.py'], 
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            file_list = files_process.stdout.strip().split('\n')
            if not file_list or not file_list[0]:
                return {"total_lines": 0, "total_files": 0}
            total_lines = 0
            for filepath in file_list:
                if not os.path.exists(filepath): continue
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        total_lines += sum(1 for line in f)
                except Exception as e:
                    logger.warning(f"Could not read file {filepath}: {e}")
            return {"total_lines": total_lines, "total_files": len(file_list)}
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Git command failed. Error: {e}", exc_info=True)
            return {"error": "Impossible d'exécuter les commandes git locales."}
        except Exception as e:
            logger.error(f"Unexpected error in get_loc_stats: {e}", exc_info=True)
            return {"error": "An unexpected error occurred."}

    @app_commands.command(name="project_stats", description="[STAFF] Affiche les statistiques complètes du projet.")
    @app_commands.guild_only()
    async def project_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            commit_data_task = self.get_commit_stats()
            loc_data_task = asyncio.to_thread(self.get_loc_stats)
            commit_data, loc_data = await asyncio.gather(commit_data_task, loc_data_task)

            errors = []
            if "error" in commit_data: errors.append(f"GitHub: {commit_data['error']}")
            if "error" in loc_data: errors.append(f"Local Error: {loc_data['error']}")
            if errors:
                await interaction.followup.send(f"❌ " + "\n".join(errors), ephemeral=True)
                return

            # --- MODIFIED: Added URL to embed and improved description ---
            embed = create_styled_embed(
                title=f"📊 Project Stats - {GITHUB_REPO_NAME}",
                description="A deep dive into the development activity and codebase of the project.",
                url=commit_data["repo_url"], # The title is now a link
                color=discord.Color.from_rgb(4, 30, 66) # Une couleur bleu nuit
            )

            # --- Section 1: Stats Clés ---
            codebase_value = f"**{loc_data['total_lines']:,}** Lines of Code\n**{loc_data['total_files']}** Python Files"
            embed.add_field(name="<:python:1186326476140511313> Codebase", value=codebase_value, inline=True)

            # --- MODIFIED: Display dev time in hours ---
            estimated_hours = commit_data['estimated_duration'].total_seconds() / 3600
            activity_value = (
                f"**{commit_data['total_commits']}** Total Commits\n"
                f"**{estimated_hours:.1f}** Hours of Coding (Est.)"
            )
            embed.add_field(name="<:github:1186326473212874833> Development Activity", value=activity_value, inline=True)
            
            pace_value = f"**{commit_data['commits_last_30_days']}** in 30 days\n**{commit_data['commits_last_7_days']}** in 7 days"
            embed.add_field(name="📈 Recent Pace", value=pace_value, inline=True)
            
            # --- Section 2: Timeline ---
            project_age = datetime.now().astimezone() - commit_data['first_commit_date']
            timeline_str = (
                f"**Project Age:** {format_time_delta(project_age)}\n"
                f"**First Commit:** <t:{int(commit_data['first_commit_date'].timestamp())}:D>\n"
                f"**Last Commit:** <t:{int(commit_data['last_commit_date'].timestamp())}:R>"
            )
            embed.add_field(name="🗓️ Project Timeline", value=timeline_str, inline=False)
            
            # --- Section 3: Contributeurs ---
            leaderboard = []
            for i, (name, count) in enumerate(commit_data['top_contributors'][:5]):
                emoji = ["🥇", "🥈", "🥉", "🔹", "🔹"][i]
                leaderboard.append(f"{emoji} **{name}**: `{count}` commits")
            
            if leaderboard:
                embed.add_field(name="🏆 Top Contributors", value="\n".join(leaderboard), inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Critical error in /project_stats: {e}", exc_info=True)
            await interaction.followup.send("A critical error occurred.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(DevStatsCog(bot))