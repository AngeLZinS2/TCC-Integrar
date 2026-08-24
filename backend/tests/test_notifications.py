import pytest
from apps.checklist.models import ChecklistItem, ChecklistProgress
from apps.courses.models import Course, CourseProgress
from apps.materials.models import Material
from apps.notifications.models import Notification
from apps.sectors.models import Position, Sector


@pytest.fixture
def sector_ti(db, company):
    return Sector.objects.create(name="TI", company=company)


@pytest.fixture
def sector_rh(db, company):
    return Sector.objects.create(name="RH", company=company)


def titles_for(user):
    return list(Notification.objects.filter(user=user).values_list("title", flat=True))


@pytest.mark.django_db
class TestWelcomeNotification:
    def test_new_colaborador_gets_welcome(self, django_user_model, company):
        user = django_user_model.objects.create_user(
            email="novo@example.com", full_name="Novo", password="senha@123",
            role="colaborador", company=company,
        )
        assert "Bem-vindo(a) ao time!" in titles_for(user)

    def test_rh_admin_does_not_get_welcome(self, rh_admin_user):
        assert titles_for(rh_admin_user) == []

    def test_owner_does_not_get_welcome(self, owner_user):
        assert titles_for(owner_user) == []


@pytest.mark.django_db
class TestCourseCompletionNotification:
    def test_completing_course_notifies(self, colaborador_user, company):
        course = Course.objects.create(title="Curso A", company=company, order=1)
        Notification.objects.filter(user=colaborador_user).delete()

        progress = CourseProgress.objects.create(
            user=colaborador_user, course=course, status="in_progress"
        )
        assert "Treinamento concluído" not in titles_for(colaborador_user)

        progress.status = "completed"
        progress.save()
        assert "Treinamento concluído" in titles_for(colaborador_user)

    def test_resaving_completed_does_not_duplicate(self, colaborador_user, company):
        course = Course.objects.create(title="Curso A", company=company, order=1)
        progress = CourseProgress.objects.create(
            user=colaborador_user, course=course, status="completed"
        )
        progress.save()
        progress.save()

        count = Notification.objects.filter(
            user=colaborador_user, title="Treinamento concluído"
        ).count()
        assert count == 1

    def test_completing_whole_track_notifies(self, colaborador_user, company):
        course = Course.objects.create(title="Único", company=company, order=1)
        CourseProgress.objects.create(
            user=colaborador_user, course=course, status="completed"
        )
        assert "Trilha de treinamentos concluída!" in titles_for(colaborador_user)

    def test_partial_track_does_not_notify_completion(self, colaborador_user, company):
        c1 = Course.objects.create(title="Um", company=company, order=1)
        Course.objects.create(title="Dois", company=company, order=2)
        CourseProgress.objects.create(user=colaborador_user, course=c1, status="completed")
        assert "Trilha de treinamentos concluída!" not in titles_for(colaborador_user)

    def test_completing_prerequisite_notifies_unlock(self, colaborador_user, company):
        base = Course.objects.create(title="Base", company=company, order=1)
        Course.objects.create(title="Avançado", company=company, order=2, prerequisite=base)

        CourseProgress.objects.create(user=colaborador_user, course=base, status="completed")
        assert "Novo treinamento desbloqueado" in titles_for(colaborador_user)


@pytest.mark.django_db
class TestChecklistCompletionNotification:
    def test_completing_all_items_notifies(self, colaborador_user, company):
        item = ChecklistItem.objects.create(
            title="Assinar NDA", company=company, deadline="day1", order=1
        )
        ChecklistProgress.objects.create(user=colaborador_user, item=item, completed=True)
        assert "Checklist de integração concluído!" in titles_for(colaborador_user)

    def test_partial_checklist_does_not_notify(self, colaborador_user, company):
        i1 = ChecklistItem.objects.create(
            title="Item 1", company=company, deadline="day1", order=1
        )
        ChecklistItem.objects.create(
            title="Item 2", company=company, deadline="day1", order=2
        )
        ChecklistProgress.objects.create(user=colaborador_user, item=i1, completed=True)
        assert "Checklist de integração concluído!" not in titles_for(colaborador_user)

    def test_unchecking_does_not_notify(self, colaborador_user, company):
        item = ChecklistItem.objects.create(
            title="Item", company=company, deadline="day1", order=1
        )
        progress = ChecklistProgress.objects.create(
            user=colaborador_user, item=item, completed=False
        )
        assert "Checklist de integração concluído!" not in titles_for(colaborador_user)
        progress.completed = True
        progress.save()
        assert "Checklist de integração concluído!" in titles_for(colaborador_user)


@pytest.mark.django_db
class TestNewContentNotification:
    def test_new_general_course_notifies_all_colaboradores(self, colaborador_user, company):
        Notification.objects.all().delete()
        Course.objects.create(title="Geral", company=company, order=1)
        assert "Novo treinamento disponível" in titles_for(colaborador_user)

    def test_new_sector_course_notifies_only_that_sector(
        self, colaborador_user, company, sector_ti, sector_rh
    ):
        colaborador_user.sector = sector_ti
        colaborador_user.save()
        Notification.objects.all().delete()

        Course.objects.create(title="Só RH", company=company, sector=sector_rh, order=1)
        assert "Novo treinamento disponível" not in titles_for(colaborador_user)

        Course.objects.create(title="Só TI", company=company, sector=sector_ti, order=2)
        assert "Novo treinamento disponível" in titles_for(colaborador_user)

    def test_new_course_does_not_notify_other_company(
        self, colaborador_user, django_user_model
    ):
        from apps.companies.models import Company

        other = Company.objects.create(name="Outra")
        Notification.objects.all().delete()
        Course.objects.create(title="Da outra empresa", company=other, order=1)
        assert titles_for(colaborador_user) == []

    def test_new_course_respects_position_scope(self, colaborador_user, company, sector_ti):
        pos_a = Position.objects.create(name="Cargo A", sector=sector_ti)
        pos_b = Position.objects.create(name="Cargo B", sector=sector_ti)
        colaborador_user.sector = sector_ti
        colaborador_user.position = pos_a
        colaborador_user.save()
        Notification.objects.all().delete()

        Course.objects.create(
            title="Para cargo B", company=company, sector=sector_ti, position=pos_b, order=1
        )
        assert titles_for(colaborador_user) == []

    def test_new_material_notifies(self, colaborador_user, company):
        Notification.objects.all().delete()
        Material.objects.create(
            title="Manual", file_url="https://example.com/a.pdf", company=company
        )
        assert "Novo material disponível" in titles_for(colaborador_user)

    def test_editing_course_does_not_renotify(self, colaborador_user, company):
        course = Course.objects.create(title="Curso", company=company, order=1)
        Notification.objects.all().delete()
        course.title = "Curso editado"
        course.save()
        assert titles_for(colaborador_user) == []


@pytest.mark.django_db
class TestNotificationApi:
    def test_colaborador_sees_own_notifications(self, api_client, colaborador_user, company):
        Course.objects.create(title="Novo", company=company, order=1)
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get("/api/v1/notifications/")
        assert response.status_code == 200
        assert len(response.data["results"]) > 0

    def test_mark_all_read(self, api_client, colaborador_user, company):
        Course.objects.create(title="Novo", company=company, order=1)
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.post("/api/v1/notifications/mark-all-read/")
        assert response.status_code == 200
        assert not Notification.objects.filter(user=colaborador_user, read=False).exists()

    def test_does_not_see_other_users_notifications(
        self, api_client, colaborador_user, django_user_model, company
    ):
        other = django_user_model.objects.create_user(
            email="outro@example.com", full_name="Outro", password="senha@123",
            role="colaborador", company=company,
        )
        api_client.force_authenticate(user=colaborador_user)
        response = api_client.get("/api/v1/notifications/")
        ids = {n["id"] for n in response.data["results"]}
        other_ids = set(
            Notification.objects.filter(user=other).values_list("id", flat=True)
        )
        assert ids.isdisjoint(other_ids)
