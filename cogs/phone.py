# --- cogs/phone.py (FINAL - BACK BUTTON FIX) ---
import discord
from discord.ext import commands
from discord import ui
from db.database import SessionLocal
from db.models import PlayerProfile
import traceback

# --- La Vue du Menu Principal du Téléphone ---
class PhoneMainView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="💬 SMS", style=discord.ButtonStyle.green, custom_id="phone_sms", disabled=True)) # SMS désactivé pour l'instant
        self.add_item(ui.Button(label="🛍️ Smoke-Shop", style=discord.ButtonStyle.blurple, custom_id="phone_shop"))
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu"))

# --- NOUVELLE VUE POUR LA BOUTIQUE ---
class ShopView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        self.add_item(ui.Button(label="Acheter Cigarettes (5$) [x10]", style=discord.ButtonStyle.secondary, custom_id="shop_buy_cigarettes", disabled=(player.wallet < 5), emoji="🚬"))
        self.add_item(ui.Button(label="Acheter Bière (3$) [x1]", style=discord.ButtonStyle.blurple, custom_id="shop_buy_beer", disabled=(player.wallet < 3), emoji="🍺"))
        self.add_item(ui.Button(label="Acheter Eau (1$) [x1]", style=discord.ButtonStyle.primary, custom_id="shop_buy_water", disabled=(player.wallet < 1), emoji="💧"))
        self.add_item(ui.Button(label="Acheter Nourriture (4$) [x1]", style=discord.ButtonStyle.success, custom_id="shop_buy_food", disabled=(player.wallet < 4), emoji="🍔"))
        # --- CORRECTION ---
        # Le bouton retour ramène bien au menu principal du téléphone
        self.add_item(ui.Button(label="⬅️ Retour", style=discord.ButtonStyle.grey, custom_id="nav_phone", row=1))


class Phone(commands.Cog):
    """Gestion des applications du téléphone, y compris la boutique."""
    def __init__(self, bot):
        self.bot = bot

    def generate_shop_embed(self, player: PlayerProfile):
        """Génère l'embed de la boutique."""
        embed = discord.Embed(title="🛍️ Smoke-Shop", description="Faites vos achats ici.", color=discord.Color.purple())
        embed.add_field(name="Votre Portefeuille", value=f"**{player.wallet}$**", inline=False)
        embed.add_field(name="Votre Inventaire", value=f"🚬 Cigarettes: {player.cigarettes}\n🍺 Bières: {player.beers}\n💧 Eau: {player.water_bottles}\n🍔 Nourriture: {player.food_servings}", inline=False)
        return embed

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.data or "custom_id" not in interaction.data: return
        custom_id = interaction.data["custom_id"]
        if not (custom_id.startswith("phone_") or custom_id.startswith("shop_buy_") or custom_id == "nav_phone"):
            return

        await interaction.response.defer()
        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild.id)).first()
            state = db.query(ServerState).filter_by(guild_id=str(interaction.guild.id)).first()
            if not player or not state: return

            if custom_id == "nav_phone":
                main_embed_cog = self.bot.get_cog("MainEmbed")
                if not main_embed_cog: return
                embed = main_embed_cog.generate_dashboard_embed(player, state, interaction.guild, show_stats=False)
                embed.description = "Vous ouvrez votre téléphone."
                await interaction.edit_original_response(embed=embed, view=PhoneMainView())
                return

            if custom_id == "phone_shop":
                embed = self.generate_shop_embed(player)
                await interaction.edit_original_response(embed=embed, view=ShopView(player))
            
            elif custom_id.startswith("shop_buy_"):
                message = "Transaction échouée."
                if custom_id == "shop_buy_cigarettes" and player.wallet >= 5:
                    player.wallet -= 5; player.cigarettes += 10; message = "Vous avez acheté un paquet de 10 cigarettes."
                elif custom_id == "shop_buy_beer" and player.wallet >= 3:
                    player.wallet -= 3; player.beers += 1; message = "Vous avez acheté une bière."
                elif custom_id == "shop_buy_water" and player.wallet >= 1:
                    player.wallet -= 1; player.water_bottles += 1; message = "Vous avez acheté une bouteille d'eau."
                elif custom_id == "shop_buy_food" and player.wallet >= 4:
                    player.wallet -= 4; player.food_servings += 1; message = "Vous avez acheté une portion de nourriture."
                
                db.commit(); db.refresh(player)
                await interaction.followup.send(f"🛍️ {message}", ephemeral=True)
                
                new_embed = self.generate_shop_embed(player)
                await interaction.edit_original_response(embed=new_embed, view=ShopView(player))

        except Exception as e:
            print(f"Erreur dans le listener d'interaction de Phone: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.followup.send("Une erreur est survenue.", ephemeral=True)
            db.rollback()
        finally:
            db.close()

async def setup(bot):
    await bot.add_cog(Phone(bot))