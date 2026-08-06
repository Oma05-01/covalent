from rest_framework import permissions
from .models import GovernanceProfile

class IsAccountInGoodStanding(permissions.BasePermission):
    """
    Allows access only if the user's governance status is ACTIVE or WARNING.
    RESTRICTED and SUSPENDED accounts are blocked.
    """
    message = "Your account is currently restricted due to a low trust score. You cannot create new contracts."

    def has_permission(self, request, view):
        # Always deny anonymous users
        if not request.user or not request.user.is_authenticated:
            return False
            
        try:
            profile = request.user.governance_profile
        except GovernanceProfile.DoesNotExist:
            return False

        # Block restricted and suspended users
        if profile.status in [
            GovernanceProfile.AccountStatus.RESTRICTED, 
            GovernanceProfile.AccountStatus.SUSPENDED
        ]:
            return False

        return True