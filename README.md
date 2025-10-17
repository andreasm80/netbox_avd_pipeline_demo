# My Netbox AVD pipeline demo

This repository contains the scripts, jinja templates, ansible playbooks and Netbox plugins I use in my CI pipeline demo showcasing Netbox and Arista Architect Validate Deploy working together.

This is not, by far, intended as a best practice approach, nor an offical approach from Arista. This is my own creation to just showcase how AVD and ANTA can be used as powerful tools in a CI pipeline in combination with tools such as Netbox, Git and Arista Cloudvision.

There are many ways to achieve such integrations and approaches which also cover much more details and logics. This is just my take on it to maybe inspire or getting the tought process started. 

Below I will briefly explain the different scripts, and how it is intended to work. 

## Requirements

To make this work there are some requirements. These will not cover the actual EOS devices and where those run except that they are ofcourse needed and may run as vEOS, cEOS or even physical instances. I am running two instances of Containerlab to simulate two environments of 10 EOS instances each where one is mye "dev-environment" and the second is my "production" environment.

In no particular order:

- Arista Architect Validate Deploy, pyAVD and AVD ansible collection (I am using the latest version as of this writing 5.7)
- ANTA
- Python
- Ansible
- Netbox - configured with an inventory, some required tags and labels (can be found looking in the scripts) 
- Arista Cloudvision
- Git (I am using Gitea hosted onprem and to handle my workflow/actions)
- Docker container as runner (I create and maintain my own runner that is kept updated according to AVD versions)
- EOS instances (dev and prod), I am hosting this on Containerlab
- A webhook receiver between Netbox, AVD and Gitea
- A linux machine to host the webhook receiver, access to git repository.
- Some of my own custom Netbox plugins (also provided in this repository)

## How my approach works

As I use Gitea and at the time I started creating this (many moons ago), Gitea did not support receiving webhooks. So I decided to just put some of that logic in a dedicated python script. This functions as a trigger to execute certain actions from specific events coming from Netbox and from Gitea. I have also provided the python script for this function in the repository. 

A short overview of whats happening. I have configured Netbox with labels, tags etc. When a "layer 2" vlan or and SVI (layer 3) is being created using my custom "vlan creator" script it notifies my webhook receiver to perform an action. This will trigger a couple of ansible playbook executed in serial in the right order. *I have also created a custom plugin that just send a generic "event" to my webhook receiver to start fetching update from Netbox.* 

After the ansible playbooks has run, if any changes are found it will create a branch in my git repository. This will trigger a workflow in that branch which involves running AVD and ANTA to generate new documentation and configuration from the changes made in Netbox and ANTA to perform network testing. This first workflow is only concering my dev environment. All the output will be committed and pushed to the same branch. I can review the changes then decide to merge this to my main branch. As soon as I do a pull request to main my next workflow will start. This will again run AVD to create documentation and configuration from the same change but now to my production environment. Not directly to the devices themselves, but to Arista CloudVison. 







**A note on what Netbox is responsible for in my demo:**

I have not focused on getting Netbox to provide all the configuration details such as BGP, VXLAN, EVPN config. I have only focused on letting Netbox handle adding/removing devices, configure/add/remove interfaces, add/remove VLANs (including SVIs) and AVD will take care of the rest. There is ofcourse nothing stopping you to make Netbox handle everything if you want. 



## Webhook receiver tasks explained

## The scripts explained



## Workflow tasks explained



