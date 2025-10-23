import django_tables2 as tables
from netbox.tables import NetBoxTable, ChoiceFieldColumn

from .models import RunAnta


class RunAntaTable(NetBoxTable):
    name = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = RunAnta
        fields = ("pk", "id", "name", "actions")
        default_columns = ("name",)
