# In urls.py
from django.urls import path
from .views import SyncManagerView

app_name = 'netbox_sync_manager_plugin'

urlpatterns = [
    path('', SyncManagerView.as_view(), name='sync_view'),
]
