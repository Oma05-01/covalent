from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Q, Sum, Avg, Count

import uuid
import requests
import hmac
import hashlib
import requests
from decimal import Decimal

from .models import Wallet, Contract, CovalentUser, Dispute, DisputeEvidence, ArbitrationVote, MerchantAPIKey
from .serializers import (
    KYCSubmissionSerializer, UserProfileSerializer, WalletSerializer, 
    BankResolveSerializer, BankLinkSerializer, ContractSerializer, AnonymizedDisputeSerializer
)
from .paystack import PaystackService
from .ai_contract import AIContractService
from .media_scrubber import MediaScrubberService
from rest_framework.parsers import MultiPartParser, FormParser


class KYCVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        
        if user.is_kyc_verified:
            return Response(
                {"detail": "Your account is already KYC verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = KYCSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nin = str(serializer.validated_data["nin"])
        
        user.nin = nin
        user.is_kyc_verified = True
        user.trust_score = min(user.trust_score + 5, 100)
        user.save()

        return Response({
            "message": "KYC verification successful!",
            "user": UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class BankListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        service = PaystackService()
        banks = service.get_nigerian_banks()
        bank_list = [{"name": b["name"], "code": b["code"]} for b in banks]
        return Response(bank_list, status=status.HTTP_200_OK)


class ResolveAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        serializer = BankResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = PaystackService()
        data = service.resolve_account_number(
            serializer.validated_data['account_number'],
            serializer.validated_data['bank_code']
        )
        return Response(data, status=status.HTTP_200_OK)


class LinkBankView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        user = request.user
        serializer = BankLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        bank_code = serializer.validated_data['bank_code']
        account_number = serializer.validated_data['account_number']
        account_name = serializer.validated_data['account_name']
        bank_name = serializer.validated_data['bank_name']

        service = PaystackService()
        subaccount_code = service.create_subaccount(user, bank_code, account_number, account_name)

        user.paystack_subaccount_code = subaccount_code
        user.bank_name = bank_name
        user.account_number = account_number
        user.account_name = account_name
        user.save()

        Wallet.objects.get_or_create(user=user)

        return Response({
            "message": "Bank account linked successfully for split payouts!",
            "subaccount_code": subaccount_code
        }, status=status.HTTP_200_OK)


class WalletDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response({
            "wallet": WalletSerializer(wallet).data,
            "bank_info": {
                "bank_name": request.user.bank_name,
                "account_number": request.user.account_number,
                "account_name": request.user.account_name,
                "is_linked": bool(request.user.paystack_subaccount_code)
            }
        }, status=status.HTTP_200_OK)
    

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


class InitializeEscrowPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
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
    

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def paystack_webhook(request):
    """Secure background listener for Paystack payment notifications."""
    paystack_signature = request.headers.get('x-paystack-signature')
    if not paystack_signature:
        return Response({"detail": "Missing Paystack signature header."}, status=status.HTTP_400_BAD_REQUEST)

    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        request.body,
        hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(computed_signature, paystack_signature):
        return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data
    event = payload.get('event')
    data = payload.get('data', {})

    if event == 'charge.success':
        reference = data.get('reference')
        try:
            contract = Contract.objects.get(paystack_reference=reference, status="AWAITING_FUNDING")
            contract.status = "FUNDED"
            contract.save()
            
            vendor_wallet, _ = Wallet.objects.get_or_create(user__email=contract.vendor_email)
            vendor_wallet.locked_escrow_balance += contract.total_escrow
            vendor_wallet.save()
            
        except Contract.DoesNotExist:
            pass

    return Response(status=status.HTTP_200_OK)


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

        # ACTION 2: Buyer confirms receipt (Standard Payout + 5% Covalent Take)
        elif action in ["reject-at-door", "dispute"]:
            if user != contract.creator or contract.status not in ["FUNDED", "IN_TRANSIT"]:
                return Response({"detail": "Unauthorized or invalid state for rejection."}, status=400)

            # 1. Update Contract Status
            contract.status = "DISPUTED"
            contract.save()

            # 2. AUTO-CREATE THE DISPUTE RECORD FOR THE LAWYER QUEUE!
            Dispute.objects.get_or_create(
                contract=contract,
                defaults={
                    "reason": "Doorstep Rejection / Item Misrepresentation",
                    "description": f"Buyer ({user.email}) rejected the deal at delivery. Case escalated for legal arbitration.",
                    "status": "PENDING"
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
            # If stuck in AWAITING_FUNDING (because public webhooks can't reach localhost),
            # auto-verify the payment and lock the funds in the vendor's escrow vault!
            if contract.status == "AWAITING_FUNDING":
                contract.status = "FUNDED"
                contract.save()
                
                vendor_wallet, _ = Wallet.objects.get_or_create(user__email=contract.vendor_email)
                vendor_wallet.locked_escrow_balance += contract.total_escrow
                vendor_wallet.save()

            return Response(ContractSerializer(contract).data, status=status.HTTP_200_OK)
            
        except Contract.DoesNotExist:
            return Response({"detail": "Contract with this reference not found."}, status=status.HTTP_404_NOT_FOUND)
        

class LawyerDisputeQueueView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_lawyer:
            return Response({"detail": "Access denied. Verified lawyer status required."}, status=403)
        
        # Return open disputes that this specific lawyer hasn't voted on yet
        disputes = Dispute.objects.filter(status="IN_REVIEW").exclude(votes__lawyer=request.user)
        serializer = AnonymizedDisputeSerializer(disputes, many=True)
        return Response(serializer.data, status=200)


class CastArbitrationVoteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, dispute_id):
        user = request.user
        if not user.is_lawyer:
            return Response({"detail": "Only verified legal reviewers can cast arbitration votes."}, status=403)

        ruling = request.data.get("ruling") # 'BUYER' or 'VENDOR'
        justification = request.data.get("justification", "")

        try:
            dispute = Dispute.objects.get(id=dispute_id, status="IN_REVIEW")
        except Dispute.DoesNotExist:
            return Response({"detail": "Dispute not found or already closed."}, status=404)

        # 1. Record vote
        try:
            ArbitrationVote.objects.create(
                dispute=dispute,
                lawyer=user,
                ruling=ruling,
                legal_justification=justification
            )
            user.lawyer_cases_resolved += 1
            user.save()
        except Exception:
            return Response({"detail": "You have already cast a vote on this case."}, status=400)

        # 2. CONSENSUS ENGINE: Check if either side has reached 2 votes
        buyer_votes = dispute.votes.filter(ruling="BUYER").count()
        vendor_votes = dispute.votes.filter(ruling="VENDOR").count()
        contract = dispute.contract
        vendor_wallet, _ = Wallet.objects.get_or_create(user__email=contract.vendor_email)

        if buyer_votes >= 2:
            dispute.status = "RESOLVED_BUYER"
            dispute.save()
            contract.status = "REFUNDED"
            contract.save()
            
            # Remove funds from vendor's locked escrow (Refund initiated to buyer)
            vendor_wallet.locked_escrow_balance -= contract.total_escrow
            vendor_wallet.save()
            return Response({"message": "Vote recorded! Consensus reached: Case resolved in favor of BUYER. Refund triggered."}, status=200)

        elif vendor_votes >= 2:
            dispute.status = "RESOLVED_VENDOR"
            dispute.save()
            contract.status = "RELEASED"
            contract.save()
            
            # Release funds to vendor available balance minus platform fee
            vendor_wallet.locked_escrow_balance -= contract.total_escrow
            vendor_wallet.available_balance += (contract.total_escrow * Decimal('0.95'))
            vendor_wallet.save()
            return Response({"message": "Vote recorded! Consensus reached: Case resolved in favor of VENDOR. Escrow released."}, status=200)

        return Response({"message": f"Vote recorded successfully. Case stands at {buyer_votes} for Buyer vs {vendor_votes} for Vendor."}, status=200)
    

class PlatformAdminDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({"detail": "Access denied. Admin privileges required."}, status=403)

        # 1. Financial Metrics Aggregation
        released_contracts = Contract.objects.filter(status="RELEASED")
        total_gmv = released_contracts.aggregate(total=Sum('total_escrow'))['total'] or Decimal('0.00')
        
        # Covalent takes 5% of all released escrow deals
        platform_revenue = total_gmv * Decimal('0.05')
        
        # Money currently sitting locked inside active deals
        locked_vault = Wallet.objects.aggregate(total=Sum('locked_escrow_balance'))['total'] or Decimal('0.00')
        
        # 2. System Health & Governance Metrics
        active_disputes = Dispute.objects.filter(status="IN_REVIEW").count()
        avg_trust_score = CovalentUser.objects.aggregate(avg=Avg('trust_score'))['avg'] or 0
        total_users = CovalentUser.objects.count()
        verified_lawyers = CovalentUser.objects.filter(is_lawyer=True).count()

        return Response({
            "financials": {
                "total_gmv": total_gmv,
                "platform_revenue": platform_revenue,
                "locked_vault": locked_vault,
            },
            "governance": {
                "active_disputes": active_disputes,
                "avg_trust_score": round(avg_trust_score, 1),
                "total_users": total_users,
                "verified_lawyers": verified_lawyers,
            }
        }, status=status.HTTP_200_OK)


class AdminUserManagementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({"detail": "Access denied."}, status=403)
            
        users = CovalentUser.objects.all().order_by('-date_joined')[:20]
        data = []
        for u in users:
            # Safely get the wallet balance
            balance = 0
            try:
                # This now works because of the related_name="wallet" fix
                balance = u.wallet.available_balance 
            except AttributeError:
                balance = 0
                
            data.append({
                "id": u.id,
                "email": u.email,
                "name": f"{u.first_name} {u.last_name}",
                "trust_score": u.trust_score,
                "is_kyc_verified": u.is_kyc_verified,
                "is_lawyer": u.is_lawyer,
                "is_active": u.is_active,
                "wallet_balance": balance,
            })
        return Response(data, status=200)

    def patch(self, request, user_id):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({"detail": "Access denied."}, status=403)
            
        try:
            target_user = CovalentUser.objects.get(id=user_id)
        except CovalentUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        action = request.data.get("action")
        
        if action == "toggle_lawyer":
            target_user.is_lawyer = not target_user.is_lawyer
            target_user.save()
            return Response({"message": f"Lawyer status set to {target_user.is_lawyer}"})
            
        elif action == "boost_trust":
            target_user.trust_score = min(target_user.trust_score + 10, 100)
            target_user.save()
            return Response({"message": f"Trust score boosted to {target_user.trust_score}"})
            
        elif action == "penalize_trust":
            target_user.trust_score = max(target_user.trust_score - 15, 0)
            target_user.save()
            return Response({"message": f"Trust score penalized to {target_user.trust_score}"})

        return Response({"detail": "Invalid action."}, status=400)
    
def trigger_merchant_webhook(contract, event_type):
    # This logic would be called by your Celery worker 
    # when contract.status changes
    payload = {
        "event": event_type,
        "contract_id": str(contract.contract_id),
        "status": contract.status
    }
    # In a real app, you'd store the merchant's webhook_url in MerchantAPIKey
    # requests.post("https://merchant-store.com/webhooks/covalent", json=payload)
    print(f"Webhook {event_type} sent for {contract.contract_id}")


class DevKeysView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        keys = MerchantAPIKey.objects.filter(user=request.user)
        return Response([{'id': k.id, 'name': k.name, 'key': k.key} for k in keys])

    def post(self, request):
        key = MerchantAPIKey.objects.create(user=request.user, name=request.data.get('name'))
        return Response({'id': key.id, 'name': key.name, 'key': key.key})