# --- cogs/brain_stats.py ---
import discord
from discord.ext import commands
import discord.ui as ui
from discord import ButtonStyle
from db.models import PlayerProfile
from utils.helpers import clamp

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 5, high_is_bad: bool = False) -> str:
    if not isinstance(value, (int, float)): value = 0.0
    value = clamp(value, 0, max_value)
    filled_blocks = round((value / max_value) * length)
    percent = value / max_value
    bar_filled = '🟥' if (high_is_bad and percent > 0.75) or (not high_is_bad and percent < 0.25) else '🟧' if (high_is_bad and percent > 0.5) or (not high_is_bad and percent < 0.5) else '🟩'
    bar_empty = '⬛'
    return f"{bar_filled * filled_blocks}{bar_empty * (length - filled_blocks)}"

class BrainStatsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        self.player = player
        self.current_section = "general"
        self._add_buttons()

    def _add_buttons(self):
        # Vue Générale
        self.add_item(ui.Button(
            label="Vue Générale",
            style=ButtonStyle.primary if self.current_section == "general" else ButtonStyle.secondary,
            custom_id="brain_general",
            emoji="🧠"
        ))
        
        # Besoins Physiologiques
        self.add_item(ui.Button(
            label="Besoins",
            style=ButtonStyle.primary if self.current_section == "needs" else ButtonStyle.secondary,
            custom_id="brain_needs",
            emoji="🍽️"
        ))
        
        # Dépendances
        self.add_item(ui.Button(
            label="Dépendances",
            style=ButtonStyle.primary if self.current_section == "addictions" else ButtonStyle.secondary,
            custom_id="brain_addictions",
            emoji="🚬"
        ))
        
        # État Mental
        self.add_item(ui.Button(
            label="État Mental",
            style=ButtonStyle.primary if self.current_section == "mental" else ButtonStyle.secondary,
            custom_id="brain_mental",
            emoji="🎭"
        ))
        
        # Retour
        self.add_item(ui.Button(
            label="Retour",
            style=ButtonStyle.danger,
            custom_id="brain_back",
            emoji="↩️",
            row=1
        ))

    def get_stats_fields(self) -> list:
        p = self.player
        sections = {
            "general": [
                {"name": "💪 Santé", "value": f"{p.health}/100\n{generate_progress_bar(p.health)}"},
                {"name": "🏃‍♂️ Énergie", "value": f"{p.energy}/100\n{generate_progress_bar(p.energy)}"},
                {"name": "😴 Fatigue", "value": f"{p.fatigue}/100\n{generate_progress_bar(p.fatigue, high_is_bad=True)}"},
                {"name": "💪 Force Mentale", "value": f"{p.willpower}/100\n{generate_progress_bar(p.willpower)}"}
            ],
            "needs": [
                {"name": "🍽️ Faim", "value": f"{p.hunger}/100\n{generate_progress_bar(p.hunger, high_is_bad=True)}"},
                {"name": "🚰 Soif", "value": f"{p.thirst}/100\n{generate_progress_bar(p.thirst, high_is_bad=True)}"},
                {"name": "🚽 Vessie", "value": f"{p.bladder}/100\n{generate_progress_bar(p.bladder, high_is_bad=True)}"},
                {"name": "💩 Intestins", "value": f"{p.bowels}/100\n{generate_progress_bar(p.bowels, high_is_bad=True)}"}
            ],
            "addictions": [
                {"name": "🚬 Nicotine", "value": f"{p.nicotine_addiction}/100\n{generate_progress_bar(p.nicotine_addiction)}"},
                {"name": "🥃 Alcool", "value": f"{p.alcohol_addiction}/100\n{generate_progress_bar(p.alcohol_addiction)}"},
                {"name": "🌿 Cannabis", "value": f"{p.cannabis_addiction}/100\n{generate_progress_bar(p.cannabis_addiction)}"},
                {"name": "☕ Caféine", "value": f"{p.caffeine_addiction}/100\n{generate_progress_bar(p.caffeine_addiction)}"}
            ],
            "mental": [
                {"name": "🧠 Santé Mentale", "value": f"{p.sanity}/100\n{generate_progress_bar(p.sanity)}"},
                {"name": "😊 Humeur", "value": f"{p.mood}/100\n{generate_progress_bar(p.mood)}"},
                {"name": "😰 Stress", "value": f"{p.stress}/100\n{generate_progress_bar(p.stress, high_is_bad=True)}"},
                {"name": "😌 Relaxation", "value": f"{p.relaxation}/100\n{generate_progress_bar(p.relaxation)}"}
            ]
        }
        return sections.get(self.current_section, sections["general"])

class Brain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    brain_cog = Brain(bot)
    await bot.add_cog(brain_cog)
