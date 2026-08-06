# accounts/permissions.py
from rest_framework.permissions import BasePermission
from rest_framework import permissions
from .models import AdminRole

class BaseAdminPermission(permissions.BasePermission):
    """
    Base permission that blocks anyone who isn't an active admin.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'admin_profile') and 
            request.user.admin_profile.is_active
        )

class IsSuperAdmin(BaseAdminPermission):
    """Only Super Admins can access (e.g., for promoting other admins)."""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.admin_profile.role == AdminRole.SUPER_ADMIN

class IsRiskOfficer(BaseAdminPermission):
    """Can suspend users and edit trust scores."""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        allowed_roles = [AdminRole.RISK_OFFICER, AdminRole.SUPER_ADMIN]
        return request.user.admin_profile.role in allowed_roles

class IsDisputeManager(BaseAdminPermission):
    """Can manually override and resolve contracts."""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        allowed_roles = [AdminRole.DISPUTE_MANAGER, AdminRole.SUPER_ADMIN]
        return request.user.admin_profile.role in allowed_roles
    

class IsLawyer(BasePermission):
    """Allows access only to users with the LAWYER role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'LAWYER')

class IsVendor(BasePermission):
    """Allows access only to users with the VENDOR role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'VENDOR')

class IsBuyer(BasePermission):
    """Allows access only to users with the BUYER role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'BUYER')

class IsKycVerifiedAndSafe(BasePermission):
    """
    Allows access only if the user has passed KYC, 
    has a low fraud risk, and maintains a high trust score.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.is_eligible_for_escrow()