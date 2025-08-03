import discord
from discord.ext import commands
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile, ActionLog
import datetime
import random

class MainEmbed(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_channels = {}

    # -------------------
    # Commandes Admin
    # -------------------
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setchannel(self, ctx, channel: discord.TextChannel):
        self.server_channels[ctx.guild.id] = channel.id
        await ctx.send(f"✅ Salon principal défini : {channel.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def startgame(self, ctx):
        channel_id = self.server_channels.get(ctx.guild.id, ctx.channel.id)
        channel = self.bot.get_channel(channel_id)
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=str(ctx.guild.id)).first()
        if not state:
            state = ServerState(guild_id=str(ctx.guild.id))
            db.add(state)
            db.commit()
        embed = self.generate_menu_embed(state)
        view = self.generate_main_menu(ctx.guild.id)
        await channel.send(embed=embed, view=view)

    # -------------------
    # Menu principal interactif
    # -------------------
    def generate_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="👨‍🍳 Cuisinier - Menu Principal", color=0x00ff99)
        embed.description = "Choisissez une catégorie pour interagir avec le cuisinier."
        embed.add_field(name="PHYS", value=f"{state.phys}%", inline=True)
        embed.add_field(name="MENT", value=f"{state.ment}%", inline=True)
        embed.add_field(name="HAPPY", value=f"{state.happy}%", inline=True)
        embed.add_field(name="STRESS", value=f"{state.stress}%", inline=True)
        embed.add_field(name="FOOD", value=f"{state.food}%", inline=True)
        embed.add_field(name="WATER", value=f"{state.water}%", inline=True)
        embed.add_field(name="TOX", value=f"{state.tox}%", inline=True)
        embed.add_field(name="ADDICTION", value=f"{state.addiction}%", inline=True)
        embed.add_field(name="💰 Portefeuille", value=f"{state.wallet}", inline=True)
        return embed

    def generate_main_menu(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.MenuButton("🥗 Santé & Actions", guild_id, "actions", discord.ButtonStyle.green))
        view.add_item(self.MenuButton("📦 Inventaire", guild_id, "inventory", discord.ButtonStyle.blurple))
        view.add_item(self.MenuButton("📱 Téléphone", guild_id, "phone", discord.ButtonStyle.gray))
        view.add_item(self.MenuButton("🏪 Boutique", guild_id, "shop", discord.ButtonStyle.red))
        view.add_item(self.MenuButton("📊 Historique", guild_id, "history", discord.ButtonStyle.green))
        return view

    # -------------------
    # Boutons de menu principal
    # -------------------
    class MenuButton(discord.ui.Button):
        def __init__(self, label, guild_id, menu_type, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id
            self.menu_type = menu_type

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("MainEmbed")

            if self.menu_type == "actions":
                await interaction.response.edit_message(embed=cog.generate_actions_embed(state), view=cog.generate_actions_view(self.guild_id))
            elif self.menu_type == "inventory":
                await interaction.response.edit_message(embed=cog.generate_inventory_embed(state), view=cog.generate_inventory_view(self.guild_id))
            elif self.menu_type == "phone":
                await interaction.response.edit_message(embed=cog.generate_phone_embed(state), view=cog.generate_phone_view(self.guild_id))
            elif self.menu_type == "shop":
                await interaction.response.edit_message(embed=cog.generate_shop_embed(state), view=cog.generate_shop_view(self.guild_id))
            elif self.menu_type == "history":
                logs = db.query(ActionLog).filter_by(guild_id=str(self.guild_id)).order_by(ActionLog.timestamp.desc()).limit(10).all()
                desc = "\n".join([f"<@{log.user_id}> : {log.action} ({log.timestamp.strftime('%d/%m %H:%M')})" for log in logs]) or "Aucune action enregistrée."
                embed = discord.Embed(title="📊 Historique des 10 dernières actions", description=desc, color=0x00ffcc)
                await interaction.response.edit_message(embed=embed, view=cog.generate_back_view(self.guild_id))

    # -------------------
    # Sous-menus et gestion Inventaire/Boutique
    # -------------------
    def generate_phone_embed(self, state: ServerState) -> discord.Embed:
        messages = [
            "Ton ami te demande comment tu te sens…",
            "Un client te propose un job rapide…",
            "Notification : N'oublie pas de t'hydrater !"
        ]
        question = random.choice(messages)
        embed = discord.Embed(title="📱 Téléphone", description=question, color=0xaaaaee)
        return embed

    def generate_phone_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Quiz possible plus tard
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

    def generate_inventory_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="📦 Inventaire", description="Liste des objets possédés", color=0x44ccff)
        # Placeholder pour inventaire réel
        embed.add_field(name="Inventaire", value="Eau x3 | Snack x2", inline=False)
        return embed

    def generate_inventory_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Boutons pour utiliser ou jeter des objets
        view.add_item(self.InventoryActionButton("💧 Boire Eau", guild_id, "use_water", discord.ButtonStyle.green))
        view.add_item(self.InventoryActionButton("🍽️ Manger Snack", guild_id, "use_snack", discord.ButtonStyle.blurple))
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

    def generate_shop_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🏪 Boutique", description="Achetez des objets pour aider le cuisinier", color=0xffaa44)
        embed.add_field(name="💧 Bouteille d'eau", value="10💰", inline=True)
        embed.add_field(name="🍽️ Repas", value="25💰", inline=True)
        embed.add_field(name="💊 Vitamines", value="50💰", inline=True)
        return embed

    def generate_shop_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.ShopActionButton("💧 Acheter Eau", guild_id, "buy_water", 10, discord.ButtonStyle.green))
        view.add_item(self.ShopActionButton("🍽️ Acheter Repas", guild_id, "buy_food", 25, discord.ButtonStyle.blurple))
        view.add_item(self.ShopActionButton("💊 Acheter Vitamines", guild_id, "buy_vitamins", 50, discord.ButtonStyle.red))
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

    # -------------------
    # Boutons de gestion Inventaire et Boutique
    # -------------------
    class InventoryActionButton(discord.ui.Button):
        def __init__(self, label, guild_id, action, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id
            self.action = action

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            if self.action == "use_water":
                state.water = min(100, state.water + 20)
            elif self.action == "use_snack":
                state.food = min(100, state.food + 20)
            db.commit()
            cog = interaction.client.get_cog("MainEmbed")
            await interaction.response.edit_message(embed=cog.generate_inventory_embed(state), view=cog.generate_inventory_view(self.guild_id))

    class ShopActionButton(discord.ui.Button):
        def __init__(self, label, guild_id, action, price, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id
            self.action = action
            self.price = price

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            if state.wallet >= self.price:
                state.wallet -= self.price
                if self.action == "buy_water":
                    # Ajouter à inventaire réel plus tard
                    state.water = min(100, state.water + 5)
                elif self.action == "buy_food":
                    state.food = min(100, state.food + 5)
                elif self.action == "buy_vitamins":
                    state.happy = min(100, state.happy + 10)
            db.commit()
            cog = interaction.client.get_cog("MainEmbed")
            await interaction.response.edit_message(embed=cog.generate_shop_embed(state), view=cog.generate_shop_view(self.guild_id))

    # -------------------
    # Vues de navigation
    # -------------------
    def generate_back_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

    class BackButton(discord.ui.Button):
        def __init__(self, label, guild_id, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("MainEmbed")
            await interaction.response.edit_message(embed=cog.generate_menu_embed(state), view=cog.generate_main_menu(self.guild_id))

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))