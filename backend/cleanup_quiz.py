from apps.courses.models import Course
from apps.notifications.models import Notification

qs = Course.objects.filter(title__startswith="[QA]")
print("removendo cursos:", list(qs.values_list("title", flat=True)))
Notification.objects.filter(message__contains="[QA]").delete()
Notification.objects.filter(title__contains="[QA]").delete()
qs.delete()  # cascata leva quiz, tentativas e certificados
print("cursos restantes:", Course.objects.count())
