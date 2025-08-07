# --- cogs/dev_stats_cog.py (FINAL & ROBUST) ---

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

# --- Imports ---
from utils.embed_builder import create_styled_embed
from utils.logger import get_logger
from config import GITHUB_REPO_NAME

# --- Setup ---
dotenv.load_dotenv()
logger = get_logger(__name__)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER")


class DevStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_commit_stats(self) -> dict:
        if not all([GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME]):
            return {"error": "Missing GitHub configuration in .env file."}
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        api_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/commits"
        all_commits = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, params={"per_page": 100}) as response:
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
            "total_commits": len(all_commits),
            "estimated_duration": total_duration,
            "first_commit_date": datetime.fromisoformat(all_commits[-1]['commit']['author']['date'].replace('Z', '+00:00')),
            "last_commit_date": datetime.fromisoformat(all_commits[0]['commit']['author']['date'].replace('Z', '+00:00'))
        }

    def get_loc_stats(self) -> dict:
        """Calculates local lines of code statistics using only git and Python."""
        try:
            # Get the list of python files tracked by git
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

            embed = create_styled_embed(title=f"📊 Project Stats - {GITHUB_REPO_NAME}", description="A snapshot of development activity.", color=discord.Color.dark_green())
            # ... (Rest of embed logic)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Critical error in /project_stats: {e}", exc_info=True)
            await interaction.followup.send("A critical error occurred.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(DevStatsCog(bot))