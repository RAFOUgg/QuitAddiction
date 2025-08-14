# --- cogs/main_embed.py (REWORKED FOR CONSISTENCY & CLARITY) ---

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
    """La vue principale et unifiée du tableau de bord."""
    def __init__(self, show_stats: bool = False, image_is_hidden: bool = False):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="🏃‍♂️ Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions"))
        self.add_item(ui.Button(label="👖 Inventaire", style=discord.ButtonStyle.secondary, custom_id="nav_inventory"))
        self.add_item(ui.Button(label="📱 Téléphone", style=discord.ButtonStyle.blurple, custom_id="nav_phone"))
        self.add_item(ui.Button(label="🧠 Cerveau", style=discord.ButtonStyle.success if show_stats else discord.ButtonStyle.secondary, custom_id="nav_toggle_stats", row=1))
        # Image toggle
        if image_is_hidden:
            self.add_item(ui.Button(label="🖼️ Afficher l'image", style=discord.ButtonStyle.grey, custom_id="nav_toggle_image_to_shown", row=1))
        else:
            self.add_item(ui.Button(label="🖼️ Cacher l'image", style=discord.ButtonStyle.grey, custom_id="nav_toggle_image_to_hidden", row=1))

class ActionsView(ui.View):
    """La vue pour les actions du joueur, affichée sous le dashboard principal."""
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()
        # Cooldown: 10 seconds between actions
        cooldown_active = player.last_action_at and (now - player.last_action_at).total_seconds() < 10
        self.add_item(ui.Button(label="Manger", style=discord.ButtonStyle.success, custom_id="action_eat_menu", emoji="🍽️", disabled=cooldown_active))
        self.add_item(ui.Button(label="Boire", style=discord.ButtonStyle.primary, custom_id="action_drink_menu", emoji="💧", disabled=cooldown_active))
        self.add_item(ui.Button(label="Fumer", style=discord.ButtonStyle.danger, custom_id="action_smoke_menu", emoji="🚬", disabled=cooldown_active))
        self.add_item(ui.Button(label="Dormir", style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="🛏️", disabled=cooldown_active))
        if player.bladder > 30:
            self.add_item(ui.Button(label=f"Uriner ({player.bladder:.0f}%)", style=discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple, custom_id="action_urinate", emoji="🚽", row=1, disabled=cooldown_active))
        # Ajout du bouton caca si fatigue ou vessie élevée (exemple)
        if player.fatigue > 60 or player.bladder > 60:
            self.add_item(ui.Button(label="Caca", style=discord.ButtonStyle.secondary, custom_id="action_poop_menu", emoji="💩", row=1, disabled=cooldown_active))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2))

class EatView(ui.View):
    """Vue pour choisir quoi manger."""
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        # Ajoute un bouton pour chaque item à manger
        if player.food_servings > 0:
            self.add_item(ui.Button(label=f"Manger Portion ({player.food_servings})", style=discord.ButtonStyle.success, custom_id="eat_food"))
        if player.soup_bowls > 0:
            self.add_item(ui.Button(label=f"Manger Soupe ({player.soup_bowls})", style=discord.ButtonStyle.success, custom_id="eat_soup"))
        if player.salad_servings > 0:
            self.add_item(ui.Button(label=f"Manger Salade ({player.salad_servings})", style=discord.ButtonStyle.success, custom_id="eat_salad"))
        if player.joints > 0:
            self.add_item(ui.Button(label=f"Manger Joint ({player.joints})", style=discord.ButtonStyle.secondary, custom_id="eat_joint"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1))

class DrinkView(ui.View):
    """Vue pour choisir quoi boire."""
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.water_bottles > 0:
            self.add_item(ui.Button(label=f"Boire Eau ({player.water_bottles})", style=discord.ButtonStyle.primary, custom_id="drink_water"))
        if player.beers > 0:
            self.add_item(ui.Button(label=f"Boire Bière ({player.beers})", style=discord.ButtonStyle.primary, custom_id="drink_beer"))
        if player.whisky_bottles > 0:
            self.add_item(ui.Button(label=f"Boire Whisky ({player.whisky_bottles})", style=discord.ButtonStyle.primary, custom_id="drink_whisky"))
        if player.wine_bottles > 0:
            self.add_item(ui.Button(label=f"Boire Vin ({player.wine_bottles})", style=discord.ButtonStyle.primary, custom_id="drink_wine"))
        if player.soda_cans > 0:
            self.add_item(ui.Button(label=f"Boire Soda ({player.soda_cans})", style=discord.ButtonStyle.primary, custom_id="drink_soda"))
        if player.orange_juice > 0:
            self.add_item(ui.Button(label=f"Boire Jus d'orange ({player.orange_juice})", style=discord.ButtonStyle.primary, custom_id="drink_orange_juice"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1))

class SmokeView(ui.View):
    """Vue pour choisir quoi fumer."""
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.cigarettes > 0:
            self.add_item(ui.Button(label=f"Fumer Cigarette ({player.cigarettes})", style=discord.ButtonStyle.danger, custom_id="smoke_cigarette"))
        if player.joints > 0:
            self.add_item(ui.Button(label=f"Fumer Joint ({player.joints})", style=discord.ButtonStyle.danger, custom_id="smoke_joint"))
        if player.ecigarettes > 0:
            self.add_item(ui.Button(label=f"Fumer E-cigarette ({player.ecigarettes})", style=discord.ButtonStyle.danger, custom_id="smoke_ecigarette"))
        if player.vaporizer > 0:
            self.add_item(ui.Button(label=f"Fumer Vaporisateur ({player.vaporizer})", style=discord.ButtonStyle.danger, custom_id="smoke_vaporisateur"))
        if player.chilum > 0:
            self.add_item(ui.Button(label=f"Fumer Chilum ({player.chilum})", style=discord.ButtonStyle.danger, custom_id="smoke_chilum"))
        if player.bhang > 0:
            self.add_item(ui.Button(label=f"Fumer Bhang ({player.bhang})", style=discord.ButtonStyle.danger, custom_id="smoke_bhang"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1))

class PoopView(ui.View):
    """Vue pour faire caca."""
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        self.add_item(ui.Button(label="Faire caca", style=discord.ButtonStyle.secondary, custom_id="do_poop"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1))

class InventoryView(ui.View):
    """La vue pour l'inventaire, remplace la vue 'BackView'."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="⬅️ Retour au Tableau de Bord", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))

# --- COG ---
def generate_cook_embed(player, state, guild, show_stats=False, image_is_hidden=False):
    asset_cog = guild._state._get_client().get_cog("AssetManager")
    image_name = "neutral"
    now = datetime.datetime.utcnow()
    action_image_timeout = 10
    if player.last_action and player.last_action_time and (now - player.last_action_time).total_seconds() < action_image_timeout:
        image_name = player.last_action
    else:
        if player.stomachache > 60:
            image_name = "stomachache"
        elif player.headache > 60:
            image_name = "headache"
        elif player.urge_to_pee > 80:
            image_name = "urge_to_pee"
        elif player.craving > 70:
            image_name = "craving"
        elif player.stress > 70 or player.hunger > 70 or player.health < 40:
            image_name = "sad"
    image_url = asset_cog.get_url(image_name) if asset_cog else None

    embed = discord.Embed(title="👨‍🍳 Le Quotidien du Cuisinier", color=0x3498db)
    if image_url:
        if image_is_hidden:
            embed.set_thumbnail(url=image_url)
        else:
            embed.set_image(url=image_url)
    embed.description = f"**Pensées du Cuisinier :**\n*\"{MainEmbed.get_character_thoughts_static(player)}\"*"
    # Notification
    notif_role = f"<@&{state.notification_role_id}>" if state and state.notification_role_id else None
    notif_msg = player.notification_history.strip().split("\n")[-1] if player.notification_history else None
    if notif_role or notif_msg:
        embed.add_field(
            name="🔔 Notification",
            value=f"{notif_role or ''} {notif_msg or ''}".strip(),
            inline=False
        )
    # Stats si demandé
    if show_stats:
        # --- Section Stats (TOUJOURS affichée) ---
        # NOUVEAU: Besoins Vitaux
        # Besoins Vitaux
        vital_needs = (
            f"**Faim:** {generate_progress_bar(player.hunger, high_is_bad=True)} `{player.hunger:.0f}%`\n"
            f"**Soif:** {generate_progress_bar(player.thirst, high_is_bad=True)} `{player.thirst:.0f}%`\n"
            f"**Vessie:** {generate_progress_bar(player.bladder, high_is_bad=True)} `{player.bladder:.0f}%`"
        )
        embed.add_field(name="⚠️ Besoins Vitaux", value=vital_needs, inline=True)

        # Désirs & Envies
        cravings = (
            f"🚬 **Tabac:** {generate_progress_bar(player.craving_nicotine, high_is_bad=True)} `{player.craving_nicotine:.0f}%`\n"
            f"🍺 **Alcool:** {generate_progress_bar(player.craving_alcohol, high_is_bad=True)} `{player.craving_alcohol:.0f}%`\n"
            f"❤️ **Sexe:** {generate_progress_bar(player.sex_drive, high_is_bad=True)} `{player.sex_drive:.0f}%`"
        )
        embed.add_field(name="🔥 Désirs & Envies", value=cravings, inline=True)

        # Santé Physique
        phys_health = (
            f"**Santé:** {generate_progress_bar(player.health)} `{player.health:.0f}%`\n"
            f"**Énergie:** {generate_progress_bar(player.energy)} `{player.energy:.0f}%`\n"
            f"**Fatigue:** {generate_progress_bar(player.fatigue, high_is_bad=True)} `{player.fatigue:.0f}%`\n"
        )
        embed.add_field(name="❤️ Santé Physique", value=phys_health, inline=False)

        mental_health = (f"**Mentale:** {generate_progress_bar(player.sanity, high_is_bad=False)} `{player.sanity:.0f}%`\n"
                         f"**Stress:** {generate_progress_bar(player.stress, high_is_bad=True)} `{player.stress:.0f}%`\n"
                         f"**Humeur:** {generate_progress_bar(player.happiness, high_is_bad=False)} `{player.happiness:.0f}%`\n"
                         f"**Ennui:** {generate_progress_bar(player.boredom, high_is_bad=True)} `{player.boredom:.0f}%`")
        embed.add_field(name="🧠 État Mental", value=mental_health, inline=True)

        embed.add_field(name="\u200b", value="\u200b", inline=False) # Spacer

        symptoms = (f"**Douleur:** {generate_progress_bar(player.pain, high_is_bad=True)} `{player.pain:.0f}%`\n"
                    f"**Nausée:** {generate_progress_bar(player.nausea, high_is_bad=True)} `{player.nausea:.0f}%`\n"
                    f"**Vertiges:** {generate_progress_bar(player.dizziness, high_is_bad=True)} `{player.dizziness:.0f}%`\n"
                    f"**Gorge Irritée:** {generate_progress_bar(player.sore_throat, high_is_bad=True)} `{player.sore_throat:.0f}%`")
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

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Enregistre les vues persistantes au démarrage du bot
        self.bot.add_view(DashboardView())
        self.bot.add_view(InventoryView())

    @staticmethod
    def get_character_thoughts_static(player: PlayerProfile) -> str:
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
        # Retourne la pensée la plus prioritaire (clé la plus haute) qui est vraie
        for priority in sorted(thoughts.keys(), reverse=True):
            condition, text = thoughts[priority]
            if condition:
                return text
        return "Pour l'instant, ça va à peu près."

    def generate_dashboard_embed(self, player: PlayerProfile, state: ServerState, guild: discord.Guild, show_stats: bool = False, image_is_hidden: bool = False) -> discord.Embed:
        embed = discord.Embed(title="👨‍🍳 Le Quotidien du Cuisinier", color=0x3498db)

        asset_cog = self.bot.get_cog("AssetManager")
        # --- NEW: Action-based image logic ---
        image_name = "neutral"
        now = datetime.datetime.utcnow()
        action_image_timeout = 10  # seconds to show action image after action

        if player.last_action and player.last_action_time and (now - player.last_action_time).total_seconds() < action_image_timeout:
            image_name = player.last_action  # e.g., "eat", "drink", "urinate", etc.
        else:
            # Fallback to state-based images
            if player.stomachache > 60:
                image_name = "stomachache"
            elif player.headache > 60:
                image_name = "headache"
            elif player.urge_to_pee > 80:
                image_name = "urge_to_pee"
            elif player.craving > 70:
                image_name = "craving"
            elif player.stress > 70 or player.hunger > 70 or player.health < 40:
                image_name = "sad"
            # ...add more as you add images...

        image_url = asset_cog.get_url(image_name) if asset_cog else None

        if image_url:
            if image_is_hidden:
                embed.set_thumbnail(url=image_url)
            else:
                embed.set_image(url=image_url)

        embed.description = f"**Pensées du Cuisinier :**\n*\"{self.get_character_thoughts(player)}\"*"

        # Affichage de la notification active (stockée dans player.notification_history ou state)
        notif_role = None
        notif_msg = None
        if state and state.notification_role_id:
            notif_role = f"<@&{state.notification_role_id}>"
        # Récupère la dernière notification (exemple simple)
        if player.notification_history:
            notif_msg = player.notification_history.strip().split("\n")[-1]
        if notif_role or notif_msg:
            embed.add_field(
                name="🔔 Notification",
                value=f"{notif_role or ''} {notif_msg or ''}".strip(),
                inline=False
            )

        # Affiche les stats uniquement si show_stats est True
        if show_stats:
            # --- Section Stats (TOUJOURS affichée) ---
            # NOUVEAU: Besoins Vitaux
            # Besoins Vitaux
            vital_needs = (
                f"**Faim:** {generate_progress_bar(player.hunger, high_is_bad=True)} `{player.hunger:.0f}%`\n"
                f"**Soif:** {generate_progress_bar(player.thirst, high_is_bad=True)} `{player.thirst:.0f}%`\n"
                f"**Vessie:** {generate_progress_bar(player.bladder, high_is_bad=True)} `{player.bladder:.0f}%`"
            )
            embed.add_field(name="⚠️ Besoins Vitaux", value=vital_needs, inline=True)

            # Désirs & Envies
            cravings = (
                f"🚬 **Tabac:** {generate_progress_bar(player.craving_nicotine, high_is_bad=True)} `{player.craving_nicotine:.0f}%`\n"
                f"🍺 **Alcool:** {generate_progress_bar(player.craving_alcohol, high_is_bad=True)} `{player.craving_alcohol:.0f}%`\n"
                f"❤️ **Sexe:** {generate_progress_bar(player.sex_drive, high_is_bad=True)} `{player.sex_drive:.0f}%`"
            )
            embed.add_field(name="🔥 Désirs & Envies", value=cravings, inline=True)

            # Santé Physique
            phys_health = (
                f"**Santé:** {generate_progress_bar(player.health)} `{player.health:.0f}%`\n"
                f"**Énergie:** {generate_progress_bar(player.energy)} `{player.energy:.0f}%`\n"
                f"**Fatigue:** {generate_progress_bar(player.fatigue, high_is_bad=True)} `{player.fatigue:.0f}%`\n"
            )
            embed.add_field(name="❤️ Santé Physique", value=phys_health, inline=False)

            mental_health = (f"**Mentale:** {generate_progress_bar(player.sanity, high_is_bad=False)} `{player.sanity:.0f}%`\n" f"**Stress:** {generate_progress_bar(player.stress, high_is_bad=True)} `{player.stress:.0f}%`\n" f"**Humeur:** {generate_progress_bar(player.happiness, high_is_bad=False)} `{player.happiness:.0f}%`\n" f"**Ennui:** {generate_progress_bar(player.boredom, high_is_bad=True)} `{player.boredom:.0f}%`")
            embed.add_field(name="🧠 État Mental", value=mental_health, inline=True)

            embed.add_field(name="\u200b", value="\u200b", inline=False) # Spacer

            symptoms = (f"**Douleur:** {generate_progress_bar(player.pain, high_is_bad=True)} `{player.pain:.0f}%`\n" f"**Nausée:** {generate_progress_bar(player.nausea, high_is_bad=True)} `{player.nausea:.0f}%`\n" f"**Vertiges:** {generate_progress_bar(player.dizziness, high_is_bad=True)} `{player.dizziness:.0f}%`\n" f"**Gorge Irritée:** {generate_progress_bar(player.sore_throat, high_is_bad=True)} `{player.sore_throat:.0f}%`")
            embed.add_field(name="🤕 Symptômes", value=symptoms, inline=True)
            
            addiction = (f"**Dépendance:** {generate_progress_bar(player.substance_addiction_level, high_is_bad=True)}`{player.substance_addiction_level:.1f}%`\n" f"**Manque:** {generate_progress_bar(player.withdrawal_severity, high_is_bad=True)} `{player.withdrawal_severity:.1f}%`\n" f"**Défonce:** {generate_progress_bar(player.intoxication_level, high_is_bad=True)} `{player.intoxication_level:.1f}%`")
            embed.add_field(name="🚬 Addiction", value=addiction, inline=True)
            
            if player.is_sick:
                embed.add_field(name="État Actuel", value="**Malade 🤒**", inline=False)
        embed.set_footer(text=f"Jeu sur le serveur {guild.name} • Dernière mise à jour :")
        embed.timestamp = datetime.datetime.utcnow()
        return embed

    def generate_inventory_embed(self, player: PlayerProfile, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="👖 Inventaire du Cuisinier", color=0x2ecc71)
        embed.description = "Contenu de vos poches et de votre portefeuille."
        # Liste des items et leur emoji/label
        inventory_items = [
            ("cigarettes", "🚬 Cigarettes"),
            ("beers", "🍺 Bières"),
            ("water_bottles", "💧 Bouteilles d'eau"),
            ("food_servings", "🍔 Portions de nourriture"),
            ("joints", "🌿 Joints"),
            ("soup_bowls", "🍲 Bols de soupe"),
            ("whisky_bottles", "🥃 Whisky"),
            ("wine_bottles", "🍷 Vin"),
            ("soda_cans", "🥤 Soda"),
            ("salad_servings", "🥗 Salade"),
            ("orange_juice", "🧃 Jus d'orange"),
            ("vaporizer", "🌬️ Vaporisateur"),
            ("ecigarettes", "💨 Cigarette électronique"),
            ("chilum", "🪔 Chilum"),
            ("bhang", "🥛 Bhang"),
        ]
        # Affiche uniquement les items possédés (>0)
        inventory_list = ""
        for attr, label in inventory_items:
            val = getattr(player, attr, 0)
            if isinstance(val, (int, float)) and val > 0:
                inventory_list += f"{label}: **{val}**\n"
        if not inventory_list:
            inventory_list = "*Aucun objet dans l'inventaire.*"
        embed.add_field(name="Consommables", value=inventory_list, inline=True)
        embed.add_field(name="Argent", value=f"💰 **{player.wallet}$**", inline=True)
        embed.set_footer(text=f"Jeu sur le serveur {guild.name}")
        embed.timestamp = datetime.datetime.utcnow()
        return embed

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return

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

            phone_cog = self.bot.get_cog("Phone")
            if phone_cog and custom_id.startswith(("phone_", "shop_buy_", "ubereats_buy_")):
                await phone_cog.handle_interaction(interaction, db, player, state)
                return

            cooker_brain = self.bot.get_cog("CookerBrain")
            message, changes = None, {}

            # --- NAVIGATION PRINCIPALE ---
            if custom_id == "nav_main_menu":
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=False),
                    view=DashboardView(show_stats=False, image_is_hidden=False)
                )
            elif custom_id == "nav_toggle_stats":
                show_stats = False
                if interaction.message and interaction.message.embeds:
                    for row in interaction.message.components:
                        for component in row.children:
                            if getattr(component, 'custom_id', None) == 'nav_toggle_stats' and component.style == discord.ButtonStyle.success:
                                show_stats = True
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=not show_stats, image_is_hidden=False),
                    view=DashboardView(show_stats=not show_stats, image_is_hidden=False)
                )
            elif custom_id == "nav_toggle_image_to_hidden":
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=True),
                    view=DashboardView(show_stats=False, image_is_hidden=True)
                )
            elif custom_id == "nav_toggle_image_to_shown":
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=False),
                    view=DashboardView(show_stats=False, image_is_hidden=False)
                )
            elif custom_id == "nav_actions":
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=False),
                    view=ActionsView(player)
                )
            elif custom_id == "nav_inventory":
                await interaction.edit_original_response(
                    embed=self.generate_inventory_embed(player, interaction.guild),
                    view=InventoryView()
                )
            elif custom_id == "nav_phone":
                embed = generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=True)
                embed.description = "Vous ouvrez votre téléphone."
                await interaction.edit_original_response(embed=embed, view=PhoneMainView(player))

            # --- MENUS D'ACTIONS SECONDAIRES ---
            elif custom_id == "action_eat_menu":
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=False),
                    view=EatView(player)
                )
            elif custom_id == "action_drink_menu":
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=False),
                    view=DrinkView(player)
                )
            elif custom_id == "action_smoke_menu":
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=False),
                    view=SmokeView(player)
                )
            elif custom_id == "action_poop_menu":
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=False),
                    view=PoopView(player)
                )

            # --- ACTIONS CONCRÈTES ---
            elif custom_id == "action_sleep":
                message, changes = cooker_brain.perform_sleep(player)
            elif custom_id == "action_urinate":
                message, changes = cooker_brain.perform_urinate(player)
            elif custom_id == "eat_food":
                message, changes = cooker_brain.perform_eat(player)
            elif custom_id == "eat_soup":
                message, changes = cooker_brain.use_soup(player)
            elif custom_id == "drink_water":
                message, changes = cooker_brain.perform_drink(player)
            elif custom_id == "drink_beer":
                message, changes = cooker_brain.use_beer(player)
            elif custom_id == "smoke_cigarette":
                message, changes = cooker_brain.perform_smoke(player)

            if message:
                player.last_action_at = datetime.datetime.utcnow()
                db.commit()
                await interaction.followup.send(f"✅ {message}", ephemeral=True)
                await interaction.edit_original_response(
                    embed=generate_cook_embed(player, state, interaction.guild, show_stats=False, image_is_hidden=False),
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