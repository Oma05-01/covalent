from rest_framework.views import APIView
from rest_framework import generics, status, viewsets, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from .permissions import IsRiskOfficer
from governance.permissions import IsAccountInGoodStanding
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Sum, Avg
import requests
import hmac
import hashlib
import requests
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from audit.services import AuditLogger
from audit.models import AdminActionType
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Wallet, Contract, CovalentUser, Dispute, MerchantAPIKey, ContractApplication
from .serializers import (
    KYCSubmissionSerializer, UserProfileSerializer, WalletSerializer, 
    BankResolveSerializer, BankLinkSerializer, RegistrationSerializer, 
    ContractSerializer, ContractApplicationSerializer, AdminUserListSerializer
)
from .paystack import PaystackService
from .services import accept_contract
from .ai_contract import AIContractService


User = get_user_model()


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


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens for the immediate login
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "user": serializer.data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


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


class ContractDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, contract_id):
        try:
            contract = Contract.objects.get(
                contract_id=contract_id,
                creator=request.user,
                status__in=["DRAFT", "AWAITING_FUNDING", "UNFUNDED"]
            )
            contract.delete()
            return Response({"message": "Draft contract deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Contract.DoesNotExist:
            return Response(
                {"detail": "Draft not found or cannot be deleted once funded or disputed."},
                status=status.HTTP_400_BAD_REQUEST
            )
    

class ContractViewSet(viewsets.ModelViewSet):
    serializer_class = ContractSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        # Apply the restriction only to contract creation
        if self.action == 'create':
            permission_classes = [IsAuthenticated, IsAccountInGoodStanding]
        else:
            # For reading, listing, or updating (if allowed), basic auth is enough
            permission_classes = [IsAuthenticated]
            
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Users can only see public contracts, or contracts they are a party to."""
        user = self.request.user
        return Contract.objects.filter(is_public=True) | \
               Contract.objects.filter(creator=user) | \
               Contract.objects.filter(vendor=user) | \
               Contract.objects.filter(vendor_email=user.email)

    def perform_create(self, serializer):
        """Automatically set the creator and determine initial status."""
        is_public = serializer.validated_data.get('is_public', False)
        vendor_email = serializer.validated_data.get('vendor_email', None)
        
        vendor = None
        if vendor_email:
            # Try to link an existing user if the email matches
            vendor = User.objects.filter(email=vendor_email).first()
            
        initial_status = "OPEN" if is_public else "PROPOSED"
        
        serializer.save(
            creator=self.request.user, 
            vendor=vendor,
            status=initial_status
        )

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Allows a vendor to bid on an OPEN contract."""
        contract = self.get_object()
        
        if contract.status != "OPEN":
            return Response({"error": "This contract is not open for bids."}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = ContractApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(contract=contract, applicant=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def accept_application(self, request, pk=None):
        """Allows a buyer to accept a vendor's bid."""
        contract = self.get_object()
        application_id = request.data.get('application_id')
        
        if contract.creator != request.user:
            return Response({"error": "Only the creator can accept bids."}, status=status.HTTP_403_FORBIDDEN)
            
        application = get_object_or_404(ContractApplication, id=application_id, contract=contract)
        
        # Use our service to lock the contract state
        accept_contract(contract=contract, vendor=application.applicant)
        
        # Update application statuses
        application.status = "ACCEPTED"
        application.save()
        contract.applications.exclude(id=application.id).update(status="REJECTED")
        
        return Response({"status": "Contract locked and vendor assigned."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Allows a targeted vendor to reject a direct proposal."""
        contract = self.get_object()
        
        if contract.vendor != request.user and contract.vendor_email != request.user.email:
            return Response({"error": "You are not the targeted vendor."}, status=status.HTTP_403_FORBIDDEN)
            
        if contract.status != "PROPOSED":
            return Response({"error": "Only proposed contracts can be rejected."}, status=status.HTTP_400_BAD_REQUEST)
            
        contract.status = "REJECTED"
        contract.save()
        return Response({"status": "Contract rejected."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='generate-ai-draft')
    def generate_ai_draft(self, request):
        """
        Takes a natural language negotiation prompt, parses it via Gemini,
        and returns structured contract data for human review/editing.
        """
        prompt = request.data.get('prompt')
        if not prompt:
            return Response(
                {"error": "A natural language 'prompt' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Parse prompt into structured JSON via AI service
        ai_service = AIContractService()
        parsed_terms = ai_service.parse_contract_prompt(prompt)

        # 2. Return parsed terms directly so the frontend/human can review & edit
        return Response(parsed_terms, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """
        Matches the React AIContractBuilder frontend.
        POST /api/contracts/generate/
        """
        prompt = request.data.get('prompt')
        vendor_email = request.data.get('vendor_email')

        if not prompt or not vendor_email:
            return Response(
                {"detail": "Both 'prompt' and 'vendor_email' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Parse prompt into structured JSON via AI service
        ai_service = AIContractService()
        try:
            parsed_terms = ai_service.parse_contract_prompt(prompt)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Save the contract directly to the database
        contract = Contract.objects.create(
            creator=request.user,
            vendor_email=vendor_email,
            status="PROPOSED",
            item_title=parsed_terms.get('item_title'),
            item_description=parsed_terms.get('item_description'),
            item_amount=parsed_terms.get('item_amount'),
            delivery_fee=parsed_terms.get('delivery_fee'),
            delivery_days=parsed_terms.get('delivery_days'),
            plain_language_summary=parsed_terms.get('plain_language_summary')
        )

        # 3. Calculate total for the frontend UI
        total_escrow = float(contract.item_amount) + float(contract.delivery_fee)

        # 4. Return the exact structure the React component expects
        return Response({
            "contract_id": contract.contract_id, # Or contract.contract_id if you use UUIDs
            "terms": parsed_terms,
            "total_escrow": total_escrow
        }, status=status.HTTP_201_CREATED)

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


class StandardAdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class AdminUserManagementView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    # Let DRF handle the querying, filtering, and ordering
    queryset = CovalentUser.objects.all().order_by('-date_joined')
    serializer_class = AdminUserListSerializer
    pagination_class = StandardAdminPagination
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'is_lawyer']
    search_fields = ['email', 'first_name', 'last_name']

    def get(self, request, *args, **kwargs):
        # 1. Keep your original security check
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({"detail": "Access denied."}, status=403)
            
        # 2. Let ListAPIView handle the pagination, filtering, and serialization
        return super().get(request, *args, **kwargs)

    def patch(self, request, user_id=None):
        # Keep your exact original patch logic untouched
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({"detail": "Access denied."}, status=403)
            
        # Fallback if user_id is passed in body instead of URL for the 'action' route
        if not user_id:
            user_id = request.data.get("user_id")
            
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

    
class SuspendUserView(APIView):
    """
    Suspends a user account and logs the action immutably.
    Requires Risk Officer or Super Admin privileges.
    """
    permission_classes = [IsRiskOfficer]

    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        justification = request.data.get('justification')

        if not justification:
            return Response(
                {"error": "A justification must be provided to suspend a user."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not target_user.is_active:
            return Response(
                {"error": "User is already suspended."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Capture state for the audit log
        previous_state = {"is_active": target_user.is_active}
        
        # Suspend the user
        target_user.is_active = False
        target_user.save(update_fields=['is_active'])

        # Log the immutable action
        AuditLogger.log_admin_action(
            admin=request.user,
            action_type=AdminActionType.SUSPEND_USER,
            target=target_user,
            justification=justification,
            previous_state=previous_state,
            new_state={"is_active": False},
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response(
            {"message": f"User {target_user.email} has been suspended."},
            status=status.HTTP_200_OK
        )