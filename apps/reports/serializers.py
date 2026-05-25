from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.full_name', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ['id', 'type', 'name', 'parameters', 'status', 'file', 'file_url', 'generated_by', 'generated_by_name', 'created_at', 'completed_at']
        read_only_fields = ['status', 'file', 'generated_by', 'created_at', 'completed_at']

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class ReportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['type', 'name', 'parameters']
