import django.db.models.deletion
from django.db import migrations, models


def backfill_company(apps, schema_editor):
    Sector = apps.get_model("sectors", "Sector")
    Company = apps.get_model("companies", "Company")
    empresa_demo = Company.objects.filter(name="Empresa Demo").first()
    if empresa_demo:
        Sector.objects.filter(company__isnull=True).update(company=empresa_demo)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("sectors", "0002_sector_company_alter_sector_name_and_more"),
        ("companies", "0002_seed_empresa_demo"),
    ]

    operations = [
        migrations.RunPython(backfill_company, noop),
        migrations.AlterField(
            model_name="sector",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sectors",
                to="companies.company",
                verbose_name="Empresa",
            ),
        ),
    ]
