# In views.py

import hmac
import hashlib
import json
import requests
import threading
from datetime import datetime

from django.shortcuts import render
from django.contrib import messages
from django.conf import settings
from netbox.views import generic
from dcim.models import Site


def trigger_ansible_sync():
    """
    This function runs in a background thread and sends the webhook.
    """
    plugin_settings = settings.PLUGINS_CONFIG.get('netbox_sync_manager_plugin', {})
    webhook_url = plugin_settings.get('WEBHOOK_URL')
    webhook_secret = plugin_settings.get('WEBHOOK_SECRET')

    print(f"BACKGROUND THREAD: Starting Ansible sync trigger.")

    if not webhook_url or not webhook_secret:
        print("BACKGROUND THREAD ERROR: WEBHOOK_URL or WEBHOOK_SECRET is not configured.")
        return

    payload = {
        'event': 'manual_sync',
        'timestamp': datetime.utcnow().isoformat()
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
        print(f"BACKGROUND THREAD FAILED: {e}")

class SyncManagerView(generic.ObjectView):
    queryset = Site.objects.none() 
    template_name = 'netbox_sync_manager_plugin/sync.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        thread = threading.Thread(target=trigger_ansible_sync)
        thread.start()
        
        messages.success(request, "Sync task has been started in the background.")
        return render(request, self.template_name)
