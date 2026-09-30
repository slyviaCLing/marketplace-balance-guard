from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class SellerAsset(BaseModel):
    sku: str
    title: str
    fulfillment_reference: str


class BuyerUpdate(BaseModel):
    buyer_id: str
    email: str
    delivery_note: str


class OrderHandoffRequest(BaseModel):
    order_id: str
    seller_asset: SellerAsset
    buyer_update: BuyerUpdate
    trigger_balance: float = Field(gt=0)
    recharge_amount: float = Field(gt=0)


class OrderHandoffResult(BaseModel):
    order_id: str
    fulfillment_reference: str
    state: str
    recharge_requested: bool
    notification_message_id: str | None = None


@dataclass
class OrderHandoffService:
    infrai: Any

    def handoff(self, request: OrderHandoffRequest) -> OrderHandoffResult:
        current_balance = float(self.infrai.balance()["balance"])
        recharge_requested = current_balance <= request.trigger_balance
        message_id: str | None = None

        if recharge_requested:
            self.infrai.configure_autorecharge(
                trigger_balance=request.trigger_balance,
                recharge_amount=request.recharge_amount,
            )
            email = self.infrai.send_email(
                to=request.buyer_update.email,
                subject=f"Order {request.order_id} is moving to fulfillment",
                text=(
                    f"Your update for {request.seller_asset.title} is recorded. "
                    "The account recharge policy has been activated and the order handoff continues."
                ),
            )
            message_id = str(email["message_id"])

        return OrderHandoffResult(
            order_id=request.order_id,
            fulfillment_reference=request.seller_asset.fulfillment_reference,
            state="handed_off",
            recharge_requested=recharge_requested,
            notification_message_id=message_id,
        )
