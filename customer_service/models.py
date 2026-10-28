from typing import Literal

from pydantic import BaseModel

CustomerStatus = Literal["active", "suspended"]


class Customer(BaseModel):
    id: int
    name: str
    status: CustomerStatus = "active"
