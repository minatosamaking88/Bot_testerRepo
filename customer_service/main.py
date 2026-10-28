from collections.abc import Sequence

from fastapi import FastAPI, HTTPException

from customer_service.models import Customer


def create_app(customers: Sequence[Customer] | None = None) -> FastAPI:
    seeded_customers = (
        customers
        if customers is not None
        else [
            Customer(id=1, name="Ava Patel"),
            Customer(id=2, name="Marcus Chen", status="suspended"),
            Customer(id=3, name="Sofia Reyes"),
        ]
    )

    app = FastAPI(
        title="Customer Service",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.customers = {customer.id: customer for customer in seeded_customers}

    @app.get("/customers", response_model=list[Customer])
    async def list_customers() -> list[Customer]:
        return list(app.state.customers.values())

    @app.get("/customers/{customer_id}", response_model=Customer)
    async def get_customer(customer_id: int) -> Customer:
        customer = app.state.customers.get(customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer

    return app


app = create_app()
