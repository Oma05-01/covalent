from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()

class NotificationAPITests(APITestCase):
    def setUp(self):
        # 1. Create two separate users to test data isolation
        self.user1 = User.objects.create_user(email="user1@example.com", password="pw")
        self.user2 = User.objects.create_user(email="user2@example.com", password="pw")

        # 2. Create notifications for user1
        self.notif1_user1 = Notification.objects.create(
            user=self.user1,
            title="Security Alert",
            message="Suspicious login attempt.",
            notification_type=Notification.NotificationType.SECURITY_ALERT
        )
        self.notif2_user1 = Notification.objects.create(
            user=self.user1,
            title="Account Alert",
            message="Your trust score has updated.",
            notification_type=Notification.NotificationType.ACCOUNT_UPDATE
        )

        # 3. Create a notification for user2
        self.notif1_user2 = Notification.objects.create(
            user=self.user2,
            title="Escrow Update",
            message="Funds released.",
            notification_type=Notification.NotificationType.ESCROW_ALERT
        )

    def test_user_can_only_see_their_own_notifications(self):
        """Users should only receive their own notifications in the list endpoint."""
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('notifications:notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Handle paginated vs non-paginated responses gracefully
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        
        # User 1 should only see their 2 notifications
        self.assertEqual(len(data), 2)
        
        # Verify User 2's notification ID is completely absent from the results
        notif_ids = [str(n['id']) for n in data]
        self.assertIn(str(self.notif1_user1.id), notif_ids)
        self.assertNotIn(str(self.notif1_user2.id), notif_ids)

    def test_user_cannot_retrieve_others_notification(self):
        """Attempting to access someone else's notification directly should return a 404."""
        self.client.force_authenticate(user=self.user1)
        
        # User 1 tries to access User 2's notification
        url = reverse('notifications:notification-detail', kwargs={'pk': self.notif1_user2.id})
        response = self.client.get(url)
        
        # Because get_queryset() filters by request.user, DRF will throw a 404 Not Found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_single_notification_as_read(self):
        """The custom mark-read action should update the is_read status to True."""
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('notifications:notification-mark-read', kwargs={'pk': self.notif1_user1.id})
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify the database state changed for this notification
        self.notif1_user1.refresh_from_db()
        self.assertTrue(self.notif1_user1.is_read)
        
        # Verify the other notification remains untouched
        self.notif2_user1.refresh_from_db()
        self.assertFalse(self.notif2_user1.is_read)

    def test_mark_all_notifications_as_read(self):
        """The mark-all-read action should bulk update all unread notifications for the user."""
        self.client.force_authenticate(user=self.user1)
        
        url = reverse('notifications:notification-mark-all-read')
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify both of user 1's notifications are now read
        self.notif1_user1.refresh_from_db()
        self.notif2_user1.refresh_from_db()
        self.assertTrue(self.notif1_user1.is_read)
        self.assertTrue(self.notif2_user1.is_read)
        
        # Critically verify that user 2's notification was NOT accidentally marked as read
        self.notif1_user2.refresh_from_db()
        self.assertFalse(self.notif1_user2.is_read)