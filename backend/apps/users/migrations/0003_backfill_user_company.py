from django.db import migrations


def backfill_company(apps, schema_editor):
    User = apps.get_model("users", "User")
    Company = apps.get_model("companies", "Company")
    empresa_demo = Company.objects.filter(name="Empresa Demo").first()
    if empresa_demo:
        User.objects.filter(company__isnull=True).update(company=empresa_demo)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_user_company_alter_user_role"),
        ("companies", "0002_seed_empresa_demo"),
    ]

    operations = [
        migrations.RunPython(backfill_company, noop),
    ]
