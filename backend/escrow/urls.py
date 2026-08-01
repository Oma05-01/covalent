from django.urls import path
from .views import (
    GenerateContractView,
    InitializeEscrowPaymentView,
    VerifyPaystackPaymentView,
    ContractActionView,
    UserContractsListView,
    RaiseDisputeView,
    DisputeEvidenceUploadView,
    PendingAssignmentsView,
    RespondToAssignmentView,
    ActiveDisputesView,
    CastArbitrationVoteView
)

app_name = 'escrow'

urlpatterns = [
    # Contracts & Escrow Payments
    path('contracts/', UserContractsListView.as_view(), name='user-contracts'),
    path('contracts/generate/', GenerateContractView.as_view(), name='generate-contract'),
    path('contracts/<int:contract_id>/action/', ContractActionView.as_view(), name='contract-action'),
    path('contracts/<int:contract_id>/pay/', InitializeEscrowPaymentView.as_view(), name='init-payment'),
    path('payments/verify/', VerifyPaystackPaymentView.as_view(), name='verify-payment'),
    
    # Dispute Initiation & Evidence
    path('contracts/<int:contract_id>/dispute/', RaiseDisputeView.as_view(), name='raise-dispute'),
    path('disputes/<int:dispute_id>/evidence/', DisputeEvidenceUploadView.as_view(), name='upload-evidence'),

    # Arbitration & Lawyer Dashboard
    path('disputes/active/', ActiveDisputesView.as_view(), name='active-disputes'),
    path('disputes/<int:pk>/vote/', CastArbitrationVoteView.as_view(), name='dispute-vote'),
    path('assignments/pending/', PendingAssignmentsView.as_view(), name='pending-assignments'),
    path('assignments/<int:pk>/respond/', RespondToAssignmentView.as_view(), name='respond-assignment'),
]