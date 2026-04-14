import json
import logging
import uuid
from decimal import Decimal

from django.contrib.auth import authenticate
from django.db import transaction
from phonepe.sdk.pg.common.exceptions import PhonePeException #type:ignore
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, Order, Payment, PrintShop, Service
from .phonepe_service import (
    build_meta_info,
    create_sdk_order as phonepe_create_sdk_order,
    get_order_status as phonepe_get_order_status,
    serialize_phonepe_value,
    to_paise,
    validate_callback,
)
from .serializers import DocumentSerializer, OrderSerializer, PrintShopSerializer, ServiceSerializer, UserSerializer


logger = logging.getLogger(__name__)


def _parse_document_ids(raw_document_ids):
    if isinstance(raw_document_ids, list):
        return [int(document_id) for document_id in raw_document_ids if str(document_id).isdigit()]

    if isinstance(raw_document_ids, str):
        try:
            parsed_value = json.loads(raw_document_ids)
        except json.JSONDecodeError:
            parsed_value = [value.strip() for value in raw_document_ids.split(',') if value.strip()]

        if isinstance(parsed_value, list):
            return [int(document_id) for document_id in parsed_value if str(document_id).isdigit()]

    return []


def _create_payment_for_order(order):
    merchant_transaction_id = f"PO-{order.id}-{uuid.uuid4().hex[:8].upper()}"
    payment = Payment.objects.create(
        order=order,
        merchant_transaction_id=merchant_transaction_id,
        amount=order.total_amount,
    )

    phonepe_amount = to_paise(order.total_amount)
    meta_info = build_meta_info(
        order_id=order.id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        document_count=order.documents.count(),
    )

    try:
        phonepe_response = phonepe_create_sdk_order(
            merchant_order_id=merchant_transaction_id,
            amount_paise=phonepe_amount,
            meta_info=meta_info,
            disable_payment_retry=True,
        )
    except PhonePeException as exc:
        payment.status = 'FAILED'
        payment.save(update_fields=['status', 'updated_at'])
        raise RuntimeError(f'PhonePe API error: {exc.message}') from exc

    payment.phonepe_order_id = getattr(phonepe_response, 'order_id', None) or getattr(phonepe_response, 'orderId', None)
    payment.save(update_fields=['phonepe_order_id', 'updated_at'])

    response_data = {
        'order_id': order.id,
        'pickup_token': order.pickup_token,
        'merchant_order_id': merchant_transaction_id,
        'phonepe_order_id': payment.phonepe_order_id,
        'total_amount': str(order.total_amount),
    }

    response_data.update({
        'token': getattr(phonepe_response, 'token', None),
        'state': getattr(phonepe_response, 'state', None),
        'expire_at': getattr(phonepe_response, 'expire_at', None) or getattr(phonepe_response, 'expireAt', None),
    })

    return response_data

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
    


class CreateSdkOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        document_ids = _parse_document_ids(request.data.get('document_ids', []))
        shop_id = request.data.get('shop_id')

        if not document_ids or not shop_id:
            return Response({"error": "Missing documents or shop ID"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            shop = PrintShop.objects.get(id=shop_id)
            documents = list(Document.objects.filter(id__in=document_ids, user=user).select_related('service'))

            if len(documents) != len(set(document_ids)):
                return Response({"error": "One or more documents are invalid or do not belong to the current user"}, status=status.HTTP_400_BAD_REQUEST)

            total_amount = Decimal('0.00')
            for doc in documents:
                if not doc.service:
                    return Response({"error": f"Document {doc.id} does not have a valid service"}, status=status.HTTP_400_BAD_REQUEST)
                rate = doc.service.color_price if doc.color_mode == 'COLOR' else doc.service.bw_price
                total_amount += Decimal(rate) * doc.page_count * doc.copies

            if total_amount <= 0:
                return Response({"error": "Order amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)

            pickup_token = f"P-{str(uuid.uuid4().int)[:3]}"

            with transaction.atomic():
                order = Order.objects.create(
                    user=user,
                    shop=shop,
                    total_amount=total_amount,
                    pickup_token=pickup_token,
                )
                order.documents.set(documents)

            response_data = _create_payment_for_order(order)
            response_data['total_amount'] = str(total_amount)

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AllOrdersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = (
            Order.objects.filter(user=request.user)
            .select_related('shop', 'payment')
            .prefetch_related('documents', 'documents__service')
            .order_by('-ordered_at')
        )

        order_status = request.query_params.get('status')
        if order_status:
            queryset = queryset.filter(status=order_status)

        serializer = OrderSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PhonePeOrderStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, merchant_order_id):
        try:
            response = phonepe_get_order_status(merchant_order_id, details=request.query_params.get('details', 'false').lower() == 'true')
            return Response({
                'merchant_order_id': merchant_order_id,
                'order_id': getattr(response, 'order_id', None) or getattr(response, 'orderId', None),
                'state': getattr(response, 'state', None),
                'expire_at': getattr(response, 'expire_at', None) or getattr(response, 'expireAt', None),
                'amount': getattr(response, 'amount', None),
                'meta_info': serialize_phonepe_value(getattr(response, 'meta_info', None) or getattr(response, 'metaInfo', None)),
                'error_code': getattr(response, 'error_code', None) or getattr(response, 'errorCode', None),
                'detailed_error_code': getattr(response, 'detailed_error_code', None) or getattr(response, 'detailedErrorCode', None),
                'payment_details': serialize_phonepe_value(getattr(response, 'payment_details', None) or getattr(response, 'paymentDetails', None)),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PhonePeWebhookView(APIView):
    permission_classes = [permissions.AllowAny] # PhonePe calls this

    def post(self, request):
        authorization_header = request.headers.get('Authorization', '')
        response_body = request.body.decode('utf-8')

        try:
            callback_response = validate_callback(authorization_header, response_body)
            callback_event = getattr(callback_response, 'event', None) or getattr(callback_response, 'type', None)
            payload = getattr(callback_response, 'payload', None)

            merchant_order_id = (
                getattr(payload, 'original_merchant_order_id', None)
                or getattr(payload, 'merchant_order_id', None)
                or getattr(payload, 'originalMerchantOrderId', None)
            )
            phonepe_order_id = getattr(payload, 'order_id', None) or getattr(payload, 'orderId', None)
            payment_state = getattr(payload, 'state', None)
            payment_details = getattr(payload, 'payment_details', None) or getattr(payload, 'paymentDetails', None)

            if not merchant_order_id:
                logger.warning('PhonePe webhook payload missing merchant order id', extra={'event': callback_event})
                return Response({
                    "status": "ignored",
                    "reason": "missing_merchant_order_id",
                    "event": callback_event,
                }, status=status.HTTP_200_OK)

            with transaction.atomic():
                payment = Payment.objects.select_related('order').get(merchant_transaction_id=merchant_order_id)

                payment.phonepe_order_id = phonepe_order_id or payment.phonepe_order_id

                if payment_state == 'COMPLETED' or callback_event == 'checkout.order.completed':
                    payment.status = 'SUCCESS'
                    payment.order.is_paid = True
                    payment.order.save(update_fields=['is_paid'])

                    if payment_details:
                        first_attempt = payment_details[0]
                        payment.phonepe_transaction_id = getattr(first_attempt, 'transaction_id', None) or getattr(first_attempt, 'transactionId', None) or payment.phonepe_transaction_id
                else:
                    payment.status = 'FAILED'

                payment.save(update_fields=['phonepe_order_id', 'phonepe_transaction_id', 'status', 'updated_at'])

            return Response({
                'status': 'received',
                'event': callback_event,
                'merchant_order_id': merchant_order_id,
                'phonepe_order_id': phonepe_order_id,
            }, status=status.HTTP_200_OK)

        except Payment.DoesNotExist:
            logger.warning('PhonePe webhook payment not found', exc_info=True)
            return Response({
                "status": "ignored",
                "reason": "payment_not_found",
            }, status=status.HTTP_200_OK)
        except ValueError as exc:
            logger.warning('PhonePe webhook validation error: %s', str(exc), exc_info=True)
            return Response({
                "status": "ignored",
                "reason": "validation_error",
                "message": str(exc),
            }, status=status.HTTP_200_OK)
        except PhonePeException as exc:
            logger.warning('PhonePe webhook SDK error: %s', exc.message, exc_info=True)
            return Response({
                "status": "ignored",
                "reason": "phonepe_sdk_error",
                "message": exc.message,
            }, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.exception('Unexpected PhonePe webhook error: %s', str(exc))
            return Response({
                "status": "ignored",
                "reason": "unexpected_error",
                "message": str(exc),
            }, status=status.HTTP_200_OK)

class ShopLoginView(APIView):

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        user = authenticate(email=email, password=password)
        
        if user:
            is_staff_user = user.is_staff
            if is_staff_user:

                shop = PrintShop.objects.get(admin_user=user)

                if not shop:
                    return Response({
                        "ok": False,
                        "message": "No print shop is linked to this admin user.",
                        "data": ""
                    }, status=status.HTTP_400_BAD_REQUEST)

                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    "ok": True,
                    "message" : "data fetched successfully.",
                    "token": token.key,
                    "user_id": user.pk,
                    "email": user.email,
                    "shop": {
                        "id": shop.id,
                        "name": shop.name,
                    }
                })
            else:
                return Response({
                    "ok" : False,
                    "message" : "you are not entitled to admin login",
                    "data" :""
                })
        else:
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)