from typing import Literal

from pydantic import BaseModel, Field

CustomerStatus = Literal["active", "suspended"]


class CustomerSummary(BaseModel):
    id: int
    name: str
    status: CustomerStatus = "active"


class CreateOrderRequest(BaseModel):
    customer_id: int = Field(gt=0)


class OrderRecord(BaseModel):
    id: str
    customer_id: int


class OrderResponse(BaseModel):
    id: str
    customer_id: int
    customer_name: str
