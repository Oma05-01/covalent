from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(mixins.ListModelMixin, 
                          mixins.RetrieveModelMixin, 
                          viewsets.GenericViewSet):
    
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Strict isolation: Users can only query their own notifications
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['patch'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Marks a specific notification as read."""
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'status': 'Notification marked as read'})

    @action(detail=False, methods=['patch'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """Bulk updates all unread notifications for the user."""
        unread_notifications = self.get_queryset().filter(is_read=False)
        updated_count = unread_notifications.update(is_read=True)
        return Response({
            'status': 'success', 
            'message': f'{updated_count} notifications marked as read'
        })