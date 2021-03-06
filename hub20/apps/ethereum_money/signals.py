from django.dispatch import Signal

incoming_transfer_broadcast = Signal(providing_args=["account", "amount", "transaction_hash"])
incoming_transfer_mined = Signal(providing_args=["account", "transaction", "amount", "address"])
outgoing_transfer_broadcast = Signal(providing_args=["account", "amount", "transaction_hash"])
outgoing_transfer_mined = Signal(providing_args=["account", "transaction", "amount", "address"])


__all__ = [
    "incoming_transfer_broadcast",
    "incoming_transfer_mined",
    "outgoing_transfer_broadcast",
    "outgoing_transfer_mined",
]
