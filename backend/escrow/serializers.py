from rest_framework import serializers
from .models import ArbitratorAssignment
from accounts.models import Dispute, Contract


class ContractNestedSerializer(serializers.ModelSerializer):
    contract_id = serializers.CharField(source='id', read_only=True)

    class Meta:
        model = Contract
        fields = [
            'contract_id',
            'item_title',
            'total_escrow',
            'paystack_reference',
            'status'
        ]


class DisputeSerializer(serializers.ModelSerializer):
    contract = ContractNestedSerializer(read_only=True)
    buyer_email = serializers.SerializerMethodField()
    vendor_email = serializers.SerializerMethodField()

    class Meta:
        model = Dispute
        fields = [
            'id',
            'contract',
            'buyer_email',
            'vendor_email',
            'reason',
            'created_at'
        ]

    def get_buyer_email(self, obj):
        return obj.contract.buyer.email if obj.contract and obj.contract.buyer else "Anonymized"

    def get_vendor_email(self, obj):
        return obj.contract.vendor.email if obj.contract and obj.contract.vendor else "Anonymized"


class ArbitratorAssignmentSerializer(serializers.ModelSerializer):
    dispute = DisputeSerializer(read_only=True)

    class Meta:
        model = ArbitratorAssignment
        fields = [
            'id',
            'dispute',
            'status',
            'assigned_at'
        ]