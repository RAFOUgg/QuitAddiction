# --- cogs/main_embed.py ---

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
    @commands.command(name="startgame")
    @commands.has_permissions(administrator=True)
    async def startgame(self, ctx):
        """
        Lance l'interface principale du jeu dans le salon actuel ou un salon spécifié.
        Cette commande est un alias pour l'interface principale.
        """
        guild_id_str = str(ctx.guild.id)
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()
        
        if not state:
            state = ServerState(guild_id=guild_id_str)
            db.add(state)
            db.commit()
            # Recharger l'état pour avoir les valeurs par défaut
            state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()

        # Si le jeu n'est pas lancé, on ne crée pas l'embed principal pour l'instant.
        # L'idée est que le jeu soit lancé via la commande admin '/config' puis le bouton "Lancer/Reinitialiser Partie".
        # Si vous voulez que cette commande 'startgame' lance directement l'interface, adaptez ceci.
        
        # Pour l'instant, on simule juste l'affichage d'un menu de base.
        # Il faudrait idéalement que le jeu soit en cours pour afficher les stats.
        # Si game_started est False, l'embed sera vide ou avec des valeurs par défaut.
        
        # On va simuler un état "démarré" pour tester l'affichage.
        if not state.game_started:
            state.game_started = True # Simuler le démarrage pour l'affichage
            state.game_start_time = datetime.datetime.utcnow() # Simuler le temps de début

        embed = self.generate_menu_embed(state)
        view = self.generate_main_menu(guild_id_str) # Passer guild_id en str
        
        # On pourrait vouloir envoyer dans le salon spécifié par state.game_channel_id
        # Pour l'instant, on l'envoie dans le salon de commande.
        await ctx.send(embed=embed, view=view)
        db.close()


    # -------------------
    # Menu principal interactif
    # -------------------
    def generate_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="👨‍🍳 Cuisinier - Tableau de Bord", color=0x00ff99)
        embed.description = "Voici l'état actuel de votre cuisinier."
        
        # Affichage des stats du ServerState (représentant l'état global ou du joueur principal)
        embed.add_field(name="💪 Physique", value=f"{state.phys:.0f}%", inline=True)
        embed.add_field(name="🧠 Mental", value=f"{state.ment:.0f}%", inline=True)
        embed.add_field(name="😊 Bonheur", value=f"{state.happy:.0f}%", inline=True)
        embed.add_field(name="😨 Stress", value=f"{state.stress:.0f}%", inline=True)
        embed.add_field(name="🍎 Faim", value=f"{state.food:.0f}%", inline=True) # Assumant que FOOD est la faim
        embed.add_field(name="💧 Soif", value=f"{state.water:.0f}%", inline=True) # Assumant que WATER est la soif
        embed.add_field(name="☠️ Toxines", value=f"{state.tox:.0f}%", inline=True)
        embed.add_field(name="💥 Addiction", value=f"{state.addiction:.0f}%", inline=True)
        embed.add_field(name="💰 Portefeuille", value=f"{state.wallet}", inline=True)
        
        # Ajout des stats du joueur (si disponible, sinon on affiche des défauts)
        # Ceci est un placeholder, car `state` ne contient pas les stats individuelles.
        # Il faudrait une logique pour récupérer le joueur principal ou une moyenne.
        
        return embed

    def generate_main_menu(self, guild_id: str) -> discord.ui.View: # guild_id en str pour la cohérence avec admin.py
        view = discord.ui.View(timeout=None)
        # Utilisation de la classe MenuButton définie plus bas dans ce cog.
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
            # On accède au cog via interaction.client.get_cog("MainEmbed")
            cog = interaction.client.get_cog("MainEmbed") 

            if not cog:
                await interaction.response.send_message("Erreur interne: Cog MainEmbed non trouvé.", ephemeral=True)
                db.close()
                return

            if self.menu_type == "actions":
                # Les méthodes comme generate_actions_embed doivent exister dans MainEmbed
                await interaction.response.edit_message(embed=cog.generate_actions_embed(state), view=cog.generate_actions_view(self.guild_id))
            elif self.menu_type == "inventory":
                await interaction.response.edit_message(embed=cog.generate_inventory_embed(state), view=cog.generate_inventory_view(self.guild_id))
            elif self.menu_type == "phone":
                await interaction.response.edit_message(embed=cog.generate_phone_embed(state), view=cog.generate_phone_view(self.guild_id))
            elif self.menu_type == "shop":
                await interaction.response.edit_message(embed=cog.generate_shop_embed(state), view=cog.generate_shop_view(self.guild_id))
            elif self.menu_type == "history":
                # Récupération des 10 dernières actions pour ce serveur
                logs = db.query(ActionLog).filter_by(guild_id=str(self.guild_id)).order_by(ActionLog.timestamp.desc()).limit(10).all()
                desc = "\n".join([f"<@{log.user_id}> : {log.action} ({log.timestamp.strftime('%d/%m %H:%M')})" for log in logs]) or "Aucune action enregistrée."
                embed = discord.Embed(title="📊 Historique des 10 dernières actions", description=desc, color=0x00ffcc)
                # Utilisation de la vue de retour générique
                await interaction.response.edit_message(embed=embed, view=cog.generate_back_view(self.guild_id))

            db.close() # Fermer la session DB après utilisation

    # --- Placeholder pour les méthodes générant les vues des sous-menus ---
    # Ces méthodes devraient être implémentées dans ce Cog pour un fonctionnement complet.

    # Génère l'embed pour le téléphone
    def generate_phone_embed(self, state: ServerState) -> discord.Embed:
        messages = [
            "Ton ami te demande comment tu te sens…",
            "Un client te propose un job rapide…",
            "Notification : N'oublie pas de t'hydrater !"
        ]
        question = random.choice(messages)
        embed = discord.Embed(title="📱 Téléphone", description=question, color=0xaaaaee)
        return embed

    # Génère la vue pour le téléphone
    def generate_phone_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Potentiellement ajouter des boutons pour des actions liées au téléphone (ex: répondre, ignorer)
        # ou pour des mini-jeux comme des quiz.
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

    # Génère l'embed pour l'inventaire
    def generate_inventory_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="📦 Inventaire", description="Voici ce que tu possèdes actuellement.", color=0x44ccff)
        # Ceci est un placeholder. L'inventaire devrait être une liste d'objets gérée dans la DB.
        # Pour l'instant, on affiche des objets fictifs liés aux stats du ServerState.
        embed.add_field(name="Consommables", value=f"💧 Eau : x{int(state.water / 20)} | 🍎 Snacks : x{int(state.food / 20)}", inline=False) # Simple estimation
        embed.add_field(name="Argent", value=f"💰 {state.wallet}", inline=False)
        return embed

    # Génère la vue pour l'inventaire
    def generate_inventory_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Boutons pour utiliser ou jeter des objets. Les actions devraient affecter le ServerState ou PlayerProfile.
        view.add_item(self.InventoryActionButton("💧 Boire Eau", guild_id, "use_water", discord.ButtonStyle.green))
        view.add_item(self.InventoryActionButton("🍽️ Manger Snack", guild_id, "use_snack", discord.ButtonStyle.blurple))
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

    # Génère l'embed pour la boutique
    def generate_shop_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🏪 Boutique", description="Achète des objets pour aider le cuisinier à survivre !", color=0xffaa44)
        embed.add_field(name="💧 Bouteille d'eau", value="10💰", inline=True)
        embed.add_field(name="🍽️ Repas équilibré", value="25💰", inline=True)
        embed.add_field(name="💊 Vitamines", value="50💰", inline=True)
        # Ajout d'autres items potentiels
        embed.add_field(name="🚬 Cigarette", value="5💰 (Augmente le bonheur, mais crée de l'addiction et de la toxine)", inline=False)
        return embed

    # Génère la vue pour la boutique
    def generate_shop_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.ShopActionButton("💧 Acheter Eau", guild_id, "buy_water", 10, discord.ButtonStyle.green))
        view.add_item(self.ShopActionButton("🍽️ Acheter Repas", guild_id, "buy_food", 25, discord.ButtonStyle.blurple))
        view.add_item(self.ShopActionButton("💊 Acheter Vitamines", guild_id, "buy_vitamins", 50, discord.ButtonStyle.red))
        # Action pour acheter une cigarette (à adapter en fonction des effets)
        view.add_item(self.ShopActionButton("🚬 Acheter Cigarette", guild_id, "buy_cigarette", 5, discord.ButtonStyle.orange))
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

    # --- Boutons de gestion Inventaire et Boutique ---
    class InventoryActionButton(discord.ui.Button):
        def __init__(self, label, guild_id, action, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id
            self.action = action

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            
            if not state:
                await interaction.response.send_message("Erreur: Etat du serveur non trouvé.", ephemeral=True)
                db.close()
                return

            # --- Logique d'utilisation d'objets ---
            # Ces valeurs sont simplifiées. Idéalement, il faudrait gérer un inventaire séparé.
            if self.action == "use_water":
                if state.water >= 1: # Vérifier si l'objet est disponible
                    state.water = min(100.0, state.water + 20.0) # Augmente la statistique 'water' (simplification)
                    # state.water -= 1 # Diminuer la quantité dans l'inventaire (si géré séparément)
                    await interaction.response.edit_message(embed=self.view.generate_inventory_embed(state), view=self.view.generate_inventory_view(self.guild_id))
                    await interaction.followup.send("Tu as bu de l'eau. Tu te sens un peu mieux hydraté.", ephemeral=True)
                else:
                    await interaction.response.send_message("Tu n'as plus d'eau !", ephemeral=True)
            elif self.action == "use_snack":
                if state.food >= 1: # Vérifier si l'objet est disponible
                    state.food = min(100.0, state.food + 20.0) # Augmente la statistique 'food' (simplification)
                    # state.food -= 1 # Diminuer la quantité dans l'inventaire
                    await interaction.response.edit_message(embed=self.view.generate_inventory_embed(state), view=self.view.generate_inventory_view(self.guild_id))
                    await interaction.followup.send("Tu as mangé un snack. Ta faim a un peu diminué.", ephemeral=True)
                else:
                    await interaction.response.send_message("Tu n'as plus de snacks !", ephemeral=True)

            db.commit()
            db.close()

    class ShopActionButton(discord.ui.Button):
        def __init__(self, label, guild_id, action, price, style):
            super().__init__(label=label, style=style)
            self.guild_id = guild_id
            self.action = action
            self.price = price

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            
            if not state:
                await interaction.response.send_message("Erreur: Etat du serveur non trouvé.", ephemeral=True)
                db.close()
                return

            # --- Logique d'achat ---
            if state.wallet >= self.price:
                state.wallet -= self.price
                
                if self.action == "buy_water":
                    # Augmente la quantité d'eau disponible ou la statistique directement
                    state.water = min(100.0, state.water + 5.0) # Ajoute 5 unités d'hydratation
                    await interaction.followup.send("Tu as acheté une bouteille d'eau.", ephemeral=True)
                elif self.action == "buy_food":
                    state.food = min(100.0, state.food + 5.0) # Ajoute 5 unités de nourriture
                    await interaction.followup.send("Tu as acheté un repas équilibré.", ephemeral=True)
                elif self.action == "buy_vitamins":
                    state.happy = min(100.0, state.happy + 10.0) # Augmente le bonheur
                    await interaction.followup.send("Tu as acheté des vitamines. Tu te sens un peu plus en forme.", ephemeral=True)
                elif self.action == "buy_cigarette":
                    state.water = max(0.0, state.water - 2.0) # Déshydrate un peu
                    state.food = max(0.0, state.food - 1.0) # Diminue la faim (parfois fumer coupe l'appétit)
                    state.happiness = min(100.0, state.happy + 5.0) # Petit boost de bonheur
                    state.stress = max(0.0, state.stress - 5.0) # Réduit un peu le stress
                    state.tox += 1.0 # Augmente les toxines
                    state.addiction = min(100.0, state.addiction + 0.5) # Crée une petite addiction
                    await interaction.followup.send("Tu as fumé une cigarette. Les effets sont immédiats mais pas forcément bons sur le long terme...", ephemeral=True)
                
                db.commit()
                # Rafraîchir l'embed de la boutique après achat
                await interaction.response.edit_message(embed=self.view.generate_shop_embed(state), view=self.view.generate_shop_view(self.guild_id))
            else:
                await interaction.response.send_message("Tu n'as pas assez d'argent !", ephemeral=True)
            
            db.close()

    # -------------------
    # Vues de navigation
    # -------------------
    def generate_back_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Utilisation de la classe BackButton définie plus bas dans ce cog.
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
            
            if not cog:
                await interaction.response.send_message("Erreur interne: Cog MainEmbed non trouvé.", ephemeral=True)
                db.close()
                return

            # Retourne au menu principal
            await interaction.response.edit_message(embed=cog.generate_menu_embed(state), view=cog.generate_main_menu(self.guild_id))
            db.close()

    # --- Méthodes Placeholder pour les sous-menus Actions, Statistiques, etc. ---
    # Ces méthodes doivent être implémentées pour rendre les boutons fonctionnels.

    # Exemple pour le menu Actions
    def generate_actions_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(title="🥗 Santé & Actions", description="Que veux-tu faire ?", color=0x90ee90)
        embed.add_field(name="Besoin de Manger ?", value=f"Faim actuelle : {state.food:.0f}/100. Utilise `!manger`.", inline=False)
        embed.add_field(name="Besoin de Boire ?", value=f"Soif actuelle : {state.water:.0f}/100. Utilise `!boire`.", inline=False)
        embed.add_field(name="Besoin de Fumer ?", value=f"Stress actuel : {state.stress:.0f}. Utilise `!fumer <type>`.", inline=False)
        return embed
    
    def generate_actions_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Ajout des boutons pour les actions (qui seraient des commandes !manger, !boire, etc.)
        # Pour les slash commands, ce serait différent. Ici, on pourrait ajouter des boutons qui lancent ces commandes.
        # Pour l'instant, on se contente de les afficher dans l'embed.
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.secondary))
        return view

async def setup(bot):
    await bot.add_cog(MainEmbed(bot))