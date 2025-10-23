from netbox.filtersets import NetBoxModelFilterSet
from .models import SyncManager


# class SyncManagerFilterSet(NetBoxModelFilterSet):
#
#     class Meta:
#         model = SyncManager
#         fields = ['name', ]
#
#     def search(self, queryset, name, value):
#         return queryset.filter(description__icontains=value)
