# --- cogs/phone.py (REFACTORED) ---
import discord
from discord.ext import commands
from discord import ui
from sqlalchemy.orm import Session
from db.models import PlayerProfile, ServerState
import json
from utils.helpers import get_player_notif_settings # Import the helper

# --- VUES ---
class PhoneMainView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="💬 SMS", style=discord.ButtonStyle.green, custom_id="phone_sms"))
        self.add_item(ui.Button(label="🔔 Notifications", style=discord.ButtonStyle.primary, custom_id="phone_notifications"))
        self.add_item(ui.Button(label="⚙️ Paramètres", style=discord.ButtonStyle.secondary, custom_id="phone_settings"))
        self.add_item(ui.Button(label="🍔 Uber Eats", style=discord.ButtonStyle.success, custom_id="phone_ubereats"))
        self.add_item(ui.Button(label="🛍️ Smoke-Shop", style=discord.ButtonStyle.blurple, custom_id="phone_shop", disabled=(not player.has_unlocked_smokeshop)))
        self.add_item(ui.Button(label="⬅️ Fermer le téléphone", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2))

class SMSView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open"))
        
class UberEatsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Tacos (6$)", emoji="🌮", style=discord.ButtonStyle.success, custom_id="ubereats_buy_tacos", disabled=(player.wallet < 6)))
        self.add_item(ui.Button(label="Soda (2$)", emoji="🥤", style=discord.ButtonStyle.success, custom_id="ubereats_buy_soda", disabled=(player.wallet < 2)))
        self.add_item(ui.Button(label="Pizza (12$)", emoji="🍕", style=discord.ButtonStyle.success, custom_id="ubereats_buy_pizza", disabled=(player.wallet < 12)))
        self.add_item(ui.Button(label="Salade (8$)", emoji="🥗", style=discord.ButtonStyle.success, custom_id="ubereats_buy_salad", disabled=(player.wallet < 8)))
        self.add_item(ui.Button(label="Bol de Soupe (5$)", emoji="🍲", style=discord.ButtonStyle.success, custom_id="ubereats_buy_soup", disabled=(player.wallet < 5)))
        self.add_item(ui.Button(label="Jus d'Orange (3$)", emoji="🧃", style=discord.ButtonStyle.success, custom_id="ubereats_buy_orange_juice", disabled=(player.wallet < 3)))
        self.add_item(ui.Button(label="Eau (1$)", emoji="💧", style=discord.ButtonStyle.success, custom_id="ubereats_buy_water", disabled=(player.wallet < 1)))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", row=2))

class ShopView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Acheter Cigarettes (5$)", emoji="🚬", style=discord.ButtonStyle.secondary, custom_id="shop_buy_cigarettes", disabled=(player.wallet < 5)))
        self.add_item(ui.Button(label="Acheter Bière (3$)", emoji="🍺", style=discord.ButtonStyle.blurple, custom_id="shop_buy_beer", disabled=(player.wallet < 3)))
        self.add_item(ui.Button(label="Acheter Eau (1$)", style=discord.ButtonStyle.primary, custom_id="shop_buy_water", disabled=(player.wallet < 1), emoji="💧"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", row=2))

class NotificationsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open"))

class SettingsView(ui.View):
    def __init__(self, player: PlayerProfile, settings: dict):
        super().__init__(timeout=180)
        
        notif_types = {
            "low_vitals": "📉 Vitals Faibles",
            "cravings": "🚬 Envies",
            "friend_messages": "💬 Messages d'amis"
        }

        for key, label in notif_types.items():
            is_enabled = settings.get(key, True)
            style = discord.ButtonStyle.success if is_enabled else discord.ButtonStyle.danger
            button_label = f"{label}: {'Activé' if is_enabled else 'Désactivé'}"
            self.add_item(ui.Button(label=button_label, style=style, custom_id=f"phone_toggle_notif:{key}"))

        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="phone_open", row=2))

class Phone(commands.Cog):
    """Fournit la logique pour les applications du téléphone."""
    def __init__(self, bot):
        self.bot = bot

    def _add_thumbnail(self, embed: discord.Embed, player: PlayerProfile, main_embed_cog: commands.Cog):
        if image_url := main_embed_cog.get_image_url(player):
            embed.set_thumbnail(url=image_url)

    def generate_phone_main_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="📱 Téléphone", description="Choisissez une application.", color=discord.Color.light_grey())
        embed.set_footer(text=f"Batterie: 100%")
        self._add_thumbnail(embed, player, main_embed_cog)
        return embed

    def generate_shop_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="🛍️ Smoke-Shop", description="Faites vos achats ici.", color=discord.Color.purple())
        embed.add_field(name="Votre Portefeuille", value=f"**{player.wallet}$**", inline=False)
        self._add_thumbnail(embed, player, main_embed_cog)
        return embed

    def generate_ubereats_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="🍔 Uber Eats", description="Une petite faim ? Commandez ici.", color=discord.Color.green())
        embed.add_field(name="Votre Portefeuille", value=f"**{player.wallet}$**", inline=False)
        embed.set_footer(text="Chaque commande ajoute une portion de nourriture générique.")
        self._add_thumbnail(embed, player, main_embed_cog)
        return embed

    def generate_sms_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="💬 Messagerie", color=discord.Color.blue())
        if player.messages and player.messages.strip():
            messages = player.messages.strip().split("\n---\n")
            formatted_messages = "\n\n".join(f"✉️\n> {msg.replace('\n', '\n> ')}" for msg in messages if msg)
            embed.description = formatted_messages
        else:
            embed.description = "Aucun nouveau message."
        self._add_thumbnail(embed, player, main_embed_cog)
        return embed

    def generate_notifications_embed(self, player: PlayerProfile, state: ServerState, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="🔔 Notifications", color=discord.Color.orange())
        notif_role = f"<@&{state.notification_role_id}>" if state and state.notification_role_id else ""
        notif_history = player.notification_history.strip().split("\n") if player.notification_history else []
        if notif_history:
            notif_text = "\n".join(f"{notif_role} {msg}" for msg in notif_history[-5:])
        else:
            notif_text = "Aucune notification récente."
        embed.description = notif_text
        self._add_thumbnail(embed, player, main_embed_cog)
        return embed

    def generate_settings_embed(self, player: PlayerProfile, main_embed_cog: commands.Cog) -> discord.Embed:
        embed = discord.Embed(title="⚙️ Paramètres de Notification", description="Choisissez les notifications que vous souhaitez recevoir.", color=discord.Color.dark_grey())
        self._add_thumbnail(embed, player, main_embed_cog)
        return embed

    async def handle_interaction(self, interaction: discord.Interaction, db: Session, player: PlayerProfile, state: ServerState, main_embed_cog: commands.Cog):
        """Gère toutes les interactions liées au téléphone."""
        try:
            await interaction.response.defer()
        except discord.errors.InteractionResponded:
            pass

        custom_id = interaction.data["custom_id"]
        
        # Navigation
        if custom_id == "phone_open":
            await interaction.edit_original_response(embed=self.generate_phone_main_embed(player, main_embed_cog), view=PhoneMainView(player))
        elif custom_id == "phone_shop":
            await interaction.edit_original_response(embed=self.generate_shop_embed(player, main_embed_cog), view=ShopView(player))
        elif custom_id == "phone_sms":
            await interaction.edit_original_response(embed=self.generate_sms_embed(player, main_embed_cog), view=SMSView(player))
        elif custom_id == "phone_ubereats":
            await interaction.edit_original_response(embed=self.generate_ubereats_embed(player, main_embed_cog), view=UberEatsView(player))
        elif custom_id == "phone_notifications":
            await interaction.edit_original_response(
                embed=self.generate_notifications_embed(player, state, main_embed_cog),
                view=NotificationsView(player)
            )
        elif custom_id == "phone_settings":
            settings = get_player_notif_settings(player)
            await interaction.edit_original_response(embed=self.generate_settings_embed(player, main_embed_cog), view=SettingsView(player, settings))
        
        elif custom_id.startswith("phone_toggle_notif:"):
            key_to_toggle = custom_id.split(":")[1]
            settings = get_player_notif_settings(player)
            settings[key_to_toggle] = not settings.get(key_to_toggle, True)
            player.notifications_config = json.dumps(settings)
            db.commit()
            db.refresh(player)
            await interaction.edit_original_response(embed=self.generate_settings_embed(player, main_embed_cog), view=SettingsView(player, settings))

        # Achats
        elif custom_id.startswith("shop_buy_") or custom_id.startswith("ubereats_buy_"):
            items = {
                "shop_buy_cigarettes": {"cost": 5, "action": lambda p: setattr(p, 'cigarettes', p.cigarettes + 10), "msg": "Vous avez acheté 10 cigarettes.", "type": "shop"},
                "shop_buy_beer": {"cost": 3, "action": lambda p: setattr(p, 'beers', p.beers + 1), "msg": "Vous avez acheté une bière.", "type": "shop"},
                "shop_buy_water": {"cost": 1, "action": lambda p: setattr(p, 'water_bottles', p.water_bottles + 1), "msg": "Vous avez acheté une bouteille d'eau.", "type": "shop"},
                "ubereats_buy_tacos": {"cost": 6, "action": lambda p: setattr(p, 'tacos', p.tacos + 1), "msg": "Vous avez commandé un tacos.", "type": "ubereats"},
                "ubereats_buy_soda": {"cost": 2, "action": lambda p: setattr(p, 'soda_cans', p.soda_cans + 1), "msg": "Vous avez commandé un soda.", "type": "ubereats"},
                "ubereats_buy_salad": {"cost": 8, "action": lambda p: setattr(p, 'salad_servings', p.salad_servings + 1), "msg": "Vous avez commandé une salade.", "type": "ubereats"},
            }

            item = items.get(custom_id)
            if item and player.wallet >= item["cost"]:
                player.wallet -= item["cost"]
                item["action"](player)
                if item["type"] == "ubereats": player.food_servings += 1
                db.commit(); db.refresh(player)

                shop_emoji = "🛍️" if item["type"] == "shop" else "🍔"
                await interaction.followup.send(f'{shop_emoji} {item["msg"]}', ephemeral=True)
                
                if item["type"] == "shop":
                    await interaction.edit_original_response(embed=self.generate_shop_embed(player, main_embed_cog), view=ShopView(player))
                else:
                    await interaction.edit_original_response(embed=self.generate_ubereats_embed(player, main_embed_cog), view=UberEatsView(player))
            else:
                await interaction.followup.send(f"⚠️ Transaction échouée. Fonds insuffisants ou article non valide.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Phone(bot))