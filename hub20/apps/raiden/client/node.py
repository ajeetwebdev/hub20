from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from types import FunctionType
from typing import Any, Dict, List, Optional, Union

import requests
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.utils.timezone import make_aware
from ethereum.utils import checksum_encode
from web3.datastructures import AttributeDict

from hub20.apps.blockchain.typing import Address
from hub20.apps.ethereum_money.models import EthereumTokenAmount
from hub20.apps.raiden.exceptions import RaidenConnectionError, RaidenPaymentError
from hub20.apps.raiden.models import Channel, Payment, Raiden, TokenNetwork

User = get_user_model()

logger = logging.getLogger(__name__)


def _make_request(url: str, method: str = "GET", **payload: Any) -> Union[List, Dict]:
    try:
        action = {
            "GET": requests.get,
            "PATCH": requests.patch,
            "PUT": requests.put,
            "POST": requests.post,
            "DELETE": requests.delete,
        }[method.strip().upper()]
    except KeyError:
        raise ValueError(f"{method} is not valid")

    try:
        assert isinstance(action, FunctionType)
        response = action(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise RaidenConnectionError(f"Could not connect to {url}")


class RaidenClient:
    URL_BASE_PATH = "/api/v1"

    def __init__(self, raiden_account: Raiden) -> None:
        self.raiden = raiden_account

    def _parse_payment(self, payment_data: Dict, channel: Channel) -> Optional[AttributeDict]:
        event_name = payment_data.pop("event")
        payment_data.pop("token_address", None)

        if event_name == "EventPaymentReceivedSuccess":
            payment_data["sender_address"] = payment_data.pop("initiator")
            payment_data["receiver_address"] = self.raiden.address
        elif event_name == "EventPaymentSentSuccess":
            payment_data["sender_address"] = self.raiden.address
            payment_data["receiver_address"] = payment_data.pop("target")
        else:
            return None

        iso_time = payment_data.pop("log_time")

        payment_data["amount"] = channel.token.from_wei(payment_data.pop("amount")).amount
        payment_data["timestamp"] = make_aware(datetime.fromisoformat(iso_time))
        return AttributeDict(payment_data)

    def _refresh_channel(self, channel: Channel) -> Channel:
        channel_data = _make_request(self.channel_endpoint(channel=channel))
        assert isinstance(channel_data, dict)
        Channel.make(channel.raiden, **channel_data)
        channel.refresh_from_db()
        return channel

    @property
    def raiden_root_endpoint(self) -> str:
        return f"{self.raiden.url}{self.URL_BASE_PATH}"

    @property
    def raiden_channel_list_endpoint(self) -> str:
        return f"{self.raiden_root_endpoint}/channels"

    @property
    def raiden_token_list_endpoint(self) -> str:
        return f"{self.raiden_root_endpoint}/tokens"

    def channel_endpoint(self, channel: Channel) -> str:
        raiden_endpoint = self.raiden_root_endpoint
        return f"{raiden_endpoint}/channels/{channel.token.address}/{channel.partner_address}"

    def channel_payment_list_endpoint(self, channel: Channel) -> str:
        raiden_endpoint = self.raiden_root_endpoint
        return f"{raiden_endpoint}/payments/{channel.token.address}/{channel.partner_address}"

    def token_network_endpoint(self, token_network: TokenNetwork) -> str:
        raiden_endpoint = self.raiden_root_endpoint
        return f"{raiden_endpoint}/connections/{token_network.token.address}"

    def get_channels(self):
        return [
            Channel.make(self.raiden, **channel_data)
            for channel_data in _make_request(self.raiden_channel_list_endpoint)
        ]

    def get_new_payments(self):
        for channel in self.raiden.channels.all():
            offset = channel.payments.count()
            events = _make_request(
                self.channel_payment_list_endpoint(channel=channel), offset=offset
            )
            assert type(events) is list

            payments = [self._parse_payment(ev, channel) for ev in events]

            for payment_data in [payment for payment in payments if payment is not None]:
                Payment.make(channel, **payment_data)

    def get_token_addresses(self):
        return _make_request(self.raiden_token_list_endpoint)

    def get_status(self):
        try:
            response = _make_request(f"{self.raiden_root_endpoint}/status")
            assert type(response) is dict
            return response.get("status")
        except RaidenConnectionError:
            return "offline"

    def join_token_network(self, token_network: TokenNetwork, amount: EthereumTokenAmount):
        url = self.token_network_endpoint(token_network=token_network)
        return _make_request(url, method="PUT", funds=amount.as_wei)

    def leave_token_network(self, token_network: TokenNetwork):
        url = self.token_network_endpoint(token_network=token_network)
        return _make_request(url, method="DELETE")

    def make_channel_deposit(self, channel: Channel, amount: EthereumTokenAmount):
        channel = self._refresh_channel(channel)
        new_deposit = channel.deposit_amount + amount

        return _make_request(
            self.channel_endpoint(channel), method="PATCH", total_deposit=new_deposit.as_wei
        )

    def make_channel_withdraw(self, channel: Channel, amount: EthereumTokenAmount):
        channel = self._refresh_channel(channel)
        new_withdraw = channel.withdraw_amount + amount
        return _make_request(
            self.channel_endpoint(channel=channel),
            method="PATCH",
            total_withdraw=new_withdraw.as_wei,
        )

    def _ensure_valid_identifier(self, identifier: Optional[str] = None) -> Optional[int]:
        if not identifier:
            return None

        try:
            identifier = int(identifier)
        except ValueError:
            identifier = int(identifier.encode().hex(), 16)

        return identifier % Payment.MAX_IDENTIFIER_ID

    def transfer(
        self, amount: EthereumTokenAmount, address: Address, identifier: Optional[int] = None, **kw
    ) -> Optional[str]:
        url = f"{self.raiden_root_endpoint}/payments/{amount.currency.address}/{address}"

        payload = dict(amount=amount.as_wei)

        if identifier:
            payload["identifier"] = identifier

        try:
            payment_data = _make_request(url, method="POST", **payload)
            assert isinstance(payment_data, dict)
            return payment_data.get("identifier")
        except requests.exceptions.HTTPError as error:
            logger.exception(error)

            error_code = error.response.status_code
            message = error.response.json().get("errors")
            raise RaidenPaymentError(error_code=error_code, message=message) from error

    @classmethod
    def get_node_account_address(cls, url) -> Address:
        response = _make_request(f"{url}{cls.URL_BASE_PATH}/address")
        assert isinstance(response, dict)
        return checksum_encode(response.get("our_address"))

    @classmethod
    def make(cls, url) -> RaidenClient:
        account_address: Address = cls.get_node_account_address(url)
        raiden_account, _ = Raiden.objects.get_or_create(address=account_address, url=url)
        return cls(raiden_account=raiden_account)

    @classmethod
    def select_for_transfer(
        cls,
        amount: EthereumTokenAmount,
        receiver: Optional[User] = None,
        address: Optional[Address] = None,
    ) -> Optional[RaidenClient]:
        if address is None:
            return None

        # Token is not part of a token network.
        if not hasattr(amount.currency, "tokennetwork"):
            return None

        token_channels = Channel.available.filter(
            token_network__token=amount.currency, balance__gte=amount.amount
        )

        if not token_channels.exists():
            return None

        if not amount.currency.tokennetwork.can_reach(address):
            return None

        raiden_account = Raiden.objects.first()

        return raiden_account and cls(raiden_account=raiden_account)


async def sync_channels(raiden_client: RaidenClient, **kw):
    while True:
        await asyncio.sleep(30)
        try:
            await sync_to_async(raiden_client.get_channels)()
        except RaidenConnectionError as exc:
            logger.error(f"Failed to connect to raiden node: {exc}")


async def sync_payments(raiden_client: RaidenClient, **kw):
    while True:
        await asyncio.sleep(5)
        try:
            await sync_to_async(raiden_client.get_new_payments)()
        except RaidenConnectionError as exc:
            logger.error(f"Failed to connect to raiden node: {exc}")
