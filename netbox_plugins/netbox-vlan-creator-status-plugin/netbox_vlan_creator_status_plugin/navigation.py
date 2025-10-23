# In navigation.py

from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton
from netbox.choices import ButtonColorChoices

creator_menu_item = PluginMenuItem(
    link='plugins:netbox_vlan_creator_status_plugin:vlan_creator_add',
    link_text='VLAN Creator',
    buttons=(
        PluginMenuButton(
            link='plugins:netbox_vlan_creator_status_plugin:vlan_creator_add',
            title='Add',
            icon_class='mdi mdi-plus-thick',
            color=ButtonColorChoices.GREEN
        ),
    )
)


deleter_menu_item = PluginMenuItem(
    link='plugins:netbox_vlan_creator_status_plugin:vlan_deleter_delete',
    link_text='VLAN Deleter',
    buttons=(
         PluginMenuButton(
            link='plugins:netbox_vlan_creator_status_plugin:vlan_deleter_delete',
            title='Delete VLAN',
            icon_class='mdi mdi-delete',
            color=ButtonColorChoices.RED
        ),
    )
)

menu = PluginMenu(
    label='VLAN Creator Status Plugin',
    groups=(
        ('VLAN Tools', (creator_menu_item, deleter_menu_item)),
    ),
    icon_class='mdi mdi-lan'
)
