from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at']
        # Protect the core data from being altered by PUT/PATCH requests
        read_only_fields = ['id', 'notification_type', 'title', 'message', 'created_at']