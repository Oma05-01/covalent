import hashlib
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

class GovernanceProfile(models.Model):
    class AccountStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        WARNING = 'WARNING', 'Warning (At Risk)'
        RESTRICTED = 'RESTRICTED', 'Restricted (Cannot create new contracts)'
        SUSPENDED = 'SUSPENDED', 'Suspended (Locked)'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='governance_profile'
    )
    
    # Trust Score: Public-facing metric determining reliability
    trust_score = models.IntegerField(
        default=50, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Public reputation score. Bounded between 0 and 100."
    )
    
    # Loyalty Points: Gamification for volume/clean transactions
    loyalty_points = models.PositiveIntegerField(
        default=0,
        help_text="Accrues over time for successful transactions."
    )
    
    # Fraud Score: Internal-only metric, totally detached from public actions
    fraud_risk_score = models.IntegerField(
        default=0,
        help_text="Hidden risk metric. High score = high risk."
    )
    
    status = models.CharField(
        max_length=20, 
        choices=AccountStatus.choices, 
        default=AccountStatus.ACTIVE
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Business Rule: Enforce Trust bounds at the database layer
        if self.trust_score > 100:
            self.trust_score = 100
        elif self.trust_score < 0:
            self.trust_score = 0
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Governance: {self.user.email} (Trust: {self.trust_score})"


class TrustLog(models.Model):
    """
    Immutable ledger of all trust and loyalty changes.
    Vital for resolving user complaints about score drops.
    """
    class EventType(models.TextChoices):
        CONTRACT_SUCCESS = 'CONTRACT_SUCCESS', 'Successful Contract'
        DISPUTE_LOST = 'DISPUTE_LOST', 'Lost Arbitration Dispute'
        DISPUTE_WON = 'DISPUTE_WON', 'Won Arbitration Dispute'
        PLATFORM_VIOLATION = 'PLATFORM_VIOLATION', 'TOS Violation'
        MANUAL_ADJUSTMENT = 'MANUAL_ADJUSTMENT', 'Admin Manual Adjustment'

    profile = models.ForeignKey(GovernanceProfile, on_delete=models.CASCADE, related_name='logs')
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    
    trust_impact = models.IntegerField(help_text="e.g., +5 or -15")
    loyalty_impact = models.IntegerField(default=0)
    
    # The ID of the contract/dispute that caused this, stored as a string to avoid hard coupling
    reference_id = models.CharField(max_length=100, blank=True, null=True) 
    description = models.CharField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.user.email} | {self.event_type} | Trust: {self.trust_impact}"


class DeviceFingerprint(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    fingerprint_hash = models.CharField(max_length=64, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'fingerprint_hash')

    def __str__(self):
        return f"{self.user.email} - {self.fingerprint_hash[:8]}"

    @staticmethod
    def generate_hash(ip_address, user_agent):
        """Creates a consistent SHA-256 hash from request headers."""
        raw_string = f"{ip_address}_{user_agent}".encode('utf-8')
        return hashlib.sha256(raw_string).hexdigest()

