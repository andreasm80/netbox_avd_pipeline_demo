# In netbox_run_anta_plugin/netbox_run_anta_plugin/views.py

import hashlib
import hmac
import requests
import time
import json
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.conf import settings
from .models import AntaStatus
from markdown_it import MarkdownIt  

class AntaStatusView(View):
    template_name = 'netbox_run_anta_plugin/run-anta.html'

    def get(self, request):
        plugin_settings = settings.PLUGINS_CONFIG.get('netbox_run_anta_plugin', {})
        status_url = plugin_settings.get('anta_status_url')
        report_url = plugin_settings.get('anta_report_url') 
        
        context = {
            'button_color': 'secondary',
            'api_error': False,
            'html_report': None,
        }

        if not status_url or not report_url:
            messages.error(request, "ANTA status or report URL is not configured in configuration.py.")
            context['api_error'] = True
            return render(request, self.template_name, context)

        try:
            response = requests.get(status_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            current_hash = data.get('file_hash')
            if not current_hash: raise ValueError("Hash not found in API response")
            context['current_hash'] = current_hash
        except (requests.exceptions.RequestException, ValueError) as e:
            messages.error(request, f"Could not get status from remote server: {e}")
            context['api_error'] = True
            return render(request, self.template_name, context)
        
        status_obj, created = AntaStatus.objects.get_or_create(pk=1)
        context['last_hash'] = status_obj.last_known_hash or "N/A"
        context['button_color'] = 'red' if context['current_hash'] != context['last_hash'] else 'green'

        try:
            report_response = requests.get(report_url, timeout=10)
            report_response.raise_for_status()
            report_data = report_response.json()
            report_content = report_data.get('report_content', '')
            
            # Convert Markdown to HTML
            md = MarkdownIt()
            md.enable('table')
            context['html_report'] = md.render(report_content)

        except (requests.exceptions.RequestException, ValueError) as e:
            messages.warning(request, f"Could not fetch latest report: {e}")
            context['html_report'] = "<p class='text-warning'>Could not load report content.</p>"

        return render(request, self.template_name, context)
        
    def post(self, request):
        plugin_settings = settings.PLUGINS_CONFIG.get('netbox_run_anta_plugin', {})
        webhook_url = plugin_settings.get('webhook_url')
        webhook_secret = plugin_settings.get('webhook_secret')
        status_url = plugin_settings.get('anta_status_url')

        if not all([webhook_url, webhook_secret, status_url]):
            messages.error(request, "Webhook URL, secret, or status URL is not configured.")
            return redirect('plugins:netbox_run_anta_plugin:anta_status')

        try:
            status_response = requests.get(status_url, timeout=5)
            status_response.raise_for_status()
            current_hash = status_response.json().get('file_hash')
            if not current_hash: raise ValueError("Hash not found in API response")
        except (requests.exceptions.RequestException, ValueError) as e:
            messages.error(request, f"Could not get current status before triggering webhook: {e}")
            return redirect('plugins:netbox_run_anta_plugin:anta_status')

        payload = {'event': 'run_anta_test', 'timestamp': int(time.time())}
        body = json.dumps(payload).encode('utf-8')
        signature = hmac.new(webhook_secret.encode('utf-8'), body, hashlib.sha512).hexdigest()
        headers = {'Content-Type': 'application/json', 'X-Hook-Signature': signature}

        try:
            trigger_response = requests.post(webhook_url, data=body, headers=headers, timeout=10)
            trigger_response.raise_for_status()

            status_obj = AntaStatus.objects.get(pk=1)
            status_obj.last_known_hash = current_hash
            status_obj.save()
            
            messages.success(request, f"Successfully triggered ANTA test. Server responded: {trigger_response.json().get('message')}")

        except requests.exceptions.RequestException as e:
            messages.error(request, f"Failed to send trigger webhook: {e}")

        return redirect('plugins:netbox_run_anta_plugin:anta_status')
