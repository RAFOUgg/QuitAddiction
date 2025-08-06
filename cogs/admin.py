import discord
from discord.ext import commands
from discord import app_commands, ui
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile
import hashlib
import datetime
import math
from typing import List, Tuple, Dict, Optional

# Ensure this is defined and accessible
MAX_OPTIONS_PER_PAGE = 25

class AdminCog(commands.Cog):
    """Gestion des configurations du bot et du jeu pour le serveur."""
    def __init__(self, bot):
        self.bot = bot
        self.MAX_OPTION_LENGTH = 25 # For label/value length
        self.MIN_OPTION_LENGTH = 1 # For label/value length

    # --- Utility function to create options and mapping, handling truncation and hashing ---
    def create_options_and_mapping(self, items: list, item_type: str, guild: discord.Guild | None) -> Tuple[List[discord.SelectOption], Dict[str, str]]:
        options = []
        id_mapping = {}
        if not guild:
            return [discord.SelectOption(label="Erreur serveur", value="error_guild", default=True)], {}

        try:
            if item_type == "role":
                sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
            elif item_type == "channel":
                sorted_items = sorted(items, key=lambda x: (getattr(x, 'category_id', float('inf')), x.position))
            else:
                sorted_items = items
        except Exception as e:
            print(f"Error sorting {item_type}s: {e}")
            sorted_items = items

        for item in sorted_items:
            item_id = str(item.id)
            item_name = item.name
            if item_id is None or not isinstance(item_name, str) or not item_name: continue

            # Truncate label to Discord's max length
            label = item_name[:self.MAX_OPTION_LENGTH]
            if not label: label = item_id[:self.MAX_OPTION_LENGTH] # Fallback to ID if name is empty or too short
            if not label: continue

            # Create a stable, short value using a hash of the item ID
            # Hashing ensures uniqueness and avoids issues with names that are too long or contain special characters
            hashed_id = hashlib.sha256(item_id.encode()).hexdigest()
            value = hashed_id[:self.MAX_OPTION_LENGTH] # Take a slice of the hash
            if not value: continue

            # Basic validation for label and value lengths
            if not (self.MIN_OPTION_LENGTH <= len(label) <= self.MAX_OPTION_LENGTH and self.MIN_OPTION_LENGTH <= len(value) <= self.MAX_OPTION_LENGTH):
                continue

            options.append(discord.SelectOption(label=label, value=value, description=f"ID: {item_id}"))
            id_mapping[value] = item_id # Map the short value back to the full ID

        if not options:
            options.append(discord.SelectOption(label="Aucun élément trouvé", value="no_items", default=True))

        return options, id_mapping

    # --- Select Menu for Roles (with pagination support) ---
    class RoleSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, page: int = 0, cog: 'AdminCog'=None):
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping
            self.page = page
            self.cog = cog # Store cog instance

            # Filter options for the current page
            start_index = page * MAX_OPTIONS_PER_PAGE
            end_index = start_index + MAX_OPTIONS_PER_PAGE
            current_page_options = options[start_index:end_index]

            if not current_page_options:
                current_page_options.append(discord.SelectOption(label="Aucun rôle sur cette page", value="no_roles_on_page", default=True))

            placeholder = f"Sélectionnez le rôle pour {'l\'admin' if select_type == 'admin_role' else 'les notifications'}... (Page {page + 1}/{math.ceil(len(options)/MAX_OPTIONS_PER_PAGE) if options else 1})"
            placeholder = placeholder[:100] # Truncate placeholder if it's too long

            # Custom ID needs to be unique per page to be correctly identified by Discord
            super().__init__(placeholder=placeholder, options=current_page_options, custom_id=f"select_role_{select_type}_{guild_id}_page{page}", row=row)

        async def callback(self, interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Erreur: Impossible de trouver le serveur courant.", ephemeral=True)
                return

            if not self.values or self.values[0] in ["no_roles_on_page", "error_guild", "no_items"]:
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

                    # Re-generate the entire view with potentially updated page states for buttons/selects
                    await interaction.response.edit_message(
                        embed=self.cog.generate_role_and_channel_config_embed(state),
                        view=self.cog.generate_general_config_view(self.guild_id, interaction.guild) # This will re-create the whole view with correct pagination
                    )
                    await interaction.followup.send(f"Rôle pour {'l\'administration' if self.select_type == 'admin_role' else 'les notifications'} mis à jour.", ephemeral=True)
                except Exception as e:
                    db.rollback()
                    await interaction.response.send_message(f"Erreur lors de la sauvegarde : {e}", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur.", ephemeral=True)
            db.close()

    # --- Select Menu for Channels (with pagination support) ---
    class ChannelSelect(ui.Select):
        def __init__(self, guild_id: str, select_type: str, row: int, options: list[discord.SelectOption], id_mapping: dict, page: int = 0, cog: 'AdminCog'=None):
            self.guild_id = guild_id
            self.select_type = select_type
            self.id_mapping = id_mapping
            self.page = page
            self.cog = cog # Store cog instance

            # Filter options for the current page
            start_index = page * MAX_OPTIONS_PER_PAGE
            end_index = start_index + MAX_OPTIONS_PER_PAGE
            current_page_options = options[start_index:end_index]

            if not current_page_options:
                current_page_options.append(discord.SelectOption(label="Aucun salon sur cette page", value="no_channels_on_page", default=True))

            placeholder = f"Sélectionnez le salon pour le jeu... (Page {page + 1}/{math.ceil(len(options)/MAX_OPTIONS_PER_PAGE) if options else 1})"
            placeholder = placeholder[:100]

            super().__init__(placeholder=placeholder, options=current_page_options, custom_id=f"select_channel_{select_type}_{guild_id}_page{page}", row=row)

        async def callback(self, interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Erreur: Impossible de trouver le serveur courant.", ephemeral=True)
                return

            if not self.values or self.values[0] in ["no_channels_on_page", "error_guild", "no_items"]:
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

                    # Re-generate the entire view with potentially updated page states
                    await interaction.response.edit_message(
                        embed=self.cog.generate_role_and_channel_config_embed(state),
                        view=self.cog.generate_general_config_view(self.guild_id, interaction.guild) # This will re-create the whole view with correct pagination
                    )
                    await interaction.followup.send(f"Salon de jeu mis à jour.", ephemeral=True)
                except Exception as e:
                    db.rollback()
                    await interaction.response.send_message(f"Erreur lors de la sauvegarde : {e}", ephemeral=True)
            else:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur.", ephemeral=True)
            db.close()

    # --- View Manager for Pagination ---
    class PaginationManager(ui.View):
        def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, select_type: str, cog: 'AdminCog', initial_page: int = 0):
            super().__init__(timeout=180)
            self.guild_id = guild_id
            self.all_options = all_options
            self.id_mapping = id_mapping
            self.select_type = select_type # 'role' or 'channel'
            self.cog = cog
            self.current_page = initial_page

            self.total_pages = math.ceil(len(self.all_options) / MAX_OPTIONS_PER_PAGE) if self.all_options else 1

            # Create the initial SelectMenu for the current page
            if self.select_type == 'role':
                self.select_menu = AdminCog.RoleSelect(
                    guild_id=self.guild_id,
                    select_type=self.select_type, # This would be 'admin_role' or 'notification_role'
                    row=0, # Will be managed by add_component_to_view
                    options=self.all_options,
                    id_mapping=self.id_mapping,
                    page=self.current_page,
                    cog=self.cog
                )
            else: # select_type == 'channel'
                self.select_menu = AdminCog.ChannelSelect(
                    guild_id=self.guild_id,
                    select_type="game_channel", # For channel selects, it's always 'game_channel' in this context
                    row=0, # Will be managed by add_component_to_view
                    options=self.all_options,
                    id_mapping=self.id_mapping,
                    page=self.current_page,
                    cog=self.cog
                )

            # Create pagination buttons
            self.prev_button = ui.Button(
                label="⬅ Précédent",
                style=discord.ButtonStyle.secondary,
                custom_id=f"pagination_{self.select_type}_prev_{self.guild_id}",
                disabled=self.current_page == 0,
                row=1 # Put buttons on a new row
            )
            self.next_button = ui.Button(
                label="Suivant ➡",
                style=discord.ButtonStyle.secondary,
                custom_id=f"pagination_{self.select_type}_next_{self.guild_id}",
                disabled=self.current_page == self.total_pages - 1,
                row=1 # Put buttons on the same row
            )

            # Attach callbacks
            self.prev_button.callback = self.handle_page_change
            self.next_button.callback = self.handle_page_change

            # Add initial components to the view
            self.add_item(self.select_menu)
            if self.total_pages > 1: # Only add buttons if there's more than one page
                self.add_item(self.prev_button)
                self.add_item(self.next_button)

        async def handle_page_change(self, interaction: discord.Interaction):
            # Determine if it's a previous or next page click
            if interaction.data['custom_id'].endswith('_prev'):
                new_page = self.current_page - 1
            else: # next
                new_page = self.current_page + 1

            # Validate the new page number
            if not (0 <= new_page < self.total_pages):
                await interaction.response.send_message("C'est la première/dernière page.", ephemeral=True)
                return

            self.current_page = new_page

            # Update the select menu for the new page
            if self.select_type == 'role':
                self.select_menu = AdminCog.RoleSelect(
                    guild_id=self.guild_id,
                    select_type=self.select_type, # e.g., 'admin_role'
                    row=0, # Row managed by view.add_item
                    options=self.all_options,
                    id_mapping=self.id_mapping,
                    page=self.current_page,
                    cog=self.cog
                )
            else: # select_type == 'channel'
                self.select_menu = AdminCog.ChannelSelect(
                    guild_id=self.guild_id,
                    select_type="game_channel",
                    row=0, # Row managed by view.add_item
                    options=self.all_options,
                    id_mapping=self.id_mapping,
                    page=self.current_page,
                    cog=self.cog
                )

            # Update pagination buttons' disabled state
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = self.current_page == self.total_pages - 1

            # Remove old components and add new ones
            # Clear items from the view and re-add the updated ones
            self.clear_items()
            self.add_item(self.select_menu)
            if self.total_pages > 1:
                self.add_item(self.prev_button)
                self.add_item(self.next_button)

            # Respond by editing the original message with the updated view
            await interaction.response.edit_message(view=self)


    # --- Génération de la vue pour Rôles et Salons avec pagination ---
    def generate_general_config_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=180) # A view can hold multiple select menus and buttons

        all_roles = guild.roles if guild else []
        role_options, role_id_mapping = self.create_options_and_mapping(all_roles, "role", guild)

        text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else []
        channel_options, channel_id_mapping = self.create_options_and_mapping(text_channels, "channel", guild)

        # --- Role Select Menus (paginated) ---
        # We need a way to manage multiple paginated select menus if there are many roles.
        # A simpler approach for now is to have separate managers for roles and channels.

        # Manager for Admin Role selection
        admin_role_manager = self.PaginationManager(
            guild_id=guild_id,
            all_options=role_options,
            id_mapping=role_id_mapping,
            select_type="admin_role", # Use a specific type for admin role
            cog=self,
            initial_page=0 # Start on page 0
        )
        view.add_item(admin_role_manager.select_menu) # Add the select menu for admin role
        if admin_role_manager.total_pages > 1: # Add pagination buttons if needed
            view.add_item(admin_role_manager.prev_button)
            view.add_item(admin_role_manager.next_button)


        # Manager for Notification Role selection
        notification_role_manager = self.PaginationManager(
            guild_id=guild_id,
            all_options=role_options, # Using the same role options
            id_mapping=role_id_mapping,
            select_type="notification_role", # Use a specific type for notification role
            cog=self,
            initial_page=0
        )
        view.add_item(notification_role_manager.select_menu) # Add the select menu for notification role
        if notification_role_manager.total_pages > 1:
            view.add_item(notification_role_manager.prev_button)
            view.add_item(notification_role_manager.next_button)

        # --- Channel Select Menu (paginated) ---
        channel_manager = self.PaginationManager(
            guild_id=guild_id,
            all_options=channel_options,
            id_mapping=channel_id_mapping,
            select_type="channel", # Use a specific type for channel
            cog=self,
            initial_page=0
        )
        view.add_item(channel_manager.select_menu)
        if channel_manager.total_pages > 1:
            view.add_item(channel_manager.prev_button)
            view.add_item(channel_manager.next_button)

        # --- Back Button ---
        # The BackButton needs to be added to the view. Let's place it on a new row.
        back_button = self.BackButton(
            "⬅ Retour Paramètres Jeu",
            guild_id,
            discord.ButtonStyle.secondary,
            cog=self
        )
        # We need to manage the row for the back button as well.
        # Let's try adding it and see if it fits. If not, we might need another row.
        # A simple way is to ensure it gets added to the first available row.
        # We can repurpose the add_component_to_view helper logic if needed,
        # or just assign it to a row that likely has space (e.g., row=2 or row=3).
        # For now, let's assign it to row 2.
        back_button.row = 2 # Assign a row, this might need adjustment if all 5 slots on row 2 are taken by selects.
        view.add_item(back_button)


        # --- IMPORTANT NOTE ON ROW LIMITS ---
        # Each row can only have 5 components.
        # If you have 2 select menus + 2 pagination buttons for roles, and 1 select menu + 2 pagination buttons for channels,
        # that's already 8 items, which will require at least 2 rows.
        # The current structure likely places:
        # Row 0: Admin Role Select
        # Row 1: Notification Role Select, Channel Select
        # Row 2: Prev/Next for Admin Roles, Prev/Next for Notification Roles, Prev/Next for Channels
        # This is going to exceed 5 items per row quickly.

        # Let's rethink the layout to fit within the 5-component limit per row.
        # A common pattern is:
        # Row 0: First select menu (e.g., Admin Role)
        # Row 1: Second select menu (e.g., Notification Role)
        # Row 2: Third select menu (e.g., Channel)
        # Row 3: Pagination buttons for the first menu
        # Row 4: Pagination buttons for the second menu
        # Then another row for the third menu's pagination. This doesn't fit easily.

        # A better approach for multiple paginated selects:
        # Use a single view, but manage the placement and ensure no row exceeds 5 items.
        # We'll use a revised add_component_to_view helper.

        final_view = discord.ui.View(timeout=180)
        rows_item_count = [0] * 5 # Resetting the count for this final view assembly

        def add_component_to_final_view(component: discord.ui.Item):
            """
            Helper to add a component to the final view, managing rows up to 5 items per row.
            It attempts to place the component on the first available row.
            """
            # If component already has a row, try to use it if there's space
            if component.row is not None and component.row < 5 and rows_item_count[component.row] < 5:
                final_view.add_item(component)
                rows_item_count[component.row] += 1
                return True
            else:
                # Find the next available row
                for r in range(5):
                    if rows_item_count[r] < 5:
                        component.row = r # Assign the component to this row
                        final_view.add_item(component)
                        rows_item_count[r] += 1
                        return True
                print(f"WARNING: Could not add component {getattr(component, 'label', 'unknown')} to view - all rows full (5 items per row).")
                return False

        # Add the paginated selects and their buttons to the final view
        # Admin Role Select
        admin_role_manager = self.PaginationManager(
            guild_id=guild_id, all_options=role_options, id_mapping=role_id_mapping,
            select_type="admin_role", cog=self, initial_page=0
        )
        add_component_to_final_view(admin_role_manager.select_menu)
        if admin_role_manager.total_pages > 1:
            add_component_to_final_view(admin_role_manager.prev_button)
            add_component_to_final_view(admin_role_manager.next_button)

        # Notification Role Select
        notification_role_manager = self.PaginationManager(
            guild_id=guild_id, all_options=role_options, id_mapping=role_id_mapping,
            select_type="notification_role", cog=self, initial_page=0
        )
        add_component_to_final_view(notification_role_manager.select_menu)
        if notification_role_manager.total_pages > 1:
            add_component_to_final_view(notification_role_manager.prev_button)
            add_component_to_final_view(notification_role_manager.next_button)

        # Channel Select
        channel_manager = self.PaginationManager(
            guild_id=guild_id, all_options=channel_options, id_mapping=channel_id_mapping,
            select_type="channel", cog=self, initial_page=0
        )
        add_component_to_final_view(channel_manager.select_menu)
        if channel_manager.total_pages > 1:
            add_component_to_final_view(channel_manager.prev_button)
            add_component_to_final_view(channel_manager.next_button)

        # Back Button
        back_button = self.BackButton(
            "⬅ Retour Paramètres Jeu", guild_id, discord.ButtonStyle.secondary, cog=self
        )
        add_component_to_final_view(back_button) # Let the helper place it

        return final_view

    # --- BackButton class (make sure it's defined within AdminCog or accessible) ---
    class BackButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle, row: int = None, cog: 'AdminCog'=None): # row can be None if managed by helper
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            self.cog = cog

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()

            # Re-generate the main config menu and view
            await interaction.response.edit_message(
                embed=self.cog.generate_config_menu_embed(state),
                view=self.cog.generate_config_menu_view(self.guild_id, interaction.guild)
            )
            db.close()

    # --- RoleSelect and ChannelSelect classes need to be defined here or imported ---
    # (As defined above in the refactoring)

    # --- PaginationManager class needs to be defined here ---
    # (As defined above in the refactoring)


    # --- Method to generate the main config menu view ---
    def generate_config_menu_view(self, guild_id: str, guild: discord.Guild) -> discord.ui.View:
        view = discord.ui.View(timeout=None)

        # Using the add_component_to_view helper to manage rows
        rows_item_count = [0] * 5 # Reset row counts for this view

        def add_component_to_view(component: discord.ui.Item):
            if component.row is not None and component.row < 5 and rows_item_count[component.row] < 5:
                view.add_item(component)
                rows_item_count[component.row] += 1
            else:
                for r in range(5):
                    if rows_item_count[r] < 5:
                        component.row = r
                        view.add_item(component)
                        rows_item_count[r] += 1
                        return True
                print(f"WARNING: Could not add component {getattr(component, 'label', 'unknown')} to view - all rows full.")
                return False

        # Row 0: SetupGameModeButton, ConfigButton (Start/Reset)
        add_component_to_view(self.SetupGameModeButton("🕹️ Mode & Durée", guild_id, discord.ButtonStyle.primary, row=0, cog=self))
        add_component_to_view(self.ConfigButton("🎮 Lancer/Reinitialiser Partie", guild_id, discord.ButtonStyle.success, row=0, cog=self))
        add_component_to_view(self.ConfigButton("💾 Sauvegarder l'État", guild_id, discord.ButtonStyle.blurple, row=0, cog=self))

        # Row 1: GeneralConfigButton (Roles & Channels), ConfigButton (Stats)
        add_component_to_view(self.GeneralConfigButton("⚙️ Rôles & Salons", guild_id, discord.ButtonStyle.grey, row=1, cog=self))
        add_component_to_view(self.ConfigButton("📊 Voir Statistiques", guild_id, discord.ButtonStyle.gray, row=1, cog=self))

        # Row 2: ConfigButton (Notifications), ConfigButton (Advanced)
        add_component_to_view(self.ConfigButton("🔔 Notifications", guild_id, discord.ButtonStyle.green, row=2, cog=self))
        add_component_to_view(self.ConfigButton("🛠 Options Avancées", guild_id, discord.ButtonStyle.secondary, row=2, cog=self))

        # Row 3: BackButton
        add_component_to_view(self.BackButton("⬅ Retour", guild_id, discord.ButtonStyle.red, cog=self))

        return view


    # --- Helper method to generate embeds and views for different config sections ---
    # (You have generate_config_menu_embed, generate_setup_game_mode_embed, etc. - these are fine)

    # --- Methods for creating specific config interfaces ---
    def generate_role_and_channel_config_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Configuration Générale (Rôles & Salons)",
            description="Utilisez les menus déroulants pour sélectionner les rôles et salons. Naviguez avec les boutons Précédent/Suivant si la liste est longue.",
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
        view = discord.ui.View(timeout=180) # Set a timeout for the view

        # Keep track of how many components are on each row
        # We initialize this to zeros and it will be updated as we add items.
        # The index represents the row number (0-4).
        rows_item_count = [0] * 5

        def add_component_to_view(component: discord.ui.Item):
            """
            Helper function to add a component to the view.
            It tries to place the component on the first available row (0-4).
            If a row is full (5 items), it tries the next row.
            """
            # Check if component already has a row assigned and if that row has space
            if component.row is not None and component.row < 5 and rows_item_count[component.row] < 5:
                view.add_item(component)
                rows_item_count[component.row] += 1
                return True
            else:
                # If no row assigned, or current row is full, find the next available row
                for r in range(5): # Iterate through rows 0 to 4
                    if rows_item_count[r] < 5:
                        component.row = r # Assign the component to this row
                        view.add_item(component)
                        rows_item_count[r] += 1
                        return True
                print(f"WARNING: Could not add component {getattr(component, 'label', 'unknown')} to view - all rows are full (5 components per row).")
                return False

        # --- Creation des options et mapping ---
        def create_options_and_mapping(items, item_type):
            options = []
            id_mapping = {}
            if guild:
                try:
                    if item_type == "role":
                        sorted_items = sorted(items, key=lambda x: x.position, reverse=True)
                    elif item_type == "channel":
                        sorted_items = sorted(items, key=lambda x: (getattr(x, 'category_id', float('inf')), x.position))
                    else:
                        sorted_items = items
                except Exception as e:
                    print(f"Error sorting {item_type}s: {e}")
                    sorted_items = items

                for item in sorted_items:
                    item_id = str(item.id)
                    item_name = item.name
                    if item_id is None or not isinstance(item_name, str) or not item_name: continue
                    label = item_name[:self.MAX_OPTION_LENGTH]
                    if not label: label = item_id[:self.MAX_OPTION_LENGTH]
                    if not label: continue
                    hashed_id = hashlib.sha256(item_id.encode()).hexdigest()
                    value = hashed_id[:self.MAX_OPTION_LENGTH]
                    if not value: continue
                    if not (self.MIN_OPTION_LENGTH <= len(label) <= self.MAX_OPTION_LENGTH and self.MIN_OPTION_LENGTH <= len(value) <= self.MAX_OPTION_LENGTH): continue
                    options.append(discord.SelectOption(label=label, value=value, description=f"ID: {item_id}"))
                    id_mapping[value] = item_id
                if not options: options.append(discord.SelectOption(label="Aucun trouvé", value="no_items", default=True))
            else:
                options.append(discord.SelectOption(label="Erreur serveur", value="error_guild", default=True))
            return options, id_mapping

        all_roles = guild.roles if guild else []
        role_options, role_id_mapping = create_options_and_mapping(all_roles, "role")

        text_channels = [ch for ch in guild.channels if isinstance(ch, discord.TextChannel)] if guild else []
        all_channel_options, channel_id_mapping = create_options_and_mapping(text_channels, "channel")

        # --- Création des composants ---

        # Select pour le Rôle Admin
        # We initialize with row=0, but the helper will assign the final row.
        role_select_admin = self.RoleSelect(
            guild_id=guild_id,
            select_type="admin_role",
            row=0, # Initial row value, will be potentially updated by add_component_to_view
            options=role_options[:self.MAX_OPTION_LENGTH],
            id_mapping=role_id_mapping,
            cog=self
        )
        add_component_to_view(role_select_admin)

        # Select pour le Rôle de Notification
        role_select_notif = self.RoleSelect(
            guild_id=guild_id,
            select_type="notification_role",
            row=0, # Initial row value
            options=role_options[:self.MAX_OPTION_LENGTH],
            id_mapping=role_id_mapping,
            cog=self
        )
        add_component_to_view(role_select_notif)

        # --- Logique de pagination pour les salons ---
        channel_pagination_manager = self.ChannelPaginationManager(
            guild_id=guild_id,
            all_options=all_channel_options,
            id_mapping=channel_id_mapping,
            cog=self
        )

        # Add the channel select menu
        add_component_to_view(channel_pagination_manager.channel_select)

        # Add pagination buttons if needed
        if len(all_channel_options) > MAX_OPTIONS_PER_PAGE:
            add_component_to_view(channel_pagination_manager.prev_button)
            add_component_to_view(channel_pagination_manager.next_button)

        # Bouton de retour
        back_button = self.BackButton(
            "⬅ Retour Paramètres Jeu",
            guild_id,
            discord.ButtonStyle.secondary,
            cog=self
            # row will be assigned by add_component_to_view
        )
        add_component_to_view(back_button)

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
    class ChannelPaginationManager(ui.View):
        def __init__(self, guild_id: str, all_options: list[discord.SelectOption], id_mapping: dict, initial_page: int = 0, cog: 'AdminCog'=None):
            super().__init__(timeout=180) # Définir un timeout pour la vue
            self.guild_id = guild_id
            self.all_options = all_options
            self.id_mapping = id_mapping
            self.current_page = initial_page
            self.cog = cog # Stocker l'instance du cog

            # Créer le SelectMenu pour la page initiale.
            # Le row sera géré lorsque ce SelectMenu est ajouté à la vue principale.
            self.channel_select = AdminCog.ChannelSelect( # Utilisation de AdminCog.ChannelSelect
                guild_id=self.guild_id,
                select_type="game_channel",
                row=0, # Ce row sera écrasé par la vue principale qui l'ajoute
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page,
                cog=self.cog # Passer self.cog
            )
            
            # Créer les boutons de navigation. Les custom_ids sont statiques pour être trouvés par les listeners.
            self.prev_button = ui.Button(
                label="⬅ Précédent",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_prev_page_{self.guild_id}", # Static custom_id pour la navigation
                disabled=self.current_page == 0, # Désactiver si c'est la première page
                row=1 # Les boutons seront placés sur la ligne 1
            )
            self.next_button = ui.Button(
                label="Suivant ➡",
                style=discord.ButtonStyle.secondary,
                custom_id=f"channel_next_page_{self.guild_id}", # Static custom_id pour la navigation
                disabled=(self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options), # Désactiver si c'est la dernière page
                row=1 # Les boutons seront placés sur la ligne 1
            )
            
            # Attacher manuellement les callbacks aux boutons. Ceci est une alternative à l'utilisation de @ui.button
            # pour les vues qui gèrent elles-mêmes la logique de mise à jour.
            self.prev_button.callback = self.handle_prev_page
            self.next_button.callback = self.handle_next_page

        # Méthode pour mettre à jour les composants de la vue (Select et Boutons)
        def update_components(self, interaction: discord.Interaction):
            # Pour mettre à jour la vue, nous devons la modifier.
            # On retire l'ancien SelectMenu et on ajoute le nouveau.
            self.remove_item(self.channel_select) # Retirer l'ancien Select

            # Créer le nouveau SelectMenu pour la page mise à jour.
            self.channel_select = AdminCog.ChannelSelect( # Utilisation de AdminCog.ChannelSelect
                guild_id=self.guild_id,
                select_type="game_channel",
                row=0, # Le row est important car le SelectMenu est ajouté dans la vue principale.
                       # On le remet à 0 ici pour qu'il s'insère correctement.
                options=self.all_options,
                id_mapping=self.id_mapping,
                page=self.current_page,
                cog=self.cog # Passer self.cog
            )
            self.add_item(self.channel_select) # Ajouter le nouveau Select

            # Mettre à jour l'état désactivé des boutons de pagination.
            self.prev_button.disabled = self.current_page == 0
            self.next_button.disabled = (self.current_page + 1) * MAX_OPTIONS_PER_PAGE >= len(self.all_options)

        # Callback pour le bouton "Précédent"
        async def handle_prev_page(self, interaction: discord.Interaction):
            # On vérifie si l'utilisateur qui clique est bien celui qui a ouvert la config.
            # Ou, si vous voulez une sécurité plus stricte, vérifiez s'il est admin.
            # Pour l'instant, on suppose que tout utilisateur interagissant avec la vue peut naviguer.
            # Si vous voulez restreindre, ajoutez une vérification ici. Par exemple:
            # if interaction.user.id != self.interaction_user_id: # Nécessite de stocker l'ID de l'utilisateur initial
            #     await interaction.response.send_message("Vous n'êtes pas autorisé à naviguer.", ephemeral=True)
            #     return

            if self.current_page > 0:
                self.current_page -= 1
                self.update_components(interaction) # Mettre à jour les composants (Select et boutons)
                # Éditer le message avec la vue mise à jour.
                await interaction.response.edit_message(view=self)
            else:
                await interaction.response.send_message("C'est la première page.", ephemeral=True)

        # Callback pour le bouton "Suivant"
        async def handle_next_page(self, interaction: discord.Interaction):
            # Similaire à handle_prev_page pour les vérifications d'utilisateur.
            if (self.current_page + 1) * MAX_OPTIONS_PER_PAGE < len(self.all_options):
                self.current_page += 1
                self.update_components(interaction) # Mettre à jour les composants (Select et boutons)
                # Éditer le message avec la vue mise à jour.
                await interaction.response.edit_message(view=self)
            else:
                await interaction.response.send_message("C'est la dernière page.", ephemeral=True)

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