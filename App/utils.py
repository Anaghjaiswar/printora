import logging
import importlib

from asgiref.sync import async_to_sync


logger = logging.getLogger(__name__)


def serialize_order_for_shop(order):
	documents = []
	for document in order.documents.all():
		documents.append({
			'id': document.id,
			'file_name': document.file_name,
			'page_count': document.page_count,
			'copies': document.copies,
			'color_mode': document.color_mode,
			'sides': document.sides,
			'paper_size': document.paper_size,
		})

	payment = getattr(order, 'payment', None)
	payment_data = None
	if payment:
		payment_data = {
			'status': payment.status,
			'merchant_transaction_id': payment.merchant_transaction_id,
			'phonepe_order_id': payment.phonepe_order_id,
			'phonepe_transaction_id': payment.phonepe_transaction_id,
			'amount': str(payment.amount),
			'payment_method': payment.payment_method,
		}

	return {
		'id': order.id,
		'pickup_token': order.pickup_token,
		'status': order.status,
		'is_paid': order.is_paid,
		'total_amount': str(order.total_amount),
		'ordered_at': order.ordered_at.isoformat() if order.ordered_at else None,
		'completed_at': order.completed_at.isoformat() if order.completed_at else None,
		'shop': {
			'id': order.shop_id,
			'name': getattr(order.shop, 'name', None),
		},
		'customer': {
			'id': order.user_id,
			'email': getattr(order.user, 'email', None),
			'phone': getattr(order.user, 'phone', None),
		},
		'documents': documents,
		'payment': payment_data,
	}


def broadcast_shop_event(shop_id, event_name, payload):
	try:
		channels_layers = importlib.import_module('channels.layers')
		channel_layer = channels_layers.get_channel_layer()
	except ModuleNotFoundError:
		channel_layer = None

	if channel_layer is None:
		logger.warning(
			'Channel layer is not configured; skipping shop event broadcast.',
			extra={'shop_id': shop_id, 'event': event_name},
		)
		return

	async_to_sync(channel_layer.group_send)(
		f'shop_admin_{shop_id}',
		{
			'type': 'shop_event',
			'event': event_name,
			'payload': payload,
		},
	)
