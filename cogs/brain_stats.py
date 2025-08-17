import discord
from discord.ext import commands
import discord.ui as ui
from discord import ButtonStyle
from db.models import PlayerProfile, ServerState
from utils.helpers import clamp
from typing import List, Dict

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 5, high_is_bad: bool = False) -> str:
    """Generate a colored progress bar based on value."""
    if not isinstance(value, (int, float)): value = 0.0
    value = clamp(value, 0, max_value)
    filled_blocks = round((value / max_value) * length)
    percent = value / max_value
    
    # More nuanced color selection
    if high_is_bad:
        bar_filled = '🟥' if percent > 0.75 else '🟧' if percent > 0.5 else '🟨' if percent > 0.25 else '🟩'
    else:
        bar_filled = '🟩' if percent > 0.75 else '🟨' if percent > 0.5 else '🟧' if percent > 0.25 else '🟥'
    
    bar_empty = '⬛'
    return f"{bar_filled * filled_blocks}{bar_empty * (length - filled_blocks)}"

class BrainStatsView(ui.View):
    def __init__(self, player: PlayerProfile, main_embed_cog):
        super().__init__(timeout=None)
        self.player = player
        self.main_embed_cog = main_embed_cog
        self.current_section = "vitals"
        self.page = 0  # For sections with multiple pages
        self._add_buttons()

    def _add_buttons(self):
        """Add navigation buttons to the view."""
        self.clear_items()
        
        # Main category buttons (Row 0)
        categories = [
            ("Vitaux", "vitals", "❤️"),
            ("Physique", "physical", "💪"),
            ("Mental", "mental", "🧠"),
            ("Social", "social", "👥"),
            ("Addiction", "addiction", "🚬")
        ]
        
        for label, id_suffix, emoji in categories:
            self.add_item(self.create_button(label, id_suffix, emoji, row=0))

        # Navigation buttons (Row 1)
        if self.has_multiple_pages():
            prev_button = ui.Button(
                label="◀️ Page Précédente",
                style=ButtonStyle.secondary,
                custom_id="prev_page",
                disabled=self.page == 0,
                row=1
            )
            next_button = ui.Button(
                label="Page Suivante ▶️",
                style=ButtonStyle.secondary,
                custom_id="next_page",
                disabled=self.page >= self.get_max_pages() - 1,
                row=1
            )
            prev_button.callback = self.page_callback
            next_button.callback = self.page_callback
            self.add_item(prev_button)
            self.add_item(next_button)

        # Return button (Row 1)
        back_button = ui.Button(
            label="Retour au jeu",
            style=ButtonStyle.danger,
            custom_id="brain_back",
            emoji="🎮",
            row=1
        )
        back_button.callback = self.button_callback
        self.add_item(back_button)

    def create_button(self, label, custom_id_suffix, emoji, row=0):
        """Create a category selection button."""
        button = ui.Button(
            label=label,
            style=ButtonStyle.primary if self.current_section == custom_id_suffix else ButtonStyle.secondary,
            custom_id=f"brain_{custom_id_suffix}",
            emoji=emoji,
            row=row
        )
        button.callback = self.button_callback
        return button

    def has_multiple_pages(self) -> bool:
        """Check if current section has multiple pages."""
        return len(self.get_stats_fields()) > 8

    def get_max_pages(self) -> int:
        """Get the number of pages for current section."""
        fields = self.get_stats_fields()
        return (len(fields) + 7) // 8  # 8 fields per page

    async def page_callback(self, interaction: discord.Interaction):
        """Handle page navigation."""
        if interaction.data["custom_id"] == "prev_page":
            self.page = max(0, self.page - 1)
        else:
            self.page = min(self.get_max_pages() - 1, self.page + 1)

        self._add_buttons()
        embed = self.generate_stats_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def button_callback(self, interaction: discord.Interaction):
        """Handle category selection and back button."""
        custom_id = interaction.data["custom_id"]
        
        if custom_id == "brain_back":
            self.player.show_stats_in_view = False
            db = self.main_embed_cog.bot.get_cog("Database").get_db()
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            view = self.main_embed_cog.DashboardView(self.player)
            embed = self.main_embed_cog.generate_dashboard_embed(self.player, state, interaction.guild)
            await interaction.response.edit_message(embed=embed, view=view)
            return

        self.current_section = custom_id.replace("brain_", "")
        self.page = 0  # Reset page when changing sections
        self._add_buttons()
        embed = self.generate_stats_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def get_stats_fields(self) -> List[Dict]:
        """Get stat fields for current section."""
        p = self.player
        sections = {
            "vitals": [
                {"name": "❤️ Santé", "value": f"{p.health:.0f}/100\n{generate_progress_bar(p.health)}", "inline": True},
                {"name": "🌡️ Température", "value": f"{p.body_temperature:.1f}°C\n{generate_progress_bar(p.body_temperature, 42, high_is_bad=True)}", "inline": True},
                {"name": "💓 Rythme Cardiaque", "value": f"{p.heart_rate:.0f} BPM\n{generate_progress_bar(p.heart_rate, 200, high_is_bad=True)}", "inline": True},
                {"name": "🩺 Tension", "value": f"{p.blood_pressure:.0f}/80\n{generate_progress_bar(p.blood_pressure, 160, high_is_bad=True)}", "inline": True},
                {"name": "🛡️ Système Immunitaire", "value": f"{p.immune_system:.0f}/100\n{generate_progress_bar(p.immune_system)}", "inline": True}
            ],
            "physical": [
                # Basic Needs
                {"name": "🍽️ Faim", "value": f"{p.hunger:.0f}/100\n{generate_progress_bar(p.hunger, high_is_bad=True)}", "inline": True},
                {"name": "💧 Soif", "value": f"{p.thirst:.0f}/100\n{generate_progress_bar(p.thirst, high_is_bad=True)}", "inline": True},
                {"name": "🚽 Vessie", "value": f"{p.bladder:.0f}/100\n{generate_progress_bar(p.bladder, high_is_bad=True)}", "inline": True},
                {"name": "💩 Intestins", "value": f"{p.bowels:.0f}/100\n{generate_progress_bar(p.bowels, high_is_bad=True)}", "inline": True},
                # Energy & Comfort
                {"name": "⚡ Énergie", "value": f"{p.energy:.0f}/100\n{generate_progress_bar(p.energy)}", "inline": True},
                {"name": "😴 Fatigue", "value": f"{p.fatigue:.0f}/100\n{generate_progress_bar(p.fatigue, high_is_bad=True)}", "inline": True},
                {"name": "🛋️ Confort", "value": f"{p.comfort:.0f}/100\n{generate_progress_bar(p.comfort)}", "inline": True},
                {"name": "🌡️ Confort Thermique", "value": f"{p.temperature_comfort:.0f}/100\n{generate_progress_bar(p.temperature_comfort)}", "inline": True},
                # Physical Symptoms
                {"name": "🤢 Nausée", "value": f"{p.nausea:.0f}/100\n{generate_progress_bar(p.nausea, high_is_bad=True)}", "inline": True},
                {"name": "😵 Vertiges", "value": f"{p.dizziness:.0f}/100\n{generate_progress_bar(p.dizziness, high_is_bad=True)}", "inline": True},
                {"name": "🤕 Maux de Tête", "value": f"{p.headache:.0f}/100\n{generate_progress_bar(p.headache, high_is_bad=True)}", "inline": True},
                {"name": "💪 Tension Musculaire", "value": f"{p.muscle_tension:.0f}/100\n{generate_progress_bar(p.muscle_tension, high_is_bad=True)}", "inline": True}
            ],
            "mental": [
                # Core Mental Stats
                {"name": "🧠 Clarté Mentale", "value": f"{p.mental_clarity:.0f}/100\n{generate_progress_bar(p.mental_clarity)}", "inline": True},
                {"name": "📚 Concentration", "value": f"{p.concentration:.0f}/100\n{generate_progress_bar(p.concentration)}", "inline": True},
                {"name": "💭 Mémoire", "value": f"{p.memory_function:.0f}/100\n{generate_progress_bar(p.memory_function)}", "inline": True},
                {"name": "🎯 Prise de Décision", "value": f"{p.decision_making:.0f}/100\n{generate_progress_bar(p.decision_making)}", "inline": True},
                # Emotional States
                {"name": "😊 Bonheur", "value": f"{p.happiness:.0f}/100\n{generate_progress_bar(p.happiness)}", "inline": True},
                {"name": "😰 Anxiété", "value": f"{p.anxiety:.0f}/100\n{generate_progress_bar(p.anxiety, high_is_bad=True)}", "inline": True},
                {"name": "😢 Dépression", "value": f"{p.depression:.0f}/100\n{generate_progress_bar(p.depression, high_is_bad=True)}", "inline": True},
                {"name": "😠 Colère", "value": f"{p.anger:.0f}/100\n{generate_progress_bar(p.anger, high_is_bad=True)}", "inline": True},
                # Psychological States
                {"name": "💪 Volonté", "value": f"{p.willpower:.0f}/100\n{generate_progress_bar(p.willpower)}", "inline": True},
                {"name": "🎭 Créativité", "value": f"{p.creativity:.0f}/100\n{generate_progress_bar(p.creativity)}", "inline": True},
                {"name": "🎯 Motivation", "value": f"{p.motivation:.0f}/100\n{generate_progress_bar(p.motivation)}", "inline": True},
                {"name": "🔋 Confiance", "value": f"{p.confidence:.0f}/100\n{generate_progress_bar(p.confidence)}", "inline": True}
            ],
            "social": [
                {"name": "😰 Anxiété Sociale", "value": f"{p.social_anxiety:.0f}/100\n{generate_progress_bar(p.social_anxiety, high_is_bad=True)}", "inline": True},
                {"name": "🔋 Énergie Sociale", "value": f"{p.social_energy:.0f}/100\n{generate_progress_bar(p.social_energy)}", "inline": True},
                {"name": "😔 Solitude", "value": f"{p.loneliness:.0f}/100\n{generate_progress_bar(p.loneliness, high_is_bad=True)}", "inline": True},
                {"name": "🌍 Stress Environnemental", "value": f"{p.environmental_stress:.0f}/100\n{generate_progress_bar(p.environmental_stress, high_is_bad=True)}", "inline": True}
            ],
            "addiction": [
                # Addiction Levels
                {"name": "🚬 Dép. Nicotine", "value": f"{p.nicotine_addiction:.0f}/100\n{generate_progress_bar(p.nicotine_addiction, high_is_bad=True)}", "inline": True},
                {"name": "🍺 Dép. Alcool", "value": f"{p.alcohol_addiction:.0f}/100\n{generate_progress_bar(p.alcohol_addiction, high_is_bad=True)}", "inline": True},
                {"name": "🌿 Dép. Cannabis", "value": f"{p.cannabis_addiction:.0f}/100\n{generate_progress_bar(p.cannabis_addiction, high_is_bad=True)}", "inline": True},
                {"name": "☕ Dép. Caféine", "value": f"{p.caffeine_addiction:.0f}/100\n{generate_progress_bar(p.caffeine_addiction, high_is_bad=True)}", "inline": True},
                # Current States
                {"name": "😖 Sévérité du Manque", "value": f"{p.withdrawal_severity:.0f}/100\n{generate_progress_bar(p.withdrawal_severity, high_is_bad=True)}", "inline": True},
                {"name": "💊 Tolérance", "value": f"{p.substance_tolerance:.0f}/100\n{generate_progress_bar(p.substance_tolerance, high_is_bad=True)}", "inline": True},
                {"name": "🎯 Envies", "value": f"{p.craving_nicotine:.0f}/100\n{generate_progress_bar(p.craving_nicotine, high_is_bad=True)}", "inline": True},
                {"name": "⚡ Sensibilité Déclencheurs", "value": f"{p.trigger_sensitivity:.0f}/100\n{generate_progress_bar(p.trigger_sensitivity, high_is_bad=True)}", "inline": True},
                # Recovery Metrics
                {"name": "📈 Progrès Sevrage", "value": f"{p.recovery_progress:.0f}/100\n{generate_progress_bar(p.recovery_progress)}", "inline": True},
                {"name": "⚠️ Risque Rechute", "value": f"{p.relapse_risk:.0f}/100\n{generate_progress_bar(p.relapse_risk, high_is_bad=True)}", "inline": True},
                {"name": "😔 Culpabilité", "value": f"{p.guilt:.0f}/100\n{generate_progress_bar(p.guilt, high_is_bad=True)}", "inline": True},
                {"name": "💪 Détermination", "value": f"{p.determination:.0f}/100\n{generate_progress_bar(p.determination)}", "inline": True}
            ]
        }
        return sections.get(self.current_section, [])

    def generate_stats_embed(self) -> discord.Embed:
        """Generate the embed for the current stats view."""
        section_titles = {
            "vitals": "État Vital",
            "physical": "État Physique",
            "mental": "État Mental",
            "social": "État Social",
            "addiction": "État des Dépendances"
        }
        
        section_descriptions = {
            "vitals": "Paramètres vitaux et santé générale",
            "physical": "État physique et besoins corporels",
            "mental": "État psychologique et capacités cognitives",
            "social": "Relations sociales et environnement",
            "addiction": "Dépendances et processus de sevrage"
        }

        embed = discord.Embed(
            title=f"🧠 {section_titles.get(self.current_section, 'Stats')}",
            description=section_descriptions.get(self.current_section, ""),
            color=discord.Color.blue()
        )

        # Get all fields for current section
        all_fields = self.get_stats_fields()
        
        # Paginate fields (8 per page)
        start_idx = self.page * 8
        page_fields = all_fields[start_idx:start_idx + 8]
        
        # Add fields to embed
        for field in page_fields:
            embed.add_field(**field)

        # Add page indicator if needed
        if self.has_multiple_pages():
            embed.set_footer(text=f"Page {self.page + 1}/{self.get_max_pages()}")

        return 

