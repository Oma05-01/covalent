from django.test import TestCase
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from accounts.models import AdminProfile, AdminRole
from accounts.permissions import IsSuperAdmin, IsRiskOfficer, IsDisputeManager

User = get_user_model()

class AdminPermissionsTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        
        # Standard User
        self.regular_user = User.objects.create_user(email="user@example.com", password="pw")
        
        # Admins
        self.super_admin = User.objects.create_user(email="super@example.com", password="pw")
        AdminProfile.objects.create(user=self.super_admin, role=AdminRole.SUPER_ADMIN, is_active=True)
        
        self.risk_admin = User.objects.create_user(email="risk@example.com", password="pw")
        AdminProfile.objects.create(user=self.risk_admin, role=AdminRole.RISK_OFFICER, is_active=True)
        
        self.dispute_admin = User.objects.create_user(email="dispute@example.com", password="pw")
        AdminProfile.objects.create(user=self.dispute_admin, role=AdminRole.DISPUTE_MANAGER, is_active=True)
        
        # Inactive Admin (Fired or suspended)
        self.inactive_admin = User.objects.create_user(email="inactive@example.com", password="pw")
        AdminProfile.objects.create(user=self.inactive_admin, role=AdminRole.SUPER_ADMIN, is_active=False)

    def test_is_super_admin_blocks_lower_tiers(self):
        request = self.factory.get('/')
        
        request.user = self.super_admin
        self.assertTrue(IsSuperAdmin().has_permission(request, None))
        
        request.user = self.risk_admin
        self.assertFalse(IsSuperAdmin().has_permission(request, None))

    def test_is_risk_officer_allows_super_admin_but_blocks_dispute_manager(self):
        request = self.factory.get('/')
        
        # Exact role match
        request.user = self.risk_admin
        self.assertTrue(IsRiskOfficer().has_permission(request, None))
        
        # Super Admin inheritance
        request.user = self.super_admin
        self.assertTrue(IsRiskOfficer().has_permission(request, None)) 
        
        # Wrong Admin Tier
        request.user = self.dispute_admin
        self.assertFalse(IsRiskOfficer().has_permission(request, None)) 
        
    def test_base_admin_blocks_inactive_and_regular_users(self):
        request = self.factory.get('/')
        
        request.user = self.regular_user
        self.assertFalse(IsSuperAdmin().has_permission(request, None))
        
        request.user = self.inactive_admin
        self.assertFalse(IsSuperAdmin().has_permission(request, None))