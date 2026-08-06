from django.db import transaction
from .models import GovernanceProfile, TrustLog

@transaction.atomic
def process_governance_event(user, event_type, trust_impact, loyalty_impact=0, reference_id=None, description=""):
    """
    Safely applies trust/loyalty changes, evaluates warning thresholds, 
    and writes an immutable audit log.
    """
    # 1. Lock the row for update to prevent race conditions from concurrent requests
    profile = GovernanceProfile.objects.select_for_update().get(user=user)

    # 2. Apply the mathematical impact
    profile.trust_score += trust_impact
    profile.loyalty_points += loyalty_impact
    
    # Pre-calculate the bounded score to determine status correctly
    bounded_score = max(0, min(100, profile.trust_score))

    # 3. Warning Engine: Adjust account status based on the new score
    # SUSPENDED is usually a manual admin action, so we automate up to RESTRICTED
    if profile.status != GovernanceProfile.AccountStatus.SUSPENDED:
        if bounded_score >= 50:
            profile.status = GovernanceProfile.AccountStatus.ACTIVE
        elif bounded_score >= 25:
            profile.status = GovernanceProfile.AccountStatus.WARNING
        else:
            profile.status = GovernanceProfile.AccountStatus.RESTRICTED

    # 4. Save profile (which automatically enforces the 0-100 limits via the model)
    profile.save()

    # 5. Write the immutable ledger entry
    log = TrustLog.objects.create(
        profile=profile,
        event_type=event_type,
        trust_impact=trust_impact,
        loyalty_impact=loyalty_impact,
        reference_id=str(reference_id) if reference_id else "",
        description=description
    )

    return profile, log