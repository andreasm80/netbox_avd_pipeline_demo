#!/usr/bin/env python
import os
import sys
import requests

# --- CONFIGURATION ---
NETBOX_URL = os.environ.get("NETBOX_URL")
NETBOX_API_TOKEN = os.environ.get("NETBOX_API_TOKEN") 
NETBOX_CERT = os.environ.get("NETBOX_CERT")

def update_vlan_status(vlan_id, new_status):
    """Updates the deployment_status custom field for a given VLAN."""
    if not all([NETBOX_URL, NETBOX_API_TOKEN, NETBOX_CERT, vlan_id, new_status]):
        print("Error: Missing required environment variables (NETBOX_URL, NETBOX_API_TOKEN, NETBOX_CERT) or script arguments.")
        sys.exit(1)
        
    if not os.path.exists(NETBOX_CERT):
        print(f"Error: Certificate file not found at path: {NETBOX_CERT}")
        sys.exit(1)

    api_url = f"{NETBOX_URL.rstrip('/')}/api/ipam/vlans/{vlan_id}/"
    headers = {
        "Authorization": f"Token {NETBOX_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "custom_fields": {
            "deployment_status": new_status
        }
    }

    print(f"Updating NetBox: Setting VLAN {vlan_id} status to '{new_status}'...")
    try:
        response = requests.patch(api_url, headers=headers, json=payload, timeout=10, verify=NETBOX_CERT)
        response.raise_for_status()
        print(f"Successfully updated VLAN {vlan_id} status.")
    except requests.exceptions.SSLError as e:
        print(f"SSL Error updating NetBox: {e}")
        print("Please ensure the NETBOX_CERT file is the correct CA certificate or bundle for your NetBox server.")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error updating NetBox: {e}")
        if e.response:
            print(f"Response Body: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python update_netbox_status.py <VLAN_ID> <NEW_STATUS>")
        print("Example: python update_netbox_status.py 123 created")
        sys.exit(1)
    
    vlan_id_arg = sys.argv[1]
    new_status_arg = sys.argv[2]
    update_vlan_status(vlan_id_arg, new_status_arg)
