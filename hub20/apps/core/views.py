from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError, Q
from django.db.models.query import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import generics, status
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from hub20.apps.blockchain.models import Chain
from hub20.apps.blockchain.serializers import ChainSerializer
from hub20.apps.ethereum_money.models import EthereumToken

from . import models, serializers

User = get_user_model()


class UserFilter(filters.FilterSet):
    search = filters.CharFilter(label="search", method="user_suggestion")

    def user_suggestion(self, queryset, name, value):
        q_username = Q(username__istartswith=value)
        q_first_name = Q(first_name__istartswith=value)
        q_last_name = Q(last_name__istartswith=value)
        q_email = Q(email__istartswith=value)
        return self.Meta.model.objects.filter(q_username | q_first_name | q_last_name | q_email)

    class Meta:
        model = User
        fields = ("search",)


class ReadWriteSerializerMixin(generics.GenericAPIView):
    """
    Overrides get_serializer_class to choose the read serializer
    for GET requests and the write serializer for POST requests.

    Set read_serializer_class and write_serializer_class attributes on a
    generic APIView
    """

    read_serializer_class: Optional[Serializer] = None
    write_serializer_class: Optional[Serializer] = None

    def get_serializer_class(self) -> Serializer:
        if self.request and self.request.method in ["POST", "PUT", "PATCH"]:
            return self.get_write_serializer_class()
        return self.get_read_serializer_class()

    def get_read_serializer_class(self) -> Serializer:
        assert self.read_serializer_class is not None, (
            "'%s' should either include a `read_serializer_class` attribute,"
            "or override the `get_read_serializer_class()` method." % self.__class__.__name__
        )
        return self.read_serializer_class

    def get_write_serializer_class(self) -> Serializer:
        assert self.write_serializer_class is not None, (
            "'%s' should either include a `write_serializer_class` attribute,"
            "or override the `get_write_serializer_class()` method." % self.__class__.__name__
        )
        return self.write_serializer_class


class AccountCreditEntryList(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.CreditSerializer

    def get_queryset(self) -> QuerySet:
        return models.Credit.objects.filter(book__account__user=self.request.user)


class AccountDebitEntryList(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.DebitSerializer

    def get_queryset(self) -> QuerySet:
        return self.request.user.account.debits.all()


class BaseDepositView:
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.DepositSerializer


class DepositListView(BaseDepositView, generics.ListCreateAPIView):
    def get_queryset(self) -> QuerySet:
        return self.request.user.deposit_set.all()


class DepositView(BaseDepositView, generics.RetrieveAPIView):
    def get_object(self) -> models.Deposit:
        return get_object_or_404(models.Deposit, pk=self.kwargs.get("pk"), user=self.request.user)


class BasePaymentOrderView(ReadWriteSerializerMixin):
    read_serializer_class = serializers.PaymentOrderReadSerializer
    write_serializer_class = serializers.PaymentOrderSerializer


class PaymentOrderListView(BasePaymentOrderView, generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self) -> QuerySet:
        return models.PaymentOrder.objects.filter(user=self.request.user)


class PaymentOrderView(BasePaymentOrderView, generics.RetrieveDestroyAPIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self) -> models.PaymentOrder:
        return get_object_or_404(
            models.PaymentOrder, pk=self.kwargs.get("pk"), user=self.request.user
        )

    def destroy(self, request, pk=None):
        try:
            return super().destroy(request, pk=pk)
        except ProtectedError:
            return Response(
                "Order has either been paid or has open routes and can not be canceled",
                status=status.HTTP_400_BAD_REQUEST,
            )


class TransferListView(generics.ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.TransferSerializer

    def get_queryset(self) -> QuerySet:
        return self.request.user.transfers_sent.all()


class TransferView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.TransferSerializer

    def get_object(self):
        try:
            return models.Transfer.objects.get(pk=self.kwargs.get("pk"), sender=self.request.user)
        except models.Transfer.DoesNotExist:
            raise Http404


class TokenBalanceListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.HyperlinkedTokenBalanceSerializer

    def get_queryset(self) -> QuerySet:
        return self.request.user.account.get_balances()


class TokenBalanceView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.HyperlinkedTokenBalanceSerializer

    def get_object(self) -> EthereumToken:
        token = get_object_or_404(EthereumToken, address=self.kwargs["address"])
        return self.request.user.account.get_balance(token)


class CheckoutViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin):
    permission_classes = (AllowAny,)
    serializer_class = serializers.HttpCheckoutSerializer
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return models.Checkout.objects.all()

    def get_object(self):
        return get_object_or_404(models.Checkout, id=self.kwargs["pk"])


class PaymentViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return models.Payment.objects.all()

    def get_permissions(self):
        permission_class = IsAdminUser if self.action == "list" else AllowAny
        return (permission_class(),)

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.PaymentSerializer

        payment = self.get_object()

        return {
            models.InternalPayment: serializers.InternalPaymentSerializer,
            models.BlockchainPayment: serializers.BlockchainPaymentSerializer,
            models.RaidenPayment: serializers.RaidenPaymentSerializer,
        }.get(type(payment), serializers.PaymentSerializer)

    def get_object(self):
        try:
            return models.Payment.objects.get_subclass(id=self.kwargs["pk"])
        except (models.Payment.DoesNotExist, KeyError):
            return None


class StoreViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.StoreSerializer

    def get_permissions(self):
        perms = (AllowAny,) if self.action == "retrieve" else (IsAuthenticated,)
        return (perm() for perm in perms)

    def get_queryset(self) -> QuerySet:
        return self.request.user.store_set.all()

    def get_object(self, *args, **kw):
        return get_object_or_404(models.Store, id=self.kwargs["pk"])


class UserViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserSerializer
    filterset_class = UserFilter
    filter_backends = (filters.DjangoFilterBackend,)
    lookup_field = "username"

    def get_queryset(self) -> QuerySet:
        return User.objects.filter(is_active=True, is_superuser=False, is_staff=False)

    def get_object(self, *args, **kw):
        return get_object_or_404(
            User,
            is_active=True,
            is_superuser=False,
            is_staff=False,
            username=self.kwargs["username"],
        )


class StatusView(APIView):
    permission_classes = (IsAuthenticated,)


class NetworkStatusView(StatusView):
    permission_classes = (AllowAny,)

    def get(self, request, **kw):
        chain = Chain.make()
        return Response({"ethereum": ChainSerializer(chain).data})


class AccountingReportView(StatusView):
    permission_classes = (IsAdminUser,)

    def _get_serialized_book(self, accounting_model_class):
        return serializers.AccountingBookSerializer(
            accounting_model_class.balance_sheet(), many=True, context={"request": self.request}
        ).data

    def get(self, request, **kw):
        return Response(
            dict(
                treasury=self._get_serialized_book(models.Treasury),
                wallets=self._get_serialized_book(models.WalletAccount),
                raiden=self._get_serialized_book(models.RaidenClientAccount),
                user_accounts=self._get_serialized_book(models.UserAccount),
                external_addresses=self._get_serialized_book(models.ExternalAddressAccount),
            )
        )


class EthereumAccountBalanceSheets(StatusView):
    permission_classes = (IsAdminUser,)

    def _get_serialized_balances(self, account):
        return serializers.AccountingBookSerializer(
            account.get_balances(), many=True, context={"request": self.request}
        ).data

    def get(self, request, **kw):
        return Response(
            {
                account.account.address: self._get_serialized_balances(account)
                for account in models.WalletAccount.objects.all()
            }
        )
