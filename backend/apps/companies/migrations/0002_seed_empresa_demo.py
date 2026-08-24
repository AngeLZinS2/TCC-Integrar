from django.db import migrations


EMPRESA_DEMO = "Empresa Demo"


def create_empresa_demo(apps, schema_editor):
    Company = apps.get_model("companies", "Company")
    Company.objects.get_or_create(name=EMPRESA_DEMO)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_empresa_demo, noop),
    ]
