from netbox.filtersets import NetBoxModelFilterSet
from .models import RunAnta


# class RunAntaFilterSet(NetBoxModelFilterSet):
#
#     class Meta:
#         model = RunAnta
#         fields = ['name', ]
#
#     def search(self, queryset, name, value):
#         return queryset.filter(description__icontains=value)
