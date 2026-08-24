from rest_framework import serializers


class CourseStatusItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    status = serializers.CharField()
    completed_at = serializers.DateTimeField(allow_null=True)
    due_date = serializers.DateField(allow_null=True)
    is_overdue = serializers.BooleanField()


class ChecklistStatusItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    deadline = serializers.CharField()
    completed = serializers.BooleanField()
    completed_at = serializers.DateTimeField(allow_null=True)
    due_date = serializers.DateField(allow_null=True)
    is_overdue = serializers.BooleanField()


class CollaboratorStatsSerializer(serializers.Serializer):
    """Linha de progresso de um colaborador, usada na lista e como base do detalhe."""

    id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    sector_name = serializers.CharField(allow_null=True)
    position_name = serializers.CharField(allow_null=True)
    is_active = serializers.BooleanField()
    is_sector_leader = serializers.BooleanField()
    last_login = serializers.DateTimeField(allow_null=True)
    hire_date = serializers.DateField(allow_null=True)
    courses_total = serializers.IntegerField()
    courses_completed = serializers.IntegerField()
    courses_percent = serializers.IntegerField()
    checklist_total = serializers.IntegerField()
    checklist_completed = serializers.IntegerField()
    checklist_percent = serializers.IntegerField()
    overall_percent = serializers.IntegerField()
    overdue_count = serializers.IntegerField()


class CollaboratorDetailSerializer(CollaboratorStatsSerializer):
    courses = CourseStatusItemSerializer(many=True)
    checklist_items = ChecklistStatusItemSerializer(many=True)


class CourseStatusDistributionSerializer(serializers.Serializer):
    not_started = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed = serializers.IntegerField()


class SectorBreakdownSerializer(serializers.Serializer):
    sector_id = serializers.IntegerField()
    sector_name = serializers.CharField()
    collaborators = serializers.IntegerField()
    avg_course_percent = serializers.FloatField()
    avg_checklist_percent = serializers.FloatField()


class DashboardOverviewSerializer(serializers.Serializer):
    # Quadro de pessoal
    total_collaborators = serializers.IntegerField()
    active_collaborators = serializers.IntegerField()
    inactive_collaborators = serializers.IntegerField()
    hired_last_30_days = serializers.IntegerField()

    # Estágio da integração — categorias exclusivas, somam o total
    onboarding_completed = serializers.IntegerField()
    onboarding_in_progress = serializers.IntegerField()
    onboarding_overdue = serializers.IntegerField()
    onboarding_not_started = serializers.IntegerField()
    onboarding_percent = serializers.FloatField()

    active_last_30_days = serializers.IntegerField()
    never_logged_in = serializers.IntegerField()
    avg_course_completion_percent = serializers.FloatField()
    avg_checklist_completion_percent = serializers.FloatField()
    fully_completed_count = serializers.IntegerField()
    overdue_collaborators_count = serializers.IntegerField()
    course_status_distribution = CourseStatusDistributionSerializer()
    by_sector = SectorBreakdownSerializer(many=True)
