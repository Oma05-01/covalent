# accounts/permissions.py
from rest_framework.permissions import BasePermission

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
        # This calls the method we built in the previous step!
        return request.user.is_eligible_for_escrow()