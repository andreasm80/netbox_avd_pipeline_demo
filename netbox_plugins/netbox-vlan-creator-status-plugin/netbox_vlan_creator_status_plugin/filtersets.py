from netbox.filtersets import NetBoxModelFilterSet
from .models import VLANCreator


# class VLANCreatorFilterSet(NetBoxModelFilterSet):
#
#     class Meta:
#         model = VLANCreator
#         fields = ['name', ]
#
#     def search(self, queryset, name, value):
#         return queryset.filter(description__icontains=value)
