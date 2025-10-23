import threading
import logging

from django.shortcuts import render, redirect
from django.views.generic import View
from django.db import transaction
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType

from ipam.models import VLAN, Prefix, IPAddress, VRF, Role as IPRole
from tenancy.models import Tenant
from dcim.models import Site, Device, DeviceRole, Interface
from extras.models import Tag

from .forms import VlanCreatorForm, VlanDeleterForm
from .utils import trigger_ansible_sync


logger = logging.getLogger(__name__)


def get_applicable_tags(request):
    """Get tags that match device names in site dc1 with l2leaf or l3leaf roles"""
    try:
        dc1_site = Site.objects.get(slug='dc1')
        l2leaf_role = DeviceRole.objects.filter(slug='l2leaf').first()
        l3leaf_role = DeviceRole.objects.filter(slug='l3leaf').first()
        roles = [role for role in [l2leaf_role, l3leaf_role] if role]
        devices = Device.objects.filter(site=dc1_site, role__in=roles)
        device_names = set(device.name for device in devices)
        all_tags = Tag.objects.all()
        vlan_content_type = ContentType.objects.get(app_label='ipam', model='vlan')
        applicable_tags = [
            tag for tag in all_tags
            if tag.name in device_names and vlan_content_type in tag.object_types.all()
        ]
        messages.info(request, f"Found applicable tags: {[tag.name for tag in applicable_tags]}")
        return applicable_tags
    except Site.DoesNotExist:
        messages.warning(request, "Site 'dc1' not found, cannot determine tags.")
        return []
    except Exception as e:
        messages.error(request, f"Error getting applicable tags: {e}")
        return []


def create_anycast_interfaces(request, vlan, ip_address_str, vrf, ip_role_str, tenant):
    """Create interfaces on l3leaf devices with individual anycast IPs"""
    try:
        dc1_site = Site.objects.get(slug='dc1')
        l3leaf_role = DeviceRole.objects.filter(slug='l3leaf').first()
        if not l3leaf_role:
            messages.warning(request, "No 'l3leaf' device role found, cannot create interfaces.")
            return
        l3leaf_devices = Device.objects.filter(site=dc1_site, role=l3leaf_role)
        if not l3leaf_devices:
            messages.warning(request, "No devices with role 'l3leaf' found in site 'dc1'.")
            return

        interface_name = f"Vlan{vlan.vid}"
        description = vlan.name

        for device in l3leaf_devices:
            interface, created = Interface.objects.get_or_create(
                device=device,
                name=interface_name,
                defaults={
                    'type': 'vlan',
                    'description': description,
                    'vrf': vrf,
                }
            )
            if created:
                messages.info(request, f"Created interface {interface_name} on {device.name}")
            else:
                messages.info(request, f"Interface {interface_name} already exists on {device.name}, assigning IP.")

            if interface.ip_addresses.filter(address=ip_address_str).exists():
                messages.warning(request, f"IP {ip_address_str} is already assigned to {interface_name} on {device.name}. Skipping.")
                continue

            ip = IPAddress(
                address=ip_address_str,
                vrf=vrf,
                role=ip_role_str,
                tenant=tenant,
                assigned_object=interface,
                description=f"Anycast IP for {vlan.name}"
            )
            ip.save()
            messages.success(request, f"Created IP {ip.address} and assigned to {interface_name} on {device.name}")

    except Site.DoesNotExist:
        messages.warning(request, "Site 'dc1' not found for interface creation")
    except Exception as e:
        messages.error(request, f"Error creating interfaces: {e}")


class VlanCreatorView(View):
    template_name = 'netbox_vlan_creator_status_plugin/create.html'

    def get(self, request):
        form = VlanCreatorForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = VlanCreatorForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            vlan_tenant = data.get("vlan_tenant")

            try:
                with transaction.atomic():
                    vlan, created = VLAN.objects.get_or_create(
                        vid=data["vlan_id"],
                        site=data["vlan_site"],
                        group=data["vlan_group"] or None,
                        defaults={
                            'name': data["vlan_name"],
                            'role': data["vlan_role"],
                            'tenant': vlan_tenant,
                            'group': data["vlan_group"],
                        }
                    )

                    if created:
                        # Set initial deployment status to "Pending"
                        vlan.custom_field_data['deployment_status'] = 'pending'
                        vlan.save()
                        messages.success(request, f"Successfully created VLAN: {vlan}. Deployment status set to Pending.")

                        # Create a dictionary containing BOTH the database ID and the VLAN Tag.
                        vlan_data_for_webhook = {
                            'id': vlan.id,   # The Database ID (e.g., 447)
                            'vid': vlan.vid  # The VLAN Tag (e.g., 69)
                        }
                        
                        # Pass this dictionary as the argument to the background thread.
                        # The comma is important: args=(vlan_data_for_webhook,)
                        thread = threading.Thread(target=trigger_ansible_sync, args=(vlan_data_for_webhook,))
                        thread.start()
                        messages.info(request, "Automation pipeline has been triggered for VLAN sync.")
                    else:
                        messages.warning(request, f"VLAN {data['vlan_id']} in site {data['vlan_site'].name} already exists. No actions taken.")

                    tags = get_applicable_tags(request)
                    if tags:
                        vlan.tags.add(*tags)
                        messages.info(request, f"Applied tags to VLAN: {[tag.name for tag in tags]}")

                    if data["prefix"]:
                        if not data["prefix_vrf"]:
                            raise Exception("VRF is required to create a prefix.")
                        prefix, p_created = Prefix.objects.get_or_create(
                            prefix=data["prefix"],
                            vrf=data["prefix_vrf"],
                            defaults={
                                'vlan': vlan,
                                'tenant': vlan_tenant,
                                'description': f"For {vlan.name}"
                            }
                        )
                        if p_created:
                            messages.success(request, f"Created Prefix: {prefix}")

                    if data["ip_address"]:
                        if not data["prefix_vrf"]:
                            raise Exception("VRF is required to create an IP address.")
                        if data["ip_role"] != 'anycast':
                            raise Exception("This tool currently only supports creating 'anycast' role IPs and interfaces.")
                        create_anycast_interfaces(
                            request, vlan, data["ip_address"], data["prefix_vrf"], data["ip_role"], vlan_tenant
                        )

                    return redirect(vlan.get_absolute_url())

            except Exception as e:
                logger.error(f"Error during VLAN creation transaction: {e}")
                messages.error(request, f"An error occurred: {e}")
                # Re-raise in debug mode to see the full traceback on the error page
                if settings.DEBUG:
                    raise e

        return render(request, self.template_name, {'form': form})


class VlanDeleterView(View):
    template_name = 'netbox_vlan_creator_status_plugin/delete.html'

    def get(self, request):
        form = VlanDeleterForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = VlanDeleterForm(request.POST)
        if form.is_valid():
            vlan_id = form.cleaned_data['vlan_id']
            vlan_site = form.cleaned_data['vlan_site']
            vlan_tenant = form.cleaned_data['vlan_tenant']
            prefix_vrf = form.cleaned_data['prefix_vrf']

            try:
                with transaction.atomic():
                    vlan_query = VLAN.objects.filter(vid=vlan_id, site=vlan_site)
                    if vlan_tenant:
                        vlan_query = vlan_query.filter(tenant=vlan_tenant)

                    vlan = vlan_query.first()

                    if not vlan:
                        messages.error(request, f"VLAN with ID {vlan_id} in site {vlan_site.name} not found.")
                        return render(request, self.template_name, {'form': form})

                    messages.info(request, f"Found VLAN: {vlan}. Starting deletion process...")

                    if prefix_vrf:
                        prefix = Prefix.objects.filter(vlan=vlan, vrf=prefix_vrf).first()
                        if prefix:
                            prefix_str = str(prefix)
                            prefix.delete()
                            messages.success(request, f"Deleted Prefix: {prefix_str}")
                        else:
                            messages.info(request, f"No prefix found for VLAN {vlan} in VRF {prefix_vrf.name}")

                    dc1_site = Site.objects.get(slug='dc1')
                    l3leaf_role = DeviceRole.objects.filter(slug='l3leaf').first()
                    if l3leaf_role:
                        l3leaf_devices = Device.objects.filter(site=dc1_site, role=l3leaf_role)
                        interface_name = f"Vlan{vlan_id}"

                        for device in l3leaf_devices:
                            interface = Interface.objects.filter(device=device, name=interface_name).first()
                            if not interface:
                                continue

                            anycast_ips = IPAddress.objects.filter(
                                assigned_object_type__model='interface',
                                assigned_object_id=interface.id,
                                role='anycast'
                            )
                            for ip in anycast_ips:
                                ip_str = str(ip)
                                ip.delete()
                                messages.success(request, f"Deleted IP: {ip_str} from {interface_name} on {device.name}")

                            interface.delete()
                            messages.success(request, f"Deleted interface {interface_name} on {device.name}")

                    vlan_str = str(vlan)
                    vlan.delete()
                    messages.success(request, f"Successfully deleted VLAN: {vlan_str}")

                messages.info(request, "All deletion operations completed successfully!")
                return redirect('plugins:netbox_vlan_creator_status_plugin:vlan_creator_add')

            except Exception as e:
                logger.error(f"Error during VLAN deletion transaction: {e}")
                messages.error(request, f"An error occurred: {e}")
                if settings.DEBUG:
                    raise e

        return render(request, self.template_name, {'form': form})
