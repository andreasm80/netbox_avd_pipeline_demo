# Enable installed plugins. Add the name of each plugin to the list.
PLUGINS = [
    'netbox_run_anta_plugin',
    'netbox_vlan_creator_status_plugin',
    'netbox_sync_manager_plugin'
]

PLUGINS_CONFIG = {
    'netbox_vlan_creator_status_plugin': {
        'WEBHOOK_URL': 'URL',
        'WEBHOOK_SECRET': 'SECRET',
    },
    'netbox_sync_manager_plugin': {
        'WEBHOOK_URL': 'URL',
        'WEBHOOK_SECRET': 'SECRET',
    },
    'netbox_run_anta_plugin': {
        'webhook_url': 'URL',
        'webhook_secret': 'SECRET',
        'anta_status_url': 'URL/status',
        'anta_report_url': 'URL/latest-report'
    }
}
