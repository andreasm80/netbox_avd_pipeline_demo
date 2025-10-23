"""Top-level package for NetBox Run Anta Plugin."""

__author__ = "Andreas M"
__email__ = "andreas.marqvardsen@gmail.com"
__version__ = "0.1.0"


from netbox.plugins import PluginConfig


class RunAntaConfig(PluginConfig):
    name = "netbox_run_anta_plugin"
    verbose_name = "NetBox Run Anta Plugin"
    description = "NetBox plugin for Run Anta."
    version = __version__
    author = __author__
    author_email = __email__
    base_url = "netbox_run_anta_plugin"
    required_settings = []  # settings.py handles this now
    default_settings = {}


config = RunAntaConfig
