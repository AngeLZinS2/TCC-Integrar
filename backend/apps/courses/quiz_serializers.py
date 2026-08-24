"""
Serializers da avaliação.

Há DOIS conjuntos de propósito:

  - *ForTaking  → o que quem responde recebe. Nunca inclui `is_correct`.
  - *Admin      → o que quem monta o treinamento recebe, com o gabarito.

A separação é em classes distintas, e não num campo condicional, porque um
`if` esquecido em algum caminho vazaria o gabarito inteiro. Classes
separadas tornam o vazamento impossível por construção: o serializer de
resposta simplesmente não tem o campo.
"""

from rest_framework import serializers

from .quiz_models import (
    AttemptAnswer,
    Option,
    Question,
    Quiz,
    QuizAttempt,
)


# ── Para quem responde ──────────────────────────────────────────────────────

class OptionForTakingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        # `is_correct` NÃO está aqui, e não deve ser adicionado.
        fields = ["id", "text", "order"]


class QuestionForTakingSerializer(serializers.ModelSerializer):
    options = OptionForTakingSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "text", "allows_multiple", "order", "options"]


class QuizForTakingSerializer(serializers.ModelSerializer):
    questions = QuestionForTakingSerializer(many=True, read_only=True)
    attempts_left = serializers.SerializerMethodField()
    already_passed = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            "id", "title", "description", "passing_score", "max_attempts",
            "questions", "attempts_left", "already_passed",
        ]

    def get_attempts_left(self, obj) -> int | None:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        return obj.attempts_left_for(request.user)

    def get_already_passed(self, obj) -> bool:
        from . import quiz_services

        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return quiz_services.ja_aprovado(obj, request.user)


# ── Para quem administra ────────────────────────────────────────────────────

class OptionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["id", "text", "is_correct", "order"]


class QuestionAdminSerializer(serializers.ModelSerializer):
    options = OptionAdminSerializer(many=True)

    class Meta:
        model = Question
        fields = ["id", "text", "allows_multiple", "order", "options"]

    def validate_options(self, options):
        if len(options) < 2:
            raise serializers.ValidationError("Uma pergunta precisa de ao menos 2 alternativas.")
        corretas = [o for o in options if o.get("is_correct")]
        if not corretas:
            raise serializers.ValidationError("Marque ao menos uma alternativa correta.")
        return options

    def validate(self, attrs):
        opcoes = attrs.get("options", [])
        corretas = [o for o in opcoes if o.get("is_correct")]
        if not attrs.get("allows_multiple") and len(corretas) > 1:
            raise serializers.ValidationError(
                {
                    "options": (
                        "Só é possível ter mais de uma alternativa correta em "
                        "perguntas de múltipla escolha."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        opcoes = validated_data.pop("options")
        pergunta = Question.objects.create(**validated_data)
        Option.objects.bulk_create(
            [Option(question=pergunta, **dados) for dados in opcoes]
        )
        return pergunta

    def update(self, instance, validated_data):
        opcoes = validated_data.pop("options", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()

        if opcoes is not None:
            # Substitui o conjunto inteiro: manter alternativas antigas
            # deixaria respostas passadas apontando para um gabarito que já
            # não vale.
            instance.options.all().delete()
            Option.objects.bulk_create(
                [Option(question=instance, **dados) for dados in opcoes]
            )
        return instance


class QuizAdminSerializer(serializers.ModelSerializer):
    questions = QuestionAdminSerializer(many=True, read_only=True)
    question_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id", "course", "title", "description", "passing_score",
            "max_attempts", "is_active", "questions", "question_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "course", "created_at", "updated_at"]

    def validate_passing_score(self, nota):
        if not 0 <= nota <= 100:
            raise serializers.ValidationError("A nota mínima deve estar entre 0 e 100.")
        return nota


# ── Tentativas e resultado ──────────────────────────────────────────────────

class SubmitAnswersSerializer(serializers.Serializer):
    """
    Respostas enviadas: {"answers": {"<question_id>": [option_id, ...]}}.

    As chaves chegam como texto no JSON e são convertidas para int aqui,
    para o service comparar com os ids do banco sem depender do formato.
    """

    answers = serializers.DictField(
        child=serializers.ListField(child=serializers.IntegerField(), allow_empty=True)
    )

    def validate_answers(self, respostas):
        convertidas = {}
        for chave, valor in respostas.items():
            try:
                convertidas[int(chave)] = valor
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"Identificador inválido: {chave}.")
        return convertidas


class AttemptAnswerResultSerializer(serializers.ModelSerializer):
    """
    Resultado por pergunta.

    Diz SE acertou, nunca QUAL era a certa — do contrário a primeira
    tentativa entregaria o gabarito para a segunda.
    """

    question_text = serializers.CharField(source="question.text", read_only=True)

    class Meta:
        model = AttemptAnswer
        fields = ["id", "question", "question_text", "is_correct"]
        read_only_fields = fields


class QuizAttemptSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="quiz.course.title", read_only=True)
    passing_score = serializers.IntegerField(source="quiz.passing_score", read_only=True)
    attempts_left = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = [
            "id", "attempt_number", "score", "correct_count", "question_count",
            "passed", "started_at", "finished_at",
            "course_title", "passing_score", "attempts_left",
        ]
        read_only_fields = fields

    def get_attempts_left(self, obj) -> int | None:
        return obj.quiz.attempts_left_for(obj.user)


class QuizAttemptResultSerializer(QuizAttemptSerializer):
    answers = AttemptAnswerResultSerializer(many=True, read_only=True)

    class Meta(QuizAttemptSerializer.Meta):
        fields = QuizAttemptSerializer.Meta.fields + ["answers"]
        read_only_fields = fields
