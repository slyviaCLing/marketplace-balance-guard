from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .order_handoff import OrderHandoffRequest, OrderHandoffResult, OrderHandoffService

app = FastAPI(title="Marketplace balance guard")


@app.post("/orders/handoff", response_model=OrderHandoffResult)
def handoff_order(request: OrderHandoffRequest) -> OrderHandoffResult:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")

    client = InfraiClient(api_key)
    try:
        return OrderHandoffService(client).handoff(request)
    except InfraiError as exc:
        status_code = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    finally:
        client.close()

