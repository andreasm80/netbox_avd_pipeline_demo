# In netbox_run_anta_plugin/netbox_run_anta_plugin/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.AntaStatusView.as_view(), name='anta_status'),
]
