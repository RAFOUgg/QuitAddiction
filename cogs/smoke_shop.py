import discord
from discord import ui
from db.models import PlayerProfile
from db.database import SessionLocal
from sqlalchemy import text

class SmokeShopView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        
        # Shop sections
        self.add_item(BuySelect(player))
        
        # Return button
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="phone_main", emoji="⬅️"))

class BuySelect(ui.Select):
    def __init__(self, player: PlayerProfile):
        self.prices = {
            "weed": 10,  # 10$ par gramme
            "hash": 15,  # 15$ par gramme
            "cbd": 8,    # 8$ par gramme
            "tobacco": 5, # 5$ par gramme
            "papers": 2,  # 2$ le paquet
            "toncs": 1,  # 1$ l'unité
            "grinder": 25,  # 25$ une fois
            "bong": 40,   # 40$ une fois
            "chillum": 30, # 30$ une fois
            "vaporizer": 80, # 80$ une fois
        }
        
        options = []
        
        # Matériaux
        if not player.has_unlocked_smokeshop:
            options = [discord.SelectOption(
                label="🔒 Boutique verrouillée",
                description="Débloquée après le premier jour de travail",
                value="locked"
            )]
        else:
            options.extend([
                discord.SelectOption(
                    label="Weed (10$/g)",
                    description=f"Cannabis de qualité - {player.weed_grams}g en stock",
                    emoji="🌿",
                    value="buy_weed"
                ),
                discord.SelectOption(
                    label="Hash (15$/g)",
                    description=f"Résine de cannabis - {player.hash_grams}g en stock",
                    emoji="🍫",
                    value="buy_hash"
                ),
                discord.SelectOption(
                    label="CBD (8$/g)",
                    description=f"Cannabis légal sans THC - {player.cbd_grams}g en stock",
                    emoji="🌱",
                    value="buy_cbd"
                ),
                discord.SelectOption(
                    label="Tabac (5$/g)",
                    description=f"Pour les toncs - {player.tobacco_grams}g en stock",
                    emoji="🍂",
                    value="buy_tobacco"
                ),
                discord.SelectOption(
                    label="Feuilles (2$/paquet)",
                    description=f"Pour rouler - {player.rolling_papers} en stock",
                    emoji="📄",
                    value="buy_papers"
                ),
                discord.SelectOption(
                    label="Toncs (1$/unité)",
                    description=f"Pour filtrer - {player.toncs} en stock",
                    emoji="🚬",
                    value="buy_toncs"
                ),
            ])

            # Équipement (uniquement si pas déjà possédé)
            if not player.has_grinder:
                options.append(discord.SelectOption(
                    label="Grinder (25$)",
                    description="Broie l'herbe efficacement (+10% d'efficacité)",
                    emoji="⚙️",
                    value="buy_grinder"
                ))
            
            if not player.has_bong:
                options.append(discord.SelectOption(
                    label="Bong (40$)",
                    description="Pour des sessions plus intenses",
                    emoji="🌊",
                    value="buy_bong"
                ))
                
            if not player.has_chillum:
                options.append(discord.SelectOption(
                    label="Chillum (30$)",
                    description="Pipe traditionnelle indienne",
                    emoji="🪠",
                    value="buy_chillum"
                ))
                
            if not player.has_vaporizer:
                options.append(discord.SelectOption(
                    label="Vaporisateur (80$)",
                    description="Alternative plus saine à la combustion",
                    emoji="💨",
                    value="buy_vaporizer"
                ))

        super().__init__(
            placeholder="Choisissez un article...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        if self.values[0] == "locked":
            await interaction.followup.send("La boutique est verrouillée jusqu'à ce que vous terminiez votre premier jour de travail.", ephemeral=True)
            return

        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player:
                await interaction.followup.send("Erreur: Profil introuvable", ephemeral=True)
                return

            item = self.values[0].replace("buy_", "")
            price = self.prices.get(item, 0)

            if player.wallet < price:
                await interaction.followup.send(f"Vous n'avez pas assez d'argent! (Prix: {price}$, Vous avez: {player.wallet}$)", ephemeral=True)
                return

            if item in ["grinder", "bong", "chillum", "vaporizer"]:
                # Équipement
                setattr(player, f"has_{item}", True)
                player.wallet -= price
                message = f"Vous avez acheté un {item} pour {price}$!"
            else:
                # Matériaux (quantités)
                quantities = {
                    "weed": 1,
                    "hash": 1,
                    "cbd": 1,
                    "tobacco": 1,
                    "papers": 10,  # 10 feuilles par paquet
                    "toncs": 5,    # 5 toncs par achat
                }
                qty = quantities.get(item, 1)
                
                # Mise à jour de l'inventaire
                attr = f"{item}_grams" if item in ["weed", "hash", "cbd", "tobacco"] else \
                       "rolling_papers" if item == "papers" else \
                       "toncs"
                
                current_val = getattr(player, attr, 0)
                setattr(player, attr, current_val + qty)
                player.wallet -= price
                
                unit = "g" if item in ["weed", "hash", "cbd", "tobacco"] else "unités"
                message = f"Vous avez acheté {qty}{unit} de {item} pour {price}$!"

            db.commit()
            await interaction.followup.send(message, ephemeral=True)
            
            from .phone import generate_phone_embed, PhoneMainView
            await interaction.message.edit(
                embed=generate_phone_embed(player),
                view=PhoneMainView(player)
            )

        except Exception as e:
            await interaction.followup.send(f"Une erreur est survenue: {str(e)}", ephemeral=True)
            db.rollback()
        finally:
            db.close()
