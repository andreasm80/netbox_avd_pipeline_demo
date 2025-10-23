# In urls.py

from django.urls import path
from .views import VlanCreatorView, VlanDeleterView

app_name = 'netbox_vlan_creator_status_plugin'

urlpatterns = [
    path('create/', VlanCreatorView.as_view(), name='vlan_creator_add'),
    
    path('delete/', VlanDeleterView.as_view(), name='vlan_deleter_delete'),
]
