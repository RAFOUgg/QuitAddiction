# --- cogs/help.py ---

import discord
from discord.ext import commands
from discord import app_commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Affiche l'aide et les explications sur les mécaniques du jeu.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Aide de QuitAddiction",
            description="Bienvenue dans l'aventure ! Votre but est de survivre au quotidien tout en gérant vos addictions.",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🧠 Affichage des Stats (Le Cerveau)",
            value="Cliquez sur le bouton `🧠 Afficher Cerveau` pour voir vos statistiques détaillées. Le jeu continue en arrière-plan et l'interface principale est mise à jour toutes les minutes.",
            inline=False
        )

        embed.add_field(
            name="❤️ Santé Physique",
            value=(
                "**Santé :** Votre santé globale. Si elle atteint 0, c'est la fin.\n"
                "**Énergie :** Nécessaire pour agir. Le sommeil la restaure.\n"
                "**Hygiène :** Votre propreté. Une mauvaise hygiène peut vous rendre malade et affecter votre moral."
            ),
            inline=False
        )

        embed.add_field(
            name="⚠️ Besoins Vitaux",
            value=(
                "_(0% = Satisfait, 100% = Critique)_\n"
                "**Faim :** Monte avec le temps. Mangez pour la réduire.\n"
                "**Soif :** Monte plus vite que la faim. Buvez pour la réduire.\n"
                "**Vessie :** Se remplit quand vous buvez. N'attendez pas le dernier moment !"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🤔 État Mental",
            value=(
                "_(0% = Mauvais, 100% = Bon)_\n"
                "**Mentale :** Votre santé mentale. Une valeur basse entraîne des conséquences.\n"
                "**Stress :** Augmente avec les envies et les problèmes.\n"
                "**Humeur :** Votre bonheur général."
            ),
            inline=True
        )

        embed.add_field(
            name="🚬 Addiction & Manque",
            value=(
                "**Dépendance :** Augmente avec la consommation. Plus elle est haute, plus le manque est sévère.\n"
                "**Manque :** L'envie physique de consommer. Augmente le stress et diminue le bonheur.\n"
                "**Défonce :** Votre niveau d'intoxication actuel."
            ),
            inline=False
        )

        embed.add_field(
            name="📱 Téléphone",
            value="Utilisez le téléphone pour accéder à des services utiles comme **Uber Eats** pour la nourriture ou le **Smoke-Shop** pour... autre chose. Vous pouvez aussi y gérer vos notifications.",
            inline=False
        )

        embed.set_footer(text="Bonne chance pour votre sevrage !")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))