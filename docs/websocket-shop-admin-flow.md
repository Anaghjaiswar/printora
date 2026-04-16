# Shop Admin Websocket Flow

This document defines the websocket contract for the print shop admin panel.

## Purpose

The admin frontend connects to a shop-scoped websocket channel to receive live order updates.
Each shop has its own socket room, so only the linked admin user receives events for that shop.

## Transport

- Websocket route: `/ws/admin/shops/<shop_id>/`
- Query auth token: `?token=<drf_token>`
- Redis is used as the websocket broker through Django Channels.

## Authentication Rules

- The token must belong to the admin user who owns the shop.
- Superusers may connect to any shop by passing the target `shop_id`.
- If the token is missing or invalid, the connection is rejected with close code `4401`.
- If the user does not belong to the shop, the connection is rejected with close code `4403`.

## Connect Example

```text
ws://127.0.0.1:8000/ws/admin/shops/1/?token=YOUR_DRF_TOKEN
```

## Channel Group Naming

- Internal Redis group name: `shop_admin_<shop_id>`

## Initial Data Load

Before subscribing to the websocket, the frontend can load the initial order list with:

- `GET /api/admin/shop/orders/`

Optional:

- `GET /api/admin/shop/orders/?status=COMPLETED`
- Superusers can use `GET /api/admin/shop/orders/?shop_id=1`

## Websocket Messages

Server-to-client messages follow this structure:

```json
{
  "type": "order.created",
  "shop_id": 1,
  "payload": {
    "id": 101,
    "pickup_token": "P-123",
    "status": "PLACED"
  }
}
```

### Connection Acknowledgement

```json
{
  "type": "connection.accepted",
  "shop_id": 1,
  "message": "connected"
}
```

### Supported Event Types

- `order.created`
- `order.payment.updated`

## Event Payload Shape

The payload is a serialized order object:

```json
{
  "id": 101,
  "pickup_token": "P-123",
  "status": "PLACED",
  "is_paid": false,
  "total_amount": "125.00",
  "ordered_at": "2026-04-14T10:20:00+05:30",
  "completed_at": null,
  "shop": {
    "id": 1,
    "name": "Library Print Shop"
  },
  "customer": {
    "id": 44,
    "email": "user@example.com",
    "phone": "+91 90000 00000"
  },
  "documents": [
    {
      "id": 900,
      "file_name": "assignment.pdf",
      "page_count": 24,
      "copies": 1,
      "color_mode": "BW",
      "sides": "SINGLE",
      "paper_size": "A4"
    }
  ],
  "payment": {
    "status": "SUCCESS",
    "merchant_transaction_id": "PO-101-AB12CD34",
    "phonepe_order_id": "...",
    "phonepe_transaction_id": "...",
    "amount": "125.00",
    "payment_method": "UPI"
  }
}
```

## Client Rules

- Open the websocket only after the admin login API returns the token and shop id.
- Use the returned `shop.id` to construct the websocket URL.
- Reconnect on disconnect with the same token and shop id.
- Treat websocket messages as push updates only; the frontend should still load the initial list with REST.

## Backend Notes

- Broadcasts are sent from order creation and payment webhook updates.
- Redis is the websocket broker through `CHANNEL_LAYERS`.
- The frontend team only needs to consume the messages above and update the UI state.