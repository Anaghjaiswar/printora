"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import importlib

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django_asgi_application = get_asgi_application()

try:
	channels_routing = importlib.import_module('channels.routing')
	from App.middleware import TokenAuthMiddlewareStack
	from App.routing import websocket_urlpatterns

	application = channels_routing.ProtocolTypeRouter({
		'http': django_asgi_application,
		'websocket': TokenAuthMiddlewareStack(
			channels_routing.URLRouter(websocket_urlpatterns)
		),
	})
except ModuleNotFoundError:
	application = django_asgi_application
