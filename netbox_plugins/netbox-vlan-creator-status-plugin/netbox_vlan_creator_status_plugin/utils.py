import hmac
import hashlib
import json
import requests
from datetime import datetime
from django.conf import settings

def trigger_ansible_sync(vlan_data):
    plugin_settings = settings.PLUGINS_CONFIG.get('netbox_vlan_creator_status_plugin', {})
    webhook_url = plugin_settings.get('WEBHOOK_URL')
    webhook_secret = plugin_settings.get('WEBHOOK_SECRET')

    vlan_db_id = vlan_data.get('id')
    vlan_vid = vlan_data.get('vid')

    print(f"BACKGROUND THREAD: Starting sync for VLAN DB ID: {vlan_db_id}, VLAN Tag: {vlan_vid}")

    if not webhook_url or not webhook_secret:
        print("BACKGROUND THREAD ERROR: WEBHOOK_URL or WEBHOOK_SECRET is not configured for the plugin.")
        return

    payload = {
        'event': 'vlan_created',
        'timestamp': datetime.utcnow().isoformat(),
        'data': {
            'vlan_db_id': vlan_db_id,
            'vlan_tag_id': vlan_vid
        }
    }
    json_payload = json.dumps(payload).encode('utf-8')

    signature = hmac.new(
        webhook_secret.encode('utf-8'),
        json_payload,
        hashlib.sha512
    ).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'X-Hook-Signature': signature
    }

    print(f"BACKGROUND THREAD: Sending webhook to {webhook_url}")
    try:
        response = requests.post(webhook_url, data=json_payload, headers=headers, timeout=15)
        response.raise_for_status()
        print(f"BACKGROUND THREAD SUCCESS: Server responded with status {response.status_code}.")
    except requests.exceptions.RequestException as e:
        print(f"BACKGROUND THREAD FAILED to send webhook: {e}")
