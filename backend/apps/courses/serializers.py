from django.utils import timezone
from rest_framework import serializers

from .models import Content, Course, CourseProgress


class ContentSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Content
        fields = ["id", "course", "type", "type_display", "file_url", "order"]

    def validate_course(self, course):
        request = self.context.get("request")
        if not request:
            return course
        user = request.user
        if course.company_id != user.company_id:
            raise serializers.ValidationError("Curso não pertence à sua empresa.")
        if not user.is_rh_admin and user.is_sector_leader and course.sector_id != user.sector_id:
            raise serializers.ValidationError("Você só pode gerenciar conteúdo de treinamentos do seu setor.")
        return course


class CourseProgressSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CourseProgress
        fields = ["id", "user", "course", "status", "status_display", "completed_at"]
        read_only_fields = ["id", "user", "course", "completed_at"]

    def update(self, instance, validated_data):
        status = validated_data.get("status", instance.status)
        instance.status = status
        if status == "completed":
            instance.completed_at = timezone.now()
        elif status in ["not_started", "in_progress"]:
            instance.completed_at = None
        instance.save()
        return instance


class CourseSerializer(serializers.ModelSerializer):
    contents = ContentSerializer(many=True, read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    prerequisite_title = serializers.CharField(source="prerequisite.title", read_only=True, default=None)
    user_progress = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "sector",
            "sector_name",
            "position",
            "position_name",
            "target_units",
            "deadline",
            "prerequisite",
            "prerequisite_title",
            "order",
            "contents",
            "user_progress",
            "is_locked",
        ]

    def validate_target_units(self, units):
        """
        Sem isto, dava para endereçar um treinamento a uma unidade de OUTRA
        empresa: ele ficava invisível para todo mundo e o id alheio ficava
        gravado no registro.
        """
        request = self.context.get("request")
        if not request:
            return units
        for unidade in units or []:
            if unidade.company_id != request.user.company_id:
                raise serializers.ValidationError("A unidade não pertence à sua empresa.")
        return units

    def validate(self, attrs):
        request = self.context.get("request")
        if request:
            user = request.user
            company_id = user.company_id
            sector = attrs.get("sector")
            position = attrs.get("position")
            prerequisite = attrs.get("prerequisite")
            if sector and sector.company_id != company_id:
                raise serializers.ValidationError({"sector": "Setor não pertence à sua empresa."})
            if position and position.sector.company_id != company_id:
                raise serializers.ValidationError({"position": "Cargo não pertence à sua empresa."})
            if not user.is_rh_admin and user.is_sector_leader:
                # Líder de setor só cadastra/edita treinamento do próprio setor —
                # nunca geral (sector=None) nem de outro setor.
                effective_sector_id = sector.id if sector else (self.instance.sector_id if self.instance else None)
                if effective_sector_id != user.sector_id:
                    raise serializers.ValidationError(
                        {"sector": "Líderes de setor só podem cadastrar treinamentos do próprio setor."}
                    )
            if prerequisite:
                if prerequisite.company_id != company_id:
                    raise serializers.ValidationError(
                        {"prerequisite": "Pré-requisito não pertence à sua empresa."}
                    )
                if self.instance and prerequisite.id == self.instance.id:
                    raise serializers.ValidationError(
                        {"prerequisite": "Um curso não pode ser pré-requisito de si mesmo."}
                    )
                if self.instance and prerequisite.prerequisite_id == self.instance.id:
                    raise serializers.ValidationError(
                        {"prerequisite": "Ciclo de pré-requisitos não permitido."}
                    )
        return attrs

    def _mapa_de_progresso(self, user):
        """
        {course_id: CourseProgress} do usuário, carregado uma vez só.

        A view pré-carrega em `progresso_do_usuario`; quando não há contexto
        (uso isolado, testes de unidade), monta aqui — ainda numa query, e
        não uma por curso.
        """
        mapa = self.context.get("progresso_do_usuario")
        if mapa is None:
            mapa = {
                p.course_id: p
                for p in CourseProgress.objects.filter(user=user)
            }
            self.context["progresso_do_usuario"] = mapa
        return mapa

    def _progress_for(self, obj, user):
        return self._mapa_de_progresso(user).get(obj.id)

    def get_user_progress(self, obj) -> dict | None:
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None
        progress = self._progress_for(obj, request.user)
        if progress:
            return {
                "status": progress.status,
                "status_display": progress.get_status_display(),
                "completed_at": progress.completed_at,
            }
        return {
            "status": "not_started",
            "status_display": "Não iniciado",
            "completed_at": None,
        }

    def get_is_locked(self, obj) -> bool:
        request = self.context.get("request")
        if not obj.prerequisite_id or not request or not request.user or not request.user.is_authenticated:
            return False
        # Reaproveita o mesmo mapa do progresso: consultar o pre-requisito
        # aqui custava mais uma query POR CURSO da listagem.
        anterior = self._mapa_de_progresso(request.user).get(obj.prerequisite_id)
        return not (anterior and anterior.status == "completed")
