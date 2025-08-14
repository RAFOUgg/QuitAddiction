# --- cogs/phone.py (REFACTORED FOR NEW UI) ---
import discord
from discord.ext import commands
from discord import ui
from sqlalchemy.orm import Session
from db.models import PlayerProfile, ServerState
import json
from utils.helpers import get_player_notif_settings 

# --- VUES ---
class PhoneMainView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="SMS", style=discord.ButtonStyle.green, custom_id="phone_sms", emoji="💬"))
        self.add_item(ui.Button(label="Notifications", style=discord.ButtonStyle.primary, custom_id="phone_notifications", emoji="🔔"))
        self.add_item(ui.Button(label="Paramètres", style=discord.ButtonStyle.secondary, custom_id="phone_settings", emoji="⚙️"))
        self.add_item(ui.Button(label="Uber Eats", style=discord.ButtonStyle.success, custom_id="phone_ubereats", emoji="🍔"))
        self.add_item(ui.Button(label="Smoke-Shop", style=discord.ButtonStyle.blurple, custom_id="phone_shop", disabled=(not player.has_unlocked_smokeshop), emoji="🛍️"))
        # Le bouton de retour est maintenant géré par le routeur principal
        self.add_item(ui.Button(label="Fermer le téléphone", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2, emoji="⬅️"))

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

class ShopView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Cigarettes (5$)", emoji="🚬", style=discord.ButtonStyle.secondary, custom_id="shop_buy_cigarettes", disabled=(player.wallet < 5)))
        self.add_item(ui.Button(label="Bière (3$)", emoji="🍺", style=discord.ButtonStyle.blurple, custom_id="shop_buy_beer", disabled=(player.wallet < 3)))
        self.add_item(ui.Button(label="Eau (1$)", emoji="💧", style=discord.ButtonStyle.primary, custom_id="shop_buy_water", disabled=(player.wallet < 1)))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", row=2, emoji="⬅️"))

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

class Phone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _add_main_image(self, embed: discord.Embed, player: PlayerProfile, main_embed_cog: commands.Cog):
        # MODIFIÉ: Utilise set_image pour une grande image
        if image_url := main_embed_cog.get_image_url(player):
            embed.set_image(url=image_url)

    def generate_phone_main_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="📱 Téléphone", description="Choisissez une application.", color=discord.Color.light_grey())
        embed.set_footer(text=f"Batterie: 100%")
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
            formatted_messages = "\n\n".join(f"✉️\n> {msg.replace('\n', '\n> ')}" for msg in messages if msg)
            embed.description = formatted_messages
        else:
            embed.description = "Aucun nouveau message."
        self._add_main_image(embed, player, main_embed_cog)
        return embed
    
    # ... autres générateurs d'embeds modifiés de la même manière
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
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except discord.errors.InteractionResponded:
            pass

        custom_id = interaction.data["custom_id"]
        
        # Dictionnaire des constructeurs d'embed et de vue pour la navigation
        phone_screens = {
            "phone_open": (self.generate_phone_main_embed, PhoneMainView),
            "phone_shop": (self.generate_shop_embed, ShopView),
            "phone_ubereats": (self.generate_ubereats_embed, UberEatsView),
            "phone_sms": (self.generate_sms_embed, SMSView),
            "phone_notifications": (self.generate_notifications_embed, NotificationsView),
            "phone_settings": (self.generate_settings_embed, SettingsView)
        }

        # Navigation dans le téléphone
        if custom_id in phone_screens:
            embed_func, view_class = phone_screens[custom_id]
            # La fonction d'embed a besoin d'arguments différents selon le cas
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

        # Basculer les paramètres de notification
        elif custom_id.startswith("phone_toggle_notif:"):
            key_to_toggle = custom_id.split(":")[1]
            settings = get_player_notif_settings(player)
            settings[key_to_toggle] = not settings.get(key_to_toggle, True)
            player.notifications_config = json.dumps(settings)
            db.commit(); db.refresh(player)
            
            embed = self.generate_settings_embed(player, main_embed_cog)
            view = SettingsView(player, settings)
            await interaction.edit_original_response(embed=embed, view=view)

        # Logique d'achat
        elif custom_id.startswith("shop_buy_") or custom_id.startswith("ubereats_buy_"):
            items = {
                "shop_buy_cigarettes": {"cost": 5, "action": lambda p: setattr(p, 'cigarettes', p.cigarettes + 10), "msg": "Vous avez acheté 10 cigarettes.", "view": ShopView, "embed": self.generate_shop_embed},
                "ubereats_buy_tacos": {"cost": 6, "action": lambda p: setattr(p, 'tacos', getattr(p, 'tacos', 0) + 1), "msg": "Vous avez commandé un tacos.", "view": UberEatsView, "embed": self.generate_ubereats_embed},
                # ... Ajoutez les autres articles ici de la même manière
            }
            item = items.get(custom_id)
            if item and player.wallet >= item["cost"]:
                player.wallet -= item["cost"]
                item["action"](player)
                db.commit(); db.refresh(player)

                await interaction.followup.send(f'✅ {item["msg"]}', ephemeral=True)
                await interaction.edit_original_response(embed=item["embed"](player, main_embed_cog), view=item["view"](player))
            else:
                await interaction.followup.send(f"⚠️ Transaction échouée.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Phone(bot))