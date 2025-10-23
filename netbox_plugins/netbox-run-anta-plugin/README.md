# NetBox Run Anta Plugin

NetBox plugin for Run Anta.


* Free software: Apache-2.0
* Documentation: https://andreasm80.github.io/netbox-run-anta-plugin/


## Features

The features the plugin provides should be listed here.

## Compatibility

| NetBox Version | Plugin Version |
|----------------|----------------|
|     4.0        |      0.1.0     |

## Installing

For adding to a NetBox Docker setup see
[the general instructions for using netbox-docker with plugins](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins).

While this is still in development and not yet on pypi you can install with pip:

```bash
pip install git+https://github.com/andreasm80/netbox-run-anta-plugin
```

or by adding to your `local_requirements.txt` or `plugin_requirements.txt` (netbox-docker):

```bash
git+https://github.com/andreasm80/netbox-run-anta-plugin
```

Enable the plugin in `/opt/netbox/netbox/netbox/configuration.py`,
 or if you use netbox-docker, your `/configuration/plugins.py` file :

```python
PLUGINS = [
    'netbox-run-anta-plugin'
]

PLUGINS_CONFIG = {
    "netbox-run-anta-plugin": {},
}
```

## Credits

Based on the NetBox plugin tutorial:

- [demo repository](https://github.com/netbox-community/netbox-plugin-demo)
- [tutorial](https://github.com/netbox-community/netbox-plugin-tutorial)

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [`netbox-community/cookiecutter-netbox-plugin`](https://github.com/netbox-community/cookiecutter-netbox-plugin) project template.
