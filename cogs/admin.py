import discord
from discord.ext import commands
from db.database import SessionLocal
from db.models import ServerState

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_channels = {}

    # -------------------
    # Commandes Admin
    # -------------------
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setchannel(self, ctx, channel: discord.TextChannel):
        """Définit le salon principal pour les interactions du bot et sauvegarde en DB"""
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=str(ctx.guild.id)).first()
        if not state:
            state = ServerState(guild_id=str(ctx.guild.id), main_channel_id=str(channel.id))
            db.add(state)
        else:
            state.main_channel_id = str(channel.id)
        db.commit()
        db.close()

        self.server_channels[ctx.guild.id] = channel.id
        await ctx.send(f"✅ Salon principal défini et sauvegardé : {channel.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def settings(self, ctx):
        """Affiche le menu principal des paramètres de la partie"""
        guild_id = ctx.guild.id
        embed = self.generate_server_config_embed(ctx.guild.id)
        view = self.generate_game_settings_view(guild_id)
        await ctx.send(embed=embed, view=view)

    # -------------------
    # Embeds et Vues
    # -------------------
    def generate_server_config_embed(self, guild_id: int) -> discord.Embed:
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=str(guild_id)).first()
        db.close()

        if not state:
            desc = "Aucune partie n'est encore initialisée pour ce serveur. Configurez les paramètres pour démarrer."
            embed = discord.Embed(title="⚙️ Paramètres du Serveur", description=desc, color=0x44ff44)
            return embed

        embed = discord.Embed(title=f"⚙️ Paramètres du serveur {guild_id}", color=0x44ff44)
        embed.add_field(name="Salon Principal", value=f"<#{state.main_channel_id}>" if state.main_channel_id else "Non défini", inline=False)
        embed.add_field(name="Portefeuille", value=f"{state.wallet}", inline=True)
        embed.add_field(name="Addiction", value=f"{state.addiction}%", inline=True)
        embed.add_field(name="Santé Physique", value=f"{state.phys}%", inline=True)
        embed.add_field(name="Santé Mentale", value=f"{state.ment}%", inline=True)
        embed.add_field(name="Faim", value=f"{state.food}%", inline=True)
        embed.add_field(name="Hydratation", value=f"{state.water}%", inline=True)
        return embed

    def generate_game_settings_view(self, guild_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.green, row=0))
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0))
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1))
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=1))
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2))
        view.add_item(self.BackButton("⬅ Retour au Menu Principal", guild_id, discord.ButtonStyle.red, row=3))
        return view

    # -------------------
    # Boutons Paramètres
    # -------------------
    class ConfigButton(discord.ui.Button):
        def __init__(self, label: str, guild_id: int, style: discord.ButtonStyle, row: int = 0):
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            cog = interaction.client.get_cog("AdminCog")
            await interaction.response.edit_message(
                embed=cog.generate_server_config_embed(self.guild_id),
                view=cog.generate_game_settings_view(self.guild_id)
            )

    class BackButton(discord.ui.Button):
        def __init__(self, label: str, guild_id: int, style: discord.ButtonStyle, row: int = 0):
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            main_embed = interaction.client.get_cog("MainEmbed")
            state = None
            try:
                db_session = SessionLocal()
                state = db_session.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
                db_session.close()
            except Exception:
                pass

            await interaction.response.edit_message(
                embed=main_embed.generate_menu_embed(state),
                view=main_embed.generate_main_menu(self.guild_id)
            )

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
