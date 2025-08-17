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
    def __init__(self, player: PlayerProfile, main_embed_cog):
        super().__init__(timeout=None)
        self.player = player
        self.main_embed_cog = main_embed_cog
        self.current_section = "general"
        self._add_buttons()

    def _add_buttons(self):
        self.clear_items()
        # Vue Générale
        self.add_item(self.create_button("Vue Générale", "general", "🧠"))
        # Besoins Physiologiques
        self.add_item(self.create_button("Besoins", "needs", "🍽️"))
        # Dépendances
        self.add_item(self.create_button("Dépendances", "addictions", "🚬"))
        # État Mental
        self.add_item(self.create_button("État Mental", "mental", "🎭"))
        # Retour
        back_button = ui.Button(
            label="Retour",
            style=ButtonStyle.danger,
            custom_id="brain_back",
            emoji="↩️",
            row=1
        )
        back_button.callback = self.button_callback
        self.add_item(back_button)

    def create_button(self, label, custom_id_suffix, emoji):
        button = ui.Button(
            label=label,
            style=ButtonStyle.primary if self.current_section == custom_id_suffix else ButtonStyle.secondary,
            custom_id=f"brain_{custom_id_suffix}",
            emoji=emoji
        )
        button.callback = self.button_callback
        return button

    async def button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        # We need to get the server state to generate the dashboard embed
        db = self.main_embed_cog.bot.get_cog("Database").get_db()
        state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
        if custom_id == "brain_back":
            self.player.show_stats_in_view = False
            view = self.main_embed_cog.DashboardView(self.player)
            embed = self.main_embed_cog.generate_dashboard_embed(self.player, state, interaction.guild)
            await interaction.response.edit_message(embed=embed, view=view)
            return

        self.current_section = custom_id.replace("brain_", "")
        self._add_buttons()
        embed = self.main_embed_cog.generate_dashboard_embed(self.player, state, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

    def get_stats_fields(self) -> list:
        p = self.player
        sections = {
            "general": [
                {"name": "💪 Santé", "value": f"{p.health:.0f}/100\n{generate_progress_bar(p.health)}"},
                {"name": "🏃‍♂️ Énergie", "value": f"{p.energy:.0f}/100\n{generate_progress_bar(p.energy)}"},
                {"name": "😴 Fatigue", "value": f"{p.fatigue:.0f}/100\n{generate_progress_bar(p.fatigue, high_is_bad=True)}"},
                {"name": "💪 Force Mentale", "value": f"{p.willpower:.0f}/100\n{generate_progress_bar(p.willpower)}"}
            ],
            "needs": [
                {"name": "🍽️ Faim", "value": f"{p.hunger:.0f}/100\n{generate_progress_bar(p.hunger, high_is_bad=True)}"},
                {"name": "🚰 Soif", "value": f"{p.thirst:.0f}/100\n{generate_progress_bar(p.thirst, high_is_bad=True)}"},
                {"name": "🚽 Vessie", "value": f"{p.bladder:.0f}/100\n{generate_progress_bar(p.bladder, high_is_bad=True)}"},
                {"name": "💩 Intestins", "value": f"{p.bowels:.0f}/100\n{generate_progress_bar(p.bowels, high_is_bad=True)}"}
            ],
            "addictions": [
                {"name": "🚬 Nicotine", "value": f"{p.nicotine_addiction:.0f}/100\n{generate_progress_bar(p.nicotine_addiction, high_is_bad=True)}"},
                {"name": "🥃 Alcool", "value": f"{p.alcohol_addiction:.0f}/100\n{generate_progress_bar(p.alcohol_addiction, high_is_bad=True)}"},
                {"name": "🌿 Cannabis", "value": f"{p.cannabis_addiction:.0f}/100\n{generate_progress_bar(p.cannabis_addiction, high_is_bad=True)}"},
                {"name": "☕ Caféine", "value": f"{p.caffeine_addiction:.0f}/100\n{generate_progress_bar(p.caffeine_addiction, high_is_bad=True)}"}
            ],
            "mental": [
                {"name": "🧠 Santé Mentale", "value": f"{p.sanity:.0f}/100\n{generate_progress_bar(p.sanity)}"},
                {"name": "😊 Humeur", "value": f"{p.mood:.0f}/100\n{generate_progress_bar(p.mood)}"},
                {"name": "😰 Stress", "value": f"{p.stress:.0f}/100\n{generate_progress_bar(p.stress, high_is_bad=True)}"},
                {"name": "😌 Relaxation", "value": f"{p.relaxation:.0f}/100\n{generate_progress_bar(p.relaxation)}"}
            ]
        }
        return sections.get(self.current_section, sections["general"])

async def setup(bot):
    pass
