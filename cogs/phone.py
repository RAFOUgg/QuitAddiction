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
        # CORRECTION : Le bouton de retour est maintenant le bouton de navigation principal du jeu
        self.add_item(ui.Button(label="Retour au jeu", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", row=2, emoji="⬅️"))
        # Add new "Browse" button
        self.add_item(ui.Button(label="Naviguer", style=discord.ButtonStyle.primary, custom_id="phone_browse", emoji="🌐"))

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
        self.add_item(ui.Button(label="Vin (7$)", emoji="🍷", style=discord.ButtonStyle.blurple, custom_id="shop_buy_wine", disabled=(player.wallet < 7))) # Prix ajusté
        self.add_item(ui.Button(label="Joint (10$)", emoji="🌿", style=discord.ButtonStyle.green, custom_id="shop_buy_joint", disabled=(player.wallet < 10)))
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

        custom_id = interaction.data["custom_id"]
        
        phone_screens = {
            "phone_open": (self.generate_phone_main_embed, PhoneMainView),
            "phone_shop": (self.generate_shop_embed, ShopView),
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
                "shop_buy_cigarettes": {"cost": 5, "action": lambda p: setattr(p, 'cigarettes', p.cigarettes + 10), "msg": "Vous avez acheté 10 cigarettes.", "view": ShopView, "embed": self.generate_shop_embed},
                "shop_buy_wine": {"cost": 7, "action": lambda p: setattr(p, 'wine_bottles', p.wine_bottles + 1), "msg": "Vous avez acheté une bouteille de vin.", "view": ShopView, "embed": self.generate_shop_embed},
                "shop_buy_joint": {"cost": 10, "action": lambda p: setattr(p, 'joints', p.joints + 1), "msg": "Vous avez acheté un joint.", "view": ShopView, "embed": self.generate_shop_embed},
                "ubereats_buy_tacos": {"cost": 6, "action": lambda p: setattr(p, 'tacos', p.tacos + 1), "msg": "Vous avez commandé un tacos.", "view": UberEatsView, "embed": self.generate_ubereats_embed},
                "ubereats_buy_soda": {"cost": 2, "action": lambda p: setattr(p, 'soda_cans', p.soda_cans + 1), "msg": "Vous avez commandé un soda.", "view": UberEatsView, "embed": self.generate_ubereats_embed},
                "ubereats_buy_salad": {"cost": 8, "action": lambda p: setattr(p, 'salad_servings', p.salad_servings + 1), "msg": "Vous avez commandé une salade.", "view": UberEatsView, "embed": self.generate_ubereats_embed},
                "ubereats_buy_water": {"cost": 1, "action": lambda p: setattr(p, 'water_bottles', p.water_bottles + 1), "msg": "Vous avez commandé de l'eau.", "view": UberEatsView, "embed": self.generate_ubereats_embed},
                "shop_buy_water": {"cost": 1, "action": lambda p: setattr(p, 'water_bottles', p.water_bottles + 1), "msg": "Vous avez acheté de l'eau.", "view": ShopView, "embed": self.generate_shop_embed},
            }
            item = items.get(custom_id)
            if item and player.wallet >= item["cost"]:
                player.wallet -= item["cost"]
                item["action"](player)
                db.commit(); db.refresh(player)
                await interaction.followup.send(f'✅ {item["msg"]}', ephemeral=True)
                await interaction.edit_original_response(embed=item["embed"](player, main_embed_cog), view=item["view"](player))
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