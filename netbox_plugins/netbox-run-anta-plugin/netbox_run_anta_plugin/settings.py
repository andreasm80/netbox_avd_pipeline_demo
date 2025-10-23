# netbox_cvaas_status_plugin/settings.py
from django.core.exceptions import ImproperlyConfigured

# This is a dictionary of settings that are required for the plugin to work.
required_settings = {
    'webhook_url': 'URL/webhook',
    'webhook_secret': 'SECRET',
    'anta_status_url': 'URL/status',
    'anta_report_url': 'The URL of the API endpoint that returns the latest report content.'

}

# This is a dictionary of settings that have default values.
default_settings = {}
