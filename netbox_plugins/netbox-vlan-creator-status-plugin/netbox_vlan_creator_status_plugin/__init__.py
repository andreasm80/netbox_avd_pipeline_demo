# In __init__.py (NetBox v4.x Compatible)
from netbox.plugins import PluginConfig

__author__ = "Andreas M"
__email__ = "andreas.marqvardsen@gmail.com"
__version__ = "0.1.0"


class VlanCreatorStatusConfig(PluginConfig):
    name = 'netbox_vlan_creator_status_plugin'
    verbose_name = 'VLAN Creator (with Status)'
    description = 'Creates a VLAN, prefix, anycast IPs, and interfaces.'
    version = __version__
    author = __author__
    author_email = __email__
    base_url = 'vlan-creator-status'
    required_settings = []
    default_settings = {}

config = VlanCreatorStatusConfig
