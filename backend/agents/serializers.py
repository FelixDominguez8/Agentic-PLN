from rest_framework import serializers


class BranchCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class UploadPDFSerializer(serializers.Serializer):
    branch = serializers.CharField(max_length=100)
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False
    )