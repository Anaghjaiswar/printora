from django.urls import path

from .consumers import ShopAdminConsumer


websocket_urlpatterns = [
    path('ws/admin/shops/<int:shop_id>/', ShopAdminConsumer.as_asgi(), name='shop-admin-ws'),
]