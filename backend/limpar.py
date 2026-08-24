from apps.courses.models import Course
from apps.notifications.models import Notification
Notification.objects.filter(message__contains="[QA]").delete()
Notification.objects.filter(title__contains="[QA]").delete()
n, _ = Course.objects.filter(title__startswith="[QA]").delete()
print("removidos:", n, "| cursos restantes:", Course.objects.count())
