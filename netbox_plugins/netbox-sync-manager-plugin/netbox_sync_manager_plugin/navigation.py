# In netbox_sync_manager_plugin/navigation.py

from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton
from netbox.choices import ButtonColorChoices

# Define the menu item for the sync manager view
avd_sync_manager_item = PluginMenuItem(
    link='plugins:netbox_sync_manager_plugin:sync_view',
    link_text='AVD Sync Manager'
)

# Create the top-level menu for the plugin
menu = PluginMenu(
    label='Netbox Sync Manager',
    groups=(
        ('Sync Management', (avd_sync_manager_item,)),
    ),
    icon_class='mdi mdi-sync'
)
