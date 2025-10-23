# In netbox_run_anta_plugin/netbox_run_anta_plugin/navigation.py

from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(
    label='ANTA Operations',
    groups=(
        ('Testing', (
            PluginMenuItem(
                link='plugins:netbox_run_anta_plugin:anta_status',
                link_text='ANTA Test Trigger'
            ),
        )),
    ),
    icon_class='mdi mdi-robot'
)
