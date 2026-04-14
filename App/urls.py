from django.urls import path
from .views import (
    SignupView,
    LoginView,
    LogoutView,
    PrintShopViewSet,
    ServiceViewSet,
    DocumentUploadView,
    CreateSdkOrderView,
    AllOrdersView,
    PhonePeOrderStatusView,
    PhonePeWebhookView,
)




urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('shops/', PrintShopViewSet.as_view({'get': 'list'}), name='shop-list'),
    path('services/', ServiceViewSet.as_view({'get': 'list'}), name='service-list'),
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('create-sdk-order/', CreateSdkOrderView.as_view(), name='create-sdk-order'),
    path('orders/', AllOrdersView.as_view(), name='all-orders'),
    path('payment-status/<str:merchant_order_id>/', PhonePeOrderStatusView.as_view(), name='phonepe-order-status'),
    path('payment/webhook/', PhonePeWebhookView.as_view(), name='phonepe-webhook'),
]