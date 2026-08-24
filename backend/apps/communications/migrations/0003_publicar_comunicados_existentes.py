"""
Comunicados criados antes do campo `status` existir já estavam visíveis.

Com o default `draft`, eles sumiriam do mural na hora do deploy — perda de
funcionalidade silenciosa. Esta migração marca os antigos como publicados,
usando `created_at` como data de publicação.
"""

from django.db import migrations


def publicar_existentes(apps, schema_editor):
    Announcement = apps.get_model("communications", "Announcement")
    for comunicado in Announcement.objects.filter(status="draft", published_at__isnull=True):
        comunicado.status = "published"
        comunicado.published_at = comunicado.created_at
        # Já estavam visíveis, então as notificações (se houvesse) já teriam
        # saído. Marcar evita um disparo retroativo para todo mundo.
        comunicado.notified_at = comunicado.created_at
        comunicado.save(update_fields=["status", "published_at", "notified_at"])


def reverter(apps, schema_editor):
    """Reversível: desfaz apenas o que esta migração marcou."""
    Announcement = apps.get_model("communications", "Announcement")
    Announcement.objects.filter(status="published").update(
        status="draft", published_at=None, notified_at=None
    )


class Migration(migrations.Migration):
    dependencies = [
        ("communications", "0002_announcement_expires_at_announcement_notified_at_and_more"),
    ]

    operations = [migrations.RunPython(publicar_existentes, reverter)]
