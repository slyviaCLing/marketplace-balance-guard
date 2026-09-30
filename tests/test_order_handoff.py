from marketplace_balance_guard.order_handoff import (
    BuyerUpdate,
    OrderHandoffRequest,
    OrderHandoffService,
    SellerAsset,
)


class RecordingGateway:
    def __init__(self, balance: float) -> None:
        self.current_balance = balance
        self.recharge_calls: list[dict[str, float]] = []
        self.emails: list[dict[str, str]] = []

    def balance(self) -> dict[str, object]:
        return {"balance": self.current_balance}

    def configure_autorecharge(
        self, *, trigger_balance: float, recharge_amount: float
    ) -> dict[str, object]:
        self.recharge_calls.append(
            {"trigger_balance": trigger_balance, "recharge_amount": recharge_amount}
        )
        return {"enabled": True}

    def send_email(self, *, to: str, subject: str, text: str) -> dict[str, object]:
        self.emails.append({"to": to, "subject": subject, "text": text})
        return {"message_id": "msg-order-42"}


def test_low_balance_keeps_order_handoff_moving_and_notifies_buyer() -> None:
    gateway = RecordingGateway(balance=8.0)
    request = OrderHandoffRequest(
        order_id="order-42",
        seller_asset=SellerAsset(
            sku="poster-blue",
            title="Blue shop poster",
            fulfillment_reference="fulfillment-93",
        ),
        buyer_update=BuyerUpdate(
            buyer_id="buyer-7",
            email="buyer@example.com",
            delivery_note="Leave at the front desk",
        ),
        trigger_balance=10.0,
        recharge_amount=25.0,
    )

    result = OrderHandoffService(gateway).handoff(request)

    assert result.state == "handed_off"
    assert result.recharge_requested is True
    assert result.notification_message_id == "msg-order-42"
    assert gateway.recharge_calls == [
        {"trigger_balance": 10.0, "recharge_amount": 25.0}
    ]
    assert gateway.emails[0]["to"] == "buyer@example.com"


def test_healthy_balance_hands_off_without_recharge_message() -> None:
    gateway = RecordingGateway(balance=30.0)
    request = OrderHandoffRequest(
        order_id="order-43",
        seller_asset=SellerAsset(
            sku="mug-green",
            title="Green shop mug",
            fulfillment_reference="fulfillment-94",
        ),
        buyer_update=BuyerUpdate(
            buyer_id="buyer-8",
            email="buyer2@example.com",
            delivery_note="Ring the bell",
        ),
        trigger_balance=10.0,
        recharge_amount=25.0,
    )

    result = OrderHandoffService(gateway).handoff(request)

    assert result.state == "handed_off"
    assert result.recharge_requested is False
    assert gateway.recharge_calls == []
    assert gateway.emails == []

