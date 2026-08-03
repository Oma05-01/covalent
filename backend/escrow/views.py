from django.db import transaction
from django.db.models import Q
from django.utils import timezone
import uuid
from datetime import timedelta
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from accounts.ai_contract import AIContractService
from decimal import Decimal
from .models import ArbitratorAssignment
from .serializers import DisputeSerializer, ArbitratorAssignmentSerializer
from accounts.models import CovalentUser as User, Dispute, ArbitrationVote, PlatformAuditLog, Contract, DisputeEvidence
from accounts.media_scrubber import MediaScrubberService
from rest_framework.parsers import MultiPartParser, FormParser
from accounts.models import Wallet
from accounts.serializers import ContractSerializer
from .services import execute_dispute_consensus, withdraw_funds, deposit_funds, lock_escrow, release_escrow
from django.core.exceptions import ValidationError

class RaiseDisputeView(APIView):
    @transaction.atomic
    def post(self, request, contract_id):
        contract = get_object_or_404(Contract, contract_id=contract_id)
        user = request.user
        
        # 1. Calculate & Deduct Fee via Ledger Service
        ARBITRATION_FEE = Decimal('5000.00')
        
        try:
            withdraw_funds(user, ARBITRATION_FEE)
        except ValidationError:
            return Response({"detail": "Insufficient funds for arbitration fee. Please fund your wallet."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Create the Dispute
        dispute = Dispute.objects.create(
            contract=contract,
            initiator=user,
            reason=request.data.get('reason', 'Standard contract dispute.')
        )
        contract.status = 'DISPUTED'
        contract.save()

        # 3. The Draft: Pick 3 Random Lawyers
        drafted_lawyers = User.objects.filter(
            is_lawyer=True,
            is_active=True,
            trust_score__gte=50 
        ).exclude(id__in=[contract.creator.id, contract.vendor.id]).order_by('?')[:3]

        if drafted_lawyers.count() < 3:
            return Response({"detail": "Not enough active arbitrators on the network. Contact support."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        for lawyer in drafted_lawyers:
            ArbitratorAssignment.objects.create(
                dispute=dispute,
                lawyer=lawyer
            )

        # 4. Log the fee deduction
        PlatformAuditLog.objects.create(
            user=user,
            action_type="DISPUTE_FEE_DEDUCTED",
            description=f"Deducted ₦5000 for Dispute #{dispute.id} initiation."
        )

        return Response({"message": "Dispute raised. 3 Arbitrators have been drafted.", "dispute_id": dispute.id})


class PendingAssignmentsView(APIView):
    """
    GET: Returns all pending dispute drafts assigned to the logged-in lawyer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not getattr(request.user, 'is_lawyer', False):
            return Response(
                {"detail": "Access restricted to verified arbitrators."},
                status=status.HTTP_403_FORBIDDEN
            )

        pending = ArbitratorAssignment.objects.filter(
            lawyer=request.user,
            status='PENDING'
        ).select_related('dispute', 'dispute__contract', 'dispute__contract__creator', 'dispute__contract__vendor')

        serializer = ArbitratorAssignmentSerializer(pending, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RespondToAssignmentView(APIView):
    """
    POST: Lawyer accepts or declines an assignment draft.
    If declined, the consensus engine automatically drafts a replacement lawyer.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        action = request.data.get('action')  # 'ACCEPT' or 'DECLINE'
        if action not in ['ACCEPT', 'DECLINE']:
            return Response(
                {"detail": "Invalid action. Must be 'ACCEPT' or 'DECLINE'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment = get_object_or_404(ArbitratorAssignment, id=pk, lawyer=request.user)

        if assignment.status != 'PENDING':
            return Response(
                {"detail": "This assignment has already been processed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment.status = 'ACCEPTED' if action == 'ACCEPT' else 'DECLINED'
        assignment.responded_at = timezone.now()
        assignment.save()

        # Audit log entry
        PlatformAuditLog.objects.create(
            user=request.user,
            action_type=f"ARBITRATION_DRAFT_{action}",
            description=f"Lawyer {request.user.email} {action.lower()}ed draft for Dispute #{assignment.dispute_id}."
        )

        if action == 'DECLINED':
            dispute = assignment.dispute
            already_invited_ids = dispute.assignments.values_list('lawyer_id', flat=True)

            # Auto-replacement: draft a new lawyer not yet invited to this dispute
            replacement_lawyer = User.objects.filter(
                is_lawyer=True,
                is_active=True,
                trust_score__gte=50
            ).exclude(
                id__in=list(already_invited_ids) + [dispute.contract.creator_id, dispute.contract.vendor_id]
            ).order_by('?').first()

            if replacement_lawyer:
                ArbitratorAssignment.objects.create(
                    dispute=dispute,
                    lawyer=replacement_lawyer
                )
                msg = "Draft declined. A replacement arbitrator has been dispatched."
            else:
                msg = "Draft declined. Warning: No replacement arbitrators currently available."

            return Response({"message": msg}, status=status.HTTP_200_OK)

        return Response({"message": "Assignment accepted. Case added to your Active Docket."}, status=status.HTTP_200_OK)


class ActiveDisputesView(APIView):
    """
    GET: Returns open disputes that the lawyer has ACCEPTED to arbitrate.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not getattr(request.user, 'is_lawyer', False):
            return Response(
                {"detail": "Access restricted to verified arbitrators."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get disputes where this lawyer's assignment is ACCEPTED
        accepted_dispute_ids = ArbitratorAssignment.objects.filter(
            lawyer=request.user,
            status='ACCEPTED'
        ).values_list('dispute_id', flat=True)

        # Filter out disputes where the lawyer has already voted
        voted_dispute_ids = ArbitrationVote.objects.filter(
            lawyer=request.user
        ).values_list('dispute_id', flat=True)

        active_disputes = Dispute.objects.filter(
            id__in=accepted_dispute_ids
        ).exclude(
            id__in=voted_dispute_ids
        ).select_related('contract', 'contract__creator', 'contract__vendor')

        serializer = DisputeSerializer(active_disputes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GenerateContractView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        prompt = request.data.get("prompt")
        vendor_email = request.data.get("vendor_email")
        
        if not prompt or not vendor_email:
            return Response(
                {"detail": "Both a deal description and vendor email are required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            ai_service = AIContractService()
            contract_data = ai_service.parse_contract_prompt(prompt)
            
            contract = Contract.objects.create(
                creator=request.user,
                vendor_email=vendor_email,
                item_title=contract_data["item_title"],
                item_description=contract_data["item_description"],
                item_amount=contract_data["item_amount"],
                delivery_fee=contract_data["delivery_fee"],
                plain_language_summary=contract_data["plain_language_summary"]
            )
            
            return Response({
                "contract_id": contract.contract_id,
                "terms": contract_data,
                "total_escrow": contract.total_escrow
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"detail": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CastArbitrationVoteView(APIView):
    """
    POST: Lawyer records their verdict vote and justification.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        dispute = get_object_or_404(Dispute, id=pk)
        ruling = request.data.get('ruling')
        justification = request.data.get('justification', '').strip()

        if ruling not in ['buyer', 'vendor']:
            return Response({"detail": "Invalid ruling target."}, status=status.HTTP_400_BAD_REQUEST)

        if len(justification) < 80:
            return Response({"detail": "Legal justification must be at least 80 characters."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure lawyer is an accepted arbitrator for this dispute
        is_assigned = ArbitratorAssignment.objects.filter(
            dispute=dispute,
            lawyer=request.user,
            status='ACCEPTED'
        ).exists()

        if not is_assigned:
            return Response({"detail": "You are not an accepted arbitrator for this dispute."}, status=status.HTTP_403_FORBIDDEN)

        # Check for duplicate vote
        if ArbitrationVote.objects.filter(dispute=dispute, lawyer=request.user).exists():
            return Response({"detail": "You have already voted on this dispute."}, status=status.HTTP_400_BAD_REQUEST)

        # Record vote
        ArbitrationVote.objects.create(
            dispute=dispute,
            lawyer=request.user,
            ruling=ruling,
            legal_justification=justification
        )

        # Immutable Audit Log
        PlatformAuditLog.objects.create(
            user=request.user,
            action_type="ARBITRATION_VOTE_CAST",
            description=f"Lawyer {request.user.email} voted '{ruling}' for Dispute #{dispute.id}."
        )

        consensus_reached, message = execute_dispute_consensus(dispute)

        if consensus_reached:
            return Response({
                "message": "Verdict registered. 3rd vote received. " + message
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "message": "Verdict registered in legal ledger. Awaiting remaining arbitrators."
            }, status=status.HTTP_200_OK)


class InitializeEscrowPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from accounts.models import CovalentUser
        contract_id = request.data.get("contract_id")
        
        try:
            contract = Contract.objects.get(contract_id=contract_id, creator=request.user)
        except Contract.DoesNotExist:
            return Response(
                {"detail": "Contract not found or you are not authorized to fund it."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Using CovalentUser directly satisfies Pylance strict typing
            vendor = CovalentUser.objects.get(email=contract.vendor_email)
            if not vendor.paystack_subaccount_code:
                return Response(
                    {"detail": f"Vendor ({contract.vendor_email}) has not linked a settlement bank account yet."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except CovalentUser.DoesNotExist:
            return Response(
                {"detail": "The vendor email provided is not registered on Covalent."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        reference = f"COVA-{uuid.uuid4().hex[:8].upper()}"
        contract.paystack_reference = reference
        contract.status = "AWAITING_FUNDING"
        contract.save()

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", 
            "Content-Type": "application/json"
        }
        payload = {
            "email": request.user.email,
            "amount": int(contract.total_escrow * 100),  # Amount in kobo
            "reference": reference,
            "callback_url": "http://localhost:5173/",
        }
        
        # SMART MOCK BYPASS: Skip subaccount split if testing with mock codes
        if not str(vendor.paystack_subaccount_code).startswith("ACCT_mock"):
            payload["subaccount"] = vendor.paystack_subaccount_code
            payload["bearer"] = "subaccount"
        
        res = requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers)
        
        if res.status_code == 200:
            return Response(res.json()["data"], status=status.HTTP_200_OK)
            
        error_data = res.json()
        print("PAYSTACK API ERROR:", error_data)
        return Response(
            {"detail": f"Paystack Error: {error_data.get('message', 'Unknown error')}"}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class ContractActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, contract_id, action):
        contract = None

        # Robust multi-field lookup
        for field in ['contract_id', 'id', 'paystack_reference']:
            try:
                contract = Contract.objects.filter(**{field: contract_id}).first()
                if contract:
                    break
            except Exception:
                continue

        if not contract:
            return Response({"detail": "Contract not found in database."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user

        # ACTION 1: Vendor marks package as dispatched
        if action == "dispatch":
            if user.email != contract.vendor_email or contract.status != "FUNDED":
                return Response({"detail": "Unauthorized or invalid state for dispatch."}, status=400)
            contract.status = "IN_TRANSIT"
            contract.save()
            return Response({"message": "Package marked as in transit!"}, status=200)

        # 🆕 ACTION 2: Vendor marks as delivered (STARTS THE TIMER)
        elif action == "deliver":
            if user.email != contract.vendor_email or contract.status not in ["FUNDED", "IN_TRANSIT"]:
                return Response({"detail": "Unauthorized or invalid state for delivery."}, status=400)

            now = timezone.now()
            contract.status = "DELIVERED"
            contract.delivered_at = now
            # Calculate the deadline based on the contract's terms
            contract.auto_release_at = now + timedelta(hours=contract.inspection_period_hours)
            contract.save()

            return Response({
                "message": f"Package delivered! Buyer has {contract.inspection_period_hours} hours to inspect.",
                "auto_release_at": contract.auto_release_at
            }, status=200)

        # ACTION 3: Buyer confirms receipt (Happy Path)
        elif action == "approve":
            if user != contract.creator or contract.status not in ["FUNDED", "IN_TRANSIT", "DELIVERED"]:
                return Response({"detail": "Unauthorized or invalid state for approval."}, status=400)
            
            contract.status = "RELEASED"
            contract.save()
            
            # REPLACE THE DIRECT WALLET MATH WITH THIS:
            try:
                # Use our service! Moves from Buyer Locked -> Vendor Available and logs it!
                vendor_user = User.objects.get(email=contract.vendor_email)
                release_escrow(
                    buyer=contract.creator, 
                    vendor=vendor_user, 
                    amount=contract.total_escrow, 
                    reference=f"RELEASE_{contract.contract_id}"
                )
            except Exception as e:
                return Response({"detail": str(e)}, status=400)

            return Response({"message": "Deal approved! Funds released to vendor."}, status=200)

        # ACTION 4: Buyer rejects/disputes
        elif action in ["reject-at-door", "dispute"]:
            # 🆕 Allow disputes when state is DELIVERED, otherwise the timer is useless
            if user != contract.creator or contract.status not in ["FUNDED", "IN_TRANSIT", "DELIVERED"]:
                return Response({"detail": "Unauthorized or invalid state for rejection."}, status=400)

            # 1. Update Contract Status
            contract.status = "DISPUTED"
            contract.save()

            # 2. AUTO-CREATE THE DISPUTE RECORD FOR THE LAWYER QUEUE!
            Dispute.objects.get_or_create(
                contract=contract,
                defaults={
                    "initiator": user,  
                    "reason": "Doorstep Rejection / Item Misrepresentation",
                    "description": f"Buyer ({user.email}) rejected the deal. Case escalated for legal arbitration.",
                    "status": "IN_REVIEW"
                }
            )

            # 3. Apply dispatch penalty & trust score deductions
            vendor_wallet, _ = Wallet.objects.get_or_create(user__email=contract.vendor_email)
            vendor = vendor_wallet.user
            
            if hasattr(vendor_wallet, 'dispute_penalty_balance'):
                vendor_wallet.dispute_penalty_balance += contract.delivery_fee
            elif hasattr(vendor_wallet, 'penalty_balance'):
                vendor_wallet.penalty_balance += contract.delivery_fee
            vendor_wallet.save()

            vendor.trust_score = max(vendor.trust_score - 15, 0)
            vendor.save()

            return Response({
                "message": f"Deal disputed! Dispute record #COVA-DSP created for Lawyer Chamber. Seller debited ₦{contract.delivery_fee:,.2f} for dispatch."
            }, status=200)

        return Response({"detail": "Invalid action parameter."}, status=400)


class UserContractsListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        contracts = Contract.objects.filter(
            Q(creator=request.user) | Q(vendor_email=request.user.email)
        ).order_by('-created_at')
        
        serializer = ContractSerializer(contracts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    
class DisputeEvidenceUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser] # Required for handling file uploads

    def post(self, request, dispute_id):
        try:
            dispute = Dispute.objects.get(id=dispute_id)
        except Dispute.DoesNotExist:
            return Response({"detail": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)

        file_obj = request.FILES.get("file")
        file_type = request.data.get("file_type", "IMAGE")

        if not file_obj:
            return Response({"detail": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Save raw evidence
        evidence = DisputeEvidence.objects.create(
            dispute=dispute,
            uploader=request.user,
            original_file=file_obj,
            file_type=file_type
        )

        # 2. Run automated privacy scrubbing
        try:
            MediaScrubberService.process_evidence(evidence)
            return Response({
                "message": "Evidence uploaded and privacy-scrubbed successfully!",
                "evidence_id": evidence.id,
                "clean_file_url": evidence.scrubbed_file.url if evidence.scrubbed_file else None
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                "detail": "File saved, but media scrubbing failed. Please check file format."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPaystackPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        reference = request.data.get("reference")
        if not reference:
            return Response({"detail": "Transaction reference is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            contract = Contract.objects.get(paystack_reference=reference)
            
            # SMART LOCALHOST VERIFICATION:
            if contract.status == "AWAITING_FUNDING":
                contract.status = "FUNDED"
                contract.save()
                
                # REPLACE THE DIRECT VENDOR WALLET MATH WITH THIS:
                # 1. Deposit the external Paystack funds into the buyer's wallet
                deposit_funds(contract.creator, contract.total_escrow, reference=f"PAYSTACK_{reference}")
                
                # 2. Immediately lock those funds in escrow
                lock_escrow(contract.creator, contract.total_escrow, reference=f"ESCROW_{contract.contract_id}")

            return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
            
        except Contract.DoesNotExist:
            return Response({"detail": "Contract with this reference not found."}, status=status.HTTP_404_NOT_FOUND)
        
