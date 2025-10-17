#!/usr/bin/env python3

import os
import requests
import yaml
from jinja2 import Environment, FileSystemLoader

# NetBox Configuration
NETBOX_URL = os.environ["NETBOX_URL"]
NETBOX_TOKEN = os.environ["NETBOX_TOKEN"]
HEADERS = {"Authorization": f"Token {NETBOX_TOKEN}"}
NETBOX_CERT = os.environ["NETBOX_CERT"]

# CVP Configuration
CVP_HOST = os.environ["CVP_HOST"]
CVP_USER = os.environ["CVP_USER"]
CVP_PASSWORD = os.environ["CVP_PASSWORD"]

def get_netbox_devices(role_slug):
    """Fetch devices from NetBox based on role slug and site dc1."""
    url = f"{NETBOX_URL}/api/dcim/devices/?role={role_slug}&site=dc1"
    response = requests.get(url, headers=HEADERS, verify=NETBOX_CERT)
    response.raise_for_status()
    return response.json()["results"]

def main():
    # Check for required environment variables
    required_vars = ["NETBOX_URL", "NETBOX_TOKEN", "NETBOX_CERT", "CVP_HOST", "CVP_USER", "CVP_PASSWORD"]
    missing_vars = [var for var in required_vars if var not in os.environ]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Fetch devices by role slugs
    spines = [
        {"name": device["name"], "ip": device["primary_ip"]["address"].split("/")[0] if device["primary_ip"] else "0.0.0.0"}
        for device in get_netbox_devices("spine")
    ]
    l3_leaves = [
        {"name": device["name"], "ip": device["primary_ip"]["address"].split("/")[0] if device["primary_ip"] else "0.0.0.0"}
        for device in get_netbox_devices("l3leaf")
    ]
    l2_leaves = [
        {"name": device["name"], "ip": device["primary_ip"]["address"].split("/")[0] if device["primary_ip"] else "0.0.0.0"}
        for device in get_netbox_devices("l2leaf")
    ]

    # Prepare data for template
    template_data = {
        "cvp_host": CVP_HOST,
        "cvp_user": CVP_USER,
        "cvp_password": CVP_PASSWORD,
        "spines": spines,
        "l3_leaves": l3_leaves,
        "l2_leaves": l2_leaves
    }

    # Render template
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("inventory.yml.j2")
    rendered_inventory = template.render(template_data)

    # Check if inventory.yml exists and compare content
    inventory_file = "inventory.yml"
    if os.path.exists(inventory_file):
        with open(inventory_file, "r") as f:
            current_content = f.read()
        if current_content == rendered_inventory:
            print("No changes detected in inventory.yml")
            exit(0)  # Exit with 0 to indicate no change

    # Write to inventory.yml if there’s a change
    with open(inventory_file, "w") as f:
        f.write(rendered_inventory)


if __name__ == "__main__":
    main()
