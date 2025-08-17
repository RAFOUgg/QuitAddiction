import discord
from discord.ext import commands
from discord import ui, ButtonStyle
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
        self._add_buttons()
        self.current_section = "general"

    def _add_buttons(self):
        self.add_item(ui.Button(label="Vue Générale", style=ButtonStyle.primary, custom_id="brain_general", emoji="🧠"))
        self.add_item(ui.Button(label="Besoins", style=ButtonStyle.secondary, custom_id="brain_needs", emoji="🍽️"))
        self.add_item(ui.Button(label="Dépendances", style=ButtonStyle.secondary, custom_id="brain_addictions", emoji="🚬"))
        self.add_item(ui.Button(label="État Mental", style=ButtonStyle.secondary, custom_id="brain_mental", emoji="🎭"))
        self.add_item(ui.Button(label="Retour", style=ButtonStyle.danger, custom_id="brain_back", emoji="↩️"))

    def get_current_stats(self) -> dict:
        p = self.player
        sections = {
            "general": [
                {"name": "💪 Santé", "value": f"{generate_progress_bar(p.health)} {p.health}/100"},
                {"name": "🏃‍♂️ Énergie", "value": f"{generate_progress_bar(p.energy)} {p.energy}/100"},
                {"name": "😴 Fatigue", "value": f"{generate_progress_bar(p.fatigue, high_is_bad=True)} {p.fatigue}/100"},
                {"name": "💰 Argent", "value": f"{p.wallet}€"},
                {"name": "💪 Force Mentale", "value": f"{generate_progress_bar(p.willpower)} {p.willpower}/100"}
            ],
            "needs": [
                {"name": "🍽️ Faim", "value": f"{generate_progress_bar(p.hunger, high_is_bad=True)} {p.hunger}/100"},
                {"name": "🚰 Soif", "value": f"{generate_progress_bar(p.thirst, high_is_bad=True)} {p.thirst}/100"},
                {"name": "🚽 Vessie", "value": f"{generate_progress_bar(p.bladder, high_is_bad=True)} {p.bladder}/100"},
                {"name": "💩 Intestins", "value": f"{generate_progress_bar(p.bowels, high_is_bad=True)} {p.bowels}/100"}
            ],
            "addictions": [
                {"name": "🚬 Nicotine", "value": f"{generate_progress_bar(p.nicotine_addiction)} {p.nicotine_addiction}/100"},
                {"name": "🥃 Alcool", "value": f"{generate_progress_bar(p.alcohol_addiction)} {p.alcohol_addiction}/100"},
                {"name": "🌿 Cannabis", "value": f"{generate_progress_bar(p.cannabis_addiction)} {p.cannabis_addiction}/100"},
                {"name": "☕ Caféine", "value": f"{generate_progress_bar(p.caffeine_addiction)} {p.caffeine_addiction}/100"}
            ],
            "mental": [
                {"name": "🧠 Santé Mentale", "value": f"{generate_progress_bar(p.sanity)} {p.sanity}/100"},
                {"name": "😊 Humeur", "value": f"{generate_progress_bar(p.mood)} {p.mood}/100"},
                {"name": "😰 Stress", "value": f"{generate_progress_bar(p.stress, high_is_bad=True)} {p.stress}/100"},
                {"name": "😌 Relaxation", "value": f"{generate_progress_bar(p.relaxation)} {p.relaxation}/100"}
            ]
        }
        return sections.get(self.current_section, sections["general"])

class BrainViewCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(BrainViewCog(bot))
