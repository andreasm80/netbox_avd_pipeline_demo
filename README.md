# My NetBox AVD Pipeline Demo

This repository contains the scripts, Jinja templates, Ansible playbooks, and NetBox plugins I use in my CI pipeline demo showcasing NetBox and Arista’s **Architect Validate Deploy (AVD)** working together.

This is not, by any means, intended as a best-practice approach, nor an official approach from Arista. It is my own creation to demonstrate how AVD and ANTA can be used as powerful tools in a CI pipeline, in combination with tools such as NetBox, Git, and Arista CloudVision. I have also tried to keep the examples (group_var files, etc.) provided by AVD as *“out-of-the-box”* as possible from the AVD repository, keeping AVD itself as *“unmodified”* as possible to make maintenance and upgrades simpler when new versions of AVD are released—without adding too many *custom* scripts and playbooks that would require revision if something becomes deprecated later on.  

There are many ways to achieve such integrations and approaches, some of which cover more details and logic. This is just my take on it—perhaps to inspire or start the thought process.  

Below I will briefly explain the different scripts and how they are intended to work.  

## Requirements

To make this work, there are some requirements. These do not cover the actual EOS devices or where they run, except that they are, of course, needed and may run as vEOS, cEOS, or even physical instances. I am running two instances of Containerlab to simulate two environments of 10 EOS instances each—one being my *dev environment* and the other my *production environment*. Please refer to [Getting Started with cEOS-lab in Containerlab](https://arista.my.site.com/AristaCommunity/s/article/Getting-Started-with-cEOS-lab-in-Containerlab) for instructions on creating such an environment yourself.  

If you prefer a “traditional” approach using virtual EOS (vEOS) instead of containers, you may want to check [Setting up EVE-NG, CloudVision Portal and vEOS](https://arista.my.site.com/AristaCommunity/s/article/setting-up-eve-ng-cloudvision-portal-and-veos) or [vEOS/cEOS GNS3 Labs](https://arista.my.site.com/AristaCommunity/s/article/veos-ceos-gns3-labs).

In no particular order:

- Arista Architect Validate Deploy, pyAVD, and the AVD Ansible collection (I am using version 5.7 at the time of writing)  
- ANTA  
- Python  
- Ansible  
- NetBox – configured with an inventory and some required tags and labels (see scripts for details)  
- Arista CloudVision  
- Git (I am using Gitea hosted on-premises to handle my workflow/actions)  
- Docker container as runner (I maintain my own runner that is updated according to AVD versions)  
- EOS instances (dev and prod), hosted on Containerlab  
- A webhook receiver between NetBox, AVD, and Gitea  
- A Linux machine to host the webhook receiver and access the Git repository  
- Some of my own custom NetBox plugins (also provided in this repository)

## How My Approach Works

When I started this (many moons ago), Gitea did not support receiving webhooks, so I decided to implement some of that logic in a dedicated Python script. This script functions as a trigger to execute certain actions based on specific events coming from NetBox and from Gitea. I have also provided the Python script for this functionality in the repository.  

A short overview of what happens: I have configured NetBox with labels, tags, etc. When a Layer-2 VLAN or an SVI (Layer-3) is created using my custom *“VLAN creator”* script, it notifies my webhook receiver to perform an action. This triggers a series of Ansible playbooks executed sequentially in the correct order. *I have also created a custom plugin that simply sends a generic “event” to my webhook receiver to start fetching updates from NetBox.*  

After the Ansible playbooks have run, if any changes are found, a branch is created in my Git repository. This triggers a workflow in that branch, which involves running AVD and ANTA to generate new documentation and configuration from the changes made in NetBox, and to perform network testing via ANTA. This first workflow concerns only my dev environment. All output is committed and pushed to the same branch. I can then review the changes and decide to merge them into the main branch. As soon as I create a pull request to *main*, my next workflow starts. This again runs AVD to create documentation and configuration for the same change, but now targeting the production environment—not directly on the devices, but through Arista CloudVision.  

![Pipeline Overview](images/pipeline_overview.png)

**A note on what NetBox is responsible for in my demo:**  

I have not focused on having NetBox provide all configuration details such as BGP, VXLAN, or EVPN configuration (i.e., a full data model in NetBox). I have focused only on having NetBox handle adding/removing devices, configuring/adding/removing interfaces, and adding/removing VLANs (including SVIs). AVD takes care of the rest. Of course, nothing prevents you from making NetBox handle everything if you wish.  

## Webhook Receiver Tasks Explained

Since Gitea did not have this capability, I decided to run a simple Python script (`/webhook_server/sync_netbox_avd_cvaas.py`) that triggers certain actions when it receives hooks from NetBox. These actions involve running four playbooks and one Python script that reads the changes from NetBox. Below is a short description of the responsibilities of each playbook.

- **1-playbook-update_inventory-dev-prod.yml**  
  This is the first playbook triggered. Its responsibility is to update the `inventory.yml` file based on the actual content fetched from NetBox. If I add a device in NetBox, it updates the inventory to reflect that. This approach ensures the inventory always reflects the devices currently defined in NetBox. If no change is detected, it is skipped.  
  The Ansible playbook calls a Python script (`update_inventory.py`) that performs the fetch from NetBox using certain criteria (see the script for details). The script also generates `inventory.yml` using the Jinja template `inventory.yml.j2`.  
  The final task in the playbook creates a second, similar inventory file called `dev-inventory.yml` for my dev environment by replacing content to reflect my dev device names, IPs, and fabric.

- **2-playbook-update_dc1_yml_according_to_inventory.yml**  
  This second playbook updates the `DC1.yml` group_var file according to the actual device content. It uses the Jinja template `update_dc1.j2`.  
  The `DC1.yml` file for the dev environment (`DEV_DC1.yml`) uses the `dev-inventory.yml` file to dynamically generate itself using Jinja fields.

- **3-playbook-update_network_services.yml**  
  This third playbook updates the `NETWORK_SERVICES.yml` file. It uses Ansible to fetch VLANs, VRFs, and interfaces matching certain criteria from NetBox via its API (see playbook for details) and uses the Jinja template `network_services.j2`.  
  There is no need to maintain duplicate `NETWORK_SERVICES.yml` files for dev and prod, as they should be identical.

- **4-playbook-update_connected_endpoints.yml**  
  This final playbook updates the `CONNECTED_ENDPOINTS.yml` file. It also uses Ansible to fetch information from NetBox via its API (see playbook for details) and uses the Jinja template `connected_endpoints.j2`.  
  Again, there is no need for duplicate dev/prod versions, as they should be identical.

In addition to the playbooks mentioned above, the webhook script also performs actions such as creating a branch if it detects changes indicating updates to any of the AVD-related files. When this branch is committed and pushed, it triggers a workflow in my Gitea instance.  

## Workflow Tasks Explained

In Gitea, I have defined two workflow files under `.gitea/workflows`:  

- **run_ansible_build.yaml**  
  This workflow is triggered when a branch is created. It uses my custom Gitea runner to run the AVD playbooks:  
  - `dev-build.yml` to generate new config and documentation  
  - `dev-deploy.yml` to push the config to the dev devices  
  - `dev-anta.yml` to run ANTA tests in the dev environment  
  - `dev-avd_cv_workflow.yml` to reflect the changes in CloudVision (I have added my dev environment to CloudVision as well)  
  Finally, the repository is updated with the changes produced by the above playbooks.  

- **run_ansible_build_deploy-cvp.yaml**  
  This workflow is triggered when something is merged into *main*. It runs the AVD playbook to generate documentation and configurations for the production environment. It also updates NetBox with the status *created* for the VLAN that was created. Then it runs the `cv_workflow` role to deploy the configuration to CloudVision while printing the Change Control (CC) ID created in CloudVision.  
  This ID is used by the `cv_monitor.py` script to subscribe to events from this CC job. Since I have added this CC job as a manual step, it is configured to retry a few times before timing out.  
  A note: the CC job should normally be auto-approved since it has already been validated in Git, but for demo purposes I chose a manual step here. (Yes, I know it breaks full automation.) Even if I approved it automatically, CloudVision would still block it if it detects an issue (not just warnings but errors in the config).  
  The reason for fetching the CC ID is that it is required for my ANTA task, which is supposed to start only after the CC job completes successfully. If the job completes successfully, the script also updates NetBox to *Applied*.  

## Gitea Runner

If you do not want to create your own Docker image for this purpose, you can use mine, hosted in my Docker registry:

"registry.guzware.net/avd/avd-5.7:v2"

## Summary

As I wrote initially, there are many roads to Rome—and many ways to automate or build a CI pipeline. I have chosen this approach to showcase that AVD can interoperate with other tools, such as NetBox, using either Ansible or Python. I use a mix of Python and Ansible, choosing whichever fits a given task better. It may or may not give you an idea of what’s possible, but hopefully it inspires someone to start automating with AVD and ANTA in a CI pipeline and explore the many possibilities this combination opens up.

