from apps.automations.models import AutomationRule, AutomationRun
from apps.communications.models import Announcement
from apps.notifications.models import Notification
from apps.onboarding.models import OnboardingTask, OnboardingTemplate
from apps.units.models import Unit
from apps.users.models import User

Notification.objects.filter(title__contains="[QA]").delete()
Notification.objects.filter(message__contains="[QA]").delete()
Announcement.objects.filter(title__startswith="[QA]").delete()
AutomationRun.objects.filter(rule__name__startswith="[QA]").delete()
AutomationRule.objects.filter(name__startswith="[QA]").delete()

novato = User.objects.filter(email="qa-novato@beta.com").first()
if novato:
    OnboardingTask.objects.filter(employee=novato).delete()
    novato.delete()

bruno = User.objects.filter(email="bruno@beta.com").first()
if bruno:
    OnboardingTask.objects.filter(employee=bruno).delete()

OnboardingTemplate.objects.filter(name__startswith="[QA]").delete()
Unit.objects.filter(name__startswith="[QA]").delete()
User.objects.filter(email="qa-admin@beta.com").delete()

print("unidades:", Unit.objects.count(), "| templates:", OnboardingTemplate.objects.count(),
      "| tarefas:", OnboardingTask.objects.count(), "| automacoes:", AutomationRule.objects.count())
print("usuarios:", list(User.objects.values_list("email", flat=True)))
