from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import AdminProfile, AdminRole

User = get_user_model()

class AdminDashboardTests(APITestCase):
    def setUp(self):
        # Create an Admin
        self.admin_user = User.objects.create_user(email="admin@example.com", password="pw", is_staff=True)
        AdminProfile.objects.create(user=self.admin_user, role=AdminRole.SUPER_ADMIN, is_active=True)        

        # Create test users
        self.user1 = User.objects.create_user(email="active_vendor@example.com", password="pw", role="VENDOR", is_active=True)
        self.user2 = User.objects.create_user(email="suspended_buyer@example.com", password="pw", role="BUYER", is_active=False)
        self.user3 = User.objects.create_user(email="active_buyer@example.com", password="pw", role="BUYER", is_active=True)

        self.url = reverse('admin_users')

    def test_admin_can_list_users_with_pagination(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 4) # 3 test users + 1 admin

    def test_admin_can_filter_suspended_users(self):
        self.client.force_authenticate(user=self.admin_user)
        
        # Test Exact Match Filter: ?is_active=False
        response = self.client.get(f"{self.url}?is_active=False")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['email'], "suspended_buyer@example.com")

    def test_admin_can_search_by_email(self):
        self.client.force_authenticate(user=self.admin_user)
        
        # Test Search Filter: ?search=vendor
        response = self.client.get(f"{self.url}?search=vendor")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['email'], "active_vendor@example.com")
        
    def test_non_admins_are_blocked(self):
        self.client.force_authenticate(user=self.user1) # Regular vendor
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)