from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.conf import settings
from .serializers import UserSerializer
from rest_framework import viewsets
from .models import PrintShop, Service, Document, Order, Payment
from .serializers import PrintShopSerializer, ServiceSerializer, DocumentSerializer
from rest_framework.parsers import MultiPartParser, FormParser
import uuid
import base64
import json

class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        user = authenticate(email=email, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user_id": user.pk,
                "email": user.email
            })
        else:
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    # Sirf login kiye hue users hi logout kar sakte hain
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # User ka current token delete kar rahe hain
            request.user.auth_token.delete()
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST)
        

class PrintShopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Print Shops to be viewed.
    """
    queryset = PrintShop.objects.filter(status='open')
    serializer_class = PrintShopSerializer

class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Services to be viewed.
    """
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer

    def get_queryset(self):
        # Allow filtering services by shop_id via query params: /api/services/?shop_id=1
        queryset = Service.objects.filter(is_active=True)
        shop_id = self.request.query_params.get('shop_id')
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)
        return queryset
    
class DocumentUploadView(APIView):
    """
    API endpoint to upload a document (PDF/Image).
    Automatically calculates page count for PDFs.
    """
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # We pass the user context to the serializer so it can assign the document to the logged-in user
        serializer = DocumentSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class CreateOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        document_ids = request.data.get('document_ids', [])
        shop_id = request.data.get('shop_id')

        if not document_ids or not shop_id:
            return Response({"error": "Missing documents or shop ID"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = PrintShop.objects.get(id=shop_id)
            documents = Document.objects.filter(id__in=document_ids, user=user)
            
            # 1. Calculate Total Amount
            total_amount = 0
            for doc in documents:
                # Get price based on color mode
                rate = doc.service.color_price if doc.color_mode == 'COLOR' else doc.service.bw_price
                doc_total = rate * doc.page_count * doc.copies
                total_amount += doc_total

            # 2. Generate Pickup Token (e.g., P-random)
            pickup_token = f"P-{str(uuid.uuid4().int)[:3]}"

            # 3. Create Order
            order = Order.objects.create(
                user=user,
                shop=shop,
                total_amount=total_amount,
                pickup_token=pickup_token
            )
            order.documents.set(documents)

            # 4. Initiate PhonePe Payment
            merchant_transaction_id = f"MT{uuid.uuid4().hex[:10].upper()}"
            
            # PhonePe Payload
            payload = {
                "merchantId": settings.PHONEPE_MERCHANT_ID,
                "merchantTransactionId": merchant_transaction_id,
                "merchantUserId": str(user.id),
                "amount": int(total_amount * 100), # Amount in paise
                "redirectUrl": f"https://yourdomain.com/payment-status/{merchant_transaction_id}/",
                "redirectMode": "REDIRECT",
                "callbackUrl": "https://your-api-domain.com/api/payment/webhook/",
                "paymentInstrument": {"type": "PAY_PAGE"}
            }

            # Save Payment record as Pending
            Payment.objects.create(
                order=order,
                merchant_transaction_id=merchant_transaction_id,
                amount=total_amount
            )

            # Note: You'll need to implement the PhonePe SHA256 header logic here
            # For now, returning order details and a mock payment link
            return Response({
                "order_id": order.id,
                "total_amount": total_amount,
                "pickup_token": pickup_token,
                "merchant_transaction_id": merchant_transaction_id,
                "payment_url": "https://mercuri.phonepe.com/transact/pg?token=..." # This comes from PhonePe API
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PhonePeWebhookView(APIView):
    permission_classes = [permissions.AllowAny] # PhonePe calls this

    def post(self, request):
        # 1. Decode PhonePe Response (Base64)
        response_data = request.data.get('response')
        decoded_response = json.loads(base64.b64decode(response_data).decode('utf-8'))
        
        # 2. Verify check-sum (Mandatory for security)
        # Check PhonePe docs for signature verification logic

        merchant_id = decoded_response.get('data', {}).get('merchantId')
        transaction_id = decoded_response.get('data', {}).get('merchantTransactionId')
        success = decoded_response.get('success')

        try:
            payment = Payment.objects.get(merchant_transaction_id=transaction_id)
            if success:
                payment.status = 'SUCCESS'
                payment.order.is_paid = True
                payment.order.save()
            else:
                payment.status = 'FAILED'
            
            payment.save()
            return Response({"status": "received"}, status=status.HTTP_200_OK)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)