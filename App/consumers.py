from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from .models import PrintShop


class ShopAdminConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.shop_id = self.scope['url_route']['kwargs']['shop_id']
        self.user = self.scope.get('user', AnonymousUser())

        if self.user.is_anonymous:
            await self.close(code=4401)
            return

        if not await self.can_access_shop(self.user.id, self.shop_id, self.user.is_superuser):
            await self.close(code=4403)
            return

        self.group_name = f'shop_admin_{self.shop_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({
            'type': 'connection.accepted',
            'shop_id': int(self.shop_id),
            'message': 'connected',
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})

    async def shop_event(self, event):
        await self.send_json({
            'type': event.get('event'),
            'shop_id': int(self.shop_id),
            'payload': event.get('payload', {}),
        })

    @database_sync_to_async
    def can_access_shop(self, user_id, shop_id, is_superuser=False):
        shop = PrintShop.objects.select_related('admin_user').filter(pk=shop_id).first()
        if not shop:
            return False
        return is_superuser or shop.admin_user_id == user_id