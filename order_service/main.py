import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import ValidationError

from order_service.models import (
    CreateOrderRequest,
    CustomerSummary,
    OrderRecord,
    OrderResponse,
)

logger = logging.getLogger(__name__)
DEFAULT_CUSTOMER_SERVICE_URL = "http://127.0.0.1:4174"
CUSTOMER_SERVICE_TIMEOUT_SECONDS = 2.0


def create_app(
    customer_service_url: str | None = None,
    customer_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    base_url = customer_service_url or os.getenv(
        "CUSTOMER_SERVICE_URL", DEFAULT_CUSTOMER_SERVICE_URL
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=CUSTOMER_SERVICE_TIMEOUT_SECONDS,
            transport=customer_transport,
        ) as client:
            app.state.customer_client = client
            yield

    app = FastAPI(
        title="Order Service",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.orders: dict[str, OrderRecord] = {}

    def get_customer_client(request: Request) -> httpx.AsyncClient:
        return request.app.state.customer_client

    async def fetch_customer(
        customer_id: int,
        client: httpx.AsyncClient,
    ) -> CustomerSummary | None:
        try:
            response = await client.get(f"/customers/{customer_id}")
        except httpx.RequestError as exc:
            logger.exception("Customer service request failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Customer service unavailable",
            ) from exc

        if response.status_code == status.HTTP_404_NOT_FOUND:
            return None

        if response.is_error:
            logger.warning("Customer service returned HTTP %s", response.status_code)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Customer service unavailable",
            )

        try:
            return CustomerSummary.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            logger.exception("Customer service returned an invalid response")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Customer service returned an invalid response",
            ) from exc

    CustomerClient = Annotated[
        httpx.AsyncClient,
        Depends(get_customer_client),
    ]

    @app.post(
        "/orders",
        response_model=OrderResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_order(
        order_request: CreateOrderRequest,
        client: CustomerClient,
    ) -> OrderResponse:
        customer = await fetch_customer(order_request.customer_id, client)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        if customer.status == "suspended":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Orders cannot be created for suspended customers",
            )

        order = OrderRecord(
            id=str(uuid4()),
            customer_id=customer.id,
        )
        app.state.orders[order.id] = order
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            customer_name=customer.name,
        )

    @app.get("/orders/{order_id}", response_model=OrderResponse)
    async def get_order(
        order_id: str,
        client: CustomerClient,
    ) -> OrderResponse:
        order = app.state.orders.get(order_id)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        customer = await fetch_customer(order.customer_id, client)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )

        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            customer_name=customer.name,
        )

    return app


app = create_app()
