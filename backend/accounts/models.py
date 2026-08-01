from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from decimal import Decimal
import uuid
from django.conf import settings
import secrets
from django.utils.crypto import get_random_string

class CovalentUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address must be provided to create an account.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

def generate_public_id():
    return f"CVL-{get_random_string(6).upper()}"

class CovalentUser(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        BUYER = 'BUYER', 'Buyer'
        VENDOR = 'VENDOR', 'Vendor'
        LAWYER = 'LAWYER', 'Lawyer'


    RISK_LEVELS = [
        ("LOW", "Low Risk"),
        ("MEDIUM", "Medium Risk"),
        ("HIGH", "High Risk"),
        ("CRITICAL", "Critical"),
    ]

    # Core Identifiers
    email = models.EmailField(unique=True, max_length=255, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True)
    public_id = models.CharField(
        max_length=15, 
        unique=True, 
        default=generate_public_id,
        editable=False
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.BUYER
    )
    nin = models.CharField(max_length=11, unique=True, null=True, blank=True)

    # KYC & Paystack Integration
    nin = models.CharField(max_length=11, unique=True, null=True, blank=True, help_text="National Identity Number")
    is_kyc_verified = models.BooleanField(default=False)
    paystack_customer_code = models.CharField(max_length=100, unique=True, null=True, blank=True)
    paystack_subaccount_code = models.CharField(max_length=100, null=True, blank=True, help_text="Vendor split payout subaccount")

    # Trust & Reputation Engine
    trust_score = models.IntegerField(default=70)
    fraud_risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, default="LOW")
    completed_contracts = models.PositiveIntegerField(default=0)
    disputes_count = models.PositiveIntegerField(default=0)

    # Django Permissions & Timestamps
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_lawyer = models.BooleanField(default=False, help_text="Designates user as a verified arbitration reviewer")
    lawyer_cases_resolved = models.IntegerField(default=0)

    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=10, blank=True, null=True)
    account_name = models.CharField(max_length=150, blank=True, null=True)

    objects = CovalentUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.email} ({self.get_full_name()}) - Trust: {self.trust_score}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_trust_tier_display(self):
        """Returns the public-facing reputation tier instead of the raw score."""
        if self.trust_score >= 85:
            return "🟢 Excellent"
        elif self.trust_score >= 70:
            return "🟡 Good"
        elif self.trust_score >= 50:
            return "🟠 Watchlist"
        return "🔴 Restricted"

    def is_eligible_for_escrow(self):
        """
        Evaluates if the user meets the compliance and risk criteria
        required to participate in escrow smart contracts.
        """
        # Block if KYC is incomplete
        if not self.is_kyc_verified:
            return False
            
        # Block if the automated fraud risk engine flagged them as HIGH
        if self.fraud_risk_level == 'HIGH':
            return False
            
        # Block if their reputation score dropped below the critical threshold of 50
        if self.trust_score < 50:
            return False
            
        # If they pass all checks, they are good to go
        return True

    def save(self, *args, **kwargs):
        # Generate CVL-XXXXX public ID on first creation
        if not self.public_id:
            while True:
                new_id = f"CVL-{get_random_string(6).upper()}"
                if not CovalentUser.objects.filter(public_id=new_id).exists():
                    self.public_id = new_id
                    break
        super().save(*args, **kwargs)


class Wallet(models.Model):
    user = models.OneToOneField(CovalentUser, on_delete=models.CASCADE, related_name="wallet")
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    locked_escrow_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    penalty_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet - {self.user.email} (₦{self.available_balance})"
    

class MerchantAPIKey(models.Model):
    user = models.ForeignKey(CovalentUser, on_delete=models.CASCADE, related_name="api_keys")
    key = models.CharField(max_length=64, unique=True, default=secrets.token_urlsafe)
    name = models.CharField(max_length=100) # e.g., "Main Website" or "Mobile App"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.user.email}"


class Contract(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("AWAITING_FUNDING", "Awaiting Funding"),
        ("FUNDED", "Funded & Active"),
        ("DELIVERED", "Delivered - Awaiting Inspection"),
        ("DISPUTED", "In Dispute"),                       
        ("RELEASED", "Completed"),
    ]
    contract_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_contracts")
    vendor_email = models.EmailField()
    item_title = models.CharField(max_length=255)
    item_description = models.TextField()
    item_amount = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_escrow = models.DecimalField(max_digits=12, decimal_places=2, blank=True)
    plain_language_summary = models.TextField()
    
    # 🆕 Inspection Window Config
    inspection_period_hours = models.PositiveIntegerField(default=24)
    delivered_at = models.DateTimeField(null=True, blank=True)
    auto_release_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="DRAFT")
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total_escrow = Decimal(str(self.item_amount)) + Decimal(str(self.delivery_fee))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item_title} ({self.contract_id})"


class Dispute(models.Model):
    STATUS_CHOICES = [
        ("OPEN", "Open - Awaiting Evidence"),
        ("IN_REVIEW", "Under Anonymous Review"),
        ("RESOLVED_BUYER", "Resolved - Refund Buyer"),
        ("RESOLVED_VENDOR", "Resolved - Release to Vendor"),
    ]
    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, related_name="dispute")
    initiator = models.ForeignKey(CovalentUser, on_delete=models.CASCADE, related_name="initiated_disputes")
    reason = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="OPEN")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dispute #{self.id} - {self.contract.item_title}"


class DisputeEvidence(models.Model):
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name="evidence_files")
    uploader = models.ForeignKey(CovalentUser, on_delete=models.CASCADE)
    original_file = models.FileField(upload_to="evidence/raw/")
    scrubbed_file = models.FileField(upload_to="evidence/clean/", blank=True, null=True)
    file_type = models.CharField(max_length=10, choices=[("IMAGE", "Image"), ("VIDEO", "Video")])
    is_processed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class ArbitrationVote(models.Model):
    VOTE_CHOICES = [
        ("BUYER", "Rule for Buyer (Refund Escrow)"),
        ("VENDOR", "Rule for Vendor (Release Escrow)"),
    ]
    dispute = models.ForeignKey('Dispute', on_delete=models.CASCADE, related_name="votes")
    lawyer = models.ForeignKey(CovalentUser, on_delete=models.CASCADE)
    ruling = models.CharField(max_length=10, choices=VOTE_CHOICES)
    legal_justification = models.TextField(help_text="Brief explanation of the ruling based on contract terms")
    voted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent a lawyer from voting twice on the same dispute
        unique_together = ('dispute', 'lawyer')


class PlatformAuditLog(models.Model):
    user = models.ForeignKey(CovalentUser, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action_type = models.CharField(max_length=100)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email if self.user else 'System'} | {self.action_type} | {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class NotificationPreferences(models.Model):
    user = models.OneToOneField(CovalentUser, on_delete=models.CASCADE, related_name='notification_preferences')
    email_alerts = models.BooleanField(default=True)
    sms_alerts = models.BooleanField(default=False)