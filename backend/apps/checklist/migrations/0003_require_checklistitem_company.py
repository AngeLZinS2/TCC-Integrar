import django.db.models.deletion
from django.db import migrations, models


def backfill_company(apps, schema_editor):
    ChecklistItem = apps.get_model("checklist", "ChecklistItem")
    Company = apps.get_model("companies", "Company")
    empresa_demo = Company.objects.filter(name="Empresa Demo").first()
    if empresa_demo:
        ChecklistItem.objects.filter(company__isnull=True).update(company=empresa_demo)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("checklist", "0002_checklistitem_company"),
        ("companies", "0002_seed_empresa_demo"),
    ]

    operations = [
        migrations.RunPython(backfill_company, noop),
        migrations.AlterField(
            model_name="checklistitem",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="checklist_items",
                to="companies.company",
                verbose_name="Empresa",
            ),
        ),
    ]
