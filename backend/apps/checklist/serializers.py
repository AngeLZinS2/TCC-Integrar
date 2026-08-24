from rest_framework import serializers

from .models import ChecklistItem, ChecklistProgress


class ChecklistProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistProgress
        fields = ["id", "user", "item", "completed", "completed_at"]
        read_only_fields = ["id", "user", "item", "completed_at"]


class ChecklistItemSerializer(serializers.ModelSerializer):
    deadline_display = serializers.CharField(source="get_deadline_display", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    user_progress = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistItem
        fields = [
            "id",
            "title",
            "deadline",
            "deadline_display",
            "sector",
            "sector_name",
            "order",
            "user_progress",
        ]

    def validate_sector(self, sector):
        request = self.context.get("request")
        if request and sector and sector.company_id != request.user.company_id:
            raise serializers.ValidationError("Setor não pertence à sua empresa.")
        return sector

    def get_user_progress(self, obj) -> dict:
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return {"completed": False, "completed_at": None}
        progress = ChecklistProgress.objects.filter(user=request.user, item=obj).first()
        if progress:
            return {
                "completed": progress.completed,
                "completed_at": progress.completed_at,
            }
        return {"completed": False, "completed_at": None}
