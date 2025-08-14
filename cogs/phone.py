# --- cogs/phone.py (FINAL - BACK BUTTON FIX) ---
import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal # Corrected import path
from db.models import PlayerProfile, ServerState # Corrected import path
import traceback

# --- La Vue du Menu Principal du Téléphone ---
class PhoneMainView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="💬 SMS", style=discord.ButtonStyle.green, custom_id="phone_sms", disabled=True)) # SMS désactivé pour l'instant
        self.add_item(ui.Button(label="🛍️ Smoke-Shop", style=discord.ButtonStyle.blurple, custom_id="phone_shop"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))

class SMSView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        # Le bouton retour ramène au menu principal du téléphone
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_phone"))

# --- NOUVEAU: Vue Uber Eats ---
class UberEatsView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180)
        # Ajout des articles Uber Eats avec vérification du portefeuille
        self.add_item(ui.Button(label="Tacos (6$)", emoji="🌮", style=discord.ButtonStyle.success, custom_id="ubereats_buy_tacos", disabled=(player.wallet < 6)))
        self.add_item(ui.Button(label="Pizza (12$)", emoji="🍕", style=discord.ButtonStyle.success, custom_id="ubereats_buy_pizza", disabled=(player.wallet < 12)))
        self.add_item(ui.Button(label="Salade (8$)", emoji="🥗", style=discord.ButtonStyle.success, custom_id="ubereats_buy_salad", disabled=(player.wallet < 8)))
        # Le bouton retour ramène au menu principal du téléphone
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_phone", row=1))


# --- Vue de la boutique (inchangée) ---
class ShopView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="Acheter Cigarettes (5$) [x10]", style=discord.ButtonStyle.secondary, custom_id="shop_buy_cigarettes", disabled=(player.wallet < 5), emoji="🚬"))
        self.add_item(ui.Button(label="Acheter Bière (3$) [x1]", style=discord.ButtonStyle.blurple, custom_id="shop_buy_beer", disabled=(player.wallet < 3), emoji="🍺"))
        self.add_item(ui.Button(label="Acheter Eau (1$) [x1]", style=discord.ButtonStyle.primary, custom_id="shop_buy_water", disabled=(player.wallet < 1), emoji="💧"))
        # Le bouton retour ramène bien au menu principal du téléphone
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_phone", row=1))


# --- MODIFIÉ: Vue principale du téléphone (maintenant dynamique) ---
class PhoneMainView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=180) # Timeout pour une vue dynamique
        self.add_item(ui.Button(label="💬 SMS", style=discord.ButtonStyle.green, custom_id="phone_sms"))
        # NOUVEAU: Bouton Uber Eats
        self.add_item(ui.Button(label="🍔 Uber Eats", style=discord.ButtonStyle.success, custom_id="phone_ubereats"))
        # MODIFIÉ: Le smoke shop est désactivé si non débloqué
        self.add_item(ui.Button(label="🛍️ Smoke-Shop", style=discord.ButtonStyle.blurple, custom_id="phone_shop", disabled=(not player.has_unlocked_smokeshop)))
        # Le bouton retour ramène au dashboard général
        self.add_item(ui.Button(label="⬅️ Fermer le téléphone", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))


class Phone(commands.Cog):
    """Gestion des applications du téléphone, y compris la boutique."""
    def __init__(self, bot):
        self.bot = bot

    def generate_shop_embed(self, player: PlayerProfile):
        embed = discord.Embed(title="🛍️ Smoke-Shop", description="Faites vos achats ici.", color=discord.Color.purple())
        embed.add_field(name="Votre Portefeuille", value=f"**{player.wallet}$**", inline=False)
        return embed

    def generate_ubereats_embed(self, player: PlayerProfile):
        embed = discord.Embed(title="🍔 Uber Eats", description="Une petite faim ? Commandez ici.", color=discord.Color.green())
        embed.add_field(name="Votre Portefeuille", value=f"**{player.wallet}$**", inline=False)
        embed.set_footer(text="Chaque commande ajoute 1 portion de nourriture.")
        return embed

    def generate_sms_embed(self, player: PlayerProfile):
        embed = discord.Embed(title="💬 Messagerie", color=discord.Color.blue())
        if player.messages:
            # Sépare les messages et les affiche
            messages = player.messages.split("\n---\n")
            formatted_messages = "\n\n".join(f"✉️\n> {msg.replace('\n', '\n> ')}" for msg in messages if msg)
            embed.description = formatted_messages
        else:
            embed.description = "Aucun nouveau message."
        return embed

     @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        custom_id = interaction.data["custom_id"]
        
        # Étendre le filtre pour inclure les nouveaux boutons
        if not (custom_id.startswith(("phone_", "shop_buy_", "ubereats_buy_")) or custom_id == "nav_phone"):
            return

        await interaction.response.defer()
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player or not state: return

            # --- NAVIGATION ---
            if custom_id == "nav_phone":
                main_embed_cog = self.bot.get_cog("MainEmbed")
                embed = main_embed_cog.generate_dashboard_embed(player, state, interaction.guild)
                embed.description = "Vous ouvrez votre téléphone."
                await interaction.edit_original_response(embed=embed, view=PhoneMainView(player))

            elif custom_id == "phone_shop":
                embed = self.generate_shop_embed(player)
                await interaction.edit_original_response(embed=embed, view=ShopView(player))
            
            # NOUVEAU: Gérer l'ouverture des apps SMS et Uber Eats
            elif custom_id == "phone_sms":
                embed = self.generate_sms_embed(player)
                await interaction.edit_original_response(embed=embed, view=SMSView(player))
            
            elif custom_id == "phone_ubereats":
                embed = self.generate_ubereats_embed(player)
                await interaction.edit_original_response(embed=embed, view=UberEatsView(player))

            # --- ACTIONS D'ACHAT ---
            elif custom_id.startswith("shop_buy_"):
                # (Logique existante pour le smoke shop, inchangée)
                message = "Transaction échouée."
                if custom_id == "shop_buy_cigarettes" and player.wallet >= 5:
                    player.wallet -= 5; player.cigarettes += 10; message = "Vous avez acheté un paquet de 10 cigarettes."
                elif custom_id == "shop_buy_beer" and player.wallet >= 3:
                    player.wallet -= 3; player.beers += 1; message = "Vous avez acheté une bière."
                elif custom_id == "shop_buy_water" and player.wallet >= 1:
                    player.wallet -= 1; player.water_bottles += 1; message = "Vous avez acheté une bouteille d'eau."
                db.commit(); db.refresh(player)
                await interaction.followup.send(f"🛍️ {message}", ephemeral=True)
                await interaction.edit_original_response(embed=self.generate_shop_embed(player), view=ShopView(player))
            
            # NOUVEAU: Logique pour les achats Uber Eats
            elif custom_id.startswith("ubereats_buy_"):
                message = "Transaction échouée."
                cost = 0
                if custom_id == "ubereats_buy_tacos" and player.wallet >= 6:
                    cost = 6; message = "Vous avez commandé des tacos."
                elif custom_id == "ubereats_buy_pizza" and player.wallet >= 12:
                    cost = 12; message = "Vous avez commandé une pizza."
                elif custom_id == "ubereats_buy_salad" and player.wallet >= 8:
                    cost = 8; message = "Vous avez commandé une salade (pour la bonne conscience)."

                if cost > 0:
                    player.wallet -= cost
                    player.food_servings += 1
                    db.commit(); db.refresh(player)
                    await interaction.followup.send(f"🍔 {message}", ephemeral=True)
                    # Rafraîchit l'embed et la vue pour mettre à jour le portefeuille et les boutons
                    await interaction.edit_original_response(embed=self.generate_ubereats_embed(player), view=UberEatsView(player))
                else:
                    await interaction.followup.send(f"⚠️ {message}", ephemeral=True)

        except Exception as e:
            traceback.print_exc()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(Phone(bot))