from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Any

from django.conf import settings
from phonepe.sdk.pg.common.models.request.meta_info import MetaInfo
from phonepe.sdk.pg.env import Env
from phonepe.sdk.pg.payments.v2.models.request.create_sdk_order_request import (
    CreateSdkOrderRequest,
)
from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import (
    StandardCheckoutPayRequest,
)
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient


@lru_cache(maxsize=1)
def get_phonepe_client() -> StandardCheckoutClient:
    client_id = settings.PHONEPE_CLIENT_ID or settings.PHONEPE_MERCHANT_ID
    client_secret = settings.PHONEPE_CLIENT_SECRET or settings.PHONEPE_SALT_KEY
    client_version = int(settings.PHONEPE_CLIENT_VERSION or 1)
    env_name = (settings.PHONEPE_ENV or 'SANDBOX').upper()
    env = Env.PRODUCTION if env_name == 'PRODUCTION' else Env.SANDBOX

    if not client_id or not client_secret:
        raise ValueError('PhonePe client credentials are not configured.')

    return StandardCheckoutClient.get_instance(
        client_id=client_id,
        client_secret=client_secret,
        client_version=client_version,
        env=env,
        should_publish_events=False,
    )


def build_redirect_url(merchant_order_id: str) -> str:
    base_url = (settings.FRONTEND_URL or settings.BACKEND_URL or '').rstrip('/')
    if not base_url:
        return ''
    return f'{base_url}/payment-status/{merchant_order_id}/'


def build_meta_info(*, order_id: int, user_id: int, shop_id: int, document_count: int) -> MetaInfo:
    return MetaInfo(
        udf1=str(order_id),
        udf2=str(user_id),
        udf3=str(shop_id),
        udf4=str(document_count),
    )


def to_paise(amount: Decimal) -> int:
    return int((Decimal(amount) * Decimal('100')).quantize(Decimal('1')))


def initiate_standard_checkout(
    *,
    merchant_order_id: str,
    amount_paise: int,
    redirect_url: str,
    meta_info: MetaInfo | None = None,
    expire_after: int = 3600,
    disable_payment_retry: bool = True,
):
    pay_request = StandardCheckoutPayRequest.build_request(
        merchant_order_id=merchant_order_id,
        amount=amount_paise,
        meta_info=meta_info,
        redirect_url=redirect_url,
        expire_after=expire_after,
        disable_payment_retry=disable_payment_retry,
    )
    return get_phonepe_client().pay(pay_request)


def create_sdk_order(
    *,
    merchant_order_id: str,
    amount_paise: int,
    meta_info: MetaInfo | None = None,
    disable_payment_retry: bool = True,
):
    sdk_order_request = CreateSdkOrderRequest.build_standard_checkout_request(
        merchant_order_id=merchant_order_id,
        amount=amount_paise,
        meta_info=meta_info,
        disable_payment_retry=disable_payment_retry,
    )
    return get_phonepe_client().create_sdk_order(sdk_order_request=sdk_order_request)


def get_order_status(merchant_order_id: str, *, details: bool = False):
    return get_phonepe_client().get_order_status(merchant_order_id, details=details)


def validate_callback(authorization_header: str, response_body: str):
    username = settings.PHONEPE_CALLBACK_USERNAME
    password = settings.PHONEPE_CALLBACK_PASSWORD

    if not username or not password:
        raise ValueError('PhonePe callback credentials are not configured.')

    return get_phonepe_client().validate_callback(
        username=username,
        password=password,
        callback_header_data=authorization_header,
        callback_response_data=response_body,
    )


def serialize_phonepe_value(value: Any):
    if isinstance(value, list):
        return [serialize_phonepe_value(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_phonepe_value(item) for key, item in value.items()}
    if hasattr(value, '__dict__'):
        return {
            key: serialize_phonepe_value(item)
            for key, item in vars(value).items()
            if not key.startswith('_')
        }
    return value
