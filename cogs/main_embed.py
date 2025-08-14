# --- cogs/main_embed.py (REFACTORED AND CORRECTED) ---

import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import traceback
from .phone import PhoneMainView
from utils.helpers import clamp

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 10, high_is_bad: bool = False) -> str:
    if not isinstance(value, (int, float)): value = 0.0
    value = clamp(value, 0, max_value)
    percent = value / max_value
    filled_length = int(length * percent)
    bar_filled = '🟥' if (high_is_bad and percent > 0.7) or (not high_is_bad and percent < 0.3) else '🟧' if (high_is_bad and percent > 0.4) or (not high_is_bad and percent < 0.6) else '🟩'
    bar_empty = '⬛'
    return f"`{bar_filled * filled_length}{bar_empty * (length - filled_length)}`"

# --- VUES ---

class DashboardView(ui.View):
    """
    La vue principale et unifiée du tableau de bord.
    Elle gère son propre état (stats visibles, image cachée).
    """
    def __init__(self, show_stats: bool = False, image_hidden: bool = False):
        super().__init__(timeout=None)
        self.show_stats = show_stats
        self.image_hidden = image_hidden
        self.update_buttons()

    def update_buttons(self):
        """Met à jour les boutons en fonction de l'état actuel de la vue."""
        self.clear_items()
        self.add_item(ui.Button(label="🏃‍♂️ Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions"))
        self.add_item(ui.Button(label="👖 Inventaire", style=discord.ButtonStyle.secondary, custom_id="nav_inventory"))
        self.add_item(ui.Button(label="📱 Téléphone", style=discord.ButtonStyle.blurple, custom_id="nav_phone"))

        # Bouton pour afficher/cacher les stats (le "cerveau")
        stats_label = "Cacher Cerveau" if self.show_stats else "Afficher Cerveau"
        stats_style = discord.ButtonStyle.success if self.show_stats else discord.ButtonStyle.secondary
        self.add_item(ui.Button(label=stats_label, style=stats_style, custom_id="nav_toggle_stats", row=1, emoji="🧠"))

        # Bouton pour afficher/cacher l'image
        image_label = "Afficher Image" if self.image_hidden else "Cacher Image"
        self.add_item(ui.Button(label=image_label, style=discord.ButtonStyle.grey, custom_id="nav_toggle_image", row=1, emoji="🖼️"))


class ActionsView(ui.View):
    """La vue pour les actions du joueur, affichée sous le dashboard principal."""
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()
        cooldown_active = player.last_action_at and (now - player.last_action_at).total_seconds() < 10
        self.add_item(ui.Button(label="Manger", style=discord.ButtonStyle.success, custom_id="action_eat_menu", emoji="🍽️", disabled=cooldown_active))
        self.add_item(ui.Button(label="Boire", style=discord.ButtonStyle.primary, custom_id="action_drink_menu", emoji="💧", disabled=cooldown_active))
        self.add_item(ui.Button(label="Fumer", style=discord.ButtonStyle.danger, custom_id="action_smoke_menu", emoji="🚬", disabled=cooldown_active))
        self.add_item(ui.Button(label="Dormir", style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="🛏️", disabled=cooldown_active))
        if player.bladder > 30:
            self.add_item(ui.Button(label=f"Uriner ({player.bladder:.0f}%)", style=discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple, custom_id="action_urinate", emoji="🚽", row=1, disabled=cooldown_active))
        if player.fatigue > 60 or player.bladder > 60:
            self.add_item(ui.Button(label="Caca", style=discord.ButtonStyle.secondary, custom_id="action_poop_menu", emoji="💩", row=1, disabled=cooldown_active))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2))

class EatView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.food_servings > 0: self.add_item(ui.Button(label=f"Manger Portion ({player.food_servings})", style=discord.ButtonStyle.success, custom_id="eat_food"))
        if player.soup_bowls > 0: self.add_item(ui.Button(label=f"Manger Soupe ({player.soup_bowls})", style=discord.ButtonStyle.success, custom_id="eat_soup"))
        if player.salad_servings > 0: self.add_item(ui.Button(label=f"Manger Salade ({player.salad_servings})", style=discord.ButtonStyle.success, custom_id="eat_salad"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1))

class DrinkView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.water_bottles > 0: self.add_item(ui.Button(label=f"Boire Eau ({player.water_bottles})", style=discord.ButtonStyle.primary, custom_id="drink_water"))
        if player.beers > 0: self.add_item(ui.Button(label=f"Boire Bière ({player.beers})", style=discord.ButtonStyle.primary, custom_id="drink_beer"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1))

class SmokeView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.cigarettes > 0: self.add_item(ui.Button(label=f"Fumer Cigarette ({player.cigarettes})", style=discord.ButtonStyle.danger, custom_id="smoke_cigarette"))
        if player.joints > 0: self.add_item(ui.Button(label=f"Fumer Joint ({player.joints})", style=discord.ButtonStyle.danger, custom_id="smoke_joint"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1))
        
class InventoryView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="⬅️ Retour au Tableau de Bord", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))

# --- COG ---

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Enregistrement des vues persistantes pour qu'elles fonctionnent après un redémarrage
        self.bot.add_view(DashboardView())
        self.bot.add_view(InventoryView())

    @staticmethod
    def get_character_thoughts(player: PlayerProfile) -> str:
        thoughts = {
            95: (player.thirst > 85, "J'ai la gorge complètement sèche, je pourrais boire n'importe quoi."),
            90: (player.hunger > 80, "Mon estomac gargouille si fort, il faut que je mange."),
            85: (player.withdrawal_severity > 60, "Ça tremble... il m'en faut une, vite. Je peux plus réfléchir."),
            80: (player.fatigue > 85, "Mes paupières sont lourdes, je pourrais m'endormir debout."),
            75: (player.bladder > 90, "J'ai une envie TRÈS pressante, je vais plus tenir !"),
            70: (player.stress > 70, "J'ai les nerfs à vif, tout m'angoisse."),
            60: (player.sex_drive > 80, "Je me sens un peu seul... une présence me ferait du bien."),
            50: (player.craving_nicotine > 40, "Une clope me calmerait, là."),
            40: (player.health < 40, "Je... je ne me sens pas bien. J'ai mal partout."),
            30: (player.boredom > 60, "Je m'ennuie... il ne se passe jamais rien."),
            20: (player.craving_alcohol > 50, "Un verre me détendrait bien..."),
        }
        for priority in sorted(thoughts.keys(), reverse=True):
            condition, text = thoughts[priority]
            if condition: return text
        return "Pour l'instant, ça va à peu près."

    def generate_dashboard_embed(self, player: PlayerProfile, state: ServerState, guild: discord.Guild, view: DashboardView) -> discord.Embed:
        embed = discord.Embed(title="👨‍🍳 Le Quotidien du Cuisinier", color=0x3498db)
        asset_cog = self.bot.get_cog("AssetManager")

        image_name = "neutral"
        now = datetime.datetime.utcnow()
        if player.last_action and player.last_action_time and (now - player.last_action_time).total_seconds() < 10:
            image_name = player.last_action
        else:
            if player.stomachache > 60: image_name = "stomachache"
            elif player.headache > 60: image_name = "headache"
            elif player.urge_to_pee > 80: image_name = "urge_to_pee"
            elif player.craving > 70: image_name = "craving"
            elif player.stress > 70 or player.hunger > 70 or player.health < 40: image_name = "sad"
        
        image_url = asset_cog.get_url(image_name) if asset_cog else None
        if image_url:
            if view.image_hidden:
                embed.set_thumbnail(url=image_url)
            else:
                embed.set_image(url=image_url)

        embed.description = f"**Pensées du Cuisinier :**\n*\"{self.get_character_thoughts(player)}\"*"

        # La vue (view) nous dit si on doit afficher les stats
        if view.show_stats:
            vital_needs = (f"**Faim:** {generate_progress_bar(player.hunger, high_is_bad=True)} `{player.hunger:.0f}%`\n"
                           f"**Soif:** {generate_progress_bar(player.thirst, high_is_bad=True)} `{player.thirst:.0f}%`\n"
                           f"**Vessie:** {generate_progress_bar(player.bladder, high_is_bad=True)} `{player.bladder:.0f}%`")
            embed.add_field(name="⚠️ Besoins Vitaux", value=vital_needs, inline=True)
            cravings = (f"🚬 **Tabac:** {generate_progress_bar(player.craving_nicotine, high_is_bad=True)} `{player.craving_nicotine:.0f}%`\n"
                        f"🍺 **Alcool:** {generate_progress_bar(player.craving_alcohol, high_is_bad=True)} `{player.craving_alcohol:.0f}%`\n"
                        f"❤️ **Sexe:** {generate_progress_bar(player.sex_drive, high_is_bad=True)} `{player.sex_drive:.0f}%`")
            embed.add_field(name="🔥 Désirs & Envies", value=cravings, inline=True)
            phys_health = (f"**Santé:** {generate_progress_bar(player.health)} `{player.health:.0f}%`\n"
                           f"**Énergie:** {generate_progress_bar(player.energy)} `{player.energy:.0f}%`\n"
                           f"**Fatigue:** {generate_progress_bar(player.fatigue, high_is_bad=True)} `{player.fatigue:.0f}%`")
            embed.add_field(name="❤️ Santé Physique", value=phys_health, inline=False)
            mental_health = (f"**Mentale:** {generate_progress_bar(player.sanity, high_is_bad=False)} `{player.sanity:.0f}%`\n"
                             f"**Stress:** {generate_progress_bar(player.stress, high_is_bad=True)} `{player.stress:.0f}%`\n"
                             f"**Humeur:** {generate_progress_bar(player.happiness, high_is_bad=False)} `{player.happiness:.0f}%`\n"
                             f"**Ennui:** {generate_progress_bar(player.boredom, high_is_bad=True)} `{player.boredom:.0f}%`")
            embed.add_field(name="🧠 État Mental", value=mental_health, inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=False) # Spacer
            symptoms = (f"**Douleur:** {generate_progress_bar(player.pain, high_is_bad=True)} `{player.pain:.0f}%`\n"
                        f"**Nausée:** {generate_progress_bar(player.nausea, high_is_bad=True)} `{player.nausea:.0f}%`\n"
                        f"**Vertiges:** {generate_progress_bar(player.dizziness, high_is_bad=True)} `{player.dizziness:.0f}%`")
            embed.add_field(name="🤕 Symptômes", value=symptoms, inline=True)
            addiction = (f"**Dépendance:** {generate_progress_bar(player.substance_addiction_level, high_is_bad=True)}`{player.substance_addiction_level:.1f}%`\n"
                         f"**Manque:** {generate_progress_bar(player.withdrawal_severity, high_is_bad=True)} `{player.withdrawal_severity:.1f}%`\n"
                         f"**Défonce:** {generate_progress_bar(player.intoxication_level, high_is_bad=True)} `{player.intoxication_level:.1f}%`")
            embed.add_field(name="🚬 Addiction", value=addiction, inline=True)
            if player.is_sick:
                embed.add_field(name="État Actuel", value="**Malade 🤒**", inline=False)

        embed.set_footer(text=f"Jeu sur le serveur {guild.name} • Dernière mise à jour :")
        embed.timestamp = datetime.datetime.utcnow()
        return embed

    def generate_inventory_embed(self, player: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        # ... (Cette fonction est correcte et n'a pas besoin de changer)
        embed = discord.Embed(title="👖 Inventaire du Cuisinier", color=0x2ecc71)
        inventory_items = [("cigarettes", "🚬 Cigarettes"), ("beers", "🍺 Bières"), ("water_bottles", "💧 Bouteilles d'eau"), ("food_servings", "🍔 Portions")]
        inventory_list = "".join([f"{label}: **{getattr(player, attr, 0)}**\n" for attr, label in inventory_items if getattr(player, attr, 0) > 0])
        embed.add_field(name="Consommables", value=inventory_list or "*Vide*", inline=True)
        embed.add_field(name="Argent", value=f"💰 **{player.wallet}$**", inline=True)
        return embed

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        try:
            await interaction.response.defer()
        except (discord.errors.InteractionResponded, discord.errors.NotFound):
            return

        custom_id = interaction.data["custom_id"]
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player or not state:
                await interaction.followup.send("Erreur: Profil ou état introuvable.", ephemeral=True)
                return

            # --- GESTION DES INTERACTIONS ---
            # Phone (logique externe)
            if custom_id.startswith(("phone_", "shop_buy_", "ubereats_buy_")):
                phone_cog = self.bot.get_cog("Phone")
                if phone_cog: await phone_cog.handle_interaction(interaction, db, player, state)
                return

            # Toggle des états de la vue
            if custom_id in ("nav_toggle_stats", "nav_toggle_image"):
                view = interaction.message.view
                if isinstance(view, DashboardView):
                    if custom_id == "nav_toggle_stats":
                        view.show_stats = not view.show_stats
                    else: # nav_toggle_image
                        view.image_hidden = not view.image_hidden
                    
                    view.update_buttons() # Met à jour les labels/styles des boutons
                    new_embed = self.generate_dashboard_embed(player, state, interaction.guild, view)
                    await interaction.edit_original_response(embed=new_embed, view=view)
                return

            # Navigation principale
            if custom_id == "nav_main_menu":
                view = DashboardView()
                await interaction.edit_original_response(embed=self.generate_dashboard_embed(player, state, interaction.guild, view), view=view)
                return
            elif custom_id == "nav_actions":
                await interaction.edit_original_response(view=ActionsView(player))
                return
            elif custom_id == "nav_inventory":
                await interaction.edit_original_response(embed=self.generate_inventory_embed(player, interaction.guild), view=InventoryView())
                return
            elif custom_id == "nav_phone":
                await interaction.edit_original_response(view=PhoneMainView(player))
                return

            # Menus d'actions secondaires
            action_menus = {
                "action_eat_menu": EatView(player),
                "action_drink_menu": DrinkView(player),
                "action_smoke_menu": SmokeView(player),
            }
            if custom_id in action_menus:
                await interaction.edit_original_response(view=action_menus[custom_id])
                return

            # Actions concrètes
            cooker_brain = self.bot.get_cog("CookerBrain")
            message, changes = None, {}
            action_map = {
                "action_sleep": cooker_brain.perform_sleep,
                "action_urinate": cooker_brain.perform_urinate,
                "eat_food": cooker_brain.perform_eat,
                "eat_soup": cooker_brain.use_soup,
                "drink_water": cooker_brain.perform_drink,
                "drink_beer": cooker_brain.use_beer,
                "smoke_cigarette": cooker_brain.perform_smoke,
            }
            if custom_id in action_map:
                message, changes = action_map[custom_id](player)

            if message:
                player.last_action_at = datetime.datetime.utcnow()
                db.commit()
                await interaction.followup.send(f"✅ {message}", ephemeral=True)
                
                # Après l'action, on retourne au menu des actions pour voir le cooldown
                # et l'embed principal pour voir les stats mises à jour.
                view = DashboardView(show_stats=True) # Affiche les stats après une action
                await interaction.edit_original_response(
                    embed=self.generate_dashboard_embed(player, state, interaction.guild, view),
                    view=ActionsView(player)
                )

        except Exception as e:
            print(f"Erreur critique dans le listener on_interaction: {e}")
            traceback.print_exc()
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))