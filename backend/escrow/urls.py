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
    CastArbitrationVoteView,
    DisputeDetailView,
)

app_name = 'escrow'

urlpatterns = [
    # 1. Standard Endpoints (Put these first so they don't get caught by wildcards)
    path('contracts/', UserContractsListView.as_view(), name='user-contracts'),
    path('contracts/generate/', GenerateContractView.as_view(), name='generate-contract'),
    path('payments/verify/', VerifyPaystackPaymentView.as_view(), name='verify-payment'),
    
    # 2. Specific Contract Actions
    path('contracts/<str:contract_id>/pay/', InitializeEscrowPaymentView.as_view(), name='init-payment'),
    path('contracts/<str:contract_id>/dispute/', RaiseDisputeView.as_view(), name='raise-dispute'),
    
    # 3. Dynamic Contract Actions (The wildcard MUST go last in the contracts section)
    path('contracts/<str:contract_id>/<str:action>/', ContractActionView.as_view(), name='contract-action'),
    
    # 4. Disputes & Lawyer Dashboard
    path('disputes/active/', ActiveDisputesView.as_view(), name='active-disputes'),
    path('disputes/<int:dispute_id>/evidence/', DisputeEvidenceUploadView.as_view(), name='upload-evidence'),
    path('disputes/<int:pk>/vote/', CastArbitrationVoteView.as_view(), name='dispute-vote'),
    
    # 5. Assignments
    path('assignments/pending/', PendingAssignmentsView.as_view(), name='pending-assignments'),
    path('assignments/<int:pk>/respond/', RespondToAssignmentView.as_view(), name='respond-assignment'),

    path('disputes/<int:id>/', DisputeDetailView.as_view(), name='dispute-detail'),
]