# --- cogs/main_embed.py (REFACTORED FOR NEW UI) ---

import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import datetime
import traceback
from .phone import PhoneMainView, Phone
from utils.helpers import clamp

def generate_progress_bar(value: float, max_value: float = 100.0, length: int = 10, high_is_bad: bool = False) -> str:
    if not isinstance(value, (int, float)): value = 0.0
    value = clamp(value, 0, max_value)
    percent = value / max_value
    bar_filled = '🟥' if (high_is_bad and percent > 0.7) or (not high_is_bad and percent < 0.3) else '🟧' if (high_is_bad and percent > 0.4) or (not high_is_bad and percent < 0.6) else '🟩'
    bar_empty = '⬛'
    return f"`{bar_filled * filled_blocks}{bar_empty * (length - filled_blocks)}`"

# --- VUES ---

class DashboardView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        self.update_buttons(player)

    def update_buttons(self, player: PlayerProfile):
        self.clear_items()
        self.add_item(ui.Button(label="Actions", style=discord.ButtonStyle.primary, custom_id="nav_actions", emoji="🏃‍♂️"))
        self.add_item(ui.Button(label="Téléphone", style=discord.ButtonStyle.blurple, custom_id="phone_open", emoji="📱"))
        
        # Bouton pour l'inventaire
        inv_label = "Cacher Inventaire" if player.show_inventory_in_view else "Afficher Inventaire"
        inv_style = discord.ButtonStyle.success if player.show_inventory_in_view else discord.ButtonStyle.secondary
        self.add_item(ui.Button(label=inv_label, style=inv_style, custom_id="nav_toggle_inventory", emoji="🎒", row=1))

        # Bouton pour les stats
        stats_label = "Cacher Cerveau" if player.show_stats_in_view else "Afficher Cerveau"
        stats_style = discord.ButtonStyle.success if player.show_stats_in_view else discord.ButtonStyle.secondary
        self.add_item(ui.Button(label=stats_label, style=stats_style, custom_id="nav_toggle_stats", row=1, emoji="🧠"))

# ... (Les autres vues comme ActionsView, EatView etc. restent identiques)
class ActionsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        now = datetime.datetime.utcnow()
        cooldown_active = player.last_action_at and (now - player.last_action_at).total_seconds() < 10
        self.add_item(ui.Button(label="Manger", style=discord.ButtonStyle.success, custom_id="action_eat_menu", emoji="🍽️", disabled=cooldown_active))
        self.add_item(ui.Button(label="Boire", style=discord.ButtonStyle.primary, custom_id="action_drink_menu", emoji="💧", disabled=cooldown_active))
        self.add_item(ui.Button(label="Fumer", style=discord.ButtonStyle.danger, custom_id="action_smoke_menu", emoji="🚬", disabled=cooldown_active))
        self.add_item(ui.Button(label="Dormir", style=discord.ButtonStyle.secondary, custom_id="action_sleep", emoji="🛏️", disabled=cooldown_active))
        if player.hygiene < 40: self.add_item(ui.Button(label="Prendre une douche", style=discord.ButtonStyle.blurple, custom_id="action_shower", emoji="🚿", row=1, disabled=cooldown_active))
        if player.bladder > 30: self.add_item(ui.Button(label=f"Uriner ({player.bladder:.0f}%)", style=discord.ButtonStyle.danger if player.bladder > 80 else discord.ButtonStyle.blurple, custom_id="action_urinate", emoji="🚽", row=1, disabled=cooldown_active))
        if player.bowels > 40: self.add_item(ui.Button(label=f"Déféquer ({player.bowels:.0f}%)", style=discord.ButtonStyle.danger if player.bowels > 80 else discord.ButtonStyle.blurple, custom_id="action_defecate", emoji="💩", row=1, disabled=cooldown_active))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2, emoji="⬅️"))

class EatView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.food_servings > 0: self.add_item(ui.Button(label=f"Sandwich ({player.food_servings})", emoji="🥪", style=discord.ButtonStyle.success, custom_id="eat_sandwich"))
        if getattr(player, 'tacos', 0) > 0: self.add_item(ui.Button(label=f"Tacos ({player.tacos})", emoji="🌮", style=discord.ButtonStyle.primary, custom_id="eat_tacos"))
        if getattr(player, 'salad_servings', 0) > 0: self.add_item(ui.Button(label=f"Salade ({player.salad_servings})", emoji="🥗", style=discord.ButtonStyle.success, custom_id="eat_salad"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1, emoji="⬅️"))

class DrinkView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.water_bottles > 0: self.add_item(ui.Button(label=f"Eau ({player.water_bottles})", emoji="💧", style=discord.ButtonStyle.primary, custom_id="drink_water"))
        if player.soda_cans > 0: self.add_item(ui.Button(label=f"Soda ({player.soda_cans})", emoji="🥤", style=discord.ButtonStyle.blurple, custom_id="drink_soda"))
        if getattr(player, 'wine_bottles', 0) > 0: self.add_item(ui.Button(label=f"Vin ({player.wine_bottles})", emoji="🍷", style=discord.ButtonStyle.danger, custom_id="drink_wine"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1, emoji="⬅️"))

class SmokeView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=60)
        if player.cigarettes > 0: self.add_item(ui.Button(label=f"Cigarette ({player.cigarettes})", emoji="🚬", style=discord.ButtonStyle.danger, custom_id="smoke_cigarette"))
        if player.e_cigarettes > 0: self.add_item(ui.Button(label=f"Vapoteuse ({player.e_cigarettes})", emoji="💨", style=discord.ButtonStyle.primary, custom_id="smoke_ecigarette"))
        if getattr(player, 'joints', 0) > 0: self.add_item(ui.Button(label=f"Joint ({player.joints})", emoji="🌿", style=discord.ButtonStyle.success, custom_id="smoke_joint"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_actions", row=1, emoji="⬅️"))

# --- COG ---

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_image_url(self, player: PlayerProfile) -> str | None:
        asset_cog = self.bot.get_cog("AssetManager")
        if not asset_cog: return None
        # ... (logique d'image inchangée) ...
        now = datetime.datetime.utcnow()
        image_name = "neutral"
        if player.last_action and player.last_action_time and (now - player.last_action_time).total_seconds() < 10: return asset_cog.get_url(player.last_action)
        if player.bladder >= 99: image_name = "peed"
        elif player.bowels > 85: image_name = "neutral_pooping"
        elif player.bladder > 85: image_name = "need_pee"
        elif player.hunger > 85: image_name = "hungry"
        elif player.fatigue > 90: image_name = "neutral_sleep"
        elif player.happiness < 10 and player.stress > 80: image_name = "sob"
        elif player.headache > 70: image_name = "scratch_eye"
        elif player.stomachache > 70: image_name = "hand_stomach"
        elif player.stress > 70 or player.health < 40: image_name = "sad"
        elif player.withdrawal_severity > 60: image_name = "neutral_hold_e_cig"
        elif player.hygiene < 20: image_name = "neutral_shower"
        return asset_cog.get_url(image_name)

    @staticmethod
    def get_character_thoughts(player: PlayerProfile) -> str:
        # ... (logique de pensées inchangée) ...
        if player.hunger > 70 and player.stress > 60: return "J'ai l'estomac dans les talons et les nerfs à vif. Un rien pourrait me faire craquer."
        if player.withdrawal_severity > 60 and player.health < 40: return "Chaque partie de mon corps me fait souffrir. Le manque me ronge de l'intérieur, je suis à bout."
        if player.fatigue > 80 and player.boredom > 70: return "Je suis épuisé, mais je m'ennuie tellement que je n'arrive même pas à fermer l'œil."
        thoughts = { 95: (player.thirst > 85, "J'ai la gorge complètement sèche..."), 90: (player.hunger > 80, "Mon estomac gargouille si fort..."), 85: (player.withdrawal_severity > 60, "Ça tremble... il m'en faut une, vite."), 80: (player.fatigue > 85, "Mes paupières sont lourdes..."), 75: (player.bladder > 90, "J'ai une envie TRÈS pressante !"), 70: (player.stress > 70, "J'ai les nerfs à vif..."), 60: (player.hygiene < 20, "Je me sens vraiment sale..."), 50: (player.craving_nicotine > 40, "Une clope me calmerait, là."), 40: (player.health < 40, "Je... je ne me sens pas bien."), 30: (player.boredom > 60, "Je m'ennuie..."), 20: (player.craving_alcohol > 50, "Un verre me détendrait bien..."), }
        for priority in sorted(thoughts.keys(), reverse=True):
            if thoughts[priority][0]: return thoughts[priority][1]
        return "Pour l'instant, ça va à peu près."

    def generate_dashboard_embed(self, player: PlayerProfile, state: ServerState, guild: discord.Guild) -> discord.Embed:
        embed = discord.Embed(title="👨‍🍳 Le Quotidien du Cuisinier", color=0x3498db)
        if image_url := self.get_image_url(player):
            embed.set_image(url=image_url)

        embed.description = f"**Pensées du Cuisinier :**\n*\"{self.get_character_thoughts(player)}\"*"

        # --- NOUVELLE LOGIQUE D'AFFICHAGE CONDITIONNEL ---

        # 1. AFFICHER L'INVENTAIRE
        if player.show_inventory_in_view:
            inventory_items = [
                ("food_servings", "🥪 Sandwichs"), ("tacos", "🌮 Tacos"), ("salad_servings", "🥗 Salades"),
                ("water_bottles", "💧 Eaux"), ("soda_cans", "🥤 Sodas"), ("wine_bottles", "🍷 Vins"),
                ("cigarettes", "🚬 Cigarettes"), ("e_cigarettes", "💨 Vapoteuses"), ("joints", "🌿 Joints")
            ]
            inventory_list = [f"{label}: **{getattr(player, attr, 0)}**" for attr, label in inventory_items]
            
            # Diviser en deux colonnes pour la lisibilité
            mid_point = len(inventory_list) // 2 + (len(inventory_list) % 2)
            col1 = "\n".join(inventory_list[:mid_point])
            col2 = "\n".join(inventory_list[mid_point:])
            
            embed.add_field(name="🎒 Inventaire", value=col1 or "*Vide*", inline=True)
            if col2:
                embed.add_field(name="\u200b", value=col2, inline=True)
            embed.add_field(name="💰 Argent", value=f"**{player.wallet}$**", inline=False)

        # 2. AFFICHER LES STATS (CERVEAU)
        if player.show_stats_in_view:
            vital_needs = (f"**Faim:** {generate_progress_bar(player.hunger, high_is_bad=True)} `{player.hunger:.0f}%`\n"
                           f"**Soif:** {generate_progress_bar(player.thirst, high_is_bad=True)} `{player.thirst:.0f}%`\n"
                           f"**Vessie:** {generate_progress_bar(player.bladder, high_is_bad=True)} `{player.bladder:.0f}%`")
            embed.add_field(name="⚠️ Besoins Vitaux", value=vital_needs, inline=True)
            
            mental_health = (f"**Stress:** {generate_progress_bar(player.stress, high_is_bad=True)} `{player.stress:.0f}%`\n"
                             f"**Humeur:** {generate_progress_bar(player.happiness, high_is_bad=False)} `{player.happiness:.0f}%`\n"
                             f"**Santé:** {generate_progress_bar(player.health)} `{player.health:.0f}%`")
            embed.add_field(name="🧠 État Psycho-Physique", value=mental_health, inline=True)

        embed.set_footer(text=f"Jeu sur {guild.name}")
        embed.timestamp = datetime.datetime.utcnow()
        return embed

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data:
            return

        custom_id = interaction.data["custom_id"]
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Erreur: Profil de joueur introuvable.", ephemeral=True)
                return
            
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()

            # --- ROUTEUR D'INTERACTION PRINCIPAL ---

            # 1. Gérer les interactions du téléphone (délégué au cog Phone)
            is_phone_interaction = custom_id.startswith(("phone_", "shop_buy_", "ubereats_buy_"))
            if is_phone_interaction:
                phone_cog = self.bot.get_cog("Phone")
                if phone_cog:
                    await phone_cog.handle_interaction(interaction, db, player, state, self)
                return
            
            # Defer toutes les autres interactions du tableau de bord
            if not interaction.response.is_done():
                await interaction.response.defer()

            # 2. Gérer les toggles d'affichage
            if custom_id == "nav_toggle_stats":
                player.show_stats_in_view = not player.show_stats_in_view
            elif custom_id == "nav_toggle_inventory":
                player.show_inventory_in_view = not player.show_inventory_in_view
            
            # 3. Gérer la navigation
            elif custom_id == "nav_main_menu":
                # Ce bouton est maintenant le bouton "Retour" universel
                pass # Ne fait rien d'autre que de rafraîchir la vue principale à la fin
            elif custom_id == "nav_actions":
                await interaction.edit_original_response(view=ActionsView(player))
                return # Arrête l'exécution pour ne pas rafraîchir avec la vue principale
            elif custom_id in ["action_eat_menu", "action_drink_menu", "action_smoke_menu"]:
                views = {"action_eat_menu": EatView, "action_drink_menu": DrinkView, "action_smoke_menu": SmokeView}
                await interaction.edit_original_response(view=views[custom_id](player))
                return

            # 4. Gérer les actions du jeu
            else:
                cooker_brain = self.bot.get_cog("CookerBrain")
                message = None
                action_map = {
                    "drink_wine": cooker_brain.perform_drink_wine, "smoke_joint": cooker_brain.perform_smoke_joint,
                    "action_sleep": cooker_brain.perform_sleep, "action_shower": cooker_brain.perform_shower,
                    "action_urinate": cooker_brain.perform_urinate, "action_defecate": cooker_brain.perform_defecate,
                    "drink_water": cooker_brain.perform_drink_water, "drink_soda": cooker_brain.use_soda,
                    "eat_sandwich": cooker_brain.perform_eat_sandwich, "eat_tacos": cooker_brain.use_tacos,
                    "eat_salad": cooker_brain.use_salad, "smoke_cigarette": cooker_brain.perform_smoke_cigarette,
                    "smoke_ecigarette": cooker_brain.use_ecigarette,
                }
                if custom_id in action_map:
                    message, _ = action_map[custom_id](player)
                    player.last_action_at = datetime.datetime.utcnow()
                    await interaction.followup.send(f"✅ {message}", ephemeral=True)
                    # Après une action, on retourne au menu des actions
                    db.commit()
                    await interaction.edit_original_response(
                        embed=self.generate_dashboard_embed(player, state, interaction.guild),
                        view=ActionsView(player)
                    )
                    return
            
            # --- RAFRAÎCHISSEMENT FINAL ---
            db.commit()
            new_embed = self.generate_dashboard_embed(player, state, interaction.guild)
            new_view = DashboardView(player)
            await interaction.edit_original_response(embed=new_embed, view=new_view)

        except Exception as e:
            logger.error(f"Erreur critique dans on_interaction: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))