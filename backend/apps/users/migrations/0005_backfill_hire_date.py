from django.db import migrations


def backfill_hire_date(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.filter(hire_date__isnull=True, role__in=["rh_admin", "colaborador"]):
        user.hire_date = user.created_at.date()
        user.save(update_fields=["hire_date"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_user_hire_date"),
    ]

    operations = [
        migrations.RunPython(backfill_hire_date, noop),
    ]
