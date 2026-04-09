from django.urls import path
from .views import SignupView, LoginView, LogoutView, PrintShopViewSet, ServiceViewSet, DocumentUploadView




urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('shops/', PrintShopViewSet.as_view({'get': 'list'}), name='shop-list'),
    path('services/', ServiceViewSet.as_view({'get': 'list'}), name='service-list'),
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
]