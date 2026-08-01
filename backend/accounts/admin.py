from django.contrib import admin
from .models import CovalentUser, Wallet, Contract, Dispute, DisputeEvidence, ArbitrationVote, MerchantAPIKey, PlatformAuditLog
admin.site.register(CovalentUser)
admin.site.register(Wallet)
admin.site.register(Contract)
@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_contract_title', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('contract__item_title', 'contract__contract_id', 'reason')

    def get_contract_title(self, obj):
        return obj.contract.item_title if obj.contract else "No Contract"
    get_contract_title.short_description = "Contract Item"

@admin.register(DisputeEvidence)
class DisputeEvidenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'dispute', 'uploader', 'file_type', 'uploaded_at')

@admin.register(ArbitrationVote)
class ArbitrationVoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'dispute', 'lawyer', 'ruling', 'created_at')
    list_filter = ('ruling',)


@admin.register(PlatformAuditLog)
class PlatformAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action_type', 'user', 'created_at', 'ip_address']
    list_filter = ['action_type', 'created_at']
    search_fields = ['user__email', 'action_type', 'description']
    readonly_fields = ['user', 'action_type', 'description', 'ip_address', 'created_at']
    ordering = ['-created_at']

    # 🔒 STRICT AUDIT INTEGRITY: Disable all manual modifications
    def has_add_permission(self, request):
        """Prevent manual creation of log entries."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent editing of existing log entries."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of log entries to maintain a permanent record."""
        return False