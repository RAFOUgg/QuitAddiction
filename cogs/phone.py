# --- cogs/phone.py (REFACTORED FOR NEW UI) ---
import discord
from discord.ext import commands
import discord.ui as ui
from discord.ext import commands
from discord import ui
from sqlalchemy.orm import Session
from db.models import PlayerProfile, ServerState
import json
import datetime
from utils.helpers import get_player_notif_settings, clamp
from .smoke_shop import SmokeShopView

# --- VUES ---
class PhoneMainView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="SMS", style=discord.ButtonStyle.green, custom_id="phone_sms", emoji="💬"))
        self.add_item(ui.Button(label="Uber Eats", style=discord.ButtonStyle.success, custom_id="phone_ubereats", emoji="🍔"))
        self.add_item(ui.Button(label="Smoke-Shop", 
                              style=discord.ButtonStyle.blurple, 
                              custom_id="phone_shop", 
                              disabled=(not player.has_unlocked_smokeshop), 
                              emoji="🛍️"))
        # Bouton de retour au jeu
        self.add_item(ui.Button(label="Retour au jeu", 
                              style=discord.ButtonStyle.grey, 
                              custom_id="nav_main_menu", 
                              row=1, 
                              emoji="⬅️"))

class SMSView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", emoji="⬅️"))
        
class UberEatsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Tacos (6$)", emoji="🌮", style=discord.ButtonStyle.success, custom_id="ubereats_buy_tacos", disabled=(player.wallet < 6)))
        self.add_item(ui.Button(label="Soda (2$)", emoji="🥤", style=discord.ButtonStyle.success, custom_id="ubereats_buy_soda", disabled=(player.wallet < 2)))
        self.add_item(ui.Button(label="Salade (8$)", emoji="🥗", style=discord.ButtonStyle.success, custom_id="ubereats_buy_salad", disabled=(player.wallet < 8)))
        self.add_item(ui.Button(label="Eau (1$)", emoji="💧", style=discord.ButtonStyle.success, custom_id="ubereats_buy_water", disabled=(player.wallet < 1)))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", row=2, emoji="⬅️"))

class NotificationsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", emoji="⬅️"))

class ShopGearView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Bong (30$)", emoji="🌀", style=discord.ButtonStyle.blurple, 
                              custom_id="shop_buy_bong", disabled=(player.wallet < 30 or player.has_bong)))
        self.add_item(ui.Button(label="Chillum (20$)", emoji="🔮", style=discord.ButtonStyle.blurple, 
                              custom_id="shop_buy_chillum", disabled=(player.wallet < 20 or player.has_chillum)))
        self.add_item(ui.Button(label="Vaporisateur (50$)", emoji="💨", style=discord.ButtonStyle.blurple, 
                              custom_id="shop_buy_vaporizer", disabled=(player.wallet < 50 or player.has_vaporizer)))
        self.add_item(ui.Button(label="Grinder (15$)", emoji="⚙️", style=discord.ButtonStyle.blurple, 
                              custom_id="shop_buy_grinder", disabled=(player.wallet < 15 or player.has_grinder)))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="shop_main", row=2, emoji="⬅️"))

class ShopHerbsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Weed (10$/g)", emoji="🌿", style=discord.ButtonStyle.green, 
                              custom_id="shop_buy_weed", disabled=(player.wallet < 10)))
        self.add_item(ui.Button(label="Hash (15$/g)", emoji="🟫", style=discord.ButtonStyle.green, 
                              custom_id="shop_buy_hash", disabled=(player.wallet < 15)))
        self.add_item(ui.Button(label="CBD (8$/g)", emoji="�", style=discord.ButtonStyle.green, 
                              custom_id="shop_buy_cbd", disabled=(player.wallet < 8)))
        self.add_item(ui.Button(label="Tabac (5$/g)", emoji="🚬", style=discord.ButtonStyle.green, 
                              custom_id="shop_buy_tobacco", disabled=(player.wallet < 5)))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="shop_main", row=2, emoji="⬅️"))

class ShopSuppliesView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Feuilles (2$)", emoji="📜", style=discord.ButtonStyle.secondary, 
                              custom_id="shop_buy_papers", disabled=(player.wallet < 2)))
        self.add_item(ui.Button(label="Toncs (1$)", emoji="📏", style=discord.ButtonStyle.secondary, 
                              custom_id="shop_buy_toncs", disabled=(player.wallet < 1)))
        self.add_item(ui.Button(label="E-cigarette (25$)", emoji="�", style=discord.ButtonStyle.secondary, 
                              custom_id="shop_buy_ecig", disabled=(player.wallet < 25)))
        self.add_item(ui.Button(label="Cigarettes (5$)", emoji="🚬", style=discord.ButtonStyle.secondary, 
                              custom_id="shop_buy_cigarettes", disabled=(player.wallet < 5)))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="shop_main", row=2, emoji="⬅️"))

class ShopCraftView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        # Craft joint avec weed (nécessite: weed + grinder + feuilles + toncs)
        can_craft_joint = (player.weed_grams >= 0.5 and player.has_grinder and 
                          player.rolling_papers >= 1 and player.toncs >= 1)
        
        # Craft joint avec hash (nécessite: hash + feuilles + toncs)
        can_craft_hash_joint = (player.hash_grams >= 0.3 and 
                              player.rolling_papers >= 1 and player.toncs >= 1)

        self.add_item(ui.Button(label="Craft Joint (Weed)", emoji="🌿", style=discord.ButtonStyle.success, 
                              custom_id="shop_craft_joint", disabled=not can_craft_joint))
        self.add_item(ui.Button(label="Craft Joint (Hash)", emoji="🟫", style=discord.ButtonStyle.success, 
                              custom_id="shop_craft_hash_joint", disabled=not can_craft_hash_joint))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="shop_main", row=2, emoji="⬅️"))

class NotificationsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", emoji="⬅️"))

class SettingsView(ui.View):
    def __init__(self, player: PlayerProfile, settings: dict):
        super().__init__(timeout=180)
        notif_types = { "low_vitals": "📉 Vitals Faibles", "cravings": "🚬 Envies", "friend_messages": "💬 Messages d'amis" }
        for key, label in notif_types.items():
            is_enabled = settings.get(key, True)
            style = discord.ButtonStyle.success if is_enabled else discord.ButtonStyle.danger
            button_label = f"{label}: {'Activé' if is_enabled else 'Désactivé'}"
            self.add_item(ui.Button(label=button_label, style=style, custom_id=f"phone_toggle_notif:{key}"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", row=2, emoji="⬅️"))

# Add new view for browsing
class BrowseView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        # Different browsing activities
        self.add_item(ui.Button(label="Réseaux sociaux", style=discord.ButtonStyle.primary, custom_id="browse_social", emoji="📱"))
        self.add_item(ui.Button(label="Jeux mobiles", style=discord.ButtonStyle.success, custom_id="browse_games", emoji="🎮"))
        self.add_item(ui.Button(label="Vidéos", style=discord.ButtonStyle.blurple, custom_id="browse_videos", emoji="🎥"))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", emoji="⬅️"))

class Phone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.browse_effects = {
            "browse_social": {
                "duration": 15,
                "sanity": -5.0,
                "health": -2.0,
                "boredom": -30.0,
                "energy": -5.0,
                "fatigue": 5.0,
                "message": "Vous scrollez sans fin sur les réseaux sociaux..."
            },
            "browse_games": {
                "duration": 20,
                "sanity": -7.0,
                "health": -3.0,
                "boredom": -40.0,
                "energy": -8.0,
                "fatigue": 8.0,
                "message": "Vous jouez à des jeux mobiles pendant un moment..."
            },
            "browse_videos": {
                "duration": 25,
                "sanity": -10.0,
                "health": -5.0,
                "boredom": -50.0,
                "energy": -10.0,
                "fatigue": 10.0,
                "message": "Vous regardez des vidéos en boucle..."
            }
        }

    def _add_main_image(self, embed: discord.Embed, player: PlayerProfile, main_embed_cog: commands.Cog):
        try:
            embed.set_thumbnail(url="attachment://on_phone.png")
        except Exception:
            pass  # Silently handle any image loading errors

    def check_phone_usage(self, player: PlayerProfile, db: Session) -> tuple[bool, str]:
        now = datetime.datetime.utcnow()
        
        # Reset le compteur si c'est un nouveau jour
        if not player.last_phone_reset_at or (now - player.last_phone_reset_at).days >= 1:
            player.phone_uses_today = 0
            player.last_phone_reset_at = now
            db.commit()
        
        # Incrémenter le compteur
        player.phone_uses_today += 1
        
        # Appliquer les pénalités si utilisation excessive
        warning = ""
        if player.phone_uses_today > 5:
            penalty_multiplier = (player.phone_uses_today - 5) * 0.05  # 5% de pénalité par utilisation au-delà de 5
            
            # Appliquer les pénalités
            player.health = max(0, player.health - (2 * penalty_multiplier))
            player.sanity = max(0, player.sanity - (3 * penalty_multiplier))
            player.energy = max(0, player.energy - (2 * penalty_multiplier))
            
            warning = f"⚠️ Utilisation excessive du téléphone! (-{penalty_multiplier*100:.0f}% santé/sanité/énergie)"
            
        db.commit()
        return player.phone_uses_today > 5, warning

    def generate_phone_main_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="📱 Téléphone", description="Choisissez une application.", color=discord.Color.light_grey())
        embed.set_footer(text=f"Utilisations aujourd'hui: {player.phone_uses_today}/5 recommandées")
        self._add_main_image(embed, player, main_embed_cog)
        return embed

    def generate_shop_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="🛍️ Smoke-Shop", description=f"Votre Portefeuille: **{player.wallet}$**", color=discord.Color.purple())
        self._add_main_image(embed, player, main_embed_cog)
        return embed

    def generate_ubereats_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="🍔 Uber Eats", description=f"Votre Portefeuille: **{player.wallet}$**", color=discord.Color.green())
        self._add_main_image(embed, player, main_embed_cog)
        return embed

    def generate_sms_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="💬 Messagerie", color=discord.Color.blue())
        if player.messages and player.messages.strip():
            messages = player.messages.strip().split("\n---\n")
            formatted_messages = "\n\n".join(f"✉️\n> {msg}" for msg in messages if msg)
            embed.description = formatted_messages
        else:
            embed.description = "Aucun nouveau message."
        self._add_main_image(embed, player, main_embed_cog)
        return embed
    
    def generate_notifications_embed(self, player: PlayerProfile, state: ServerState, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="🔔 Notifications", color=discord.Color.orange())
        notif_history = player.notification_history.strip().split("\n") if player.notification_history else []
        embed.description = "\n".join(notif_history[-5:]) if notif_history else "Aucune notification récente."
        self._add_main_image(embed, player, main_embed_cog)
        return embed

    def generate_settings_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Paramètres de Notification", description="Activez/Désactivez les types de notifications que vous souhaitez recevoir.", color=discord.Color.dark_grey())
        self._add_main_image(embed, player, main_embed_cog)
        return embed

    async def handle_interaction(self, interaction: discord.Interaction, db: Session, player: PlayerProfile, state: ServerState, main_embed_cog: commands.Cog):
        if not interaction.response.is_done():
            await interaction.response.defer()

        if not interaction.data:
            return
            
        custom_id = interaction.data.get("custom_id", "")
        
        # Si c'est l'ouverture initiale du téléphone
        if custom_id == "phone_open":
            excessive, warning = self.check_phone_usage(player, db)
            if warning:
                await interaction.followup.send(warning, ephemeral=True)
        
        # Handle automatic phone usage for boredom when willpower is low
        if player.willpower < 70 and player.boredom > 50 and not player.is_working:
            player.on_phone = True
        
        phone_screens = {
            "phone_open": (self.generate_phone_main_embed, PhoneMainView),
            "phone_shop": (self.generate_shop_embed, SmokeShopView),
            "phone_ubereats": (self.generate_ubereats_embed, UberEatsView),
            "phone_sms": (self.generate_sms_embed, SMSView),
            "phone_notifications": (self.generate_notifications_embed, NotificationsView),
            "phone_settings": (self.generate_settings_embed, SettingsView)
        }

        if custom_id in phone_screens:
            embed_func, view_class = phone_screens[custom_id]
            if custom_id == "phone_notifications":
                embed = embed_func(player, state, main_embed_cog)
            elif custom_id == "phone_settings":
                 embed = embed_func(player, main_embed_cog)
                 view = view_class(player, get_player_notif_settings(player))
                 await interaction.edit_original_response(embed=embed, view=view)
                 return
            else:
                embed = embed_func(player, main_embed_cog)
            view = view_class(player)
            await interaction.edit_original_response(embed=embed, view=view)

        elif custom_id.startswith("phone_toggle_notif:"):
            key_to_toggle = custom_id.split(":")[1]
            settings = get_player_notif_settings(player)
            settings[key_to_toggle] = not settings.get(key_to_toggle, True)
            player.notifications_config = json.dumps(settings)
            db.commit(); db.refresh(player)
            embed = self.generate_settings_embed(player, main_embed_cog)
            view = SettingsView(player, settings)
            await interaction.edit_original_response(embed=embed, view=view)

        elif custom_id.startswith(("shop_buy_", "ubereats_buy_")):
            items = {
                "ubereats_buy_tacos": {"cost": 6, "action": lambda p: setattr(p, 'tacos', p.tacos + 1), "msg": "Vous avez commandé un tacos."},
                "ubereats_buy_soda": {"cost": 2, "action": lambda p: setattr(p, 'soda_cans', p.soda_cans + 1), "msg": "Vous avez commandé un soda."},
                "ubereats_buy_salad": {"cost": 8, "action": lambda p: setattr(p, 'salad_servings', p.salad_servings + 1), "msg": "Vous avez commandé une salade."},
                "ubereats_buy_water": {"cost": 1, "action": lambda p: setattr(p, 'water_bottles', p.water_bottles + 1), "msg": "Vous avez commandé de l'eau."}
            }
            item = items.get(custom_id)
            if item and player.wallet >= item["cost"]:
                player.wallet -= item["cost"]
                item["action"](player)
                db.commit(); db.refresh(player)
                await interaction.followup.send(f'✅ {item["msg"]}', ephemeral=True)
                await interaction.edit_original_response(embed=self.generate_phone_main_embed(player, main_embed_cog), view=PhoneMainView(player))
            else:
                await interaction.followup.send(f"⚠️ Transaction échouée. Pas assez d'argent ?", ephemeral=True)

        # Handle browsing activities
        if custom_id in self.browse_effects:
            if player.is_working and not player.is_on_break:
                await interaction.followup.send("⚠️ Vous ne pouvez pas faire ça pendant le travail !", ephemeral=True)
                return

            effects = self.browse_effects[custom_id]
            player.sanity = clamp(player.sanity + effects["sanity"], 0, 100)
            player.boredom = clamp(player.boredom + effects["boredom"], 0, 100)
            player.energy = clamp(player.energy + effects["energy"], 0, 100)
            player.fatigue = clamp(player.fatigue + effects["fatigue"], 0, 100)

            # Set cooldown
            now = datetime.datetime.utcnow()
            player.action_cooldown_end_time = now + datetime.timedelta(seconds=effects["duration"])

            db.commit()
            await interaction.followup.send(f"📱 {effects['message']}", ephemeral=True)

            # Return to phone main view after browsing
            embed = self.generate_phone_main_embed(player, main_embed_cog)
            view = PhoneMainView(player)
            await interaction.edit_original_response(embed=embed, view=view)
            return

        # Handle first day reward message
        if player.has_completed_first_work_day and not player.first_day_reward_given:
            friend_message = (
                "---\n"
                "**Alex** - 17:45\n"
                "Hey mec ! Comme promis, je t'ai laissé un petit cadeau dans ta boîte aux lettres... 🌿\n"
                "Histoire que tu te détendes après ta première journée ! Et si t'en veux d'autres,\n"
                "j'ai un pote qui tient une petite boutique pas loin. Je t'ai mis l'adresse sur ton tel.\n"
                "---"
            )
            player.messages = friend_message + "\n" + (player.messages or "")

async def setup(bot):
    await bot.add_cog(Phone(bot))