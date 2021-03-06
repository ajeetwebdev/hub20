from django.db.models.query import QuerySet
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from hub20.apps.ethereum_money.app_settings import TRACKED_TOKENS

from . import models, serializers


class BaseRaidenViewMixin:
    permission_classes = (IsAdminUser,)


class RaidenViewSet(
    BaseRaidenViewMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = serializers.RaidenSerializer

    def get_queryset(self, *args, **kw):
        return models.Raiden.objects.all()


class ChannelViewMixin(BaseRaidenViewMixin):
    serializer_class = serializers.ChannelSerializer

    def get_queryset(self, *args, **kw):
        return models.Channel.objects.filter(raiden_id=self.kwargs["raiden_pk"])

    def get_object(self):
        return self.get_queryset().filter(pk=self.kwargs["pk"]).first()


class ServiceDepositMixin(BaseRaidenViewMixin):
    serializer_class = serializers.ServiceDepositSerializer

    def get_queryset(self, *args, **kw):
        raiden = models.Raiden.objects.first()
        return raiden and models.UserDepositContractOrder.objects.filter(raiden=raiden)


class ChannelViewSet(
    ChannelViewMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    @action(
        detail=True,
        methods=["POST"],
        serializer_class=serializers.ChannelDepositSerializer,
    )
    def deposit(self, request, *args, **kw):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=["POST"],
        serializer_class=serializers.ChannelWithdrawSerializer,
    )
    def withdraw(self, request, *args, **kw):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ServiceDepositListView(ServiceDepositMixin, generics.ListCreateAPIView):
    pass


class ServiceDepositDetailView(ServiceDepositMixin, generics.RetrieveAPIView):
    pass


class TokenNetworkViewMixin:
    permission_classes = (IsAdminUser,)
    serializer_class = serializers.TokenNetworkSerializer
    lookup_field = "address"
    lookup_url_kwarg = "address"
    queryset: QuerySet = models.TokenNetwork.objects.filter(token__address__in=TRACKED_TOKENS)


class TokenNetworkViewSet(
    TokenNetworkViewMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    def destroy(self, request, *args, **kw):
        raiden = models.Raiden.objects.first()

        if raiden:
            models.LeaveTokenNetworkOrder.objects.create(
                raiden=raiden, user=request.user, token_network=self.get_object()
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=["post"], serializer_class=serializers.JoinTokenNetworkOrderSerializer
    )
    def join(self, request, address=None):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
