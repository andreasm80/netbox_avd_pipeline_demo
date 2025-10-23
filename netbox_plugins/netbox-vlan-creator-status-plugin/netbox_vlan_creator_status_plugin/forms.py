# In forms.py

from django import forms
from ipam.models import VLAN, Prefix, IPAddress, VRF, Role as IPRole, VLANGroup
from dcim.models import Site
from tenancy.models import Tenant, TenantGroup
from utilities.forms.fields import DynamicModelChoiceField

class VlanCreatorForm(forms.Form):
    vlan_site = DynamicModelChoiceField(
        label="Site",
        queryset=Site.objects.all(),
        required=True
    )

    vlan_group = DynamicModelChoiceField(
        label="VLAN Group (Optional)",
        queryset=VLANGroup.objects.all(),
        required=False,
        query_params={
            'site_id': '$vlan_site'
        }
    )

    vlan_id = forms.IntegerField(
        label="VLAN ID",
        min_value=1,
        max_value=4094,
        required=True
    )
    vlan_name = forms.CharField(
        label="VLAN Name",
        max_length=100,
        required=True
    )
    vlan_role = DynamicModelChoiceField(
        label="VLAN Role",
        queryset=IPRole.objects.all(),
        required=True
    )
    vlan_tenant_group = DynamicModelChoiceField(
        label="Tenant Group (Optional)",
        queryset=TenantGroup.objects.all(),
        required=False
    )
    vlan_tenant = DynamicModelChoiceField(
        label="Tenant (Optional)",
        queryset=Tenant.objects.all(),
        required=False,
        query_params={
            'group_id': '$vlan_tenant_group',
            'site_id': '$vlan_site'
        }
    )
    prefix = forms.CharField(
        label="Prefix (e.g., 10.0.1.0/24, Optional)",
        max_length=100,
        required=False
    )
    prefix_vrf = DynamicModelChoiceField(
        label="VRF for Prefix (Required if Prefix is set)",
        queryset=VRF.objects.all(),
        required=False,
        query_params={
            'tenant_id': '$vlan_tenant'
        }
    )
    ip_address = forms.CharField(
        label="Anycast IP (e.g., 10.0.1.1/24, Optional)",
        max_length=100,
        required=False
    )
    ip_role = forms.ChoiceField(
        label="IP Role (Required if IP is set)",
        choices=[
            ("", "---------"),
            ("anycast", "Anycast"),
            ("secondary", "Secondary"),
            ("vip", "VIP"),
            ("vrrp", "VRRP"),
            ("hsrp", "HSRP"),
            ("glbp", "GLBP"),
            ("carp", "CARP"),
            ("loopback", "Loopback"),
        ],
        required=False
    )

class VlanDeleterForm(forms.Form):
    vlan_id = forms.IntegerField(
        label="VLAN ID to Delete",
        min_value=1,
        max_value=4094,
        required=True
    )
    vlan_site = DynamicModelChoiceField(
        label="Site of the VLAN",
        queryset=Site.objects.all(),
        required=True
    )
    vlan_tenant = DynamicModelChoiceField(
        label="Tenant of the VLAN (Optional)",
        queryset=Tenant.objects.all(),
        required=False,
        query_params={
            'site_id': '$vlan_site'
        }
    )
    prefix_vrf = DynamicModelChoiceField(
        label="VRF of the Prefix (if applicable)",
        queryset=VRF.objects.all(),
        required=False,
        query_params={
            'tenant_id': '$vlan_tenant'
        }
    )
