# --- cogs/phone.py (REFACTORED - NO LISTENER) ---
import discord
from discord.ext import commands
from discord import ui
from sqlalchemy.orm import Session
from db.models import PlayerProfile, ServerState

# --- VUES ---
class PhoneMainView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="💬 SMS", style=discord.ButtonStyle.green, custom_id="phone_sms"))
        self.add_item(ui.Button(label="🍔 Uber Eats", style=discord.ButtonStyle.success, custom_id="phone_ubereats"))
        self.add_item(ui.Button(label="🛍️ Smoke-Shop", style=discord.ButtonStyle.blurple, custom_id="phone_shop", disabled=(not player.has_unlocked_smokeshop)))
        self.add_item(ui.Button(label="⬅️ Fermer le téléphone", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))

class SMSView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_phone"))
        
class UberEatsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Tacos (6$)", emoji="🌮", style=discord.ButtonStyle.success, custom_id="ubereats_buy_tacos", disabled=(player.wallet < 6)))
        self.add_item(ui.Button(label="Pizza (12$)", emoji="🍕", style=discord.ButtonStyle.success, custom_id="ubereats_buy_pizza", disabled=(player.wallet < 12)))
        self.add_item(ui.Button(label="Salade (8$)", emoji="🥗", style=discord.ButtonStyle.success, custom_id="ubereats_buy_salad", disabled=(player.wallet < 8)))
        self.add_item(ui.Button(label="Bol de Soupe (5$)", emoji="🍲", style=discord.ButtonStyle.success, custom_id="ubereats_buy_soup", disabled=(player.wallet < 5)))
        self.add_item(ui.Button(label="Jus d'Orange (3$)", emoji="🧃", style=discord.ButtonStyle.success, custom_id="ubereats_buy_orange_juice", disabled=(player.wallet < 3)))
        self.add_item(ui.Button(label="Eau (1$)", emoji="💧", style=discord.ButtonStyle.primary, custom_id="ubereats_buy_water", disabled=(player.wallet < 1)))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_phone", row=1))

class ShopView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        self.add_item(ui.Button(label="Acheter Cigarettes (5$)", emoji="🚬", style=discord.ButtonStyle.secondary, custom_id="shop_buy_cigarettes", disabled=(player.wallet < 5)))
        self.add_item(ui.Button(label="Acheter Bière (3$)", emoji="🍺", style=discord.ButtonStyle.blurple, custom_id="shop_buy_beer", disabled=(player.wallet < 3)))
        self.add_item(ui.Button(label="Acheter Eau (1$)", style=discord.ButtonStyle.primary, custom_id="shop_buy_water", disabled=(player.wallet < 1), emoji="💧"))
        # Ajoutez ici les autres articles
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_phone", row=2))

class Phone(commands.Cog):
    """Fournit la logique pour les applications du téléphone."""
    def __init__(self, bot):
        self.bot = bot

    def generate_shop_embed(self, player: PlayerProfile):
        embed = discord.Embed(title="🛍️ Smoke-Shop", description="Faites vos achats ici.", color=discord.Color.purple())
        embed.add_field(name="Votre Portefeuille", value=f"**{player.wallet}$**", inline=False)
        return embed

    def generate_ubereats_embed(self, player: PlayerProfile):
        embed = discord.Embed(title="🍔 Uber Eats", description="Une petite faim ? Commandez ici.", color=discord.Color.green())
        embed.add_field(name="Votre Portefeuille", value=f"**{player.wallet}$**", inline=False)
        embed.set_footer(text="Chaque commande ajoute une portion de nourriture en plus de l'item.")
        return embed

    def generate_sms_embed(self, player: PlayerProfile):
        embed = discord.Embed(title="💬 Messagerie", color=discord.Color.blue())
        if player.messages and player.messages.strip():
            messages = player.messages.strip().split("\n---\n")
            formatted_messages = "\n\n".join(f"✉️\n> {msg.replace('\n', '\n> ')}" for msg in messages if msg)
            embed.description = formatted_messages
        else:
            embed.description = "Aucun nouveau message."
        return embed

    async def handle_interaction(self, interaction: discord.Interaction, db: Session, player: PlayerProfile, state: ServerState):
        """Gère toutes les interactions liées au téléphone."""
        custom_id = interaction.data["custom_id"]
        
        # Navigation
        if custom_id == "phone_shop":
            await interaction.edit_original_response(embed=self.generate_shop_embed(player), view=ShopView(player))
        elif custom_id == "phone_sms":
            await interaction.edit_original_response(embed=self.generate_sms_embed(player), view=SMSView(player))
        elif custom_id == "phone_ubereats":
            await interaction.edit_original_response(embed=self.generate_ubereats_embed(player), view=UberEatsView(player))

        # Achats
        elif custom_id.startswith("shop_buy_") or custom_id.startswith("ubereats_buy_"):
            message = "Transaction échouée ou article non implémenté."
            cost, shop_type = 0, ""

            # Boutique
            if custom_id == "shop_buy_cigarettes" and player.wallet >= 5:
                cost = 5; player.cigarettes += 10; message = "Vous avez acheté 10 cigarettes."; shop_type = "shop"
            elif custom_id == "shop_buy_beer" and player.wallet >= 3:
                cost = 3; player.beers += 1; message = "Vous avez acheté une bière."; shop_type = "shop"
            elif custom_id == "shop_buy_water" and player.wallet >=1:
                cost = 1; player.water_bottles += 1; message = "Vous avez acheté une bouteille d'eau."; shop_type="shop"
            # Uber Eats
            elif custom_id == "ubereats_buy_soup" and player.wallet >= 5:
                cost = 5; player.soup_bowls += 1; message = "Vous avez commandé une soupe."; shop_type = "ubereats"
            
            if cost > 0:
                player.wallet -= cost
                if shop_type == "ubereats": player.food_servings +=1 # Bonus de nourriture générique
                db.commit(); db.refresh(player)

                # Rafraîchir l'interface
                shop_emoji = "🛍️" if shop_type == "shop" else "🍔"
                await interaction.followup.send(f"{shop_emoji} {message}", ephemeral=True)
                if shop_type == "shop":
                    await interaction.edit_original_response(embed=self.generate_shop_embed(player), view=ShopView(player))
                else:
                    await interaction.edit_original_response(embed=self.generate_ubereats_embed(player), view=UberEatsView(player))
            else:
                await interaction.followup.send(f"⚠️ {message}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Phone(bot))