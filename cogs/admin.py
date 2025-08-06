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
MAX_OPTIONS_PER_PAGE = 25 # Discord limite à 25 options par SelectMenu
MAX_COMPONENTS_PER_ROW = 5
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
    
    def create_options_and_mapping(self, items: list, item_type: str, guild: discord.Guild | None) -> Tuple[List[discord.SelectOption], Dict[str, str]]:
        """
        Crée des options hiérarchisées et lisibles pour les SelectMenus (rôles ou salons).
        - Ajoute des icônes (📁 pour catégories, # pour salons, 🔹 pour rôles)
        - Ignore les éléments non pertinents (comme @everyone pour les rôles)
        - Fournit un mapping ID haché -> ID réel
        """
        options = []
        id_mapping = {}

        if not guild:
            return [discord.SelectOption(label="Erreur serveur", value="error_guild", default=True)], {}

        try:
            # --- Trier les items ---
            if item_type == "role":
                # Les rôles triés du plus élevé au plus bas
                sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
            elif item_type == "channel":
                # Trier par catégorie puis par position
                sorted_items = sorted(items, key=lambda x: (getattr(x, 'category_id', float('inf')), x.position))
            else:
                sorted_items = items
        except Exception as e:
            print(f"Error sorting {item_type}s: {e}")
            sorted_items = items

        # --- Construire les options ---
        for item in sorted_items:
            item_id = str(item.id)
            item_name = item.name if hasattr(item, 'name') else None

            if not item_id or not item_name:
                continue

            # --- Filtrage pour éviter le spam ---
            if item_type == "role":
                # Ignore @everyone
                if item.is_default():
                    continue
                label = f"🔹 {item_name}"
            elif item_type == "channel":
                # Ignore les salons vocaux, threads ou catégories directes
                if isinstance(item, discord.CategoryChannel):
                    continue
                if not isinstance(item, discord.TextChannel):
                    continue

                # Ajout hiérarchique : Catégorie | #Nom
                category_name = item.category.name if item.category else "Sans catégorie"
                label = f"📁 {category_name} | #{item_name}"
            else:
                label = item_name

            # Tronquer à 25 caractères (limite Discord)
            label = label[:25]

            # --- Hachage pour value ---
            hashed_id = hashlib.sha256(item_id.encode()).hexdigest()[:25]

            # --- Ajouter à la liste ---
            options.append(discord.SelectOption(
                label=label,
                value=hashed_id,
                description=f"ID: {item_id}"  # affiché en petit sous le label
            ))
            id_mapping[hashed_id] = item_id

        if not options:
            options.append(discord.SelectOption(label="Aucun élément trouvé", value="no_items", default=True))

        return options, id_mapping
    
    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
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
            selected_mode = self.values[0] # Assurez-vous que c'est bien self.values[0]
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
            selected_duration_key = self.values[0] # Assurez-vous que c'est bien self.values[0]
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
                # Si vous souhaitez que "Sauvegarder l'État" fasse quelque chose de plus,
                # implémentez la logique ici. Actuellement, il ne fait que rafraîchir la vue.
                await interaction.response.edit_message(
                    embed=self.cog.generate_config_menu_embed(state), # Utiliser self.cog
                    view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild) # Utiliser self.cog
                )
                await interaction.followup.send("L'état actuel a été sauvegardé.", ephemeral=True) # Message informatif

            elif self.label == "📊 Voir Statistiques":
                await interaction.response.edit_message(
                    embed=self.cog.generate_stats_embed(self.guild_id), # Utiliser self.cog
                    view=self.cog.generate_stats_view(self.guild_id) # Utiliser self.cog
                )
                await interaction.followup.send("Accès aux statistiques...", ephemeral=True) # Message informatif

            elif self.label == "🔔 Notifications":
                await interaction.response.edit_message(
                    embed=self.cog.generate_notifications_embed(self.guild_id), # Utiliser self.cog
                    view=self.cog.generate_notifications_view(self.guild_id) # Utiliser self.cog
                )
                await interaction.followup.send("Accès à la configuration des notifications...", ephemeral=True) # Message informatif

            elif self.label == "🛠️ Options Avancées":
                await interaction.response.edit_message(
                    embed=self.cog.generate_advanced_options_embed(self.guild_id), # Utiliser self.cog
                    view=self.cog.generate_advanced_options_view(self.guild_id) # Utiliser self.cog
                )
                await interaction.followup.send("Accès aux options avancées...", ephemeral=True) # Message informatif

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

    class PaginatedSelect(discord.ui.Select):
    def __init__(self, guild_id: str, select_type: str, options: list[discord.SelectOption], id_mapping: dict, page: int, cog: 'AdminCog'):
        self.guild_id = guild_id
        self.select_type = select_type
        self.id_mapping = id_mapping
        self.page = page
        self.cog = cog

        self.items_per_page = 24  # 24 vrais éléments + 1 pour navigation
        self.total_pages = max(1, math.ceil(len(options) / self.items_per_page))
        self.all_options = options

        # Construire les options de la page courante
        start = page * self.items_per_page
        end = start + self.items_per_page
        page_options = options[start:end]

        # Ajouter la dernière option de navigation si nécessaire
        if self.total_pages > 1:
            if page < self.total_pages - 1:
                page_options.append(discord.SelectOption(
                    label=f"… Suite (Page {page+2}/{self.total_pages})",
                    value="__next_page__"
                ))
            else:
                page_options.append(discord.SelectOption(
                    label=f"↩ Retour à la première page (1/{self.total_pages})",
                    value="__first_page__"
                ))

        placeholder = f"Sélectionnez {'un rôle' if 'role' in select_type else 'un salon'} (Page {page+1}/{self.total_pages})"
        super().__init__(placeholder=placeholder, options=page_options, custom_id=f"paginated_{select_type}_{guild_id}_p{page}", row=0)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]

        # --- Gestion de la pagination ---
        if selected in ["__next_page__", "__first_page__"]:
            self.page = self.page + 1 if selected == "__next_page__" else 0

            # Créer un nouveau Select pour la page suivante
            new_select = PaginatedSelect(
                guild_id=self.guild_id,
                select_type=self.select_type,
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.page,
                cog=self.cog
            )

            new_view = discord.ui.View(timeout=180)
            new_view.add_item(new_select)

            # Ajouter le bouton retour
            back_button = self.cog.BackButton(
                "⬅ Retour Paramètres Jeu", self.guild_id, discord.ButtonStyle.secondary, row=1, cog=self.cog
            )
            new_view.add_item(back_button)

            await interaction.response.edit_message(view=new_view)
            return

        # --- Sélection réelle ---
        selected_item_id = self.id_mapping.get(selected)
        if not selected_item_id:
            await interaction.response.send_message("Erreur: élément introuvable.", ephemeral=True)
            return

        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()
        if state:
            if self.select_type == "admin_role":
                state.admin_role_id = selected_item_id
            elif self.select_type == "notification_role":
                state.notification_role_id = selected_item_id
            elif self.select_type == "channel":
                state.game_channel_id = selected_item_id
            db.commit()

        await interaction.response.send_message("✅ Sélection mise à jour.", ephemeral=True)
        db.close()

    # --- Génération de la vue pour Rôles et Salons avec pagination pour les salons ---
    def generate_general_config_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
    """
    Vue de configuration générale avec pagination intégrée dans le menu déroulant.
    """
    view = discord.ui.View(timeout=180)

    # --- Préparer les options ---
    all_roles = guild.roles if guild else []
    role_options, role_id_mapping = self.create_options_and_mapping(all_roles, "role", guild)

    text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else []
    channel_options, channel_id_mapping = self.create_options_and_mapping(text_channels, "channel", guild)

    # --- Ajouter les SelectMenus paginés ---
    admin_role_select = PaginatedSelect(guild_id, "admin_role", role_options, role_id_mapping, page=0, cog=self)
    notification_role_select = PaginatedSelect(guild_id, "notification_role", role_options, role_id_mapping, page=0, cog=self)
    channel_select = PaginatedSelect(guild_id, "channel", channel_options, channel_id_mapping, page=0, cog=self)

    admin_role_select.row = 0
    notification_role_select.row = 1
    channel_select.row = 2

    view.add_item(admin_role_select)
    view.add_item(notification_role_select)
    view.add_item(channel_select)

    # --- Bouton retour ---
    back_button = self.BackButton(
        "⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, row=3, cog=self
    )
    view.add_item(back_button)

    return view

    # --- Classe de Menu pour la sélection des Rôles ---
    class RoleSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, cog: 'AdminCog'): # Ajout de cog
            placeholder = f"Sélectionnez le rôle pour {'l\'admin' if select_type == 'admin_role' else 'les notifications'}..."
            placeholder = placeholder[:100] # Assurer que le placeholder ne dépasse pas 100 caractères
            
            # Il faut s'assurer que le nombre d'options ne dépasse pas 25.
            # Si c'est le cas, on doit soit tronquer, soit implémenter une pagination.
            # Ici, on suppose qu'il y a moins de 25 rôles.
            
            super().__init__(placeholder=placeholder, options=options[:MAX_OPTIONS_PER_PAGE], custom_id=f"select_role_{select_type}_{guild_id}", row=row)
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping 
            self.cog = cog # Stocker l'instance du cog

        async def callback(self, interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Erreur: Impossible de trouver le serveur courant pour cette action.", ephemeral=True)
                return

            if not self.values or self.values[0] in ["no_items", "error_guild"]:
                await interaction.response.send_message("Veuillez sélectionner un rôle valide.", ephemeral=True)
                return

            selected_short_id = self.values[0]
            selected_role_id = self.id_mapping.get(selected_short_id)

            if not selected_role_id:
                await interaction.response.send_message("Erreur: Impossible de récupérer l'ID du rôle.", ephemeral=True)
                return

            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                if self.select_type == "admin_role":
                    state.admin_role_id = selected_role_id
                elif self.select_type == "notification_role":
                    state.notification_role_id = selected_role_id
                
                try:
                    db.commit()
                    db.refresh(state) 

                    # Rafraîchir la vue complète pour refléter le changement
                    await interaction.response.edit_message(
                        embed=self.cog.generate_role_and_channel_config_embed(state), # Utiliser self.cog
                        view=self.cog.generate_general_config_view(self.guild_id, interaction.guild) # Utiliser self.cog
                    )
                    await interaction.followup.send(f"Rôle pour {'l\'administration' if self.select_type == 'admin_role' else 'les notifications'} mis à jour.", ephemeral=True)
                except Exception as e:
                    db.rollback()
                    await interaction.response.send_message(f"Erreur lors de la sauvegarde : {e}", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur pour sauvegarder la configuration.", ephemeral=True)
            
            db.close()

    # --- Classe pour la sélection des Salons avec Pagination ---
    class ChannelSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, page: int = 0, cog: 'AdminCog'=None):
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping
            self.page = page
            self.cog = cog # Stocker l'instance du cog

            # Filtrer les options pour la page actuelle
            start_index = page * MAX_OPTIONS_PER_PAGE
            end_index = start_index + MAX_OPTIONS_PER_PAGE
            current_page_options = options[start_index:end_index]

            if not current_page_options:
                current_page_options.append(discord.SelectOption(label="Aucun salon sur cette page", value="no_channels", default=True))

            placeholder = f"Sélectionnez le salon pour le jeu (Page {page + 1})..."
            placeholder = placeholder[:100]
            # Le custom_id doit inclure la page pour être unique par page,
            # car chaque page aura son propre SelectMenu.
            super().__init__(placeholder=placeholder, options=current_page_options, custom_id=f"select_channel_{select_type}_{guild_id}_page{page}", row=row)

        async def callback(self, interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Erreur: Impossible de trouver le serveur courant pour cette action.", ephemeral=True)
                return

            if not self.values or self.values[0] in ["no_channels", "error_guild", "no_items"]:
                await interaction.response.send_message("Veuillez sélectionner un salon valide.", ephemeral=True)
                return

            selected_short_id = self.values[0]
            selected_channel_id = self.id_mapping.get(selected_short_id)

            if not selected_channel_id:
                await interaction.response.send_message("Erreur: Impossible de récupérer l'ID du salon.", ephemeral=True)
                return

            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=self.guild_id).first()

            if state:
                if self.select_type == "game_channel":
                    state.game_channel_id = selected_channel_id
                
                try:
                    db.commit()
                    db.refresh(state)

                    # Rafraîchir la vue entière pour que le changement de page soit bien géré
                    # dans le cas où l'utilisateur change de page et sélectionne un salon.
                    # On utilise le cog pour générer la vue complète.
                    await interaction.response.edit_message(
                        embed=self.cog.generate_role_and_channel_config_embed(state), # Utiliser self.cog
                        view=self.cog.generate_general_config_view(self.guild_id, interaction.guild) # Utiliser self.cog
                    )
                    await interaction.followup.send(f"Salon de jeu mis à jour.", ephemeral=True)
                except Exception as e:
                    db.rollback()
                    await interaction.response.send_message(f"Erreur lors de la sauvegarde : {e}", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur pour sauvegarder la configuration.", ephemeral=True)
            
            db.close()

    # --- Classe pour gérer la vue paginée des salons ---
    class PaginatedViewManager(ui.View):
    def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, select_type: str, initial_page: int = 0, cog: 'AdminCog'=None):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.all_options = all_options
        self.id_mapping = id_mapping
        self.select_type = select_type
        self.current_page = initial_page
        self.cog = cog

        self.total_pages = max(1, math.ceil(len(self.all_options) / MAX_OPTIONS_PER_PAGE))

        # Création du menu
        self.selection_menu = self.create_select()
        self.add_item(self.selection_menu)

        # Créer la pagination uniquement si plus d'une page
        if self.total_pages > 1:
            self.prev_button = ui.Button(label="◀", style=discord.ButtonStyle.secondary)
            self.page_button = ui.Button(label=f"{self.current_page+1}/{self.total_pages}", style=discord.ButtonStyle.gray, disabled=True)
            self.next_button = ui.Button(label="▶", style=discord.ButtonStyle.secondary)

            self.prev_button.callback = self.prev_page
            self.next_button.callback = self.next_page

            self.add_item(self.prev_button)
            self.add_item(self.page_button)
            self.add_item(self.next_button)

    def create_select(self):
        start_index = self.current_page * MAX_OPTIONS_PER_PAGE
        end_index = start_index + MAX_OPTIONS_PER_PAGE
        current_page_options = self.all_options[start_index:end_index]

        if not current_page_options:
            current_page_options = [discord.SelectOption(label="Aucun élément", value="no_items", default=True)]

        placeholder = f"Sélectionnez {('un rôle' if 'role' in self.select_type else 'un salon')} (Page {self.current_page+1}/{self.total_pages})"
        return (AdminCog.RoleSelect if 'role' in self.select_type else AdminCog.ChannelSelect)(
            guild_id=self.guild_id,
            select_type=self.select_type,
            row=0,
            options=current_page_options,
            id_mapping=self.id_mapping,
            cog=self.cog
        )

    async def prev_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_page(interaction)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.update_page(interaction)

    async def update_page(self, interaction: discord.Interaction):
        # Rebuild menu
        self.remove_item(self.selection_menu)
        self.selection_menu = self.create_select()
        self.add_item(self.selection_menu)

        # Update page button
        if self.total_pages > 1:
            self.page_button.label = f"{self.current_page+1}/{self.total_pages}"
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = self.current_page >= self.total_pages-1

        await interaction.response.edit_message(view=self)


    # --- Méthodes pour les autres configurations (Statistiques, Notifications, Avancées) ---
    # ... (reste des méthodes : generate_stats_embed, generate_stats_view, etc.) ...
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
        view.add_item(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary, row=0, cog=self)) 
        view.add_item(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=0, cog=self)) 
        view.add_item(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0, cog=self)) 
        
        # Ligne 1 : Rôles & Salons, Statistiques
        view.add_item(self.GeneralConfigButton("⚙️ Rôles & Salons", guild_id, discord.ButtonStyle.grey, row=1, cog=self)) 
        view.add_item(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1, cog=self)) 
        
        # Ligne 2 : Notifications, Options Avancées
        view.add_item(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=2, cog=self)) 
        view.add_item(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2, cog=self)) 
        
        # Ligne 3 : Bouton retour final
        view.add_item(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, row=3, cog=self)) 
        
        return view

async def setup(bot):
    await bot.add_cog(AdminCog(bot))