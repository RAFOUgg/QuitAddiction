import discord
from discord.ext import commands
from discord import ui
from db.models import PlayerProfile
from db.database import SessionLocal
from sqlalchemy import text

def check_inventory(player: PlayerProfile) -> dict:
    """Helper function to safely get inventory values"""
    return {
        'weed_grams': getattr(player, 'weed_grams', 0),
        'hash_grams': getattr(player, 'hash_grams', 0),
        'rolling_papers': getattr(player, 'rolling_papers', 0),
        'toncs': getattr(player, 'toncs', 0),
        'joints': getattr(player, 'joints', 0),
        'has_grinder': getattr(player, 'has_grinder', False),
        'has_bong': getattr(player, 'has_bong', False),
        'has_chillum': getattr(player, 'has_chillum', False),
        'has_vaporizer': getattr(player, 'has_vaporizer', False),
        'joints_crafted': getattr(player, 'joints_crafted', 0),
        'bong_uses': getattr(player, 'bong_uses', 0),
        'chillum_uses': getattr(player, 'chillum_uses', 0),
        'vaporizer_uses': getattr(player, 'vaporizer_uses', 0)
    }

class CraftSelect(ui.Select):
    def __init__(self, player: PlayerProfile):
        self.player = player
        inventory = check_inventory(player)
        options = []
        
        # Joint crafting options
        if inventory['weed_grams'] >= 1 and inventory['rolling_papers'] >= 1 and inventory['toncs'] >= 1:
            desc = "Nécessite: 1g Weed + 1 Feuille + 1 Tonc"
            if inventory['has_grinder']:
                desc += " (Grinder disponible: +10% d'efficacité)"
            options.append(discord.SelectOption(
                label="Crafter un Joint (Weed)",
                description=desc,
                emoji="🌿",
                value="craft_joint_weed"
            ))
            
        if inventory['hash_grams'] >= 1 and inventory['rolling_papers'] >= 1 and inventory['toncs'] >= 1:
            options.append(discord.SelectOption(
                label="Crafter un Joint (Hash)",
                description="Nécessite: 1g Hash + 1 Feuille + 1 Tonc",
                emoji="🍫",
                value="craft_joint_hash"
            ))
            
        if inventory['has_bong'] and (inventory['weed_grams'] >= 1 or inventory['hash_grams'] >= 1):
            options.append(discord.SelectOption(
                label="Préparer le Bong",
                description="Nécessite: 1g Weed/Hash",
                emoji="🌊",
                value="prepare_bong"
            ))
            
        if inventory['has_chillum'] and (inventory['weed_grams'] >= 1 or inventory['hash_grams'] >= 1):
            options.append(discord.SelectOption(
                label="Préparer le Chillum",
                description="Nécessite: 1g Weed/Hash",
                emoji="🪠",
                value="prepare_chillum"
            ))
            
        if inventory['has_vaporizer'] and inventory['weed_grams'] >= 1:
            options.append(discord.SelectOption(
                label="Préparer le Vaporisateur",
                description="Nécessite: 1g Weed",
                emoji="💨",
                value="prepare_vaporizer"
            ))

        # Si aucune option disponible
        if not options:
            options = [discord.SelectOption(
                label="Aucun craft disponible",
                description="Vous avez besoin de plus d'items pour crafter",
                emoji="❌",
                value="none"
            )]

        super().__init__(
            placeholder="Choisissez quoi crafter...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        if self.values[0] == "none":
            await interaction.followup.send("Vous n'avez pas les items nécessaires pour crafter.", ephemeral=True)
            return

        db = SessionLocal()
        try:
            player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
            if not player:
                await interaction.followup.send("Erreur: Profil introuvable.", ephemeral=True)
                return

            inventory = check_inventory(player)
            craft_success = False
            message = ""

            if self.values[0] == "craft_joint_weed":
                if inventory['weed_grams'] >= 1 and inventory['rolling_papers'] >= 1 and inventory['toncs'] >= 1:
                    bonus = 1.1 if inventory['has_grinder'] else 1.0
                    db.execute(
                        text("""
                        UPDATE player_profile 
                        SET joints = joints + :bonus_joints,
                            weed_grams = weed_grams - 1,
                            rolling_papers = rolling_papers - 1,
                            toncs = toncs - 1,
                            joints_crafted = joints_crafted + 1
                        WHERE guild_id = :guild_id
                        """),
                        {
                            'bonus_joints': int(1 * bonus),
                            'guild_id': str(interaction.guild_id)
                        }
                    )
                    craft_success = True
                    message = f"Joint crafté avec succès! {'(Bonus grinder appliqué)' if inventory['has_grinder'] else ''}"

            elif self.values[0] == "craft_joint_hash":
                if inventory['hash_grams'] >= 1 and inventory['rolling_papers'] >= 1 and inventory['toncs'] >= 1:
                    db.execute(
                        text("""
                        UPDATE player_profile 
                        SET joints = joints + 1,
                            hash_grams = hash_grams - 1,
                            rolling_papers = rolling_papers - 1,
                            toncs = toncs - 1,
                            joints_crafted = joints_crafted + 1
                        WHERE guild_id = :guild_id
                        """),
                        {'guild_id': str(interaction.guild_id)}
                    )
                    craft_success = True
                    message = "Joint de hash crafté avec succès!"

            elif self.values[0] == "prepare_bong":
                if inventory['weed_grams'] >= 1 or inventory['hash_grams'] >= 1:
                    if inventory['weed_grams'] >= 1:
                        db.execute(
                            text("""
                            UPDATE player_profile 
                            SET weed_grams = weed_grams - 1,
                                bong_uses = bong_uses + 1
                            WHERE guild_id = :guild_id
                            """),
                            {'guild_id': str(interaction.guild_id)}
                        )
                    else:
                        db.execute(
                            text("""
                            UPDATE player_profile 
                            SET hash_grams = hash_grams - 1,
                                bong_uses = bong_uses + 1
                            WHERE guild_id = :guild_id
                            """),
                            {'guild_id': str(interaction.guild_id)}
                        )
                    craft_success = True
                    message = "Bong préparé avec succès!"

            elif self.values[0] == "prepare_chillum":
                if inventory['weed_grams'] >= 1 or inventory['hash_grams'] >= 1:
                    if inventory['weed_grams'] >= 1:
                        db.execute(
                            text("""
                            UPDATE player_profile 
                            SET weed_grams = weed_grams - 1,
                                chillum_uses = chillum_uses + 1
                            WHERE guild_id = :guild_id
                            """),
                            {'guild_id': str(interaction.guild_id)}
                        )
                    else:
                        db.execute(
                            text("""
                            UPDATE player_profile 
                            SET hash_grams = hash_grams - 1,
                                chillum_uses = chillum_uses + 1
                            WHERE guild_id = :guild_id
                            """),
                            {'guild_id': str(interaction.guild_id)}
                        )
                    craft_success = True
                    message = "Chillum préparé avec succès!"

            elif self.values[0] == "prepare_vaporizer":
                if inventory['weed_grams'] >= 1:
                    db.execute(
                        text("""
                        UPDATE player_profile 
                        SET weed_grams = weed_grams - 1,
                            vaporizer_uses = vaporizer_uses + 1
                        WHERE guild_id = :guild_id
                        """),
                        {'guild_id': str(interaction.guild_id)}
                    )
                    craft_success = True
                    message = "Vaporisateur préparé avec succès!"

            if craft_success:
                db.commit()
                # Rafraichir le joueur
                player = db.query(PlayerProfile).filter_by(guild_id=str(interaction.guild_id)).first()
                await interaction.followup.send(message, ephemeral=True)
                # Re-afficher l'inventaire mis à jour
                try:
                    if interaction.message:
                        await interaction.message.edit(
                            embed=generate_inventory_embed(player),
                            view=InventoryView(player)
                        )
                    else:
                        await interaction.followup.send(
                            embed=generate_inventory_embed(player),
                            view=InventoryView(player)
                        )
                except discord.NotFound:
                    await interaction.followup.send(
                        embed=generate_inventory_embed(player),
                        view=InventoryView(player)
                    )
            else:
                await interaction.followup.send("Erreur: Items insuffisants pour le craft.", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"Une erreur est survenue: {str(e)}", ephemeral=True)
            db.rollback()
        finally:
            db.close()

class InventoryView(ui.View):
    def __init__(self, player: PlayerProfile):
        super().__init__(timeout=None)
        self.add_item(CraftSelect(player))
        self.add_item(ui.Button(label="Retour", style=discord.ButtonStyle.grey, custom_id="nav_main_menu", emoji="⬅️"))

def generate_inventory_embed(player: PlayerProfile) -> discord.Embed:
    embed = discord.Embed(title="🎒 Inventaire", color=discord.Color.blue())
    inventory = check_inventory(player)
    
    # Section Consommables
    consumables = []
    if getattr(player, 'food_servings', 0) > 0: consumables.append(f"🥪 Sandwich: {player.food_servings}")
    if getattr(player, 'water_bottles', 0) > 0: consumables.append(f"💧 Eau: {player.water_bottles}")
    if getattr(player, 'soda_cans', 0) > 0: consumables.append(f"🥤 Soda: {player.soda_cans}")
    if getattr(player, 'tacos', 0) > 0: consumables.append(f"🌮 Tacos: {player.tacos}")
    if getattr(player, 'salad_servings', 0) > 0: consumables.append(f"🥗 Salade: {player.salad_servings}")
    if getattr(player, 'wine_bottles', 0) > 0: consumables.append(f"🍷 Vin: {player.wine_bottles}")
    if consumables:
        embed.add_field(name="🍽️ Consommables", value="\n".join(consumables), inline=True)

    # Section Smoke
    smoke_items = []
    if getattr(player, 'cigarettes', 0) > 0: smoke_items.append(f"🚬 Cigarettes: {player.cigarettes}")
    if getattr(player, 'e_cigarettes', 0) > 0: smoke_items.append(f"💨 E-cigarettes: {player.e_cigarettes}")
    if inventory['joints'] > 0: smoke_items.append(f"🌿 Joints: {inventory['joints']}")
    if smoke_items:
        embed.add_field(name="🚬 Items Fumables", value="\n".join(smoke_items), inline=True)

    # Section Matériaux
    materials = []
    if inventory['weed_grams'] > 0: materials.append(f"🌿 Weed: {inventory['weed_grams']}g")
    if inventory['hash_grams'] > 0: materials.append(f"🍫 Hash: {inventory['hash_grams']}g")
    if getattr(player, 'cbd_grams', 0) > 0: materials.append(f"🌱 CBD: {player.cbd_grams}g")
    if getattr(player, 'tobacco_grams', 0) > 0: materials.append(f"🍂 Tabac: {player.tobacco_grams}g")
    if inventory['rolling_papers'] > 0: materials.append(f"📄 Feuilles: {inventory['rolling_papers']}")
    if inventory['toncs'] > 0: materials.append(f"🚬 Toncs: {inventory['toncs']}")
    if materials:
        embed.add_field(name="📦 Matériaux", value="\n".join(materials), inline=True)

    # Section Équipement
    equipment = []
    if inventory['has_grinder']: equipment.append("⚙️ Grinder")
    if inventory['has_bong']: equipment.append("🌊 Bong")
    if inventory['has_chillum']: equipment.append("🪠 Chillum")
    if inventory['has_vaporizer']: equipment.append("💨 Vaporisateur")
    if equipment:
        embed.add_field(name="🛠️ Équipement", value="\n".join(equipment), inline=True)

    # Statistiques de craft
    stats = []
    if inventory['joints_crafted'] > 0: stats.append(f"🌿 Joints craftés: {inventory['joints_crafted']}")
    if inventory['bong_uses'] > 0: stats.append(f"🌊 Utilisations Bong: {inventory['bong_uses']}")
    if inventory['chillum_uses'] > 0: stats.append(f"🪠 Utilisations Chillum: {inventory['chillum_uses']}")
    if inventory['vaporizer_uses'] > 0: stats.append(f"💨 Utilisations Vaporisateur: {inventory['vaporizer_uses']}")
    if stats:
        embed.add_field(name="📊 Statistiques", value="\n".join(stats), inline=True)

    embed.set_footer(text="💡 Utilisez le menu déroulant pour crafter des items")
    return embed

class InventoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
