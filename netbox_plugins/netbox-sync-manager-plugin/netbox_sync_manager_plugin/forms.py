from django import forms
from ipam.models import Prefix
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms.fields import CommentField, DynamicModelChoiceField

from .models import SyncManager


class SyncManagerForm(NetBoxModelForm):
    class Meta:
        model = SyncManager
        fields = ("name", "tags")
