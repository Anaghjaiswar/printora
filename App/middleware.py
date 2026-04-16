from urllib.parse import parse_qs
import importlib

from asgiref.sync import sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        scope['user'] = await self.get_user(scope)
        return await self.inner(scope, receive, send)

    async def get_user(self, scope):
        query_params = parse_qs(scope.get('query_string', b'').decode())
        token_key = query_params.get('token', [None])[0]

        if not token_key:
            return scope.get('user', AnonymousUser())

        user = await self.get_user_from_token(token_key)
        return user or scope.get('user', AnonymousUser())

    @sync_to_async
    def get_user_from_token(self, token_key):
        try:
            return Token.objects.select_related('user').get(key=token_key).user
        except Token.DoesNotExist:
            return None


def TokenAuthMiddlewareStack(inner):
    try:
        channels_auth = importlib.import_module('channels.auth')
        return TokenAuthMiddleware(channels_auth.AuthMiddlewareStack(inner))
    except ModuleNotFoundError:
        return inner