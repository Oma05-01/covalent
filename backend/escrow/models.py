from django.db import models
from django.conf import settings

class DisputeEvidence(models.Model):
    FILE_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('DOCUMENT', 'Document'),
        ('VIDEO', 'Video'),
        ('OTHER', 'Other'),
    ]

    dispute = models.ForeignKey(
        'accounts.Dispute', 
        on_delete=models.CASCADE, 
        related_name='evidence_items'
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='uploaded_evidence'
    )
    original_file = models.FileField(upload_to='disputes/raw_evidence/')
    scrubbed_file = models.FileField(upload_to='disputes/clean_evidence/', null=True, blank=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='IMAGE')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence #{self.id} for Dispute #{self.dispute_id} by {self.uploader.email}"


class ArbitratorAssignment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Response'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined')
    ]
    
    dispute = models.ForeignKey('accounts.Dispute', on_delete=models.CASCADE, related_name='assignments')
    
    # Safely referencing the User model from your accounts app
    lawyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='dispute_invitations'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    assigned_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('dispute', 'lawyer')

    def __str__(self):
        return f"Assignment: {self.lawyer} -> Dispute #{self.dispute.id} ({self.status})"