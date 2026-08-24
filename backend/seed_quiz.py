from apps.companies.models import Company
from apps.courses.models import Course
from apps.courses.quiz_models import Option, Question, Quiz

c = Company.objects.first()
curso, _ = Course.objects.get_or_create(
    title="[QA] LGPD na prática", company=c, defaults={"order": 99}
)
Quiz.objects.filter(course=curso).delete()
q = Quiz.objects.create(course=curso, title="Avaliação LGPD", passing_score=70, max_attempts=2)

p1 = Question.objects.create(quiz=q, text="Dado pessoal sensível inclui?", order=1)
Option.objects.create(question=p1, text="Dados de saúde", is_correct=True, order=1)
Option.objects.create(question=p1, text="Nome da empresa", is_correct=False, order=2)

p2 = Question.objects.create(quiz=q, text="Titular pode pedir exclusão?", order=2)
Option.objects.create(question=p2, text="Sim", is_correct=True, order=1)
Option.objects.create(question=p2, text="Não", is_correct=False, order=2)

print("COURSE_ID", curso.id, "COMPANY", c.name)
