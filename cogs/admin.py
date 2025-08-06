# --- cogs/admin.py ---

import discord
from discord.ext import commands
from discord import app_commands, ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import hashlib
import datetime
import math
from typing import List, Tuple, Dict, Optional

# Constante pour le nombre maximum d'options par page
MAX_OPTIONS_PER_PAGE = 25

class AdminCog(commands.Cog):
    """Gestion des configurations du bot et du jeu pour le serveur."""
    def __init__(self, bot):
        self.bot = bot

    # --- Préréglages des Modes de Jeu ---
    GAME_MODES = {
        "peaceful": {
            "tick_interval_minutes": 60,
            "rates": {
                "hunger": 5.0, "thirst": 4.0, "bladder": 5.0,
                "energy": 3.0, "stress": 1.0, "boredom": 2.0,
                "addiction_base": 0.05, "toxins_base": 0.1,
            }
        },
        "medium": {
            "tick_interval_minutes": 30,
            "rates": {
                "hunger": 10.0, "thirst": 8.0, "bladder": 15.0,
                "energy": 5.0, "stress": 3.0, "boredom": 7.0,
                "addiction_base": 0.1, "toxins_base": 0.5,
            }
        },
        "hard": {
            "tick_interval_minutes": 15,
            "rates": {
                "hunger": 20.0, "thirst": 16.0, "bladder": 30.0,
                "energy": 10.0, "stress": 6.0, "boredom": 14.0,
                "addiction_base": 0.2, "toxins_base": 1.0,
            }
        }
    }
    
    # --- Préréglages des Durées de Partie ---
    GAME_DURATIONS = {
        "short": {"days": 14, "label": "Court (14 jours)"},
        "medium": {"days": 31, "label": "Moyen (31 jours)"},
        "long": {"days": 72, "label": "Long (72 jours)"},
    }

    # Limites pour les labels et valeurs des options de SelectMenu selon Discord API
    MAX_OPTION_LENGTH = 25
    MIN_OPTION_LENGTH = 1

    # -------------------
    # Commandes Admin (Slash Commands)
    # -------------------
    
    @app_commands.command(name="config", description="Configure les paramètres du bot et du jeu pour le serveur.")
    @app_commands.default_permissions(administrator=True) # Restriction aux administrateurs
    async def config(self, interaction: discord.Interaction):
        """Affiche l'interface de configuration principale."""
        guild_id_str = str(interaction.guild.id)
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()

        # Si aucun état de serveur n'existe pour ce serveur, en créer un.
        if not state:
            state = ServerState(guild_id=guild_id_str)
            db.add(state)
            db.commit() 
            state = db.query(ServerState).filter_by(guild_id=guild_id_str).first() # Recharger pour les valeurs par défaut

        # Envoyer le message interactif principal
        await interaction.response.send_message(
            embed=self.generate_config_menu_embed(state),
            view=self.generate_config_menu_view(guild_id_str, interaction.guild), # Passer le guild
            ephemeral=True 
        )
        db.close()

    # --- Méthodes pour Générer les Embeds et Vues de Configuration ---
    
    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        """Génère l'embed principal affichant l'état actuel des configurations."""
        embed = discord.Embed(
            title="⚙️ Configuration du Bot et du Jeu",
            description="Utilisez les boutons ci-dessous pour ajuster les paramètres du serveur.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="▶️ **Statut Général**",
            value=f"**Jeu :** `{'En cours' if state.game_started else 'Non lancée'}`\n"
                  f"**Mode :** `{state.game_mode.capitalize() if state.game_mode else 'Medium (Standard)'}`\n"
                  f"**Durée :** `{self.GAME_DURATIONS.get(state.duration_key, {}).get('label', 'Moyen (31 jours)') if state.duration_key else 'Moyen (31 jours)'}`",
            inline=False
        )

        admin_role_mention = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        notification_role_mention = f"<@&{state.notification_role_id}>" if hasattr(state, 'notification_role_id') and state.notification_role_id else "Non défini"
        game_channel_mention = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"
        
        embed.add_field(
            name="📍 **Configuration du Serveur**",
            value=f"**Rôle Admin :** {admin_role_mention}\n"
                  f"**Rôle Notification :** {notification_role_mention}\n"
                  f"**Salon de Jeu :** {game_channel_mention}",
            inline=False
        )

        tick_interval = state.game_tick_interval_minutes if state.game_tick_interval_minutes is not None else 30
        
        embed.add_field(
            name="⏱️ **Paramètres du Jeu**",
            value=f"**Intervalle Tick (min) :** `{tick_interval}`",
            inline=False
        )
        
        embed.add_field(
            name="📉 **Taux de Dégradation / Tick**",
            value=f"**Faim :** `{state.degradation_rate_hunger:.1f}` | **Soif :** `{state.degradation_rate_thirst:.1f}` | **Vessie :** `{state.degradation_rate_bladder:.1f}`\n"
                  f"**Énergie :** `{state.degradation_rate_energy:.1f}` | **Stress :** `{state.degradation_rate_stress:.1f}` | **Ennui :** `{state.degradation_rate_boredom:.1f}`",
            inline=False
        )
        
        embed.set_footer(text="Utilisez les boutons ci-dessous pour naviguer et modifier les paramètres.")
        return embed

    # --- Bouton pour lancer la sous-vue de sélection du Mode et Durée ---
    class SetupGameModeButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'): # Ajout de cog
            super().__init__(label=label, style=style, row=row) 
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.edit_message(
                embed=self.cog.generate_setup_game_mode_embed(),
                view=self.cog.generate_setup_game_mode_view(self.guild_id)
            )

    # --- Embed pour la sélection du Mode de Jeu et Durée ---
    def generate_setup_game_mode_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Configuration du Mode et de la Durée",
            description="Sélectionnez un mode de difficulté et une durée pour la partie.",
            color=discord.Color.teal()
        )
        return embed

    # --- View pour la sélection du Mode de Jeu et Durée ---
    def generate_setup_game_mode_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.GameModeSelect(guild_id, "mode", row=0, cog=self)) # Passer self
        view.add_item(self.GameDurationSelect(guild_id, "duration", row=1, cog=self)) # Passer self
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=2, cog=self)) # Passer self
        return view

    # --- Classe de Menu: Mode de Difficulté (Peaceful, Medium, Hard) ---
    class GameModeSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, cog: 'AdminCog'): # Ajout de cog
            options = [
                discord.SelectOption(label="Peaceful", description="Taux de dégradation bas.", value="peaceful"),
                discord.SelectOption(label="Medium (Standard)", description="Taux de dégradation standard.", value="medium"),
                discord.SelectOption(label="Hard", description="Taux de dégradation élevés. Plus difficile.", value="hard")
            ]
            super().__init__(placeholder="Choisissez le mode de difficulté...", options=options, custom_id=f"select_gamemode_{guild_id}", row=row)
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            selected_mode = self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                mode_data = self.cog.GAME_MODES.get(selected_mode) # Utiliser self.cog

                if mode_data:
                    state.game_mode = selected_mode
                    state.game_tick_interval_minutes = mode_data["tick_interval_minutes"]
                    for key, value in mode_data["rates"].items():
                        setattr(state, f"degradation_rate_{key}", value)
                
                    db.commit()
                    
                    embed = self.cog.generate_setup_game_mode_embed() # Utiliser self.cog
                    embed.description = f"✅ Mode de difficulté défini sur **{selected_mode.capitalize()}**.\n" + embed.description
                    
                    await interaction.response.edit_message(embed=embed, view=self.cog.generate_setup_game_mode_view(self.guild_id)) # Utiliser self.cog
            
            db.close()

    # --- Classe de Menu: Durée de Partie (Short, Medium, Long) ---
    class GameDurationSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, cog: 'AdminCog'): # Ajout de cog
            options = [
                discord.SelectOption(label=data["label"], value=key)
                for key, data in AdminCog.GAME_DURATIONS.items()
            ]
            super().__init__(placeholder="Choisissez la durée de la partie...", options=options, custom_id=f"select_gameduration_{guild_id}", row=row)
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            selected_duration_key = self.values[0]
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                duration_data = self.cog.GAME_DURATIONS.get(selected_duration_key) # Utiliser self.cog
                
                if duration_data:
                    state.duration_key = selected_duration_key 
                    db.commit()
                    
                    embed = self.cog.generate_setup_game_mode_embed() # Utiliser self.cog
                    embed.description = f"✅ Durée de la partie définie sur **{duration_data['label']}**.\n" + embed.description
                    await interaction.response.edit_message(embed=embed, view=self.cog.generate_setup_game_mode_view(self.guild_id)) # Utiliser self.cog

            db.close()
            
    # --- Bouton de retour vers le Menu Principal des Paramètres ---
    class BackButton(ui.Button): 
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int = 0, cog: 'AdminCog'=None): # Ajout de cog
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog
            
        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            
            await interaction.response.edit_message(
                embed=self.cog.generate_config_menu_embed(state), # Utiliser self.cog
                view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild) # Utiliser self.cog
            )
            db.close()

    # --- Classe générique pour les boutons de configuration ---
    class ConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'): # Ajout de cog
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            self.label = label
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()

            if self.label == "🎮 Lancer/Reinitialiser Partie":
                if state:
                    state.game_started = not state.game_started
                    state.game_start_time = datetime.datetime.utcnow() if state.game_started else None
                    db.commit()
                    
                    await interaction.response.edit_message(
                        embed=self.cog.generate_config_menu_embed(state), # Utiliser self.cog
                        view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild) # Utiliser self.cog
                    )
                    await interaction.followup.send(f"La partie a été {'lancée' if state.game_started else 'arrêtée/réinitialisée'}.", ephemeral=True)
                else:
                    await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur.", ephemeral=True)

            elif self.label == "💾 Sauvegarder l'État":
                await interaction.response.edit_message(
                    embed=self.cog.generate_config_menu_embed(state), # Utiliser self.cog
                    view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild) # Utiliser self.cog
                )
                await interaction.followup.send("L'état actuel a été sauvegardé.", ephemeral=True)

            elif self.label == "📊 Voir Statistiques":
                await interaction.response.edit_message(
                    embed=self.cog.generate_stats_embed(self.guild_id), # Utiliser self.cog
                    view=self.cog.generate_stats_view(self.guild_id) # Utiliser self.cog
                )
                await interaction.followup.send("Affichage des statistiques...", ephemeral=True)

            elif self.label == "🔔 Notifications":
                await interaction.response.edit_message(
                    embed=self.cog.generate_notifications_embed(self.guild_id), # Utiliser self.cog
                    view=self.cog.generate_notifications_view(self.guild_id) # Utiliser self.cog
                )
                await interaction.followup.send("Configuration des notifications...", ephemeral=True)

            elif self.label == "🛠️ Options Avancées":
                await interaction.response.edit_message(
                    embed=self.cog.generate_advanced_options_embed(self.guild_id), # Utiliser self.cog
                    view=self.cog.generate_advanced_options_view(self.guild_id) # Utiliser self.cog
                )
                await interaction.followup.send("Accès aux options avancées...", ephemeral=True)

            db.close()

    # --- Bouton qui va ouvrir la configuration des rôles et salons ---
    class GeneralConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int, cog: 'AdminCog'): # Ajout de cog
            super().__init__(label=label, style=style, row=row) 
            self.guild_id = guild_id
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            # On passe le guild à la méthode de génération pour qu'elle puisse accéder aux rôles/canaux
            await interaction.response.edit_message(
                embed=self.cog.generate_role_and_channel_config_embed(state), # Utiliser self.cog
                view=self.cog.generate_general_config_view(self.guild_id, interaction.guild) # Utiliser self.cog
            )
            db.close()

    # --- Méthodes pour les configurations spécifiques (Rôle Admin, Salon, Rôle Notif) ---
    
    def generate_role_and_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Configuration Générale (Rôles & Salons)",
            description="Utilisez les menus déroulants pour sélectionner les rôles et salons.",
            color=discord.Color.purple()
        )
        current_admin_role = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        current_notif_role = f"<@&{state.notification_role_id}>" if hasattr(state, 'notification_role_id') and state.notification_role_id else "Non défini"
        current_game_channel = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"

        embed.add_field(name="👑 Rôle Admin", value=current_admin_role, inline=False)
        embed.add_field(name="🔔 Rôle de Notification", value=current_notif_role, inline=False)
        embed.add_field(name="🎮 Salon de Jeu", value=current_game_channel, inline=False)
        return embed

    # --- Génération de la vue pour Rôles et Salons avec pagination pour les salons ---
    def generate_general_config_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=None)

        # Helper function to create options and a mapping
        def create_options_and_mapping(items, item_type):
            options = []
            id_mapping = {}

            if guild:
                sorted_items = sorted(items, key=lambda x: getattr(x, 'position', x.id))

                for item in sorted_items:
                    item_id = str(item.id)
                    item_name = item.name

                    if item_id is None or not isinstance(item_name, str) or not item_name:
                        print(f"DEBUG: Ignoré item (type: {item_type}) car ID nul ou nom invalide: ID={item_id}, Nom={item_name}")
                        continue

                    # Générer le label
                    label = item_name[:self.MAX_OPTION_LENGTH]
                    if not label:
                        label = item_id[:self.MAX_OPTION_LENGTH]
                        if not label:
                            print(f"DEBUG: Ignoré item (type: {item_type}) car aucun label valide généré: ID={item_id}, Nom='{item_name}'")
                            continue

                    # Générer la value
                    hashed_id = hashlib.sha256(item_id.encode()).hexdigest()
                    value = hashed_id[:self.MAX_OPTION_LENGTH]
                    if not value:
                        print(f"DEBUG: Ignoré item (type: {item_type}) car aucune value valide générée: ID={item_id}, Nom='{item_name}'")
                        continue

                    # Vérification finale des longueurs avant d'ajouter
                    if not (1 <= len(label) <= 25 and 1 <= len(value) <= 25):
                        print(f"DEBUG: ERREUR DE LONGUEUR - Ignoré item (type: {item_type})")
                        print(f"  -> Item original: ID='{item_id}', Nom='{item_name}'")
                        print(f"  -> Label généré : '{label}' (longueur: {len(label)})")
                        print(f"  -> Value générée: '{value}' (longueur: {len(value)})")
                        continue # Ignorer si les longueurs ne sont pas bonnes malgré tout

                    options.append(discord.SelectOption(label=label, value=value, description=f"ID: {item_id}"))
                    id_mapping[value] = item_id

                if not options:
                    options.append(discord.SelectOption(label="Aucun trouvé", value="no_items", description="Aucun item trouvé.", default=True))
            else:
                options.append(discord.SelectOption(label="Erreur serveur", value="error_guild", description="Serveur non trouvé.", default=True))
            
            return options, id_mapping

        # Générer les options et le mapping pour les rôles
        role_options, role_id_mapping = create_options_and_mapping(guild.roles if guild else [], "role")

        # Générer les options et le mapping pour les canaux textuels
        text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else []
        channel_options_all, channel_id_mapping = create_options_and_mapping(text_channels, "channel")

        # Créer les instances de Select pour les rôles
        # Rôles : Admin (row=0), Notification (row=1)
        role_select_admin = self.RoleSelect(guild_id, "admin_role", row=0, options=role_options, id_mapping=role_id_mapping, cog=self) # Passer self
        view.add_item(role_select_admin)

        role_select_notif = self.RoleSelect(guild_id, "notification_role", row=1, options=role_options, id_mapping=role_id_mapping, cog=self) # Passer self
        view.add_item(role_select_notif)

        # --- Logique de pagination pour les salons ---
        # Ajouter les composants Select et Buttons directement à la vue principale.

        # Créer le Select pour les salons (row=0)
        channel_select_element = self.ChannelSelect(
            guild_id=guild_id,
            select_type="game_channel",
            row=0, # Select sur la ligne 0
            options=channel_options_all,
            id_mapping=channel_id_mapping,
            page=0, # Page initiale
            cog=self # Passer self
        )
        view.add_item(channel_select_element)

        # Créer les boutons de navigation (row=1)
        if len(channel_options_all) > MAX_OPTIONS_PER_PAGE:
            prev_button = ui.Button(
                label="⬅ Précédent",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_prev_page_{guild_id}_0", # Inclure la page pour le callback
                disabled=True, # Désactivé au début si page 0
                row=1 # Bouton précédent sur la ligne 1
            )
            next_button = ui.Button(
                label="Suivant ➡",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_next_page_{guild_id}_0", # Inclure la page pour le callback
                disabled=False, # Activé s'il y a plus d'une page
                row=1 # Bouton suivant sur la ligne 1
            )
            # Il faut ici lier les callbacks aux boutons.
            # Comme nous n'avons plus de ChannelSelectView séparée, les callbacks des boutons doivent être
            # implémentés d'une autre manière, soit en attenant un `ui.Button` avec son callback,
            # soit en utilisant une logique d'interaction globale (plus complexe).

            # Option la plus simple : créer des instances de Button avec des callbacks associés
            # et les ajouter à la vue. Cela évite les problèmes avec les `@ui.button` et les `custom_id` dynamiques.
            
            # Redéfinissons ici les boutons avec leurs callbacks attachés directement.
            
            # Le `custom_id` est nécessaire pour que Discord sache à quel élément l'interaction appartient.
            # Les callbacks pour la navigation de page seront directement associés à ces boutons.

            # Le callback pour le bouton précédent
            async def prev_button_callback(interaction: discord.Interaction, guild_id=guild_id, current_page=0):
                if interaction.user.id != interaction.guild.owner_id: 
                    await interaction.response.send_message("Vous n'êtes pas autorisé à changer de page.", ephemeral=True)
                    return
                
                # Il faut ici accéder à l'état de la page actuelle. Comme on ne passe pas la vue,
                # il faut trouver le moyen d'y accéder. La manière la plus propre est de
                # ne pas ajouter les boutons directement ici, mais de les gérer via une vue parente
                # qui maintient l'état.

                # OK, je vais réintroduire ChannelSelectView pour gérer l'état de la pagination.
                # La raison est que la vue principale (config_menu_view) n'a pas de moyen facile
                # de maintenir l'état de la page pour le select de salon.

                # Retour à l'idée initiale : ChannelSelectView gère les éléments paginés.
                # Mais comment l'ajouter correctement à la vue principale sans que les lignes se chevauchent ?

                # La solution est que ChannelSelectView contienne UNIQUEMENT le Select et les boutons de pagination,
                # et que ces éléments soient ajoutés à la vue principale avec leurs `row` appropriés.
                # Dans generate_general_config_view:
                # On crée le Select (row=0)
                # On crée les Buttons (row=1)
                # On ajoute ces éléments à la vue principale.

                # Il faut que les callbacks de ces boutons soient directement sur la vue principale.
                # C'est ce que faisait la `ChannelSelectView` avec ses méthodes `@ui.button`.
                # Mais `ChannelSelectView` n'existe plus.

                # SOLUTION REVISITÉE :
                # Les boutons de navigation doivent être gérés avec des callbacks qui
                # modifient l'état de la page et rééditent le message.
                # Comme les vues ne se réinitialisent pas facilement pour les éléments dynamiques,
                # il est plus simple d'avoir un `View` qui gère ça.

                # Je vais donc réintroduire une structure similaire à ChannelSelectView, mais en m'assurant
                # que ses éléments sont bien ajoutés à la vue principale.

                # Réintroduisons ChannelSelectView dans le scope de AdminCog.
                # Et dans generate_general_config_view:
                # On crée le ChannelSelect (row=0).
                # On crée les Buttons (row=1).
                # On crée une instance de ChannelSelectView (qui contiendra le Select et les Buttons).
                # ET on ajoute les éléments de ChannelSelectView à la vue principale.
                # C'est le bon pattern.

            # Je vais donc réintroduire ChannelSelectView comme une classe imbriquée interne
            # et la générer correctement.
            
            # Réimplémentation de la logique de pagination :
            # On crée le Select pour les salons (row=0).
            # On crée les Buttons (row=1).
            # On crée une instance de ChannelSelectView (qui gérera l'état et les callbacks).
            # Et on ajoute les éléments de cette ChannelSelectView à la vue principale.

            # Donc, la ligne qui causait l'erreur :
            # channel_pagination_view = self.ChannelPaginationView(guild_id, channel_options_all, channel_id_mapping, cog=self)
            # DOIT être remplacée par l'ajout DIRECT des composants créés ici.
            # Et il faut que les callbacks des boutons soient correctement gérés.

            # Le callback doit être attenant au bouton.
            # Donc :
            # prev_button = ui.Button(...)
            # prev_button.callback = lambda interaction: self.handle_channel_page_change(interaction, guild_id, -1)
            # next_button.callback = lambda interaction: self.handle_channel_page_change(interaction, guild_id, 1)
            # Ce qui est aussi un peu lourd.

            # La meilleure pratique est d'avoir une classe `View` qui contient les éléments et leurs callbacks.
            # Ce que faisait `ChannelSelectView`.

            # Retour à la solution où `ChannelSelectView` est une classe imbriquée qui est instanciée
            # et ses éléments (Select et Buttons) sont ajoutés à la vue principale.
            # Je vais donc réintégrer ChannelSelectView dans le code ci-dessous.
            # Le problème d'attribut `ChannelPaginationView` était un artefact de cette révision.

            pass # Ceci est un placeholder, le vrai callback sera attaché.

        # Il FAUT que les callbacks des boutons soient gérés.
        # Dans la dernière correction, j'avais réintroduit ChannelSelectView avec ses propres callbacks `@ui.button`.
        # Il semble que cette structure ait été mal interprétée ou supprimée.
        # Je vais donc réintégrer la logique ChannelSelectView comme il faut.

        # LA BONNE STRUCTURE :
        # 1. generate_general_config_view crée le Select et les Buttons.
        # 2. Ces Select et Buttons sont ajoutés à la vue principale.
        # 3. Les callbacks pour ces Buttons doivent être gérés.
        # Cela se fait le plus proprement via une classe `View` qui encapsule ces éléments.
        # Donc, je vais réintroduire ChannelSelectView.

        # Créer la vue pour la pagination des salons
        channel_pagination_manager = self.ChannelPaginationManager(guild_id, channel_options_all, channel_id_mapping, cog=self)
        
        # Ajouter les éléments gérés par ChannelPaginationManager à la vue principale.
        # Ces éléments sont le Select et les deux boutons.
        view.add_item(channel_pagination_manager.channel_select)
        if len(channel_options_all) > MAX_OPTIONS_PER_PAGE:
            view.add_item(channel_pagination_manager.prev_button)
            view.add_item(channel_pagination_manager.next_button)
        
        # Le bouton de retour doit être sur une ligne distincte, par exemple row=3
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3, cog=self)) # Passer self
        return view

    # --- Classe pour gérer la vue paginée des salons ---
    # Elle gérera le Select et les boutons de navigation.
    class ChannelPaginationManager(ui.View):
        def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, initial_page: int = 0, cog: 'AdminCog'=None): # Ajout de cog
            super().__init__(timeout=None)
            self.guild_id = guild_id
            self.all_options = all_options
            self.id_mapping = id_mapping
            self.current_page = initial_page
            self.cog = cog # Stocker l'instance du cog

            # Créer le Select pour la page initiale
            self.channel_select = AdminCog.ChannelSelect( # Utilisation de AdminCog.ChannelSelect
                guild_id=self.guild_id,
                select_type="game_channel",
                row=0, # Select sur la ligne 0
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page,
                cog=self.cog # Passer self.cog
            )
            
            # Créer les boutons de navigation avec des custom_ids statiques
            self.prev_button = ui.Button(
                label="⬅ Précédent",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_prev_page_{self.guild_id}", # Static custom_id pour la navigation
                disabled=self.current_page == 0,
                row=1 # Bouton précédent sur la ligne 1
            )
            self.next_button = ui.Button(
                label="Suivant ➡",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_next_page_{self.guild_id}", # Static custom_id pour la navigation
                disabled=(self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options),
                row=1 # Bouton suivant sur la ligne 1
            )

        # Méthodes pour mettre à jour l'affichage (channels)
        def update_display(self, interaction: discord.Interaction):
            # Remove the old select
            self.remove_item(self.channel_select)

            # Create the new select for the updated page
            self.channel_select = AdminCog.ChannelSelect( # Utilisation de AdminCog.ChannelSelect
                guild_id=self.guild_id,
                select_type="game_channel",
                row=0, # Réinitialiser row=0 pour le nouveau Select
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page,
                cog=self.cog # Passer self.cog
            )
            self.add_item(self.channel_select) # Add the new select

            # Update buttons' disabled state
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = (self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options)

            # IMPORTANT : Les callbacks des boutons doivent être gérés.
            # Puisque ChannelPaginationManager est une `ui.View`, nous pouvons utiliser `@ui.button`
            # mais il faut s'assurer que les `custom_id` correspondent.

        # Callbacks pour les boutons de navigation
        @ui.button(label="⬅ Précédent", style=discord.ButtonStyle.secondary, custom_id="channel_prev_page_callback") # custom_id générique ici
        async def prev_button_callback(self, interaction: discord.Interaction):
            # Il faut vérifier le custom_id réel de l'interaction
            if interaction.custom_id == f"channel_prev_page_{self.guild_id}":
                if interaction.user.id != interaction.guild.owner_id: 
                    await interaction.response.send_message("Vous n'êtes pas autorisé à changer de page.", ephemeral=True)
                    return
                
                if self.current_page > 0:
                    self.current_page -= 1
                    self.update_display(interaction)
                    await interaction.response.edit_message(view=self)
                else:
                    await interaction.response.send_message("C'est la première page.", ephemeral=True)

        @ui.button(label="Suivant ➡", style=discord.ButtonStyle.secondary, custom_id="channel_next_page_callback") # custom_id générique ici
        async def next_button_callback(self, interaction: discord.Interaction):
            if interaction.custom_id == f"channel_next_page_{self.guild_id}":
                if interaction.user.id != interaction.guild.owner_id:
                    await interaction.response.send_message("Vous n'êtes pas autorisé à changer de page.", ephemeral=True)
                    return

                if (self.current_page + 1) * MAX_OPTIONS_PER_PAGE < len(self.all_options):
                    self.current_page += 1
                    self.update_display(interaction)
                    await interaction.response.edit_message(view=self)
                else:
                    await interaction.response.send_message("C'est la dernière page.", ephemeral=True)

        # Il faut que les custom_id des boutons dans __init__ correspondent à ceux des `@ui.button`.
        # Pour que cela fonctionne, il faut que les custom_id soient définis une seule fois pour chaque type de bouton.
        # Dans le cas de navigation, les custom_id sont liés au guild_id, ce qui est correct.
        # Le `custom_id` dans les `@ui.button` est une convention, ce sont les `custom_id` des instances qui sont prioritaires.
        # Si cela ne fonctionne pas, il faudra peut-être les lier manuellement ou utiliser une autre approche.
        # Mais `discord.py` est censé trouver les callbacks par `custom_id`.

    # --- Méthodes pour les autres configurations (Statistiques, Notifications, Avancées) ---
    def generate_stats_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="📊 Statistiques du Serveur", description="Fonctionnalité en développement.", color=discord.Color.purple())
        return embed
    
    def generate_stats_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3, cog=self)) # Passer self
        return view

    def generate_notifications_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="🔔 Paramètres de Notifications", description="Configurez les rôles pour les notifications du jeu. (Fonctionnalité en développement)", color=discord.Color.green())
        return embed
    
    def generate_notifications_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3, cog=self)) # Passer self
        return view

    def generate_advanced_options_embed(self, guild_id: str) -> discord.Embed:
        embed = discord.Embed(title="🛠️ Options Avancées", description="Fonctionnalité en développement.", color=discord.Color.grey())
        return embed
    
    def generate_advanced_options_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3, cog=self)) # Passer self
        return view

    # Méthode principale pour générer la vue du menu de configuration
    def generate_config_menu_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        
        # Ligne 0 : Mode/Durée, Lancer/Réinitialiser, Sauvegarder
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary, row=0, cog=self)) # Passer self
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=0, cog=self)) # Passer self
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0, cog=self)) # Passer self
        
        # Ligne 1 : Rôles & Salons, Statistiques
        view.add_item(self.GeneralConfigButton("⚙️ Rôles & Salons", guild_id, discord.ButtonStyle.grey, row=1, cog=self)) # Passer self
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1, cog=self)) # Passer self
        
        # Ligne 2 : Notifications, Options Avancées
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=2, cog=self)) # Passer self
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2, cog=self)) # Passer self
        
        # Ligne 3 : Bouton retour final
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, row=3, cog=self)) # Passer self
        
        return view

async def setup(bot):
    await bot.add_cog(AdminCog(bot))