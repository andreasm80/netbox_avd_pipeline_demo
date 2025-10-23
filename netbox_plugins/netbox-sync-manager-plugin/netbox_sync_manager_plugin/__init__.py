"""Top-level package for NetBox Sync Manager Plugin."""

__author__ = "Andreas M"
__email__ = "andreas.marqvardsen@gmail.com"
__version__ = "0.1.1"


from netbox.plugins import PluginConfig


class SyncManagerConfig(PluginConfig):
    name = "netbox_sync_manager_plugin"
    verbose_name = "NetBox Sync Manager Plugin"
    description = "NetBox plugin for Sync Manager."
    version = __version__
    author = __author__
    author_email = __email__
    base_url = "netbox_sync_manager_plugin"
    required_settings = ['WEBHOOK_URL', 'WEBHOOK_SECRET']
    default_settings = {}


config = SyncManagerConfig
