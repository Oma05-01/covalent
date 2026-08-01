from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Wallet, Contract, Dispute, DisputeEvidence, ArbitrationVote

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    trust_tier = serializers.CharField(source='get_trust_tier_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone_number', 
            'is_kyc_verified', 'trust_score', 'trust_tier', 
            'completed_contracts', 'disputes_count', 'is_lawyer'
        ]
        read_only_fields = ['email', 'is_kyc_verified', 'trust_score', 'completed_contracts', 'disputes_count']


class KYCSubmissionSerializer(serializers.Serializer):
    nin = serializers.CharField(max_length=11, min_length=11)

    def validate_nin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("NIN must contain only 11 digits.")
        if User.objects.filter(nin=value).exists():
            raise serializers.ValidationError("This NIN is already registered to another account.")
        return value

    
class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['available_balance', 'locked_escrow_balance', 'penalty_balance', 'updated_at']


class BankResolveSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=10, min_length=10)
    bank_code = serializers.CharField(max_length=10)


class BankLinkSerializer(BankResolveSerializer):
    bank_name = serializers.CharField(max_length=100)
    account_name = serializers.CharField(max_length=150)


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = [
            'contract_id', 'paystack_reference', 'vendor_email', 
            'item_title', 'item_description', 'item_amount', 
            'delivery_fee', 'total_escrow', 'status', 'created_at',
            'inspection_period_hours', 'delivered_at', 'auto_release_at' # 🆕 Added
        ]
        
        # Make sure users can't artificially alter the timer or status
        read_only_fields = [
            'contract_id', 'paystack_reference', 'total_escrow', 
            'status', 'created_at', 'delivered_at', 'auto_release_at'
        ]


class AnonymizedEvidenceSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = DisputeEvidence
        fields = ['id', 'file_type', 'file_url', 'uploaded_at']

    def get_file_url(self, obj):
        # STRICK PRIVACY RULE: Always return the scrubbed file, never the raw upload!
        if obj.scrubbed_file:
            return obj.scrubbed_file.url
        return None


class AnonymizedDisputeSerializer(serializers.ModelSerializer):
    # Pull contract details without revealing emails or names
    item_title = serializers.CharField(source='contract.item_title', read_only=True)
    item_description = serializers.CharField(source='contract.item_description', read_only=True)
    plain_language_summary = serializers.CharField(source='contract.plain_language_summary', read_only=True)
    total_escrow = serializers.DecimalField(source='contract.total_escrow', max_digits=12, decimal_places=2, read_only=True)
    evidence_files = AnonymizedEvidenceSerializer(many=True, read_only=True)
    total_votes = serializers.SerializerMethodField()
    item_amount = serializers.DecimalField(source='contract.item_amount', max_digits=12, decimal_places=2, read_only=True)
    contract_reference = serializers.CharField(source='contract.paystack_reference', read_only=True)

    class Meta:
        model = Dispute
        fields = [
            'id', 'reason', 'description', 'status', 'created_at',
            'item_title', 'item_description', 'plain_language_summary', 
            'total_escrow', 'evidence_files', 'total_votes', 'item_amount', 'contract_reference'
        ]

    def get_total_votes(self, obj):
        return obj.votes.count()


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password', 'role', 'nin']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Use create_user to ensure the password gets hashed!
        return User.objects.create_user(**validated_data)